#!/usr/bin/env python

import sys
import signal
import getopt

import nidhoeggr

def handle_shutdown(signal,frame):
	# check if the server already shuts down
	global server
	if server.inShutdown():
		print >>sys.stderr, "shutdown already in progress"
		return
	server.stop()
	sys.exit(0)

def usage(message=None,errorcode=0):
	if message is not None:
		print >>sys.stderr, message
		print >>sys.stderr, ""
	print >>sys.stderr, "Usage:"
	print >>sys.stderr, "server -s <servername> [-r <port>] [-b <port>]"
	print >>sys.stderr, "-s <servername>: IP or FQDN of the server"
	print >>sys.stderr, "-r <port>: port where the racelist server is listening (default=%d)" % nidhoeggr.DEFAULT_RACELISTPORT
	print >>sys.stderr, "-b <port>: port where the broadcast listen server is listening (default=%d)" % nidhoeggr.DEFAULT_BROADCASTPORT
	sys.exit(errorcode)

def main(argv=None):
	servername = None
	racelistport = nidhoeggr.DEFAULT_RACELISTPORT
	broadcastport = nidhoeggr.DEFAULT_BROADCASTPORT

	# check for arguments
	if argv==None:
		argv = sys.argv
	try:
		try:
			opts, args = getopt.getopt(argv[1:], "s:r:b:h")
		except getopt.error, msg:
			usage(msg, 1)

		for o,a in opts:
			if o in ("-h", "--help"): 
				usage()

			if o in ("-s", "--servername"):
				servername = a

			if o in ("-r", "--racelistport"):
				try:
					racelistport = string.long(a)
					assert( 0 < racelistport < 65536 )
				except Exception,e:
					usage("error in argument: expect value between 1 and 65535 for raceport (%s)" % e, 2)

			if o in ("-b", "--broadcastport"):
				try:
					broadcastport = string.long(a)
					assert( 0 < broadcastport < 65536 )
				except Exception,e:
					usage("error in argument: expect value between 1 and 65535 for broadcastport (%s)" % e, 2)
	except Exception, err:
		usage(err, 2)
	
	# servername is vital
	if servername is None:
		usage("missing argument: need servername - either give IP or FQDN", 2)

	# fire up the server
	global server
	server = nidhoeggr.Server(servername,racelistport,broadcastport)
	# set the signals the server listens on for the shutdown
	if hasattr(signal, "SIGINT"):
		signal.signal(signal.SIGINT, handle_shutdown)
	if hasattr(signal, "SIGTERM"):
		signal.signal(signal.SIGTERM, handle_shutdown)
	if hasattr(signal, "SIGKILL"):
		signal.signal(signal.SIGKILL, handle_shutdown)
	server.start()

if __name__=="__main__":
	sys.exit(main())

