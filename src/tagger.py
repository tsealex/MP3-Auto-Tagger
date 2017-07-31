
import re
import os, sys, stat, shutil

from utils import * 
from resources import Album, Track
from searcher import search
from scraper import get_album_covers

from mutagen.mp3 import MP3
from mutagen.id3 import ID3
from mutagen.easyid3 import EasyID3

PRE_PROCESS_DIR = 'ready/' # TODO
POST_PROCESS_DIR = 'processed/'
ATTR_LIST = ['artist', 'genre', 'album', 'tracknumber', 'date', 'title', 'albumartist']

def load_tracks():
	'''
	Load tracks from disk
	'''
	albums, tracks = {}, []

	mp3_files = get_all_files(PRE_PROCESS_DIR) 

	# TODO: should be inside a for loop as we traverse through the directory given by PRE_PROCESS_DIR
	for filepath in mp3_files:
		if not load_track(filepath, albums, tracks): log('skipped file due to insufficient track info: ' + filepath)
		else: log('loaded file: ' + filepath)

	# TODO: for loop ends here

	# process tracks in 'albums' first
	covers = {}

	for album_index in albums:
		album = albums[album_index]
		artist_name = get_artist_str(album.artists, '')
		# TODO: change the next line
		track_count = len(album.tracklist) if len(album.tracklist) > 8 else None 
		res_albums = search(album.title, artist_name, track_count)
		best_album, best_mapping, score = Album.find_best_album_match(album, res_albums)

		if not best_album:
			log('no matched album found for ' + album.title)
			continue
		else: pass

		# add cover for the album
		img_file, scrap_err = get_album_covers(best_album.artists[0], best_album.title)
		if scrap_err: break
		# TODO: ask if the user wants to proceed even no album cover can be obtained instead
		elif img_file: best_album.add_cover(img_file)
			

		for i, j in best_mapping:
			log('{} -> {} ({})'.format(str(album.tracklist[i]), str(best_album.tracklist[j]), str(best_album)), 'change')
			# TODO: let user confirm using input()
			album.tracklist[i].apply_track_diff(best_album.tracklist[j])

		for track in album.tracklist:
			if track.changed:
				track.save()
				log('file saved with new changes: ' + track.filepath)
				# move the file to new location and rename it
				new_filepath = construct_filepath(track)
				log('new file path: ' + new_filepath)
				move_file(track.filepath, new_filepath)
				log('file moved')
				track.filepath = new_filepath
			else: tracks.append(track) # else treat it as an individual track

	# TODO: then process tracks in 'tracks'
	album = Album()
	for track in tracks:
		album.tracklist.append(track)
		artist_name = get_artist_str(track.artists, '')
		res_albums = search(track.title, artist_name, track=True)
		# noe bascally copy and paste, may be I should factor the code at some point
		best_album, best_mapping, score = Album.find_best_album_match(album, res_albums)

		if not best_album:
			log('no matched album found for ' + track.title)
			continue
		else: pass

		# add cover for the album
		img_file, scrap_err = get_album_covers(best_album.artists[0], best_album.title)
		if scrap_err: break
		# TODO: ask if the user wants to proceed even no album cover can be obtained instead
		elif img_file: best_album.add_cover(img_file)
			

		for i, j in best_mapping:
			log('{} -> {} ({})'.format(str(album.tracklist[i]), str(best_album.tracklist[j]), str(best_album)), 'change')
			# TODO: let user confirm using input()
			album.tracklist[i].apply_track_diff(best_album.tracklist[j])

		if track.changed:
			track.save()
			log('file saved with new changes: ' + track.filepath)

			# move the file to new location and rename it
			new_filepath = construct_filepath(track)
			log('new file path: ' + new_filepath)
			move_file(track.filepath, new_filepath)
			log('file moved')
			track.filepath = new_filepath

		album.tracklist.clear()


	delete_dir()


