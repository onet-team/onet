import os
import pathlib
import tempfile
import unittest

import onet


def walk(p):
	if not p.is_dir():
		# yield p
		return
	z = [x for x in p.iterdir()]
	yield from z
	for each in z:
		yield from walk(each)
		
		
class TestOnet(unittest.TestCase):
	def test_something(self):
		self.assertEqual(True, False)
	
	def test_import(self):
		tmpdirname = "Onet-001"
		if True:
		#with tempfile.TemporaryDirectory() as tmpdirname:
			print (tmpdirname)
			store = onet.OnetStore(tmpdirname)
			# store.remove('sample', recursive=True)
			
			y = pathlib.Path("sample")
			
			for each in walk(y):
				print(98, each)
				if each.is_dir():
					y_path = onet.Path('sample', each)
					# if not store.exists(y_path):
					store.mkdir(y_path, skip_if_exists=True)
					store.import_dir_stat(y_path, os.stat(y), move=False)
				else:
					y_path = onet.Path('sample', each)
					store.import_file_stat(y_path, os.stat(y), move=False)
			
			self.assertEqual(True, False)


if __name__ == '__main__':
	unittest.main()
