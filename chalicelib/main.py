#!/usr/bin/env python

from string import join

from resetter import launch as get_mlb
from ncaaf_ncaa import get as get_ncaaf
from nhl import get as get_nhl

def get_team(team):
	"Generic fetch prioritization"
	
	line = team.strip().lower()
	
	if line.endswith("football"):
		retList = get_ncaaf(team[:-8].strip())
	elif line.endswith("hockey"):
		retList = get_nhl(team[:-6].strip())
	elif line.endswith("nhl"):
		retList = get_nhl(team[:-3].strip())
	elif line.endswith("mlb"):
		retList = get_mlb(team[:-3].strip())
	elif line.endswith("baseball"):
		retList = get_mlb(team[:-8].strip())
	else:	
		retList = get_mlb(team,True)
		if retList == None:
			# try football?
			retList = get_ncaaf(team)
		if retList == None:
			# how about hockey?
			retList = get_nhl(team)
	
	if retList and (retList.__class__ != list):
		retList = [retList]
	
	if retList == None:
		rtext = "I'm sorry, I can't reset " + team + "."
	elif len(retList) == 1:
		rtext = retList[0]
	else:
		rtext = join(retList," ")
	
	return rtext