#!/usr/bin/env python

from chalicelib.resetter import launch

print "Should see: standard, verbose for each game. 'Today' starts at rolloverTime.\n"

print "yesterday:"
print str(launch("WSH",rewind=True))
print str(launch("WSH",fluidVerbose=True,rewind=True))
print str(launch("SD",rewind=True))
print str(launch("SD",fluidVerbose=True,rewind=True))

print "today:"
print str(launch("WSH"))
print str(launch("WSH",fluidVerbose=True))
print str(launch("SD"))
print str(launch("SD",fluidVerbose=True))

print "tomorrow:"
print str(launch("WSH",ffwd=True))
print str(launch("WSH",fluidVerbose=True,ffwd=True))
print str(launch("SD",ffwd=True))
print str(launch("SD",fluidVerbose=True,ffwd=True))

print "bad team:"
print str(launch("asdfas"))
