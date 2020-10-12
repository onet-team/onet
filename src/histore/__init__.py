import builtins
import json
import os
import types
from datetime import timedelta
from pathlib import Path
from io import StringIO
from typing import Any, Union, Dict, Tuple


def number_to_path_string(number):
	path = '%08x' % (number & 0xffffffff)  # TODO does this do anything?
	pp = StringIO(path)
	p = '/'.join([pp.read(2), pp.read(2), pp.read(2), pp.read(2)])
	return p


class DirectoryPage:
	def __init__(self, number, store):
		self._flush_actions = []
		self.number = number
		self.store = store
		if type(number) is int:
			self.path_string = number_to_path_string(number)
		else:
			self.path_string = number
		self.path = Path(self.path_string)
		
	def exists(self):
		return Path(self.store.root, self.path, "HiStore.info").exists()
	
	def read(self):  # -> Optional[HiStoreKey]:
		if not self.exists():
			return None
		with open(Path(self.store.root, self.path, "HiStore.info"), 'r') as fp:
			x = json.loads(fp.read())
			print (10034, x)
			#
			# TODO Support reservation on Content not whole directory
			#
			if x['type']=='reservation':
				k = HiStoreKey(self.path_string, x['type'], timedelta(seconds=30), self.path)
			else:
				k = HiStoreKey(self.path_string, x['type'], 0, self.path)
			return k
		
	def flush(self):
		errs = []
		for each in self._flush_actions:
			b = each.act()
			if b:
				self._flush_actions.remove(each)
			else:
				errs += (each, b)
		return errs
	
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

	def hasContent(self, filename):
		if filename == 'HiStore.info':
			return None
		r = Path(self.store.root, self.path, filename).exists()
		return r
	
	def listInternal(self):
		pth = Path(self.store.root, self.path)
		x = [(x, x.parts[-1]) for x in pth.iterdir()]
		return x

class HiStoreKey:
	page: DirectoryPage
	
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
	pagecache: Dict[int, DirectoryPage]
	
	def __init__(self, root: str):
		self.root = root
		self.pagecache = {}
		self.freepage = None
		if not Path(root).exists():
			os.makedirs(Path(root))

	def allocate(self) -> HiStoreKey:
		p = self.find_next_page()
		k = HiStoreKey(p.path_string, 'reservation', timedelta(seconds=30), p)
		return k
	
	def resolve(self, key: int) -> HiStoreKey:
		p, f = self._get_page(key)
		k = HiStoreKey(p.path_string, 'content', timedelta(seconds=30), p)
		return k

	def resolve_key(self, skey: str) -> HiStoreKey:
		key = int(skey.replace('/', ''), 16)
		return self.resolve(key)

	def find_next_page(self):
		if self.freepage is None:
			self.freepage, f = self._get_page(0)
			
		if self.freepage.exists():
			while self.freepage.exists():
				(self.freepage, new_page) = self._get_page(self.freepage.number+1, True)
				if new_page:
					break
		
		return self.freepage
	
	def _get_page(self, number, reservation=False) -> Tuple[DirectoryPage, bool]:
		new_page = False
		if number in self.pagecache:
			return (self.pagecache[number], False)
		p = DirectoryPage(number, self)
		x = p.read()
		if x is None:
			os.makedirs(Path(self.root, p.path), exist_ok=True)
			with open(Path(self.root, p.path, "HiStore.info"), 'w') as fp:
				if reservation:
					y = {'type': 'reservation'}
					new_page = True  # TODO
				else:
					y = {'type': 'content'}
				fp.write(json.dumps(y))
			x = p.read()
		self.pagecache[number] = p
		return (p, new_page)

	def openReader(self, key: HiStoreKey, filename: str):
		# print (10123, filename)
		return key.page.openReader(filename)

	def openWriter(self, key: HiStoreKey, filename: str):
		"""

		:param key:
		:type filename: basestring
		"""
		with open(Path(self.root, key.page.path, "HiStore.info"), 'w') as fp:
			y = {'type': 'content'}
			fp.write(json.dumps(y))
		return key.page.openWriter(filename)
	
	def validKeys(self):
		"""
		Implement a naive version for now
		Should read a HiStore.info file at every level, or you could just walk the dirs
		
		:return: a list of valid key strings
		"""
		r = []
		x = 0
		while True:
			dp = DirectoryPage(x, self)
			if dp.exists():
				r.append(dp.path_string)
			else:
				break
			x = x + 1
		return r

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
			content = content.encode()  # convert to bytes
		self.fp.write(content)

	def close(self):
		if self.fp is not None:
			self.fp.close()
			self.fp = None


class HiStoreReader(object):
	filename: str
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
