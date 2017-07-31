
###
# TODO: document this file
###
import atexit
import sys
import os
import re
import time
import requests
import argparse
from urllib import parse, request

from utils import *

from lxml import etree
import PIL
from PIL import Image
import json

PROFILE_DIR = 'genius/'
TMP_DIR = 'genius/tmp/'
UPDATE_PEROID = 3 # update every three days
ALWAYS_UPDATE = False
MAX_RETRY_NUM = 3
TARGET_SIZE = 500, 500


def make_request(_type, url):
	log('request sent: {}'.format(url))
	return requests.request(_type, url) 

API_ERR_COUNT = 0 # keep track of # of consecutivee rrors related to the API connection
API_ERR_THRESHOLD = 12

FORMAT_ERR_COUNT = 0 # keep track of # of consecutive errors related to the API response's JSON format
FORMAT_ERR_THRESHOLD = 4 # terminate the program if five consecutive errors occured (implying the JSON format has likely changed)

def create_artist_profile(artist):
	log('constructing new artist profile')
	success, retry = False, 0
	artist_url = get_artist_url(artist)
	global API_ERR_COUNT
	while not success and retry < MAX_RETRY_NUM:
		if retry == 0: log('obtaining artist id')
		else: log('re-attempting')
		try: 
			artist_id = get_artist_id(artist_url)
			success = True
			API_ERR_COUNT = 0
		except: 
			err('failed')
			retry += 1
			API_ERR_COUNT += 1
			backoff()

	if not success: return None
	else: success, retry = False, 0
	log('done')

	while not success and retry < MAX_RETRY_NUM:
		if retry == 0: log('obtaining album list')
		else: log('re-attempting')
		try: 
			albums = get_album_list(artist_id)
			success = True
			API_ERR_COUNT = 0
		except: 
			err('failed')
			retry += 1
			API_ERR_COUNT += 1
			backoff()

	if not success: return None
	log('done')

	profile = {'artist_id': artist_id, 'albums': albums}
	try:
		filename = get_filename(artist)
		log('saving profile'.format(filename))
		with open(filename, 'w') as file: file.write(json.dumps(profile))
		FORMAT_ERR_COUNT = 0
		log('done')
	except: 
		FORMAT_ERR_COUNT += 1
		err('unable to save prfile file: ' + filename)
	return profile

def get_artist_profile(artist):
	log('loading artist profile')
	filename = get_filename(artist)
	update = not os.path.exists(filename) or os.path.getmtime(filename) + UPDATE_PEROID * 86400 < time.time() or ALWAYS_UPDATE
	if not update: 
		try: profile = json.loads(open(filename, 'r').read())
		except: 
			err('unable to parse profile file: ' + filename)
			update = True
	if update: profile = create_artist_profile(artist)
	return profile

def get_filename(artist):
	return PROFILE_DIR + get_artist_url(artist) + '.json'

def get_artist_url(artist):
	return artist.replace(' ', '-').lower()

def get_artist_id(artist_url):
	url = 'https://genius.com/artists/' + artist_url
	tree = etree.HTML(make_request('get', url).content)
	id_link = tree.xpath('/html/head/link[@rel="alternate"]')[0].get('href')
	return id_link.split('/')[-1]

def get_album_list(artist_id):
	url, pnum = 'https://genius.com/api/artists/{}/albums?page='.format(artist_id), 1
	albums = []
	while pnum is not None:
		res = make_request('get', url + str(pnum))
		print('ok ar')
		tmp = json.loads(res.content.decode('utf-8'))['response']
		for album in tmp['albums']:
			if not album['cover_art_url'] or 'default_cover_art' in album['cover_art_url']: continue
			albums.append({
				'name': album['name'],
				'cover_art_url': album['cover_art_url'],
				'year': None if not album['release_date_components'] else album['release_date_components']['year'] 
			})
		pnum = tmp['next_page']
	return albums

def dl_image(url):
	res = make_request('get', url)
	filename = TMP_DIR + url.split('/')[-1]
	with open(filename, 'wb') as file:
		try: file.write(bytes(res.content))
		except: return None
	image = Image.open(filename)
	w = image.size[0]
	h = image.size[1]
	ratio = float(min(w, h)) / float(max(w, h))
	if ratio <= 0.95 or w < 0.96 * TARGET_SIZE[0] or h < 0.96 * TARGET_SIZE[1]:
		os.remove(filename)
		return None
	if w == TARGET_SIZE[0] == h: return filename
	image = image.resize(TARGET_SIZE, PIL.Image.ANTIALIAS)
	image.save(filename)
	return filename


def get_album_covers(artist_name, album_title):
	log('processing album cover requests')
	profile, rtn = get_artist_profile(artist_name), None
	if API_ERR_COUNT >= API_ERR_THRESHOLD:
		err('cover art server has changed its web interface / is currently offline')
		return rtn, True
	elif FORMAT_ERR_COUNT >= FORMAT_ERR_THRESHOLD:
		err('cover art server has changed its API')
		return rtn, True
	if not profile:
		err('unable to obtain artist info for ' + artist_name)
		return rtn, False
	else: log('retrieving album cover for ' + album_title)
	album_title = album_title.lower()
	max_score, target_url = -1, None
	for prof_album in profile['albums']:
		score = jw.get_sim_score(prof_album['name'].lower(), album_title)
		if score == 1.0:
			target_url = prof_album['cover_art_url']
			break
		elif score >= 0.8 and score > max_score:
			target_url = prof_album['cover_art_url']
			max_score = score
	if not target_url: rtn = None
	else:
		try: rtn = dl_image(target_url)
		except: pass
	if rtn: log('album cover downloaded')
	else: err('no suitable album cover for {}\'s {}'.format(artist_name, album_title))
	return rtn, False



# # # # # # # # # # # # # # # # # # # # # # # # # # # #
# single api: https://genius.com/api/artists/16698/songs?page=1&sort=release_date
# # # # # # # # # # # # # # # # # # # # # # # # # # # #
# response
# -> songs[]
#    -> header_image_url
#    -> title
#    -> path
# -> next_page (int)
# # # # # # # # # # # # # # # # # # # # # # # # # # # #
# album api: https://genius.com/api/artists/16698/albums?page=1
# # # # # # # # # # # # # # # # # # # # # # # # # # # # 
# response 
# -> albums[]
#    -> name
#    -> cover_art_url
#    -> release_date_components
#       -> year (int)
# -> next_page (int)
# # # # # # # # # # # # # # # # # # # # # # # # # # # #
# artist: https://genius.com/artists/ + artist_name.replace(' ', '-')
# artist id: /html/head/link[@rel="alternate"] -> getAttribute('href') -> split('/')[-1]

'''
CHROMEDRIVER_PATH = 'chromedriver.exe'

options = webdriver.ChromeOptions()
# options.add_argument('headless')

driver = webdriver.Chrome(CHROMEDRIVER_PATH, chrome_options=options)
'''
'''
argparser = argparse.ArgumentParser(description='Retrieve album cover info for specified artists.')
argparser.add_argument('artists', metavar='Artist', type=str, nargs='+', help='an artist to be processed.')

args = argparser.parse_args()

for artist in args.artists:
	prof = get_artist_profile(artist)
	if not prof: continue
	print('')
	print(prof['artist_id'])
	for album in prof['albums']:
		print(album)
	print('')
'''
'''
alb_list = {
	'Metallica': ['Metallica', 'Reload', '...And Justice for All'],
	'The Strokes': ['Is This It', 'Angles'],
	'Yeah Yeah Yeahs': ['Fever To Tell']
}

get_album_covers(alb_list)
'''