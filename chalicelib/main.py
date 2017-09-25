#!/usr/bin/env python

from string import join

from resetter import launch as get_mlb
from ncaaf_ncaa import get as get_ncaaf


def get_team(team):
	"Generic fetch prioritization"
	
	if team.strip().lower().endswith("football"):
		retList = get_ncaaf(team[:-8].strip())
				
	else:	
		retList = get_mlb(team,True)
		if retList == None:
			# try football?
			retList = get_ncaaf(team)
	
	if retList and (retList.__class__ != list):
		retList = [retList]
	
	if retList == None:
		rtext = "I'm sorry, I can't reset " + team + "."
	elif len(retList) == 1:
		rtext = retList[0]
	else:
		rtext = join(retList," ")
	
	return rtext