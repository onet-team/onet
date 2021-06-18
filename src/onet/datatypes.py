# datatypes.py
from typing import Dict, Any, Optional


class User:
	uuid: str
	
	def __init__(self, uuid):
		self.uuid = uuid


class Acls:
	
	def __init__(self, version, user, deny_first=True):
		self.deny_first = deny_first
		self.inherits = {}
		self.acls = []
	
	def to_dict(self):
		r = {}
		if self.deny_first:
			order = 'deny'
		else:
			order = 'allow'
		count = len(self.acls)
		acl = {'order': order, 'count': count}
		r['acl'] = acl
		for each in range(count):
			acl = self.acls[each]
			aclstr = 'acl-%d' % each
			r[aclstr] = acl.to_dict()
			acl.name = aclstr
		if len(self.inherits):
			inharr = [x.version for x in self.inherits.keys()]
			r['inherits'] = inharr
			
			for k, v in self.inherits.items():
				print(k, v)
				r['inherit-%s' % k] = v
		return r

	def from_dict(self, d):
		dacl = d['acl']
		order = dacl['order']
		if order == 'deny':
			self.deny_first = True
		elif order == 'allow':
			self.deny_first = False
		else:
			raise ValueError(order)
		count = int(dacl['count'])
		for each in range(count):
			aclstr = 'acl-%d' % each
			acld = d[aclstr]
			type_ = acld['type']
			principal = acld['principal']
			acl = Acl(type_, User(principal))
			self.acls.append(acl)
		# TODO inherits
		pass


class Acl:
	type: str
	principal: User
	name: str
	
	acl_types = ['read', 'write', 'append', 'list', 'delete', 'all', 'deny', 'allow']
	
	def __init__(self, type_, principal):
		self.type = type_
		self.principal = principal
	
	def to_dict(self):
		r = {'type': self.type, 'principal': self.principal.uuid}
		return r


class InheritedAcl:
	inherit_uuid: str
	acls: list  # of str i guess
	
	def __init__(self, inherit_uuid, acls):
		self.inherit_uuid = inherit_uuid
		self.acls = acls
	
	def to_list(self):
		r = [x for x in self.acls]
		return r


class Version:
	uuid: str
	name: str
	acl: str
	attributes: str  # a pointer to an attr file
	previous: list  # of uuids/versions of old versions
	entries: Optional[str]     # a pointer to an entries file
	
	def __init__(self, name, uuid, acl_uuid, node):
		self.name = name
		self.uuid = uuid
		self.acl = acl_uuid
		self.node = node
		self.previous = []
		self.attributes = ''
		self.entries = None
	
	def to_dict(self):
		r = {}
		if self.name is not None:
			version = {'uuid': self.uuid, 'name': self.name, 'acl': self.acl}
		else:
			version = {'uuid': self.uuid, 'acl': self.acl}  # TODO version string
		r['version'] = version
		if len(self.previous):
			r['previous'] = self.previous
		info = {}
		if self.node.is_dir():
			info['entries'] = self.node.last_ver  # TODO was uuid
		# elif self.node.is_file():
		info['attributes'] = self.attributes
		r['info'] = info
		return r
	
	def from_dict(self, d):
		version = d['version']
		self.uuid = version['uuid']
		self.name = version['name']
		self.acl = version['acl']
		
		info = d['info']
		if 'entries' in info:
			self.entries = info['entries']
		else:
			self.entries = None
		self.attributes = info['attributes']
		pass
	

class InvalidEntryException(Exception):
	pass


class Entries:
	entries: list
	version: str
	
	def __init__(self, version):
		self.entries = []
		self.version = version
	
	def to_dict(self):
		r = {}
		count = len(self.entries)
		entrylist = {'count': count, 'version': self.version}
		r['entrylist'] = entrylist
		for each in range(count):
			entry = self.entries[each]
			entstr = 'entry-%d' % each
			r[entstr] = entry.to_dict()
		return r

	def from_dict(self, d):
		if not ('entrylist' in d): return
		#
		entrylist = d['entrylist']
		self.version = entrylist['version']
		count = entrylist['count']
		for each in range(count):
			entstr = 'entry-%d' % (each)
			entry_value = d[entstr]
			# print(10141, entry_value)
			entry_type = entry_value['type']
			if entry_type == 'chunk':
				entry = ChunkEntry()
				entry.from_dict(entry_value)
			elif entry_type == 'external':
				entry = ExternalEntry()
				entry.from_dict(entry_value)
			elif entry_type == 'storage':
				entry = StorageEntry()
				entry.from_dict(entry_value)
			elif entry_type == 'normal':
				entry = NormalEntry()
				entry.from_dict(entry_value)
			else:
				raise InvalidEntryException(entry_value)

			self.entries.append(entry)

	def add(self, entry):
		self.entries.append(entry)
		
		
