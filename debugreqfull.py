#!/usr/bin/env python

from random import random, choice, randint
from sys import argv
from time import sleep

from nidhoeggr import Client
from config import DEFAULT_RACELISTPORT


class ReqFull:

	def __init__(self, servername='localhost', serverport=DEFAULT_RACELISTPORT):
		self.servername = servername
		self.serverport = serverport

	def run(self):
		c = Client(self.servername,self.serverport)
		c.doLogin('Dummy %f' % (random()))
		result = c.doRequest([['req_full',c.client_id]])
		for row in result: print str(row)

if __name__=="__main__":
	servername = "localhost"
	serverport = DEFAULT_RACELISTPORT
	if len(argv)==2:
		servername = argv[1]
	if len(argv)==3:
		serverport = int(argv[2])
	dc = ReqFull(servername, serverport)
	dc.run()

