import builtins
import json
import os
import types
from datetime import timedelta
from pathlib import Path
from io import StringIO
from typing import Any, Union


class ContentPage:
	def __init__(self, number, store):
		self._flush_actions = []
		self.number = number
		self.store = store
		path = '%08x' % number
		pp = StringIO(path)
		self.path_string = '/'.join([pp.read(2), pp.read(2), pp.read(2), pp.read(2)])
		self.path = Path(self.path_string)
	
	def exists(self):
		return Path(self.path, "HiStore.info").exists()
	
	def read(self):
		if not self.exists():
			return None
		with open(Path(self.path, "HiStore.info"), 'r') as fp:
			x = json.loads(fp.read())
			print (x)
			k = HiStoreKey(self.path_string, x['type'], 0, self.path)
			return k
		
	def flush(self):
		for each in self._flush_actions:
			b = each.act()
			if b:
				self._flush_actions.remove(each)
			else:
				return False
		return True
	
	def openReader(self, filename: str):
		if filename == 'HiStore.info':
			return None
		r = HiStoreReader(filename, Path(self.store.root, self.path), self)
		return r
	
	def openWriter(self, filename):
		if filename == 'HiStore.info':
			return None
		r = HiStoreWriter(filename, Path(self.store.root, self.path), self)
		return r
	
	
class HiStoreKey:
	page: ContentPage
	
	def __init__(self, path, type_, expiry, page):
		self.path = path
		self.type = type_
		self.expiry = expiry
		self.page = page
		
	__slots__ = ('path', 
				 'type', # type is Reservation or Content
				 'expiry',
	             'page')
	

class HiStore(object):
	def __init__(self, root: str):
		self.root = root
		self.pagecache = {}
		self.freepage = None
		if not Path(root).exists():
			os.makedirs(Path(root))

	def allocate(self):
		p = self.find_next_page()
		k = HiStoreKey(p.path_string, 'reservation', timedelta(seconds=30), p)
		return k
	
	def resolve(self, key: int):
		p = self._get_page(key)
		k = HiStoreKey(p.path_string, 'content', timedelta(seconds=30), p)
		return k

	def resolve_key(self, skey: str):
		key = int(skey.replace('/', ''), 16)
		return self.resolve(key)

	def find_next_page(self):
		if self.freepage is None:
			self.freepage = self._get_page(0)
			
		if self.freepage.exists():
			while self.freepage.exists():
				self.freepage = self._get_page(self.freepage.number+1)
		
		return self.freepage
	
	def _get_page(self, number):
		if number in self.pagecache:
			return self.pagecache[number]
		p = ContentPage(number, self)
		p.read()
		self.pagecache[number] = p
		return p

	def openReader(self, key: HiStoreKey, filename: str):
		print (100, filename)
		return key.page.openReader(filename)

	def openWriter(self, key: HiStoreKey, filename: str):
		"""

		:param key:
		:type filename: basestring
		"""
		return key.page.openWriter(filename)


class HiStoreWriter(object):
	filename: str
	path: Path
	store: HiStore
	
	def __init__(self, filename, path, store):
		self.filename = filename
		self.path = Path(path, filename)
		self.store = store
		self.fp = open(self.path, 'wb')

	def write(self, content: bytes, offset: int = None):
		if content is not None:
			if offset is not None:
				self.fp.seek(offset)
		if type(content) is str:
			content = content.encode()
		self.fp.write(content)

	def close(self):
		if self.fp is not None:
			self.fp.close()
			self.fp = None


class HiStoreReader(object):
	filename: type('')
	path: Path
	store: HiStore
	
	def __init__(self, filename, path, store):
		self.filename = filename
		if not path.exists():
			os.makedirs(path)
		self.path = Path(path, filename)
		self.store = store
		if os.path.exists(self.path):
			self.fp = open(self.path, 'rb')
		else:
			self.fp = None
			
	def read(self, amount: int = None) -> bytes:
		if self.fp is not None:
			if amount is None:
				return self.fp.read()
			else:
				return self.fp.read(amount)
		else:
			return b''

	def close(self):
		if self.fp is not None:
			self.fp.close()
			self.fp = None
