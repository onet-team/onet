import toml
import json
from typing import Dict, Any

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
		if getattr(self, 'node'):
			return self.node.is_dir()
		return False
	
	def exists(self):
		if self.st_uuid == '':
			return False
		if getattr(self, 'node'):
			return True
		return False


class DirectoryNotEmpty(Exception):
	pass


class MalformedPageFile(Exception):
	pass
	

def new_hex_uuid():
	return uuid.uuid4().hex


class OnetStore:
	def __init__(self, path):
		self.stat_cache = {}
		# self._cache = []
		self._path = path
		if not FilePath(path).exists():
			FilePath(path).mkdir(parents=True)
		self._init_spaces()
		self._read_cache()
		self._init_default()
		self._init_user()
	
	def _read_cache(self):
		from .cache import Cache
		self._cache = Cache(FilePath(self._path), self._space_name, self)
		
	# def _read_cache(self, key):
	# 	po = self.h.openReader(key, ".cache")
	# 	rd = po.read().decode()
	# 	po.close()
	# 	x = [str.split(y, maxsplit=1) for y in rd.splitlines()]
	# 	print (10059, x)
	# 	x = [tuple([y[0], int(y[1])]) for y in x]
	# 	self._cache += x
	# 	import atexit
	# 	atexit.register(self.write_cache, (key, x))
	
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
		p = histore.LeafPage(0, h)
		# print(100, p.path, p.path_string)
		key = h.resolve_key(p.path_string)
		# print(101, key)
		po = h.openReader(key, "Page.onet")
		self.h = h
		# self._read_cache(key)
		# print(po)
		if po.fp is None:
			self._write_default()
			po = h.openReader(key, "Page.onet")
		
		n = self.read_page_file(po, '/')  # TODO is this an appropriate filename?
		n.histore_key = key
		n.path = p.path
		n.content_page = p
		n.full_path = '.'
		self.root_node = n
		if self._cache._new_store:
			self._reload_cache()
			self._cache._new_store = False
		if n.last_ver != '':
			n.read_entries()
		# print(97, n, n.__dict__)
	
	def _reload_cache(self):
		for each_key in self.h.validKeys():
			p = histore.LeafPage(each_key, self.h)
			x = p.listInternal()
			for (_, each) in x:
				if each in ['HiStore.info', 'Page.onet']:
					continue
				uuid_, type_ = str.split(each, '.', maxsplit=1)
				self._cache.record_uuid(uuid_, each_key, type_)
	
	def read_page_file(self, po, filename):
		"""

		:param filename:
		:type po: histore.HiStoreReader
		:rtype: DirectoryNode | FileNode
		"""
		l = self._read_page_file_int(po)
		d = dict(l)
		try:
			node_type = d['Type']
			node_guid = d['URN']
			if 'Last-Version' in d:
				last_ver = d['Last-Version']
			else:
				last_ver = ''
			
			if node_type == 'Directory':
				n = DirectoryNode(self, po.store.number, filename)
			elif node_type == 'File':
				n = FileNode(self, po.store.number)
			else:
				raise ValueError(node_type)
			n.guid = node_guid
			n.last_ver = last_ver
		except KeyError as e:
			raise MalformedPageFile(e)
		return n
	
	def _read_page_file_int(self, po):
		raw = po.read().decode()
		l = raw.splitlines(keepends=False)
		l = [str.split(x, ':', maxsplit=1) for x in l]
		l = [(str.strip(x), str.strip(y)) for x, y in l]
		# print(200, l, dict(l))
		po.close()
		return l
	
	def _write_default(self):
		p = histore.LeafPage(0, self.h)
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
		print("import_dir_stat", path, stat, type(stat), oct(stat.st_mode), c)
		pass
	
	def import_file_stat(self, path: Path, stat, move=False):
		c = (stat.st_dev, stat.st_ino)
		print("import_file_stat", path, c)
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
				each = Path(each).parts[-1]
				x = self.stat_one(node, each)
				if not x.exists():
					return s  # TODO or x ??
				else:
					if x.is_dir():  # TODO and has listing permissions
						node = x.node
					else:
						print (20206, path)
						raise NotADirectoryError
				print(each, x, x.__dict__)
		self.stat_cache[s.node] = s
		return s
	
	def remove(self, path: Path, recursive=False):
		if not type(path) is Path:
			path = Path(path)
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
			x = None
			if str(param) in root_node.entries:
				x = root_node.entries[str(param)]
			s = OnetStat()
			s.st_storage = root_node.store._storage
			s.st_uuid = ''
			if x is not None:
				s.st_uuid = x.last_ver
				s.st_guid = x.guid
				s.st_key = x.path_string
				s.node = x
		return s
	
	def list(self, path: Path):
		print("TODO list here")
		x = self.resolve(path)
		if x.is_dir():
			return x.entries.keys()
		else:
			raise NotADirectoryError
	
	def mkdir_simple(self, parent, filename, skip_if_exists=False):
		if self.exists_in_parent(parent, filename):
			if not skip_if_exists:
				raise FileExistsError
			else:
				return self.resolve_from(parent, filename)
		else:
			print ("TODO mkdir_simple", parent, filename)
			parent: DirectoryNode
			
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
			acl_uuid = new_hex_uuid()
			#
			directory_node = DirectoryNode(self, key.page.number, filename)
			directory_node.full_path = Path(parent.full_path, filename)
			directory_node.guid = node_guid
			directory_node.last_ver = last_version
			directory_node.histore_key = key
			directory_node.path = key.path
			directory_node.content_page = key.page
			#
			version = datatypes.Version(name=acl_uuid, uuid=last_version, acl_uuid=acl_uuid, node=directory_node)
			parent.version = version
			acls = self.copy_acls_or_default(parent, last_version)
			attr = datatypes.Attributes(version)
			attr.uuid = version.uuid
			print(10283, acls.acls)
			attr.put('filename', datatypes.AttributeValue(filename, acl=acls.acls[0]))
			version.attributes = attr.uuid
			entries = datatypes.Entries(version.uuid)
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
			fp = self.h.openWriter(key, last_version+'.entries')
			s = toml.dumps(entries.to_dict())
			fp.write(s)
			fp.close()
			#
			parent.add(filename, directory_node, version=version, file_uuid=last_version)
			#
			return directory_node

	def exists_in_parent(self, parent, path):
		"""
		:type path: str
		:type parent: DirectoryNode
		"""
		# print ("TODO exists_in_parent", parent, path)
		path = Path(path).parts[-1]
		if not parent.exists():
			return False
		if parent.last_ver == '':
			return False
		if not parent.entries_read:
			parent.read_entries()
		if path in parent.entries:
			return True
		return False
	
	def resolve(self, path: FilePath):
		"""

		:rtype: DirectoryNode
		"""
		print("TODO resolve ", path.parts)
		parent = self.root_node
		for each in path.parts:
			if self.exists_in_parent(parent, each):
				parent = parent.entries[each]
			else:
				return None
		return parent
	
	def resolve_from(self, root_node, path: Path):
		"""

		:param path:
		:type root_node: DirectoryNode
		:rtype: DirectoryNode
		"""
		if type(path) is not Path:
			path = Path(path)
		print("TODO resolve ", path.parts)
		parent = root_node
		for each in path.parts:
			if self.exists_in_parent(parent, each):
				parent = parent.entries[each]
			else:
				return None
		return parent
	
	def copy_acls_or_default(self, parent, version):
		"""

		:type parent: DirectoryNode
		:type version: str #onet.datatypes.Version
		"""
		from . import datatypes
		if parent.last_ver == '':
			acls = datatypes.Acls(version, self.u)  # TODO arguments not even used
			acl = datatypes.Acl('all', self.u)
			acls.acls.append(acl)
			return acls
		else:
			print ("TODO copy acls")
			acls = datatypes.Acls(None, None)
			rdf = parent.content_page.openReader(parent.version.acl+".acls")
			if rdf.fp is not None:
				acls_raw = rdf.read()
				acls_decoded = acls_raw.decode()
				print(10339, acls_decoded)
				rdf.close()
				d = toml.loads(acls_decoded)
				print(10344, d)
				acls.from_dict(d)
			else:
				acl = datatypes.Acl('all', self.u)
				acls.acls.append(acl)
			return acls


