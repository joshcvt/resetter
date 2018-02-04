#!/usr/bin/env python

from chalicelib.ncaaf_ncaa import get
from chalicelib.reset_lib import NoGameException

print "Trying some teams that are likely to have midweek games, some early, and Hawaii (aloha).\n"

teams = ["Northern Ill.","Toledo","Western Michigan","MSU","VT","FSU","Tennessee","LSU","California","UCLA","Hawaii"]

for t in teams:
	try:
		print get(t)
	except NoGameException as nge:
		print str(nge)

print "Now: I-AA, Unclear, Doesn't Exist:"

teams = ["jmu","tigers","aasdfasdg"]

for t in teams:
	try:
		print get(t)
	except NoGameException as nge:
		print str(nge)

print "Make sure a reload works (and dump exception directly if not): " + str(get("VT",forceReload=True))
