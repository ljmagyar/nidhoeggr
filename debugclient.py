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

def getMod():
	return choice([
			'gpl',
			'gpl1955',
			'gpl1965'
	])

def getTrack():
	return choice([
			'monza',
			'rouen',
			'pants',
			'nurburg',
			'wglen',
			'thereisnosuchtrack'
	])

c = nidhoeggr.Client('Dummy %f' % (random()),'localhost')
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
			getMod(),
			'0',
			'1,1,1,1',
			'20',
			getTrack(),
			'1',
			'900',
			'4',
			'1',
			'0',
			'',
			getFirstName(),
			getLastName(),
			str(randint(0,6)),
			str(randint(1,3)),
			'gpl1965',
			str(randint(0,28)),
			str(randint(0,15))
		]])
for i in range(randint(1,10)):
	c = nidhoeggr.Client('Dummy %f' % (random()),'localhost')	
	j = nidhoeggr.RequestSender(c,[[
			'join',
			r.result[0][0],
			c.client_id,
			getFirstName(),
			getLastName(),
			str(randint(0,6)),
			str(randint(1,3)),
			getMod(),
			str(randint(0,28)),
			str(randint(0,15))
	]])

f = nidhoeggr.RequestSender(c,[['req_full',c.client_id]])
for row in f.result:
	if row[0]=='R':
		print row[1]
	else:
		print "\t"+str(row)
