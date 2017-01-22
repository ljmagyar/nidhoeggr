Nidhoeggr - the iGOR racelist server
====================================

This is the server software used by the /iGOR/ racelist for the game /Grand
Prix Legends/.


Keep the community together
---------------------------

I release this code in the intend, that the code is shared on a public place
and the community is able to continue services regardless what is happening.
I hope it will not be used to split or fragment the community by providing
multiple competing servers e.g. from different leagues.


History
-------

Please note, that this GIT repository is the attempt to stitch together two
private CVS repositories.  So there is a commit in between, that is used to
plaster a gap (8c86c2cd22c43d8398316dff1225914596c2e920).

Also note, that the part about the master/slave reproduction was placed in
production but never was finished.  And while I assume, that iGOR accepts the
protocol version 1.1 as is, but does not actually implement the features for
it.  The part about GPLTV is completely unfinished work.


Installation
------------

You need python 2 on something UNIX-y (the server was never intended or tested
for e.g. windows - but it is known to run on Linux, Solaris, OpenBSD,
FreeBSD).  

Copy the `server.conf.sample` to `server.conf` and adjust as you see fit (e.g.
set your proper host name, change the port, ...).  

Start the server then with: `python server.py`.  While the server runs, it
logs to stdout and writes on changes in the data into `serverlist.cpickle` and
`racelist.cpickle`.

You don't need root privileges to run the server, so it's a good idea to use
some unprivileged user dedicated just for nidhoeggr for regular operations.


Copyright
---------

The /nidhoeggr/ server: (c) Copyright 2003-2005 Christoph Frick, iGOR
Development Group

The /scary/ protocol: Copyright (c) 2002-2004 Phil Flack, Christoph Frick,
iGOR Development Group

The code and documentation of this repository are shared under the GNU General
Public License v3 (GPLv3).
