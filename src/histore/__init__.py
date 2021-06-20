import builtins
import json
import os
import types
from datetime import timedelta
from pathlib import Path, PurePosixPath
from io import StringIO
from typing import Any, Union, Dict, Tuple, Optional, List
from enum import Enum, unique


def number_to_path_string(number):
	path = '%08x' % (number & 0xffffffff)  # TODO does this do anything?
	pp = StringIO(path)
	p = '/'.join([pp.read(2), pp.read(2), pp.read(2), pp.read(2)])
	return p


@unique
class STATUS(Enum):
	COMMIT = 1
	DELETE = 2


class BranchPage:
	pending: bool
	path: str
	#store: HiStore
	#parent: Optional[BranchPage]
	full_path: Path
	allocated: set
	dirty: bool
	
	def __init__(self, path: str, store):
		self.path = path
		self.store = store
		self.number = None
		if len(path) == 0:
			self.parent = None
		else:
			if len(path) > 1:
				self.number = int(path[-2:], 16)
			parent_page = str(PurePosixPath(path).parent)
			if parent_page == '.':
				parent_page = ''
				# self.number = None
			self.parent = store.get_branch_page(parent_page)
		self.full_path = Path(store.root, self.path, "HiStore.info")
		self.allocated = set()
		self.dirty = False
		self.pending = False
		
	def create(self):
		assert not self.exists()
		self.allocated = set()
		self.dirty = True
		self.persist()
		
	def read(self):
		with open(self.full_path, 'r') as fp:
			x = json.loads(fp.read())
			
			assert x['type'] == 'branch'
			self.allocated = [int(y) for y in x['allocated']]
			
			# TODO verify allocateds are not empty (ie has HiStroe.info and >0 content entries)
			# TODO verify sub-branches and add to store
			
			self.allocated = set(filter(lambda z: 0 <= z <= 255, self.allocated))

	def update(self, number, status: STATUS):
		# doesn't persist reservations (this is not a bug)
		if status == STATUS.COMMIT:
			old_len = len(self.allocated)
			self.allocated.add(number)
			new_len = len(self.allocated)
			if old_len == new_len - 1:
				self.dirty = True
			else:
				# assert False
				pass
			# self.dirty = True
			if self.parent is not None:
				self.parent.update(self.number, STATUS.COMMIT)
		elif status == STATUS.DELETE:
			assert number in self.allocated
			self.allocated.remove(number)
			if len(self.allocated) == 0:
				# wait 30 seconds
				self.pending = True
				# and delete HiStore.info and dir
				self.unlink()
				if self.parent is not None:
					self.parent.update(self.number, STATUS.DELETE)
	
	def unlink(self):
		"""Delete of CRUD."""
		self.full_path.unlink()
		if not (str(self.full_path.parent) == self.store.root):
			assert self.parent is None
			self.full_path.parent.unlink()
		
	def persist(self):
		if not self.dirty:
			return
		if self.parent is not None:
			os.makedirs(self.full_path.parent, exist_ok=True)
		with open(self.full_path, 'w') as fp:
			d = {'type': 'branch', 'allocated': tuple(self.allocated)}
			fp.write(json.dumps(d))
		self.dirty = False
		
	def persist_all(self):
		self.persist()
		if self.parent is not None:
			self.parent.persist_all()
		
	def exists(self):
		return self.full_path.exists()
	
	
class LeafPage(object):
	branch: BranchPage
	path_string: str
	
	def __init__(self, number, store):
		self._flush_actions = []
		self.number = number
		self.store = store
		if type(number) is int:
			self.path_string = number_to_path_string(number)
		else:
			self.path_string = number
		self.path = Path(self.path_string)
		
	def exists(self) -> bool:
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
				k = HiStoreKey(self.path_string, x['type'], timedelta(seconds=self.store._default_timeout), self.path)
			else:
				k = HiStoreKey(self.path_string, x['type'], 0, self.path)
			return k
		
	def flush(self) -> List[Tuple]:
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

	__slots__ = ('_flush_actions', 'number', 'store', 'path_string', 'path')


class HiStoreKey:
	page: LeafPage
	type: str  # content | reservation
	path: str
	expiry: timedelta
	
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
	pagecache: Dict[int, LeafPage]
	branch_pages: Dict[str, BranchPage]
	
	def __init__(self, root: str):
		self._default_timeout = 30 # seconds
		self.root = root
		self.pagecache = {}
		self.branch_pages = {}
		self.freepage = None
		if not Path(root).exists():
			os.makedirs(Path(root))
		
		self.root_braanch = self.get_branch_page('')

	def allocate(self) -> HiStoreKey:
		p = self.find_next_page()
		k = HiStoreKey(p.path_string, 'reservation', timedelta(seconds=self._default_timeout), p)
		return k
	
	def resolve(self, key: int) -> HiStoreKey:
		p, f = self._get_page(key)
		k = HiStoreKey(p.path_string, 'content', timedelta(seconds=self._default_timeout), p)
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
	
	def _get_page(self, number, reservation=False) -> Tuple[LeafPage, bool]:
		new_page = False
		if number in self.pagecache:
			return (self.pagecache[number], False)
		p = LeafPage(number, self)
		pb = str(PurePosixPath(p.path).parent)
		p.branch = self.get_branch_page(pb)
		x = p.read()
		if x is None:
			pb2 = int(p.path_string[:-2].replace('/', ''), 16)
			p.branch.update(pb2, STATUS.COMMIT)
			os.makedirs(Path(self.root, p.path), exist_ok=True)
			with open(Path(self.root, p.path, "HiStore.info"), 'w') as fp:
				if reservation:
					y = {'type': 'reservation'}
					new_page = True  # TODO
				else:
					y = {'type': 'content'}
				fp.write(json.dumps(y))
			x = p.read()
			p.branch.persist_all()
		else:
			pb2 = int(p.path_string[:-2].replace('/', ''), 16)
			p.branch.update(pb2, STATUS.COMMIT)
			p.branch.persist_all()
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
			dp = LeafPage(x, self)
			if dp.exists():
				r.append(dp.path_string)
			else:
				break
			x = x + 1
		return r

	def get_branch_page(self, s):
		if s in self.branch_pages.keys():
			return self.branch_pages[s]
		x = BranchPage(s, self)
		if x.exists():
			x.read()
		else:
			x.create()
		self.branch_pages[s] = x
		return x
		

class HiStoreWriter(object):
	filename: str
	path: Path
	store: LeafPage
	
	def __init__(self, filename, path, store):
		self.filename = filename
		self.path = Path(path, filename)
		self.key_path = path
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
			with open(Path(self.key_path, "HiStore.info"), 'w') as fp:
				y = {'type': 'content'}
				fp.write(json.dumps(y))
				
			pb = int(str(self.key_path)[-2:], 16)
			self.store.branch.update(pb, STATUS.COMMIT)
			self.store.branch.persist_all()

			self.fp.close()
			self.fp = None


class HandleError(Exception):
	pass


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
			raise HandleError(self)

	def close(self):
		if self.fp is not None:
			self.fp.close()
			self.fp = None
