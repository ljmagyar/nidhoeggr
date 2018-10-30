def check_string(value):
	"""
	"""
	if len(value)>4096:
		return "string may not be longer than 4096 chars"
	return None

def check_boolean(value):
	return __int_range_check(value,0,1)

def check_suint(value):
	return __int_range_check(value,0,65535)

def check_team(value):
	return __int_range_check(value,0,19)

def check_helmetcolour(value):
	return __int_range_check(value,0,15)

def check_nationality(value):
	return __int_range_check(value,0,28)

def check_maxload(value):
	return __int_range_check(value,0,999)

def check_class(value):
	return __int_range_check(value,1,3)

def check_racetype(value):
	return __int_range_check(value,0,5)

def check_sessiontype(value):
	return __int_range_check(value,0,1)

def check_players(value):
	return __int_range_check(value,0,20)

def check_chassisbitfield(value):
	return __bitfield_check(20,value)

def check_carclassbitfield(value):
	return __bitfield_check(3,value)

def check_bandwidthfield(value):
	fields = value.split(',')
	if len(fields)!=4:
		return "expect 4 numbers separated with a kommata"
	try:
		for field in fields:
			int(field)
	except ValueError:
		return "expect 4 numbers separated with a kommata"
	return None

def check_ip(value):
	fields = value.split('.')
	if len(fields)!=4:
		return "expect 4 numbers between 0 and 255 separated with a dot"
	try:
		for field in fields:
			num = int(field)
			if not 0<=num<=255:
				return "expect 4 numbers between 0 and 255 separated with a dot"
	except ValueError:
		return "expect 4 numbers between 0 and 255 separated with a dot"
	return None

def __int_range_check(value, min, max):
	try:
		i = int(value)
		if not min <= i <= max:
			return "value is not in valid range (%d-%d)" % (min,max)
	except ValueError:
		return "value is not in valid range (%d-%d)" % (min,max)
	return None

def __bitfield_check(length,value):
	"""
	"""
	if len(value)!=length:
		return "length must be %d chars" % (length)
	for x in value:
		if not (x=='0' or x=='1'):
			return "only 1 and 0 chars are allowed"
	return None

# vim:fdm=marker
