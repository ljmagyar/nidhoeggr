#!/usr/bin/env python2.2

import sys
import signal
import getopt

import nidhoeggr

def handle_shutdown(signal,frame):
	global server
	if server.inShutdown():
		print >>sys.stderr, "shutdown already in progress"
		return
	server.stop()
	sys.exit(0)

def main(argv=None):
	if argv==None:
		argv = sys.argv
	try:
		racelistport = nidhoeggr.DEFAULT_RACELISTPORT
		broadcastport = nidhoeggr.DEFAULT_BROADCASTPORT

		try:
			opts, args = getopt.getopt(argv[1:], "r:b:h")
		except getopt.error, msg:
			raise Exception(msg)

		for o,a in opts:
			if o in ("-h", "--help"): 
				print >>sys.stderr, "Usage:"
				print >>sys.stderr, "%s [-r <port>] [-b <port>]" % argv[0]
				print >>sys.stderr, "-r <port>: port where the racelist server is listening (default=%d)" % nidhoeggr.DEFAULT_RACELISTPORT
				print >>sys.stderr, "-b <port>: port where the broadcast listen server is listening (default=%d)" % nidhoeggr.DEFAULT_BROADCASTPORT
				return 0

			if o in ("-r", "--racelistport"):
				try:
					racelistport = string.atoi(a)
					assert( 0 < racelistport < 65536 )
				except Exception,e:
					raise Exception("expect value between 1 and 65535 for raceport (%s)" % e)

			if o in ("-b", "--broadcastport"):
				try:
					broadcastport = string.atoi(a)
					assert( 0 < broadcastport < 65536 )
				except Exception,e:
					raise Usage("expect value between 1 and 65535 for broadcastport (%s)" % e)
	except Exception, err:
		print >>sys.stderr, err
		print >>sys.stderr, "For help use -h"
		return 2
	
	global server
	server = nidhoeggr.Server(racelistport,broadcastport)
	signal.signal(signal.SIGINT, handle_shutdown)
	signal.signal(signal.SIGTERM, handle_shutdown)
	signal.signal(signal.SIGKILL, handle_shutdown)
	server.start()

if __name__=="__main__":
	sys.exit(main())

