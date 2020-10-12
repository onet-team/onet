from sqlalchemy import Column, Integer, String, Sequence
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base

import sqlalchemy

from pathlib import Path as FilePath

Base = declarative_base()


class UUID(Base):
	__tablename__ = 'uuid_to_key_map'
	# TODO Not sure if we need an id primary key
	id = Column(Integer, Sequence('uuid_id_seq'), primary_key=True)
	uuid = Column(String(50))
	key = Column(String(50))
	type = Column(String(10))

	types = ['version', 'entries', 'attr', 'acls', 'chunks']
	

class GUID(Base):
	__tablename__ = 'guid_to_key_map'
	# TODO Not sure if we need an id primary key
	id = Column(Integer, Sequence('guid_id_seq'), primary_key=True)
	guid = Column(String(50))
	key = Column(String(50))
	type = Column(String(10))
	
	types = ['File', 'Directory', 'Chunk']  # chunk is for content-addressable-store


class Cache:
	def __init__(self, path, space_name):
		self.parent_path = path
		self.space_name  = space_name
		self.path = FilePath(path, space_name, "cache.sqlite")
		self.engine = create_engine('sqlite:///'+str(self.path), echo=True)
		self._new_store = False
		
		if not self.path.exists():
			Base.metadata.create_all(self.engine)
			self._new_store = True
		
		Session = sessionmaker(bind=self.engine)
		self.session = Session()
	
	def record_uuid(self, uuid, key, type_):
		x = UUID(uuid=uuid, key=key, type=type_)
		self.session.add(x)

	def record_guid(self, uuid, key, type_):
		x = GUID(uuid=uuid, key=key, type=type_)
		self.session.add(x)
