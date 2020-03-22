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
        try:
            photo_url = photo.getPhotoFile("Original")
        except flickr_api.flickrerrors.FlickrServerError as e:
            print(f"Couldn't get original size URL {e}. Skipping")
            continue
        except flickr_api.flickrerrors.FlickrError as e:
            print(f"Couldn't get original size URL {e}. Skipping")
            continue

        info = {
            "id": photo['id'],
            "title": photo['title'],
            "photoUrl": photo_url,
            "processed": False,
            "description": photo.getInfo()['description'],
            "tags": photo.getTags(),
            "taken": photo.getInfo()['taken']
        }

        print(f"info {info}")

        r.set(photo_key(photo), json.dumps(info))

        photo_counter += 1
