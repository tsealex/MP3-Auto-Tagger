
from utils import * 
from resources import Album, Track

import re
import random

from heapq import *

import discogs_client

MAX_RESULT_PAGES = 2
MAX_ALBUM_LIST_SIZE = 8
DISCOGS_USER_TOKEN = 'yXfAPFdRdjVNPVoKiLXIYSCHjzNUcylClawDJWif'

SEARCHER_DEBUGGING = True

DEBUG_SRC = 'searcher'

dc = discogs_client.Client('Tagger/0.1', user_token=DISCOGS_USER_TOKEN)

def search(release_title, artist_name='', track_count=None, track=False):
	'''
	Search on discogs through its API and construct an album for a number of satisfied releases, specified
	by the value of MAX_ALBUM_LIST_SIZE
	Args:
		artist_name - name of the artist to be searched
		release_title - title of an album / a song
		track_count - number of tracks in the release (indicate whether track count should be considered)
		track - whether this is a search for a track
	Return:
		a list of Album with matched title and artist, constructed from the discogs release objects
	'''
	if not track: release_title = remove_edition(release_title)

	query = artist_name + ' - ' + release_title if artist_name else release_title

	log('search {}'.format(query))
	if not track:
		results = dc.search(query, title=release_title, artist=artist_name, type='release') \
			if artist_name else dc.search(query, title=release_title, type='release')
	else: results = dc.search(query, artist=artist_name, type='release') if artist_name else dc.search(query, type='release')

	debug(DEBUG_SRC, 'result pages returned: ' + str(results.pages))
	
	albums, pq, skip_count = [], [], 0
	for i in range(0, min(MAX_RESULT_PAGES, results.pages)):
		for release in results.page(i):

			if skip_count > MAX_ALBUM_LIST_SIZE / 2: break # TODO: make this configurable

			request_failed = True
			while request_failed: # TODO: make this configurable
				try:
					score = jw.get_sim_score(query, release.title)
					debug(DEBUG_SRC, 'examining {}: {}%'.format(release.title, \
					 	(int(score * 10000) / 100.0)))				
					'''
					if score < 0.5 or len(release.tracklist) == 0 or \
						parse_position(release.tracklist[0].position) == (None, None): 
						skip_count += 1
						debug(DEBUG_SRC, 'album skipped')
						continue
					'''
					request_failed = False

				except discogs_client.exceptions.HTTPError:
					err('too many requests made to discogs')
					backoff()

			if score < 0.5:
				skip_count += 1
				continue

			if track_count:
				tmp = len(release.tracklist)
				score *= 1.0 - abs(track_count - tmp) / float(max(track_count, tmp))

			if len(pq) < MAX_ALBUM_LIST_SIZE: 
				skip_count = 0
				heappush(pq, (score, random.random(), release))
				debug(DEBUG_SRC, 'album added to the queue')
			elif score > pq[0][0]:
				skip_count = 0
				heapreplace(pq, (score, random.random(), release))
				debug(DEBUG_SRC, 'album added to the queue')
			else:
				skip_count += 1
				debug(DEBUG_SRC, 'album skipped')

	log('finished examining search results')

	for release in pq:
		request_failed = True
		while request_failed:
			try:
				release = release[2]
				extra = {} if not release.labels else { 'label': release.labels[0].name }
				albums.append(Album(release.title, construct_artist_list(release.artists), \
					construct_tracklist(release), release.genres, release.year, extra))
				request_failed = False
			except discogs_client.exceptions.HTTPError: 
				tmp = random.random() * 2.0
				err('too many requests made to discogs')
				backoff()

	log('{} related albums selected for further processing'.format(len(albums)))
	
	for album in albums: debug(DEBUG_SRC, str(album))

	return albums


def construct_tracklist(release):
	'''
	Given a discogs release object, construct a list of tracks based on its tracklist 
	Args:
		release - a discogs Release object (discogs_client.models.Release)
		album - the album the tracks belong
	Return:
		a list of tracks (Track[])
	'''
	rtn = []
	for track in release.tracklist:
		rtn.append(Track(track.title, parse_position(track.position), \
			construct_artist_list(track.artists), parse_duration(track.duration)))
	return rtn

def construct_artist_list(artists):
	'''
	Given a list of discogs artist objects, construct a list of artist names
	Args:
		artists - a list of discogs artist objects (discogs_client.models.Artist)
	Return:
		a list of artist names (str[])
	'''
	rtn = []
	for artist in artists:
		rtn.append(remove_noise_in_artist_name(artist.name))
	return rtn