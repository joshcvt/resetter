#!/usr/bin/env python

from chalicelib.ncaaf_ncaa import get

print "Trying some teams that are likely to have midweek games, some early, and Hawaii (aloha).\n"

print "MACtion:"
print str(get("Northern Ill.",True))
print str(get("Toledo",True))
print str(get("Western Michigan",True))

print "#goacc:"
print str(get("Wake Forest",True))
print str(get("VT",True))
print str(get("UVa",True))

print "SEC:"
print str(get("Tennessee",True))
print str(get("Mizzou",True))
print str(get("LSU",True))

print "Aloha:"
print str(get("Hawaii",True))

print "unclear:"
print str(get("tigers",True))

print "I-AA:"
print str(get("jmu",True))


print "Doesn't exist:"
print str(get("sdagasdgas",True))

print "Make sure the non-persistent path works:"
print str(get("VT"))