def load_track(filepath, albums, tracks):
	'''
	Load a single mp3 file from the disk and construct a corresponding Track object using its ID3 info,
	and link it to a corresponding Album object
	Args:
		filepath - file path to the target mp3 file (str)
		albums - a dictionary mapping (artist name, album title) to an Album object ({(str, str): Album})
		tracks - a list of Track objects created without album info (Track[])
	Return:
		Truw if a new track is loaded, False if a track cannot be loaded or has no info identifying this track
	'''
	audio = MP3(filepath, ID3=EasyID3)
	track_info, duration = {}, audio.info.length

	# extract from the id3 tags
	for attr in ATTR_LIST:
		tmp = audio.get(attr)
		if tmp: track_info[attr] = tmp[0]

	# TODO: extract from the filename

	album = None # album to which the track will be added
	album_title = track_info.get('album')
	artist_name = track_info.get('albumartist', track_info.get('artist'))
	artist_list = construct_artist_list(artist_name)
	if album_title:
		album = albums.get((artist_name, album_title))
		if not album: # create a new album if it does not already exist
			album = Album(album_title, artist_list)
			albums[(artist_name, album_title)] = album

	title, tracknum = track_info.get('title'), track_info.get('tracknumber')
	if not title and not album and not tracknum: return False # too little info about this track
	# we use two ways to identify a track: track title, or album title and track number

	track = Track(title, parse_position(tracknum), artist_list, duration=duration, filepath=filepath)
	if album:
		album.tracklist.append(track)
		track.album = album
	else: tracks.append(track)

	return True

def move_file(filepath, new_filepath):
	'''
	Move a file specified by filepath to the location specified by new_filepath
	Args:
		filepath - the path to the file
		new_filepath - the new file's location
	Return:
		True on success, False if a file with the name already exists in the new location
	'''
	dir_list = new_filepath.split('/')
	curr_dir, i = '', 0
	try:
		while i < len(dir_list) - 1:
			curr_dir += dir_list[i]
			if not os.path.exists(curr_dir):
				os.makedirs(curr_dir)
			curr_dir += '/'
			i += 1
		os.rename(filepath, new_filepath)
		return True
	except: return False

def get_all_files(directory=PRE_PROCESS_DIR, file_ext='.mp3', rtn=[]):
	'''
	Get all the files under a given directory that end with the given file extension
	Args:
		directory - the directory to process i.e. "dir/dir2/"
		file_ext - target file extension
		rtn - list of filepaths to be returned
	Return:
		a list of filepaths with the given file extension under the directory
	'''
	print(directory)
	for filename in os.listdir(directory):
		try:
			if os.path.isdir(directory + filename):
				rtn = get_all_files(directory + filename + '/', rtn=rtn)
			elif filename.endswith(file_ext):
				filepath = directory + filename
				os.chmod(os.path.abspath(filepath), stat.S_IWRITE)
				rtn.append(filepath)
				log('added to the process queue: {}'.format(filepath))
		except: err('unable to enqueue file: ' + filepath)
	return rtn

def delete_dir(directory=PRE_PROCESS_DIR):
	delete = True
	for filename in os.listdir(directory):
		filename = directory + filename
		if os.path.isdir(filename):
			if delete_dir(filename + '/'):
				try: 
					os.chmod(os.path.abspath(filename), stat.S_IWRITE)
					shutil.rmtree(filename)
					log('directory "{}" deleted'.format(filename))
				except:
					delete = False
					err('unable to delete directory "{}"'.format(filename))
			else: delete = False
		else: delete = False
	return delete


def construct_filepath(track):
	'''
	Construct a new file path for this mp3 file based on its artist, album and position.
	Args:
		track - the track object of the file
	'''
	path = POST_PROCESS_DIR or ''
	if track.album:
		if track.album.title:
			if track.album.artists: path += re.sub('[~#%&*{}\\:<>?/||\"]', '-', get_artist_str(track.album.artists)) + '/'
			path += track.album.title if not track.album.year else str(track.album.year) + ' - ' + re.sub('[~#%&*{}\\:<>?/||\"]', '-', track.album.title)
			path += '/'
	if track.position[0]: path += 'Disc ' + str(track.position[0]) + '/'
	if track.position[1]: path += str(track.position[1]) + '. '
	path += re.sub('[~#%&*{}\\:<>?/||\"]', '-', track.title) + '.mp3'
	return path


def construct_artist_list(artist_str):
	'''
	Convert a string representing the artists to a list of Artist objects 
	Args:
		artist_str - string representing the artists (str)
	Return:
		a list of artist names (str[])
	'''
	if not artist_str: return []
	rtn = []
	artists = re.split(';', artist_str)
	for artist in artists:
		artist = artist.strip()
		if artist != '': rtn.append(artist)
	return rtn

load_tracks()