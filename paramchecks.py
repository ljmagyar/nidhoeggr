#!/usr/bin/env python2.2

# FIXME: dont use general exceptions here

import string

def check_string(value):
	"""
	"""
	if len(value)>4096:
		return "string may not be longer than 4096 chars"
	return None

def check_boolean(value):
	"""
	"""
	try:
		bool = string.atoi(value)
		if not 0 <= bool <= 1:
			return "value is not boolean (0 or 1)"
	except:
		return "value is not boolean (0 or 1)"
	return None

def check_suint(value):
	"""
	"""
	try:
		suint = string.atoi(value)
		if not 0 <= suint <= 65535:
			return "value is no small unsigned integer"
	except:
		return "value is no small unsigned integer"
	return None

def check_chassisbitfield(value):
	"""
	"""
	return __bitfieldcheck(7,value)

def check_carclassbitfield(value):
	"""
	"""
	return __bitfieldcheck(3,value)

def __bitfieldcheck(length,value):
	"""
	"""
	if len(value)!=length:
		return "lenght must be 7 chars"
	for x in value:
		if not (x=='0' or x=='1'):
			return "only 1 and 0 chars are allowed"
	return None

def check_bandwidthfield(value):
	"""
	"""
	fields = string.split(value,',')
	if len(fields)!=4:
		return "expect 4 numbers separated with a kommata"
	try:
		for field in fields:
			string.atoi(field)
	except:
		return "expect 4 numbers separated with a kommata"
	return None

def check_ip(value):
	"""
	"""
	fields = string.split(value,'.')
	if len(fields)!=4:
		return "expect 4 numbers between 0 and 255 separated with a dot"
	try:
		for field in fields:
			num = string.atoi(field)
			if not 0<=num<=255:
				return "expect 4 numbers between 0 and 255 separated with a dot"
	except:
		return "expect 4 numbers between 0 and 255 separated with a dot"
	return None

