from __future__ import print_function
from googleapiclient.discovery import build
from httplib2 import Http
from oauth2client import file, client, tools
import requests
import urllib
from io import BytesIO
from pathlib import Path
import redis

r = redis.Redis(host='0.0.0.0', port=6379, db=0, decode_responses=True)


def authorize_with_google():
    store = file.Storage((Path().parent / "auth/google_token.json").resolve().as_posix())
    return store.get()


def get_google_photos_service(google_creds):
    return build('photoslibrary', 'v1',
                 http=google_creds.authorize(Http()),
                 cache_discovery=False,static_discovery=False)


def find_album_on_google(album_title):
    return r.get(album_title)


def create_album_on_google(service, album_title):
    albums = service.albums()
    new_album = albums.create(body={"album": {"title": album_title}}).execute()
    r.set(album_title, new_album.get('id', None))
    return new_album.get("id", None)


def upload_photo_to_google(google_auth, service, album_id, photo_data,
                           photo_title, photo_tags):
    media_items = service.mediaItems()

    url = 'https://photoslibrary.googleapis.com/v1/uploads'
    authorization = 'Bearer ' + google_auth.access_token
    headers = {
        "Authorization": authorization,
        'Content-type': 'application/octet-stream',
        'X-Goog-Upload-File-Name': photo_title,
        'X-Goog-Upload-Protocol': 'raw',
    }

    upload_response = requests.post(url, headers=headers, data=photo_data)
    upload_token = upload_response.text

    if upload_token is not None:
        payload = {
            "albumId": album_id,
            "newMediaItems": [{
                "description": photo_tags,
                "simpleMediaItem": {
                    "uploadToken": upload_token
                }
            }]
        }

        add_photo_req = media_items.batchCreate(body=payload)
        add_photo_resp = add_photo_req.execute()

        return add_photo_resp

def upload_photo_grp_to_google(google_auth, service, album_id, photo_list):
    media_items = service.mediaItems()
  
    url = 'https://photoslibrary.googleapis.com/v1/uploads'
    uploaded_photos = {}
    
    if len(photo_list) > 50:
      raise ValueError("Too many items in list.  Limit to max of 50")
    
    for photo in photo_list:
      with open(photo['path'], "rb") as photo_data:
        authorization = 'Bearer ' + google_auth.access_token
        headers = {
            "Authorization": authorization,
            'Content-type': 'application/octet-stream',
            'X-Goog-Upload-File-Name': photo['file_name'],
            'X-Goog-Upload-Protocol': 'raw',
        }
      
        upload_response = requests.post(url, headers=headers, data=photo_data)
        upload_token = upload_response.text
        
        if upload_token is not None:
          uploaded_photos[upload_token] = photo

    mediaItems = []
    for token, photo in uploaded_photos.items():
      mItem = {
                "description": photo['description'][:999], #Need to limit to < 1000
                "simpleMediaItem": {
                    "uploadToken": token
                    # Optional  "fileName" : '
                }
            }
      mediaItems.append(mItem)
      
    payload = {
        "albumId": album_id,
        "newMediaItems": mediaItems
    }

    add_photo_req = media_items.batchCreate(body=payload)
    add_photo_resp = add_photo_req.execute()

    #Process success and flag in DB
    success_list = []
    for ul_item in add_photo_resp['newMediaItemResults']:
      if ul_item['mediaItem'] is not None:
        photo = uploaded_photos[ul_item['uploadToken']]
        photo['g_id'] = ul_item['mediaItem']['id']
        success_list.append(photo)

    return add_photo_resp, success_list

def get_photo_from_flickr(photo_url):
    photo_url_obj = urllib.request.urlopen(photo_url)
    return BytesIO(photo_url_obj.read())



