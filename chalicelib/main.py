#!/usr/bin/env python

from string import join

from resetter import launch as get_mlb
from ncaaf_ncaa import get as get_ncaaf
from nhl import get as get_nhl
from reset_lib import NoGameException, NoTeamException, DabException
	
def get_team(team,debug=False):

	hold = False
	retList = None
	opts = []
		
	fns = {"mlb":get_mlb,"football":get_ncaaf,"nhl":get_nhl}
	
	# first, try if the sport's defined.
	try:
		(tm,sport) = sport_strip(team)
		if debug:
			print "got " + tm + ", " + sport
		if sport in fns:
			try:
				retList = fns[k](tm)
			except NoGameException as e:
				hold = str(e)
			except NoTeamException as e:
				hold = "No team " + tm + " found."
	
	# if it isn't:
	except NoSportException:
		
		for k in fns:
			if debug:
				print "calling " + k,
			
			try:
				return rtext(fns[k](team))
			except Exception as e:
				if debug:
					print e.__class__.__name__,
				
				if isinstance(e,NoGameException):
					hold = str(e)
				elif isinstance(e,NoTeamException):
					hold = "No team " + team + " found."
				elif isinstance(e,DabException):
					opts.extend(teamOpts)
								
	if opts:
		retList = "Did you mean " + joinOr(opts) + "?"
	elif hold:
		retList = hold
	else:
		if team.startswith("my "):
			team = "your " + team[3:]
		elif team.startswith("our "):
			team = "your " + team[4:]
		retList = "I'm sorry, I can't reset " + team + "."
	
	return rtext(retList)
	

def rtext(retList):
	
	if not retList:
		retList = [""]
	elif (retList.__class__ != list):
		retList = [retList]
	
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