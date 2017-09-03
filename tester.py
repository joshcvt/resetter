#!/usr/bin/env python

from chalicelib.resetter import launch

print "rewind:"
print str(launch("WSH",rewind=True))
print str(launch("SD",rewind=True))

print "today:"
print str(launch("WSH"))
print str(launch("SD"))

print "ffwd:"
print str(launch("WSH",ffwd=True))
print str(launch("SD",ffwd=True))

print "bad team:"
print str(launch("asdfas"))