class DirectoryNode(object):
	content_page: histore.LeafPage
	guid: str
	histore_key: histore.HiStoreKey
	key: int
	last_ver: str
	path: Path
	store: OnetStore
	filename: str
	# entries: Dict[str, datatypes.Entry]
	entries_read: bool
	full_path: Path
	
	def __init__(self, store, key, filename):
		self.store = store
		self.key = key
		self.filename = filename
		self.entries = {}
		self.entries_read = False
		
	def exists(self):
		if self.last_ver == '':
			return False
		try:
			x = getattr(self, 'content_page')
		except AttributeError:
			dp = histore.LeafPage(self.key, self.store.h)
			self.content_page = dp
		if self.content_page.hasContent('%s.version'%self.last_ver):
			return True
		assert False
		return False

	def is_dir(self):
		return True  #self.store.is_dir(self.full_path)
	
	def add(self, filename, directory_node, version, file_uuid):
		"""

		:type version: onet.datatypes.Version
		"""
		last_ver = new_hex_uuid()
		p = histore.LeafPage(self.key, self.store.h)
		key = self.store.h.resolve_key(p.path_string)
		wr = self.store.h.openWriter(key, "Page.onet")
		wr.write("Type: Directory\n")
		wr.write("URN: " + self.guid + "\n")
		wr.write("Last-Version: " + last_ver + "\n")
		wr.close()
		#
		from . import datatypes
		#
		acls = self.store.copy_acls_or_default(self, self.last_ver)
		acl_uuid = new_hex_uuid()
		#
		if self.last_ver == '':
			ver_name = "v1"
		else:
			import re
			x = re.match(r'v(\d+)', self.last_ver)
			if x is not None and len(x.groups()):
				ver = int(x.group(1))+1
				ver_name = 'v%d' % ver
			else:
				ver_name = last_ver
		version = datatypes.Version(ver_name, last_ver, acl_uuid, self)
		attr = datatypes.Attributes(version)
		attr.uuid = version.uuid
		attr.put('filename', datatypes.AttributeValue(self.filename, acl=acls.acls[0]))
		version.attributes = attr.uuid
		#
		fp = self.store.h.openWriter(key, acl_uuid + '.acls')
		s = toml.dumps(acls.to_dict())
		fp.write(s)
		fp.close()
		fp = self.store.h.openWriter(key, last_ver + '.version')
		s = toml.dumps(version.to_dict())
		fp.write(s)
		fp.close()
		fp = self.store.h.openWriter(key, last_ver + '.attr')
		s = toml.dumps(attr.to_dict())
		fp.write(s)
		fp.close()
		#
		es = datatypes.Entries(version.uuid)
		e = datatypes.NormalEntry()
		e.uuid = file_uuid
		e.filename = filename
		es.add(e)
		wr = self.store.h.openWriter(key, "%s.entries" % last_ver)
		s = toml.dumps(es.to_dict())
		wr.write(s)
		wr.close()
		#
		self.entries[filename] = e
		self.last_ver = last_ver

	def read_entries(self):
		p = histore.LeafPage(self.key, self.store.h)
		key = self.store.h.resolve_key(p.path_string)
		rr = self.store.h.openReader(key, "%s.entries" % self.last_ver)
		rd = rr.read().decode()
		rr.close()
		from . import datatypes
		entf = toml.loads(rd)
		ents = datatypes.Entries(None)
		ents.from_dict(entf)
		for each in ents.entries:
			print (each)
			if isinstance(each, datatypes.NormalEntry):
				found_key = self.find_key(each.uuid)
				#
				key1 = self.store.h.resolve_key(found_key)
				po = self.store.h.openReader(key1, "Page.onet")
				node = self.store.read_page_file(po, None)  # fill in filename later
				#
				ver, attr, filename = self.read_version(each, found_key)
				node.version = ver
				if ver.name is not None:
					node.version_name = ver.name
				node.attr = attr
				node.filename = filename
				node.full_path = Path(self.full_path, filename)
				node.path_string = found_key
				#
				self.entries[filename] = node
				ver.attributes_object = attr
			else:
				raise ValueError(each)
		self.entries_read = True
	
	def read_version(self, entry, path_str):
		from . import datatypes
		
		# key1 = self.store.h.resolve_key(path_str)
		dp = histore.LeafPage(path_str, self.store.h)
		rdr = dp.openReader("%s.version" % entry.uuid)
		try:
			rd = rdr.read().decode()
			ver_dict = toml.loads(rd)
			ver = datatypes.Version(None, None, None, None)
			ver.from_dict(ver_dict)
		finally:
			rdr.close()
		
		rdr = dp.openReader("%s.attr" % ver.attributes)
		try:
			rd = rdr.read().decode()
			attr_dict = toml.loads(rd)
			attr = datatypes.Attributes(None)
			attr.from_dict(attr_dict)
			attr.version = ver
			# print (toml.dumps(attr.to_dict()))
		finally:
			rdr.close()
			
		return (ver, attr, attr.attr['filename'].value)

	
	def find_key(self, uuid):
		x = self.store._cache.get_version(uuid)
		assert len(x) == 1
		x = x[0]
		return x.key


class FileNode(object):
	content_page: histore.LeafPage
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
