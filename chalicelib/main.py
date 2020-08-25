#!/usr/bin/env python

from string import capwords

from .mlb import launch as get_mlb
#from .ncaaf_ncaa import get as get_ncaaf
from .nhl import get as get_nhl
from .reset_lib import joinOr, NoGameException, NoTeamException, DabException

def get_team(team,debug=False):

	hold = None
	retList = None
	opts = []
		
	#fns = {"mlb":get_mlb,"football":get_ncaaf,"nhl":get_nhl}
	fns = {"mlb":get_mlb,"nhl":get_nhl}
	
	# first, try if the sport's defined.
	try:
		(team,sport) = sport_strip(team)
		if debug:
			print("got " + team + ", " + sport)
		if sport in fns:
			try:
				rv = fns[sport](team)
				if rv:
					return rtext(rv)
			#except NoGameException as e:
			#	hold = "No game today for " + tm + "."
			#except NoTeamException as e:
			#	hold = "No team " + tm + " found."
			except Exception as e:
				print("got exception: " + e.__class__.__name__ + " " + str(e))
				hold = e
	
	# if it isn't:
	except NoSportException:
		
		for k in fns:
			if debug:
				print("calling " + k, end=' ')
			
			try:
				rv = fns[k](team)
				if rv:
					return rtext(rv)
			except Exception as e:
				if debug:
					print(e.__class__.__name__, end=' ')
				
				if isinstance(e,NoTeamException) and not isinstance(hold,NoGameException): 
					# don't override an NGE.
					hold = "No team " + team + " found."
				elif isinstance(e,NoGameException):
					hold = e
				elif isinstance(e,DabException):
					opts.extend(e.teamOpts)
								
	if opts:
		retList = "Did you mean " + joinOr(opts) + "?"
	elif hold and isinstance(hold,NoGameException):
		
		if team in ('scoreboard','schedule'):
			retList = str(e)
		else:
			if team.upper() != team:	# don't override if it's something like NYY
				team = capwords(team)
			retList = "No game today for " + team + "."
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
	
	if len(retList) > 1:
		rtext = join(retList,'\n')
	else:
		rtext = join(retList," ")
	
	return rtext

	
def sport_strip(team):
	"""If sport is specified either first or last, return team plus it as a tuple. If not, throw Exception."""
	line = team.strip().lower()
	
	#if line.endswith("football"):
	#	return (team[:-8].strip(),"football")
	#elif line.startswith("football "):
	#	return (team[9:].strip(),"football")
	#elif line.endswith("hockey"):
	if line.endswith("hockey"):
		return (team[:-6].strip(),"nhl")
	elif line.startswith("hockey "):
		return (team[7:].strip(),"nhl")
	elif line.endswith("nhl"):
		print("did dis")
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
