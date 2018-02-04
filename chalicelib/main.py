#!/usr/bin/env python

from string import join

from resetter import launch as get_mlb
from ncaaf_ncaa import get as get_ncaaf
from nhl import get as get_nhl
from reset_lib import NoGameException	
	
def get_team(team):

	hold = False
	retList = None
		
	
	try:
		(tm,sport) = sport_strip(team)
		print "got " + tm + ", " + sport
		if sport == "nhl":
			try:
				retList = get_nhl(tm)
			except NoGameException as nge:
				hold = str(nge)
		elif sport == "mlb":
			try:
				retList = get_mlb(tm)
			except NoGameException as nge:
				hold = str(nge)
		elif sport == "football":
			try:
				retList = get_ncaaf(tm)
			except NoGameException as nge:
				hold = str(nge)
	
	except NoSportException:
		
		try:
			retList = get_mlb(team,True)
		except NoGameException as nge:
			hold = str(nge)

		if not retList:		# it's None
			try:
				retList = get_ncaaf(team)
			except NoGameException as nge:
				hold = str(nge)	# it'll override in a Miami situation, but that's OK.
		
		if not retList:
			try:
				retList = get_nhl(team)
			except NoGameException as nge:
				hold = str(nge)
		
	if not retList:
		if hold:
			retList = hold
		else:
			if team.startswith("my "):
				team = "your " + team[3:]
			elif team.startswith("our "):
				team = "your " + team[4:]
			retList = "I'm sorry, I can't reset " + team + "."
	
	if retList and (retList.__class__ != list):
		retList = [retList]
	
	if len(retList) == 1:
		rtext = retList[0]
	else:
		rtext = join(retList," ")
	
	return rtext

	
def sport_strip(team):
	"""If sport is specified either first or last, return team plus it as a tuple. If not, throw Exception."""
	line = team.strip().lower()
	
	if line.endswith("football"):
		return (team[:-8].strip(),"football")
	elif line.startswith("football "):
		return (team[9:].strip(),"football")
	elif line.endswith("hockey"):
		return (team[:-6].strip(),"nhl")
	elif line.startswith("hockey "):
		return (team[7:].strip(),"nhl")
	elif line.endswith("nhl"):
		print "did dis"
		return (team[:-3].strip(), "nhl")
	elif line.startswith("nhl "):
		return (team[4:].strip(), "nhl")
	elif line.endswith("mlb"):
		return (team[:-3].strip(), "mlb")
	elif line.startswith("mlb "):
		return (team[4:].strip(), "mlb")
	elif line.endswith("baseball"):
		return (team[:-8].strip(), "mlb")
	elif line.startswith("baseball "):
		return (team[9:].strip(),"mlb")
	
	raise NoSportException()


class NoSportException(Exception):
	pass