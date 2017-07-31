
from mutagen.mp3 import MP3
from mutagen.id3 import ID3, APIC, TYER
from mutagen.easyid3 import EasyID3

from utils import *

import math

DEBUG_SRC = 'resources'

class Album:

	def __init__(self, title=None, artists=[], tracklist=[], genres=[], year=None, extra={}):
		self.title = title # album title (str)
		self.year = year # release year (str)
		if artists is not None: self.artists = artists # a list of album artists (str[])
		if tracklist is not None: self.tracklist = tracklist # a list of tracks belong to this album (Track[])
		if genres is not None: self.genres = genres # a list of genres that describe this album (str[])
		self.extra = extra # extra info in (attribute, value) format ({str: str})
		self.cover = None # file path to the cover art image of this album (str)

		for track in self.tracklist: track.album = self

	def add_cover(self, file):
		'''
		Add cover to this album
		Args:
			file - the filepath to the image file being added (str)
		'''
		self.cover = file

	@staticmethod
	def find_best_album_match(src_album, albums, threshold=0.8):
		'''
		Given an album, find the most similar album from a given list of albums
		Args:
			src_album - the album for which we find the most similar album in the list (Album)
			albums - a list of albums to be inspected (Album[])
			threshold - similarity threshold for every mapping in the returned mapping to exist
		Retrun:
			the most similar album (Album), None if albums is empty
			the mapping between tracks from two albums ((int, int)[]), None if albums is empty
			the similarity score between src_album and the most similar album (float), -1 if albums is empty

		[NOTE: subject to change in the future]
		'''
		max_score, best_album, best_mapping, best_matrix = -1, None, None, None

		for album in albums:
			sim_matrix = []
			# construct similarity matrix between two tracklists
			for track1 in src_album.tracklist:
				tmp = []
				for track2 in album.tracklist:
					tmp.append(Track.compare_tracks(track1, track2))
				sim_matrix.append(tmp)
			# find the mapping that maximize the similarity score

			score, mapping = maximize_assignment(sim_matrix)

			debug(DEBUG_SRC, 'optimal mapping in {} computed ({}%)'.format(str(album),\
				get_percentage(score)))

			if score > max_score:
				debug(DEBUG_SRC, 'update the most similar album (old: {}, new: {})'.format( \
					get_percentage(max_score), get_percentage(score)))
				best_album = album
				max_score = score
				best_mapping = mapping
				best_matrix = sim_matrix
		
		if best_mapping:
			tmp = []
			log('most similar album: {} ({}%)'.format(str(best_album), get_percentage(max_score)))
			debug('tagger', 'optimal mapping: ' + str(best_mapping))

			debug(DEBUG_SRC, '{} tracklist:'.format(str(best_album)))
			for track in best_album.tracklist: 
				debug(DEBUG_SRC, str(track))

			for i, j in best_mapping:
				if best_matrix[i][j] > threshold or src_album.tracklist[i].title in best_album.tracklist[j].title:
					tmp.append((i, j))
			best_mapping = tmp

		return best_album, best_mapping, max_score

	def __str__(self):
		if not self.title: return '"NO ALBUM INFO"'
		rtn = get_artist_str(self.artists, ' &')
		rtn = rtn + ' - ' + self.title if self.artists else self.title
		return '"' + rtn + '"'

class Track:

	def __init__(self, title, position=(None, None), artists=[], duration=None, filepath=None):
		self.title = title # track title (str)
		self.position = position # track position in (disc #, track #) format ((int, int))
		self.album = None # album of this track (Album)
		self.artists = artists # list of performers for this track (str[])
		self.duration = duration # duration of this track in seconds (float)
		self.filepath = filepath # file path to this track's mp3 file (str)
		self.changed = False # whether apply_track_diff has been called

	def save(self, refresh=True):
		'''
		Apply the id3 tag changes to the mp3 file
		Args: 
			refresh - whether the original id3 tag info will be cleared out (bool)
		Return: 
			True if tag info being saved, else False (bool)
		'''
		if not self.filepath: return False
		audio = MP3(self.filepath, ID3=EasyID3)
		album = self.album

		if refresh:
			log('old file info cleared: ' + self.filepath)
			audio.delete()

		# artist name(s)
		if self.artists: audio['artist'] = get_artist_str(self.artists)

		if self.position and self.position[1]:
			if self.position[0]: audio['discnumber'] = str(self.position[0])
			audio['tracknumber'] = str(self.position[1])

		if self.title: audio['title'] = self.title

		if self.album:
			if album.artists:
				tmp = get_artist_str(album.artists)
				audio['albumartist'] = tmp
				if not self.artists: audio['artist'] = tmp
			if album.title: audio['album'] = album.title
			if album.genres: audio['genre'] = get_genre(album.genres) # only pick the first genre

		
		audio.save()

		audio = MP3(self.filepath, ID3=ID3)
		if album.year: audio['TYER']= TYER(encoding=3, text=u'{}'.format(album.year)) # mutagen bug
						
		if album.cover:
			audio['TDRC'] = APIC(3, 'image/jpeg', 3, 'Cover', open(album.cover, 'rb').read())
			log('added new cover art')
		
		audio.save(self.filepath, v2_version=3)

		return True

	def apply_track_diff(self, track):
		'''
		Copy the attribute values of { position, title, artists, album } from track to this track
		Args:
			track - the track to be copied from
		'''
		self.title = track.title
		self.position = track.position
		self.artists = track.artists
		self.album = track.album
		self.changed = True

	@staticmethod
	def compare_tracks(track1, track2, tracknum=False):
		'''
		Compute the similarity score between two tracks based on their titles/track numbers and duration
		Args: 
			track1 - the track to be compared (Track)
			track2 - another track to be compared (Track)
			tracknum - the comparison bases on the track numbers instead of titles
		Return: 
			the similarity score between two tracks between 0 and 1 (float)

		[NOTE: subject to change in the future]
		'''
		if not track1 or not track2: return 0.0
		dur1, dur2 = track1.duration, track2.duration
		dur_sim = 1.0 if not dur1 or not dur2 else 1.0 - (abs(dur1 - dur2)) / float(max(dur1, dur2))
		if not tracknum:
			# three percent penalty for unmatched track number
			pen_mod = 0.0 if not track1.position[1] and track1.position[1] == track2.position[1] else 0.03
			# the penalty increases by another 10% if the track2 position is missing
			pen_mod += 0.10 if not track2.position[1] else 0.0
			return max(jw.get_sim_score(track1.title.lower(), track2.title.lower()) * dur_sim - pen_mod, 0.0)
		else: return 1.0 * dur_sim if track1.position[1] == track2.position[1] else 0.0

	def __str__(self):
		rtn = str(self.position[1]) + '. ' if self.position[1] else '' 
		rtn = str(self.position[0]) + '-' + rtn if self.position[0] else rtn
		rtn += self.title
		return '"' + rtn + '"'


