from chalice import Chalice
import requests
import os
import json
import boto3
from base64 import b64decode
FB_BASE_URL = 'https://graph.facebook.com/v2.8'
app = Chalice(app_name='social-media-scraper')
USER_ID = 'AnthonyBourdain'


@app.route('/')
def index():
    try:
        encrypted_fb_id = os.environ['APP_ID']
        decrypted_fb_id = boto3.client('kms').decrypt(CiphertextBlob=b64decode(encrypted_fb_id))['Plaintext']
        encrypted_fb_secret = os.environ['APP_SECRET']
        decrypted_fb_secret = boto3.client('kms').decrypt(CiphertextBlob=b64decode(encrypted_fb_secret))['Plaintext']
    except KeyError as e:
        import ConfigParser
        config_parser = ConfigParser.ConfigParser()
        config_parser.readfp(open('.config'))
        decrypted_fb_id = config_parser.get('fb', 'id')
        decrypted_fb_secret = config_parser.get('fb', 'secret')

    payload = {
        'client_id': decrypted_fb_id,
        'client_secret': decrypted_fb_secret,
        'grant_type': 'client_credentials'
    }
    response = requests.get(
        'https://graph.facebook.com/oauth/access_token',
        params=payload
    )
    fb_access_token = response.text.split('=')[-1]
    recent_fb_photos = get_recent_fb_photos(fb_access_token)
    return {'photos': recent_fb_photos}


def get_recent_fb_photos(fb_access_token):
    photos = []
    payload = {
        'type': 'uploaded',
        'access_token': fb_access_token,
        'fields': 'place'
    }
    try:
        response = requests.get(
            '{}/{}/photos'.format(FB_BASE_URL, USER_ID),
            params=payload
        )
        response_dict = response.json()
        harvest_dict_for_photos(photos, response_dict, fb_access_token)

        while len(photos) < 20 and 'next' in response_dict['paging']:
            response = requests.get(response_dict['paging']['next'])
            response_dict = response.json()
            harvest_dict_for_photos(photos, response_dict, fb_access_token)
    except Exception as e:
        print(e)
    return photos


def harvest_dict_for_photos(photo_list, response_dict, fb_access_token):
    for photo in response_dict['data']:
        if 'place' in photo.keys():
            image_url_payload = {
                'access_token': fb_access_token,
                'fields': 'images'
            }

            response = requests.get(
                '{}/{}'.format(FB_BASE_URL, photo['id']),
                params=image_url_payload
            )
            response_dict = response.json()
            image_url = response_dict['images'][0]['source']
            photo_list.append({
                'caption': photo['place']['name'],
                'location': photo['place']['location'],
                'image_url': image_url
            })
