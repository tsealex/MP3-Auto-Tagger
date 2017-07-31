import py_stringmatching as sm
from munkres import Munkres, make_cost_matrix 

import math
import re

DEBUGGING = {
	'tagger': True,
	'resources': True,
	'searcher': True
}

def parse_duration(dur_str):
	'''
	Args:
		dur_str - a string representing the duration i.e. '5:42' (str)
	Return:
		the duration in seconds (float), or None if dur_str is not valid
	'''
	if not dur_str or dur_str == '': return None
	m = re.search('^(?P<minute>[0-9]+):(?P<second>[0-9]+)$', dur_str)
	if not m: return None
	return float(m.group('minute')) * 60.0 + float(m.group('second'))

def parse_position(pos_str):
	'''
	Parse a position string into a 2-entry position tuple (disc #, track #).
	Args:
		pos_str - a string representing the track position i.e. '2-3' (str)
	Return:
		track position ((int, int)), or (None, None) if pos_str is not valid
	'''
	# case 0: null string -> (None. None)
	if not pos_str or pos_str == '': return (None, None)
	# case 1: '12' -> (None, 12)
	if pos_str.isdigit(): return (None, int(pos_str)) 
	# match strings like '2-3', 'A8', '3/2', '3.5' etc (UPDATE: now letters are no longger supported)
	m = re.search('(^(?P<disc>[0-9]+))(-|.|/)?(?P<track>[0-9]+$)', pos_str)
	# case 2: not a valid position string -> (None, None)
	if not m: return (None, None)
	# case 3: valid strings i.e. 'A8' -> (1, 8), '3/2' -> (3, 2)
	if m.group('disc').isdigit(): return (int(m.group('disc')), int(m.group('track')))
	if len(m.group('disc')) > 1: return (None, int(m.group('track')))
	j = 64 if ord(m.group('disc')) < 97 else 96
	return (ord(m.group('disc')) - j, int(m.group('track'))) 

def extract_disc_number(title):
	'''
	Extract the disc number of an album from its title
	Args:
		title - album title from which the disc # is extracted (str)
	Return:
		the disc number (int), or 1 if unable to extract from the title
	'''
	m = re.search('(Disc|CD) *(?P<disc>[0-9])', title, flags=re.IGNORECASE)
	if m: return int(m.group('disc'))
	else: return 1

def get_artist_str(artists, delimiter=';'):
	'''
	Args:
		artists - a list of artists (str[])
		delimiter - the string that seperates each artist 
	Return: 
		a string representing the list of artists (str)
	'''
	if not artists: return ''
	rtn = artists[0]
	for i in range(1, len(artists)):
		rtn += delimiter + ' ' + artists[i]
	return rtn

def get_genre(genres):
	'''
	Args:
		genres - a list of genres (str[])
	Return:
		the first genre in that list (this is tentative) (str)
	'''
	return genres[0] if genres else ''

# TODO: unfinished
def remove_edition(title):
	'''
	Remove any edition and disc info from the title i.e. [Deluxe Edition]
	Args:
		title - title to be modified
	Return:
		new title without any edition information
	'''
	if not title: return title
	# remove disc number
	# title = re.sub('(\[|\(|\{) *(Disc|CD) *[0-9]+ *(\)|\]\}) *$', '', title, flags=re.IGNORECASE).strip()
	# remove edition
	title = re.sub('(\[|\(\{).+(\]|\}|\)) *$', '', title).strip()

	return title

# an object used to compute the edit distance between two strings
lev = sm.Levenshtein()

# an object used to compute the Jaro-Winkler distance between two strings
jw = sm.JaroWinkler()


def maximize_assignment(matrix):
	'''
	Solve the assignment problem presented by the similarity matrix using hungarian algorithm,
	and produce a mapping the maximize the similarity
	Args:
		matrix - a float similarity matrix representing an assignment problem (float[][])
	Return:
		the maximized consine score of the similarity matrix (float)
		the optimal mapping in the form of a list of (row, col) tuples ((int, int)[])
	'''
	max_matrix = make_cost_matrix(matrix)
	mapping = Munkres().compute(max_matrix)
	cost = 0
	for i, j in mapping:
		cost += matrix[i][j]
	cost = cost / (math.sqrt(len(matrix)) * math.sqrt(len(matrix[0])))
	return cost, mapping


def log(msg, log_type='log', end='\n'):
	'''
	Print a message to the console
	Args:
		msg - message to be logged
		log_type - type of the message, default to 'log'
		end - ending string of the message 
	'''
	print('[{}] {}'.format(log_type, msg), end=end)

def debug(debug_src, msg):
	'''
	Print a debugging message to the console
	Args:
		debug_src - name of the source file that made this call 
		msg - message to be logged
	'''
	if DEBUGGING.get(debug_src, False):
		log(msg, 'debug')

def err(msg):
	'''
	Print an error message to the console
	Args:
		msg - message to be logged
	'''
	log(msg, 'error')

def get_percentage(number):
	'''
	Args:
		number - a number to be converted to percentage (float)
	Return:
		percentage representation of the number (float)
	'''
	number = int(number * 10000) / 100.0
	return number
