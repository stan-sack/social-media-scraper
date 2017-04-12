from chalice import Chalice
# from requests import async
import requests
import grequests
import os
import json
import boto3
from base64 import b64decode
FB_BASE_URL = 'https://graph.facebook.com/v2.8'
app = Chalice(app_name='social-media-scraper')
USER_ID = 'AnthonyBourdain'


@app.route('/fb/photos', cors=True)
def get_facebook_photos():
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
    response_dict = response.json()
    fb_access_token = response_dict['access_token']
    try:
        recent_fb_photos = get_recent_fb_photos(fb_access_token)
    except Exception as e:
        raise Exception('Error retrieving photos')
    return {'photos': recent_fb_photos}


def get_recent_fb_photos(fb_access_token):
    photos = []
    payload = {
        'type': 'uploaded',
        'access_token': fb_access_token,
        'fields': 'place',
        'limit': 1000
    }
    try:
        response = requests.get(
            '{}/{}/photos'.format(FB_BASE_URL, USER_ID),
            params=payload
        )
        response_dict = response.json()
        while True:
            print('looping')
            for photo in response_dict['data']:
                if 'place' in photo.keys():
                    if 'location' in photo['place'].keys():
                        photos.append({
                            'caption': photo['place']['name'],
                            'location': photo['place']['location'],
                            'image_url': '{}/{}?access_token={}&fields=images'.format(FB_BASE_URL, photo['id'], fb_access_token)
                        })
            if not (len(photos) < 20 and 'next' in response_dict['paging']):
                break
            response = requests.get(response_dict['paging']['next'])
            response_dict = response.json()

        requests_to_send = (grequests.get(photo['image_url']) for photo in photos)
        results_array = grequests.map(requests_to_send)
        for i in range(len(results_array)):
            response_dict = results_array[i].json()
            photos[i]['image_url'] = response_dict['images'][0]['source']
    except Exception as e:
        raise
    return photos
