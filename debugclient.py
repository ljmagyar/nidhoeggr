#!/usr/bin/env python2.2

from random import random, choice, randint

import nidhoeggr

def getFirstName():
	return choice([
			'Jim',
			'John',
			'Tom',
			'Jochen',
			'Christoph',
			'Phil'
	])

def getLastName():
	return choice([
			'Clark',
			'King',
			'DeMuer',
			'Rindt',
			'Frick',
			'Flack'
	])

c = nidhoeggr.Client('Dummy %f' % (random()),'ridcully.mine.nu')
r = nidhoeggr.RequestSender(c, [[
			"host", 
			c.client_id,
			'32766',
			'Dummy %f' % (random()),
			'Info 1',
			'Info 2',
			'Comment',
			'0',
			'0',
			'0',
			'0',
			'1111111',
			'111',
			'0',
			'gpl1965',
			'0',
			'1,1,1,1',
			'20',
			'monza',
			'1',
			'900',
			'4',
			'1',
			'0',
			'',
			getFirstName(),
			getLastName(),
			'1',
			'1',
			'gpl1965',
			str(randint(0,100)),
			str(randint(0,100))
		]])
for i in range(randint(1,10)):
	c = nidhoeggr.Client('Dummy %f' % (random()),'ridcully.mine.nu')	
	j = nidhoeggr.RequestSender(c,[[
			'join',
			r.result[0][0],
			c.client_id,
			getFirstName(),
			getLastName(),
			'1',
			'1',
			'gpl1965',
			str(randint(0,100)),
			str(randint(0,100))
	]])

f = nidhoeggr.RequestSender(c,[['req_full',c.client_id]])
for row in f.result:
	if row[0]=='R':
		print row[1]
	else:
		print "\t"+str(row)
