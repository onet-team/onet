#!/usr/bin/python3

import sys, os

sys.path.insert(1, os.path.join(os.getcwd(), 'src'))

from pathlib import Path


y = Path('sample')


def walk(p):
	if not p.is_dir():
		# yield p
		return
	z = [x for x in p.iterdir()]
	yield from z
	for each in z:
		yield from walk(each)


# print ([(x, os.stat(x)) for x in y.iterdir()])

# print ([x for x in y.iterdir() if x.is_dir()])


import histore

# p = histore.ContentPage(0, None)
# print(100, p.path)
# h = histore.HiStore('histore')
# print(101, h.resolve_key(p.path_string))

for each in walk(y):
	print(99, each)

import onet
store = onet.OnetStore("onet-000")
store.remove('sample', recursive=True)

for each in walk(y):
	print (98, each)
	if each.is_dir():
		y_path = onet.Path('sample', each)
		# if not store.exists(y_path):
		store.mkdir(y_path, skip_if_exists=True)
		store.import_dir_stat(y_path, os.stat(y), move=False)
	else:
		y_path = onet.Path('sample', each)
		store.import_file_stat(y_path, os.stat(y), move=False)
