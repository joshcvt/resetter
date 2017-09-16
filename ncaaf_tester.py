#!/usr/bin/env python

from chalicelib.ncaaf_ncaa import get

print "Trying some teams that are likely to have midweek games, some early, and Hawaii (aloha).\n"

print "MACtion:"
print str(get("Northern Ill."))
print str(get("Toledo"))
print str(get("Western Michigan"))

print "#goacc:"
print str(get("Wake Forest"))
print str(get("VT"))
print str(get("UVa"))

print "SEC:"
print str(get("Tennessee"))
print str(get("Mizzou"))
print str(get("LSU"))

print "Aloha:"
print str(get("Hawaii"))

print "unclear:"
print str(get("tigers"))

print "Doesn't exist:"
print str(get("sdagasdgas"))
