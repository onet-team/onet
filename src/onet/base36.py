# https://stackoverflow.com/questions/1181919/python-base-36-encoding


def base36encode(number: int):
	if not isinstance(number, int):
		raise TypeError('number must be an integer')
	if number < 0:
		raise ValueError('number must be positive')
	
	alphabet, base36 = ['0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ', '']
	
	while number:
		number, i = divmod(number, 36)
		base36 = alphabet[i] + base36
	
	return base36 or alphabet[0]


def base36decode(number):
	return int(number, 36)


def test():
	print(base36encode(1412823931503067241))
	print(base36decode('AQF8AA0006EH'))
