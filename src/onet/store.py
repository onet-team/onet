import json

import histore
from pathlib import PurePosixPath as Path
from . import chunker
from pathlib import Path as FilePath
import uuid
from . import base36


class OnetStat(object):
	st_mode: int
	st_key: histore.HiStoreKey
	st_storage: str
	st_owner: str  # uuid
	st_uuid: str
	st_guid: str
	
	def is_dir(self):
		if not self.exists():
			return False
		if self.st_uuid == '':
			return False
		return True
	
	def exists(self):
		if self.st_uuid == '':
			return False
		return True


class DirectoryNotEmpty(Exception):
	pass


class MalformedPageFile(Exception):
	pass
	

def new_hex_uuid():
	return uuid.uuid4().hex


class OnetStore:
	def __init__(self, path):
		self.stat_cache = {}
		self._path = path
		if not FilePath(path).exists():
			FilePath(path).mkdir(parents=True)
		self._init_spaces()
		self._init_default()
		self._init_user()
	
	def _init_user(self):
		p = FilePath(self._path, 'user.dat')
		from . import datatypes
		if not p.exists():
			with p.open('w') as fp:
				user_uuid = new_hex_uuid()
				fp.write('%s\n' % user_uuid)
		else:
			with p.open('r') as fp:
				user_uuid = fp.readline().strip()
		self.u = datatypes.User(user_uuid)
	
	def _init_spaces(self):
		p = FilePath(self._path, 'spaces.json')
		if not p.exists():
			spaces = {"spaces": [{"id": str(uuid.uuid4()), "name": "space", "default": True, "type": "histore"}]}
			with p.open('w') as f:
				f.write(json.dumps(spaces))
		with open(p, 'r') as f:
			spaces = json.loads(f.read())
		# print(spaces)
		x = spaces["spaces"]
		print(900, x)
		y = []
		for each in x:
			if each['default'] is True:
				y.append((each['name'], each['id']))
		print(y)
		# print ([y['default'] is True for y in x])
		# print([(x,y)# for x,y in spaces["spaces"].items()])
		# newDict = dict(filter(lambda elem: elem[0]['default'] is True, spaces["spaces"].items()))
		# print (newDict)
		# print([x["default"] for x in spaces["spaces"].keys()])
		self._storage = y[0][1]
		self._space_name = y[0][0]
	
	def _init_default(self):
		h = histore.HiStore(FilePath(self._path, 'space/histore'))
		p = histore.ContentPage(0, h)
		print(100, p.path, p.path_string)
		key = h.resolve_key(p.path_string)
		print(101, key)
		po = h.openReader(key, "Page.onet")
		self.h = h
		print(po)
		if po.fp is None:
			self._write_default()
			po = h.openReader(key, "Page.onet")
		
		n = self.read_page_file(po)
		n.key = key
		n.path = p.path
		n.content_page = p
		self.root_node = n
		print (97, n, n.__dict__)
	
	def read_page_file(self, po):  # po: histore.HiStoreReader
		raw = po.read()
		l = raw.splitlines(keepends=False)
		l = [str.split((x.decode()), ':', maxsplit=1) for x in l]
		l = [(str.strip(x), str.strip(y)) for x, y in l]
		print(200, l, dict(l))
		po.close()
		d = dict(l)
		try:
			node_type = d['Type']
			node_guid = d['URN']
			if 'Last-Version' in d:
				last_ver = d['Last-Version']
			else:
				last_ver = ''
			
			if node_type == 'Directory':
				n = DirectoryNode()
			else:
				n = FileNode()
			n.guid = node_guid
			n.last_ver = last_ver
		except KeyError as e:
			raise MalformedPageFile(e)
		return n
	
	def _write_default(self):
		p = histore.ContentPage(0, self.h)
		key = self.h.resolve_key(p.path_string)
		wr = self.h.openWriter(key, "Page.onet")
		wr.write("Type: Directory\n")
		wr.write("URN: " + new_hex_uuid() + "\n")
		wr.close()
	
	def mkdir(self, path: FilePath, skip_if_exists=False):
		if self.exists(path) and self.is_dir(path):
			if not skip_if_exists:
				raise FileExistsError
	
	def import_dir_stat(self, path: FilePath, stat, move=False):
		c = (stat.st_dev, stat.st_ino)
		print ("import_dir_stat", path, stat, type(stat), oct(stat.st_mode))
		pass
	
	def import_file_stat(self, path: FilePath, stat, move=False):
		c = (stat.st_dev, stat.st_ino)
		print ("import_file_stat", path)
		pass

	def exists(self, path: FilePath):
		return False
	
	def is_dir(self, path):
		return False
	
	def stat(self, path: FilePath):
		print ("stat", path)
		if not isinstance(path, FilePath):
			path = FilePath(path) # raise TypeError("path %s is not FilePath" % path)
		parents = path.parents
		l = list([str(x) for x in parents])
		if l == ['.']:
			print (1)
			return self.stat_one(self.root_node, l[0])
		else:
			l.reverse()
			if not l:
				print (2)
				pass
			else:
				print (3)
				for each in l:
					print (each, type(each))
		s = OnetStat()
		self.stat_cache[s.node] = s
		return s
		
	def remove(self, path: FilePath, recursive=False):
		s = self.stat(path)
		if s.is_dir():
			if recursive:
				for each in s:
					self.remove(s, recursive)
			else:
				raise DirectoryNotEmpty()
		pass
	
	def stat_one(self, root_node, param):
		print (96, root_node, param)
		pass
