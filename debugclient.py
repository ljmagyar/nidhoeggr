#!/usr/bin/env python

from random import random, choice, randint
from sys import argv
from time import sleep

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
			'gpl55',
			'gpl65',
			'gplat',
			'gplbt',
			'gples',
			'gplfd',
			'gplfg'
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

def test(bool,ontrue,onfalse):
	if bool: return ontrue
	return onfalse

class DebugClient:

	def __init__(self, servername, serverport):
		self.servername = servername
		self.serverport = serverport

	def run(self, verbose=1, delay=None):
		while 1:
			c = nidhoeggr.Client('Dummy %f' % (random()),self.servername,self.serverport)
			r = nidhoeggr.RequestSender(c, [[
						"host", 
						c.client_id,
						'32766',
						'Dummy %f' % (random()),
						'Info 1',
						'Info 2',
						'Comment',
						str(randint(0,1)),
						str(randint(0,1)),
						str(randint(0,1)),
						str(randint(0,1)),
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
						str(randint(1,3)),
						str(randint(0,6)),
						getMod(),
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
						str(randint(1,3)),
						str(randint(0,6)),
						getMod(),
						str(randint(0,28)),
						str(randint(0,15))
				]])

			f = nidhoeggr.RequestSender(c,[['req_full',c.client_id]])
			if verbose:
				for row in f.result:
					print test(row[0]=='D', "\t", "")+str(row)
			if delay is not None:
				if delay>0:
					sleep(randint(0,delay))
			else:
				break

if __name__=="__main__":
	servername = "localhost"
	serverport = nidhoeggr.DEFAULT_RACELISTPORT
	if len(argv)==2:
		servername = argv[1]
	if len(argv)==3:
		serverport = string.atoi(argv[2])
	dc = DebugClient(servername, serverport)
	dc.run()

