from migration_util import *
from pathlib import Path
from requests.exceptions import RequestException
from googleapiclient.errors import HttpError
import redis
import sys, os, pickle
import pdb

from optparse import OptionParser



r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)


def read_meta_txt(file):
    meta_fields = ['id','title','description','public','friends','family','taken','tags']
    
    file = file + '.txt'
    meta = {}
    if os.path.exists(file):
      with open(file, "r") as fh:
        lines = fh.readlines()
        id = None
        for line in lines:
          if line[0] == '[':
            continue
          key_val = [x.strip() for x in line.split('=')]
          if key_val[0] in meta_fields and len(key_val) >= 2:
            meta[key_val[0]] = ''.join(key_val[1::])
            id = key_val[0]
          else:
            meta[id] += line
            #pdb.set_trace()
    else:
      #for field in meta_fields:
      #  meta[field] = ''
      meta = {'id':os.path.basename(file).split('.')[0],
               'title':'',
               'description':'',
               'public':'no',
               'friends':'no',
               'family':'no',
               'taken':'',
               'tags':''
              }
    return meta


def traverse_path(rootdir):
    skip_extensions = ['txt', 'stamp', 'db']
    #Valid media types are specified here, but I had a smaller list
    # https://developers.google.com/photos/library/guides/upload-media
    media_extensions = ['jpg', 'mov', 'gif', 'png']
    auto_upload_paths = ['2005','2006','2007','2008','2009','2010','2011','2012','2013','2014','2015','2016','2017','2018','2019','2020','2021','2022','2023','Auto sync','Auto Upload','Pictures to Upload','Pictures to Upload_1_']
    
    file_list = []
    print("Reading file structure, please be patient")
    for dirpath, dirs, files in os.walk(rootdir):
      for file in files:
        extension = file.split('.')[-1]
        
        
        if extension in skip_extensions:
          continue
          
        full_file = os.path.join(dirpath, file)
        if not extension in media_extensions:
          print(f"Unknown extension on {full_file}")
          pdb.set_trace()
                  
        meta = read_meta_txt(full_file)
        
        rel_dir_path = os.path.relpath(dirpath,rootdir)
        path = os.path.normpath(rel_dir_path)
        paths = path.split(os.sep)
        album = paths[0]
        paths.append(file)
        if album in auto_upload_paths:
          album = 'Flick_No_Set'
        meta['album'] = album
        meta['path'] = full_file
        meta['file_name'] = file
        meta['db_key'] = '_'.join(paths)
        
        #print(meta)
        file_list.append(meta)
        
        if (len(file_list) %1024) == 0:
          print(f"Currently {len(file_list)} files")
    return file_list

def submit_group(google_creds, service, photo_list, start_count, total_photos):
    album_title = photo_list[0]['album']

    with r.lock("find-album"):
      album_id = find_album_on_google(album_title)
      if album_id is None:
        album_id = create_album_on_google(service, album_title)

    print(f"Uploading {start_count} of {total_photos} to '{album_title}'")
    try:
      add_photo_resp, success_list = upload_photo_grp_to_google(google_creds, service, album_id, photo_list)
    except Exception as e:
      print(f"Upload Error!")
      print(e)
      return

    with r.lock("find-photo"):
      for photo in success_list:
        r.set(photo['db_key'], photo['g_id'])
        
      #Debug prints for success/failures
      if 0:
        for photo in photo_list:
          if r.get(photo['db_key']) is None:
            print(f"Failed: {photo['file_name']}")
          else:
            #print(f"Success: {photo['file_name']}")
            pass


def send_to_gphoto(file_list):
    google_creds = authorize_with_google()
    service = get_google_photos_service(google_creds)
    
    prev_album = None
    photo_group = []
    photo_count = 0
    for photo in file_list:
      photo_count += 1
      if (photo_count % 1024) == 0:
        print(f"Processed {photo_count} photos")

      if len(photo_group) == 50 or (prev_album and prev_album != photo['album']):
        #We have a full group, so submit it
        if len(photo_group) > 0:
          submit_group(google_creds, service, photo_group, photo_count, len(file_list))
        prev_album = photo['album']
        photo_group = []
      
      with r.lock("find-photo"):
        if r.get(photo['db_key']) is None:
          #Temp fix for meta parse error
          if not 'description' in photo:
            photo['description']=''
          photo_group.append(photo)
      
    if len(photo_group) > 0:
      submit_group(google_creds, service, photo_group, photo_count, len(file_list))

          
if __name__ == '__main__':

    note = '''
    It's expected that prior to running this script you've
       1.) created auth/google_credentials.json
       2.) run oauth.py to authenticate
       3.) run create_album_cache.py
       
    This file will create 'parsed_photo_tree.txt' in the cwd which can be used with the -p option to skip re-parsing the photo tree
    
    If you want to pause, ctrl+c just after an "Uploading x of y" print
'''

    parser = OptionParser()
    parser.add_option("-r", "--rootpath", dest="rootpath",
                      help="Root path to start photo search", metavar="FILE")
    parser.add_option("-p", "--prased_tree", dest="pickle_file",
                      help="Pickle File from the parsed photo tree to avoid reparsing on retries")
    parser.add_option("-q", "--quiet",
                      action="store_false", dest="verbose", default=True,
                      help="don't print status messages to stdout")

    (options, args) = parser.parse_args()

    if not options.rootpath or not os.path.exists(options.rootpath):
      pdb.set_trace()
      sys.exit("Invalid 'rootpath' specified")
      
    print(note)
    print(f"rootpath = {options.rootpath}")
    
    if not options.pickle_file:
      file_list = traverse_path(options.rootpath)
      if len(file_list)>0:
        print(f"Writing picklefile 'parsed_photo_tree.txt'")
        with open('parsed_photo_tree.txt', 'wb') as fp:
          pickle.dump(file_list, fp)
    else:
      with open(options.pickle_file, 'rb') as fp:
        file_list = pickle.load(fp)
    
    send_to_gphoto(file_list)
    
    
    
