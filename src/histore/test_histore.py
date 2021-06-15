import tempfile
import unittest
from fractions import Fraction

import unittest

import histore


class TestSum(unittest.TestCase):
	def test_list_int(self):
		"""
		Test that it can sum a list of integers
		"""
		data = [1, 2, 3]
		result = sum(data)
		self.assertEqual(result, 6)

	def test_list_fraction(self):
		"""
		Test that it can sum a list of fractions
		"""
		data = [Fraction(1, 4), Fraction(1, 4), Fraction(2, 4)]
		result = sum(data)
		self.assertEqual(result, 1)

	def test_histore(self):
		with tempfile.TemporaryDirectory() as tmpdirname:
			print (tmpdirname)
			hi = histore.HiStore(tmpdirname)
			for x in range(1, 512):
				key = hi.allocate()
				wr = hi.openWriter(key, "content")
				wr.write("a"*256)
				wr.close()
			# import subprocess
			# subprocess.call(['fdfind', '-d', '5'])
			
			i = input()
	
if __name__ == '__main__':
	unittest.main()

