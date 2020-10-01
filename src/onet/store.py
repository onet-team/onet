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
			spaces = {"spaces": [{"id": str(uuid.uuid4()), "name": "space", "default": True, "type": "histore"}]}  # TODO owner
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
		print(899, y)
		if len(y) > 1:
			print(888, "Multiple defaults", y)
		elif len(y) == 0:
			print(887, "No defaults")
		# print ([y['default'] is True for y in x])
		# print([(x,y)# for x,y in spaces["spaces"].items()])
		# newDict = dict(filter(lambda elem: elem[0]['default'] is True, spaces["spaces"].items()))
		# print (newDict)
		# print([x["default"] for x in spaces["spaces"].keys()])
		self._storage = y[0][1]
		self._space_name = y[0][0]
	
	def _init_default(self):
		h = histore.HiStore(FilePath(self._path, self._space_name, 'histore'))
		p = histore.DirectoryPage(0, h)
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
		n.histore_key = key
		n.path = p.path
		n.content_page = p
		n.full_path = '.'
		self.root_node = n
		print(97, n, n.__dict__)
	
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
				n = DirectoryNode(self, po.store.number)
			else:
				n = FileNode(self, po.store.number)
			n.guid = node_guid
			n.last_ver = last_ver
		except KeyError as e:
			raise MalformedPageFile(e)
		return n
	
	def _write_default(self):
		p = histore.DirectoryPage(0, self.h)
		key = self.h.resolve_key(p.path_string)
		wr = self.h.openWriter(key, "Page.onet")
		wr.write("Type: Directory\n")
		wr.write("URN: " + new_hex_uuid() + "\n")
		wr.close()
	
	def mkdir(self, path: Path, skip_if_exists=False):
		if self.exists(path) and self.is_dir(path):
			if not skip_if_exists:
				raise FileExistsError
		else:
			p = ([str(x) for x in path.parents])
			p.insert(0, str(path))
			p.reverse()
			parent = self.root_node
			for each in p[1:]:
				print (20159, each)
				parent = self.mkdir_simple(parent, each, skip_if_exists)
				if not parent or not parent.is_dir():
					raise NotADirectoryError
	
	def import_dir_stat(self, path: Path, stat, move=False):
		c = (stat.st_dev, stat.st_ino)
		print("import_dir_stat", path, stat, type(stat), oct(stat.st_mode))
		pass
	
	def import_file_stat(self, path: Path, stat, move=False):
		c = (stat.st_dev, stat.st_ino)
		print("import_file_stat", path)
		pass
	
	def exists(self, path: Path):
		return self.stat(path).exists()
	
	def is_dir(self, path):
		return self.stat(path).is_dir()
	
	def stat(self, path: Path):
		print("stat", path)
		if not isinstance(path, Path):
			path = Path(path)  # raise TypeError("path %s is not Path" % path)
		parents = path.parents
		l = list([str(x) for x in parents])
		s = OnetStat()
		s.st_uuid = ''
		if l == ['.']:
			print(1)
			return self.stat_one(self.root_node, path)
		else:
			l.insert(0, str(path))
			l.reverse()
			print(3)
			node = self.root_node
			for each in l[1:]:
				if each == '.':
					continue
				x = self.stat_one(node, each)
				if not x.exists():
					return s  # TODO or x ??
				else:
					if x.is_dir():  # TODO and has listing permissions
						node = x
					else:
						print (20206, path)
						raise NotADirectoryError
				print(each, x, x.__dict__)
		self.stat_cache[s.node] = s
		return s
	
	def remove(self, path: Path, recursive=False):
		s = self.stat(path)
		if s.exists():
			if s.is_dir():
				if recursive:
					for each in self.list(path):
						self.remove(each, recursive)
				else:
					raise DirectoryNotEmpty()
			else:
				print ("TODO remove here")
				pass
	
	def stat_one(self, root_node, param):  # root_node: DirectoryNode
		print(20226, root_node, param)
		if param == '/':
			return root_node
		if root_node.last_ver == '':
			s = OnetStat()
			s.st_storage = root_node.store._storage
			s.st_uuid = ''
		else:
			x = root_node.entries[param]
			s = OnetStat()
			s.st_storage = root_node.store._storage
			s.st_uuid = ''
		return s
	
	def list(self, path):
		print("TODO list here")
		x = self.resolve(path)
		if x.is_dir():
			pass
		else:
			raise NotADirectoryError
		pass
	
	def mkdir_simple(self, parent, filename, skip_if_exists=False):
		if self.exists_in_parent(parent, filename):
			if not skip_if_exists:
				raise FileExistsError
			else:
				return self.resolve(Path(parent, filename))
		else:
			print ("TODO mkdir_simple", parent, filename)
			key = parent.store.h.allocate()
			wr = self.h.openWriter(key, "Page.onet")
			wr.write("Type: Directory\n")
			node_guid = new_hex_uuid()
			wr.write("URN: " + node_guid + "\n")
			last_version = new_hex_uuid()
			wr.write("Last-Version: " + last_version + "\n")
			wr.close()
			#
			from . import datatypes
			acls = self.copy_acls_or_default(parent, last_version)
			acl_uuid = new_hex_uuid()
			#
			directory_node = DirectoryNode(self, key.page.number)
			directory_node.full_path = Path(parent.full_path, filename)
			directory_node.guid = node_guid
			directory_node.last_ver = last_version
			directory_node.histore_key = key
			directory_node.path = key.path
			directory_node.content_page = key.page
			#
			version = datatypes.Version("v1", last_version, acl_uuid, directory_node)
			attr = datatypes.Attributes(version)
			attr.put('filename', datatypes.AttributeValue(filename, acl=acls.acls[0]))
			version.attributes = attr.uuid
			#
			import toml
			fp = self.h.openWriter(key, acl_uuid+'.acls')
			s = toml.dumps(acls.to_dict())
			fp.write(s)
			fp.close()
			fp = self.h.openWriter(key, last_version+'.version')
			s = toml.dumps(version.to_dict())
			fp.write(s)
			fp.close()
			fp = self.h.openWriter(key, last_version+'.attr')
			s = toml.dumps(attr.to_dict())
			fp.write(s)
			fp.close()
			#
			return directory_node

	def exists_in_parent(self, parent, path):
		# print ("TODO exists_in_parent", parent, path)
		if not parent.exists():
			return False
		if parent.last_ver == '':
			return False
		if path in parent.entries:
			return True
	
	def resolve(self, path):
		print ("TODO resolve ", path)
		return path
	
	def copy_acls_or_default(self, parent, version):
		if parent.last_ver == '':
			from . import datatypes
			acls = datatypes.Acls(version, self.u)  # TODO arguments not even used
			acl = datatypes.Acl('all', self.u)
			acls.acls.append(acl)
			return acls
		else:
			print ("TODO copy acls")


class DirectoryNode(object):
	content_page: histore.DirectoryPage
	guid: str
	histore_key: histore.HiStoreKey
	key: int
	last_ver: str
	path: Path
	store: OnetStore
	
	def __init__(self, store, key):
		self.store = store
		self.key = key
		
	def exists(self):
		if self.last_ver == '':
			return False
		if self.content_page.hasContent('%s.version'%self.last_ver):
			return True
		assert False
		return False

	def is_dir(self):
		return True  #self.store.is_dir(self.full_path)
	

class FileNode(object):
	content_page: histore.DirectoryPage
	guid: str
	histore_key: histore.HiStoreKey
	key: int
	last_ver: str
	path: Path
	store: OnetStore
	
	def __init__(self, store, key):
		self.store = store
		self.key = key

	def exists(self):
		if self.last_ver == '':
			return False
		assert False
		return False

	def is_dir(self):
		return False
