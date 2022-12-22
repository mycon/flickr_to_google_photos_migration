from __future__ import print_function
import flickr_api
import pickle
import os
from pathlib import Path
import redis
import json

r = redis.Redis(host='redis', port=6379, db=0, decode_responses=True)
flickr_api.set_keys(api_key=os.environ['FLICKR_API_KEY'], api_secret=os.environ['FLICKR_API_SECRET'])

flickr_api.set_auth_handler((Path.cwd() / "auth" / "flickr_credentials.dat").resolve().as_posix())
user = flickr_api.test.login()

photo_counter = 0

def photo_key(photo):
    return f"photo-{photo['id']}"

photo_walker = flickr_api.Walker(user.getPhotos)
for photo in photo_walker:

    print(f"photo: {photo_counter} - {photo.getInfo()}")

    if r.get(photo_key(photo)) is None:
        retry = 50
        while(retry > 0):
          try:
              photo_url = photo.getPhotoFile("Original")
              photo_description = photo.getInfo()['description']
              photo_tags = photo.getTags()
              photo_taken = photo.getInfo()['taken']
              retry = -1
          except flickr_api.flickrerrors.FlickrServerError as e:
              print(f"Couldn't get original size URL {e}. Skipping")
              retry -= 1
              
          except flickr_api.flickrerrors.FlickrError as e:
              print(f"Couldn't get original size URL {e}. Skipping")
              retry -= 1
              
        if retry == 0:
          print(f"Max retries reached.  Skipping {photo_key(photo)}.")
          continue

        info = {
            "id": photo['id'],
            "title": photo['title'],
            "photoUrl": photo_url,
            "processed": False,
            "description": photo_description,
            "tags": photo_tags,
            "taken": photo_taken
        }

        print(f"info {info}")
        
        try:
          if isinstance(info['tags'], list):
            info['tags']=''
          r.set(photo_key(photo), json.dumps(info))
        except:
          import pdb; pdb.set_trace()

        photo_counter += 1
