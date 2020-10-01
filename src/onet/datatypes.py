# datatypes.py
from typing import Dict, Any


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
			aclstr = 'acl-%d' % count
			r[aclstr] = acl.to_dict()
			acl.name = aclstr
		if len(self.inherits):
			inharr = [x.version for x in self.inherits.keys()]
			r['inherits'] = inharr
			
			for k, v in self.inherits.items():
				print(k, v)
				r['inherit-%s' % k] = v
		return r


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
	attributes: str  # dict of Attributes
	previous: list  # of uuids/versions of old versions
	
	def __init__(self, name, uuid, acl_uuid, node):
		self.name = name
		self.uuid = uuid
		self.acl = acl_uuid
		self.node = node
		self.previous = []
		self.attributes = ''
	
	def to_dict(self):
		r = {}
		version = {'uuid': self.uuid, 'name': self.name, 'acl': self.acl}
		r['version'] = version
		if len(self.previous):
			r['previous'] = self.previous
		info = {}
		if self.node.is_dir():
			info['entries'] = self.node.uuid
		# elif self.node.is_file():
		info['attributes'] = self.attributes
		return r


class Entries:
	entries: list
	
	def __init__(self):
		self.entries = []
	
	def to_dict(self):
		r = {}
		count = len(self.entries)
		entrylist = {'count': count}
		r['entrylist'] = entrylist
		for each in range(count):
			entry = self.entries[each]
			entstr = 'entry-%d' % count
			r[entstr] = entry.to_dict()
		return r


class Entry:
	pass


class ChunkEntry(Entry):
	uuid: str
	filename: str
	key: str  # ??
	
	def __init__(self):
		pass

	def to_dict(self):
		r = {}
		
		return r


class ExternalEntry(Entry):
	uuid: str
	filename: str
	key: str # ??
	
	def __init__(self):
		pass


class StorageEntry(Entry):
	uuid: str
	filename: str
	key: str # ??
	
	def __init__(self):
		pass


class NormalEntry(Entry):
	uuid: str
	filename: str
	key: str # ??
	
	def __init__(self):
		pass


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


class Attributes:
	version: Version
	attr: Dict[str, AttributeValue]
	
	def __init__(self, version):
		self.attr = {}
		self.version = version
	
	def put(self, k, v):
		self.attr[k] = v
		pass
	
	def to_dict(self):
		r = {}
		count = len(self.attr)
		r['attributes'] = {'attributes': {'count': count}}
		r['meta'] = {'meta': {'version': self.version.name, 'uuid': self.version.uuid}}
		count = 0
		for k, v in self.attr.items():
			attrstr = 'attr-%d' % count
			r[attrstr] = {}
			r[attrstr]['name'] = k
			if v.type:
				r[attrstr]['type'] = v.type
			r[attrstr]['value'] = v.value
			if v.acl:
				r[attrstr]['acl'] = v.acl.name  # TODO make sure you call acl.to_dict before this
			count += 1
		return r


__all__ = ['User', 'Acls', 'Acl', 'InheritedAcl', 'Version',
           'Entries', 'Entry', 'ChunkEntry', 'ExternalEntry', 'StorageEntry', 'NormalEntry',
           'Chunks', 'AttributeValue', 'Attributes']
