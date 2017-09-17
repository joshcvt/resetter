#!/usr/bin/env python

from chalicelib.ncaaf_ncaa import get

print "Trying some teams that are likely to have midweek games, some early, and Hawaii (aloha).\n"


print str(get("Northern Ill."))
print str(get("Toledo"))
print str(get("Western Michigan"))
print str(get("VT"))
print str(get("FSU"))
print str(get("Tennessee"))
print str(get("LSU"))
print str(get("California"))
print str(get("UCLA"))
print str(get("Hawaii"))

print "\nI-AA: " + str(get("jmu"))
print "Unclear: " + str(get("tigers"))
print "Doesn't exist (should be None): " + str(get("sdagasdgas"))

print "Make sure a reload works: " + str(get("VT",forceReload=True))
