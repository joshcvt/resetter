#!/usr/bin/env python

#from chalicelib.ncaaf_ncaa import get
from chalicelib.ncaaf_espn import get
from chalicelib.reset_lib import NoGameException, NoTeamException

from argparse import ArgumentParser

args = ArgumentParser()
args.add_argument('--file', type=str, default='', help='Test input file to run against')
theargs = args.parse_args()

print ("Trying some teams that are likely to have midweek games, some early, and Hawaii (aloha).\n")

teams = ["Northern Illinois","Marshall","East Carolina","Virginia","MSU","VT","FSU","Tennessee","LSU","California","UCLA","Hawaii","Ohio","Princeton"]

for t in teams:
	try:
		print( get(t,debug=True,file=theargs.file) )
	except NoGameException as nge:
		print (str(nge))
	except NoTeamException as nte:
		print (str(nte))

print ("\nNow: I-AA, Unclear, Doesn't Exist:")

teams = ["jmu","tigers","aasdfasdg"]

for t in teams:
	try:
		print (get(t,debug=True))
	except NoGameException as nge:
		print (str(nge))
	except NoTeamException as nte:
		print (str(nte))

print ("\nMake sure a reload works (and dump exception directly if not): " + str(get("VT",forceReload=True)))