class Entry:
	pass


class ChunkEntry(Entry):
	uuid: str
	# filename: str
	# key: str  # ??
	
	def __init__(self):
		pass

	def to_dict(self):
		r = {}
		r['uuid'] = self.uuid
		return r
	
	def from_dict(self, d):
		self.uuid = d['uuid']
		assert d['type'] == 'chunk'


class ExternalEntry(Entry):
	"""
	An entry where the content is stored on the filesystem
	"""
	uuid: str
	filename: str
	# key: str # ??
	
	def __init__(self):
		pass
	
	def from_dict(self, d):
		self.uuid = d['uuid']
		self.filename = d['filename']
		assert d['type'] == 'external'


class StorageEntry(Entry):
	"""
	:storage_name: The uuid of the external store to get file from
	:uuid: The actual file  # TODO can this be a guid?
	
	:type storage_name: str
	"""
	uuid: str
	# filename: str
	storage_name: str
	
	def __init__(self):
		pass
	
	def from_dict(self, d):
		self.uuid = d['uuid']
		self.storage_name = d['storage_name']
		assert d['type'] == 'storage'


class NormalEntry(Entry):
	uuid: str
	filename: str
	key: str # ??
	
	def __init__(self):
		pass

	def to_dict(self):
		r = {}
		r['uuid'] = self.uuid
		r['filename'] = self.filename
		r['type'] = 'normal'
		return r
	
	def from_dict(self, d):
		assert d['type'] == 'normal'
		self.uuid = d['uuid']
		self.filename = d['filename']
	

class Chunks:
	pass


class AttributeValue:
	type: str
	value: Any
	acl: Acl
	
	def __init__(self, value, type=None, acl=None):
		self.value = value
		self.type = type
		self.acl = acl


class InheritedAttr(object):
	ref: str
	uuid: str
	
	pass


class Attributes:
	version: Version
	attr: Dict[str, AttributeValue]
	uuid: str
	
	def __init__(self, version):
		self.attr = {}
		self.version = version
	
	def put(self, k, v):
		self.attr[k] = v
		pass
	
	def to_dict(self):
		r = {}
		count = len(self.attr)
		r['attributes'] = {'count': count}
		r['meta'] = {'version': self.version.name, 'uuid': self.version.uuid}
		count = 0
		for k, v in self.attr.items():
			attrstr = 'attr-%d' % count
			r[attrstr] = {}
			r[attrstr]['name'] = k
			if v.type:
				r[attrstr]['type'] = v.type
			r[attrstr]['value'] = v.value
			if v.acl:
				if type(v.acl) is str:
					r[attrstr]['acl'] = v.acl
				else:
					r[attrstr]['acl'] = v.acl.name  # TODO make sure you call acl.to_dict before this
			count += 1
		return r
	
	def from_dict(self, d):
		a = d['attributes']
		count = a['count']
		meta = d['meta']
		if 'version' in meta:
			self.version = meta['version']
		if 'uuid' in meta:
			self.version_uuid = meta['uuid']
		attr = Attributes(self.version or self.version_uuid)
		for each in range(int(count)):
			attrstr = "attr-%d" % each
			attrd = d[attrstr]
			if "inherited" in attrd:
				attr = InheritedAttr()
				attr.ref = attrd['ref']
				attr.uuid = attrd['uuid']
			else:
				value1 = attrd['value']
				attr_value = AttributeValue(value1)
				if "acl" in attrd:
					attr_value.acl = attrd['acl']
				attr.put(attrd['name'], attr_value)
				self.attr[attrd['name']] = attr_value


__all__ = ['User', 'Acls', 'Acl', 'InheritedAcl', 'Version',
           'Entries', 'Entry', 'ChunkEntry', 'ExternalEntry', 'StorageEntry', 'NormalEntry',
           'Chunks', 'AttributeValue', 'Attributes']
