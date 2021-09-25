#!/usr/bin/env python

import urllib.request, urllib.error, urllib.parse, json, traceback, time
from datetime import datetime, timedelta
from .reset_lib import joinOr, sentenceCap, NoGameException, NoTeamException
#from .ncaa_lib import ncaaNickDict, displayOverrides, iaa, validFbSet

# when, during the season, we go from EDT to EST.
# correct way to do this is with tzinfo, but I'd like to avoid packaging extra libraries,
# and we have to manually set the WEEK_1_2_FLIP_UTC value every year anyway.
DST_FLIP_UTC = datetime(2021,10,31,6,0)

# what we expect the API to give us.  EST/EDT, most likely.
API_TZ_STD_DT = (-5,-4)

SCOREBOARD_URL = "http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"

__MOD = {}


def get_scoreboard(file=None,iaa=False,debug=False):
	"""Get scoreboard from site, or from file if specified for testing."""
	
	if file:
		print ("Using scoreboard from file: " + file)
		with open(file) as f:
			sb = json.load(f)
	else:
		
		if iaa:
			raise NoGameException("NCAAF_ESPN module can't get I-AA scores for now.")
		
		if debug:
			print(SCOREBOARD_URL)
		try:
			fh = urllib.request.urlopen(SCOREBOARD_URL)
			sb = json.load(fh)
		except urllib.error.HTTPError as e:
			if e.code == 404:
				raise NoGameException("Scoreboard was HTTP 404 Not Found. This probably means the season is over.\n")	
			else:
				raise e
		except Exception as e:
			raise e
		finally:
			fh.close()

	return sb

def find_game(sb,team):
	"""Passed scoreboard dict and team string, get game."""

	for event in sb['events']:
		if test_game(event,team):
			return event

	return None

def test_game(game,team):
	"""Broken out so we can test for all kinds of variations once we build the variation list."""
	return (team.lower() in [game["competitions"][0]["competitors"][0]["team"]["location"].lower(),
		game["competitions"][0]["competitors"][1]["team"]["location"].lower(),
		game["competitions"][0]["competitors"][0]["team"]["displayName"].lower(),
		game["competitions"][0]["competitors"][1]["team"]["displayName"].lower(),
		game["competitions"][0]["competitors"][0]["team"]["abbreviation"].lower(),
		game["competitions"][0]["competitors"][1]["team"]["abbreviation"].lower()])

def game_loc(game):
	
	#return "at " + game["home"]["names"]["short"]

	return "in " + game["competitions"][0]["venue"]["address"]["city"]
	"""sp = game["location"].rsplit(",",2)
	if len(sp) != 3:
		# something that definitely isn't stadium, city, state, so just return it all
		return "at " + game["location"].strip()	
	else:
		# if this matches either no commas or a "Memorial Stadium (Lincoln, NE)" pattern, it's standard
		# regex would be simpler, but I'd like to save importing re if I can
		stsp = sp[0].strip().split(",")
		if ((len(stsp) == 1) or ((len(stsp) == 2) and ("(" in stsp[0]) and stsp[1].endswith(")"))):
			return "in " + sp[1].strip()
		else:
			# it's something messy, send it all back.
			return "at " + game["location"].strip()	
	"""

def rank_name(team):
	
	#return 	# could also be displayName which is full name
	
	pref = team["team"]["location"]
	#if pref.lower() in displayOverrides:		pref = displayOverrides[raw.lower()]
	
	if team["curatedRank"]['current'] == 99:
		return pref
	else:
		return "#" + str(team["curatedRank"]['current']) + " " + pref


def scoreline(game):
	# flip home first if they're leading, otherwise away-first convention if it's tied
	t1 = game["competitions"][0]["competitors"][0]
	t2 = game["competitions"][0]["competitors"][1]
	if int(t1["score"]) > int(t2["score"]):
		gleader = t1
		gtrailer = t2
	else:
		gleader = t2
		gtrailer = t1
	
	return (rank_name(gleader) + " " + gleader["score"].strip() + ", " + rank_name(gtrailer) + " " + gtrailer["score"].strip())

def spaceday(game,sayToday=False):
	now = datetime.utcnow()
	#system_utc_offset_hours = (time.timezone if (time.localtime().tm_isdst == 0) else time.altzone) / 60 / 60 * -1
	#if (now < DST_FLIP_UTC):
	#	now += timedelta(hours=API_TZ_STD_DT[1])
	#else:
	#  	now += timedelta(hours=API_TZ_STD_DT[0])
	# so now is in ET to compare with the game day.
	if (now.strftime('%Y-%m-%d') == game['competitions'][0]['startDate'].split('T')[0]):
		if sayToday:
			return ' today'
		else:
			return ''
	else:
		return ' ' + datetime.strptime(game['competitions'][0]['startDate'].split('T')[0],'%Y-%m-%d').strftime("%A")
	

def status(game):

	if game == None:
		return None
	
	statusnode = game["competitions"][0]["status"]
	
	if statusnode["type"]["name"] == "STATUS_FINAL":
		status = "Final " + game_loc(game) + ", " + scoreline(game) 
		if statusnode["type"]["detail"].endswith("OT)"):
			status += statusnode["type"]["detail"].split("/")[1]
		status += "."
		
	elif statusnode["type"]["name"] == "STATUS_IN_PROGRESS":
		
		status = scoreline(game) 
		#if game["currentPeriod"].strip() == "Halftime":
		#	status += " at halftime "
		#elif game["currentPeriod"].startswith("End"):
		#	status += ", " + game["currentPeriod"].strip().lower() + " quarter "
		#elif game["currentPeriod"].strip().endswith("OT"):
		#	status += " in " + game["currentPeriod"].strip() + " "
		#else:
		status += ", " + statusnode["displayClock"].strip() + " to go in the " + str(statusnode["period"]) + " quarter "
		status += game_loc(game) + "."
		
	elif statusnode["type"]["name"] == "STATUS_SCHEDULED":
		
		status = rank_name(game["competitions"][0]['competitors'][1]) + " plays " + rank_name(game["competitions"][0]['competitors'][0]) + " at " + game["status"]["type"]["shortDetail"].strip() + spaceday(game) + " " + game_loc(game) + "."
	else:

		status = "HELP! I don't understand game status[type][name] '" + statusnode["type"]["name"] + "' for " + rank_name(game["competitions"][0]['competitors'][1]) + " vs. " + rank_name(game["competitions"][0]['competitors'][0]) + "."

	if 0:
		if 1:
			pass
		elif game["gameState"] in ("cancelled","postponed"):
			status = rank_name(game["away"]) + " vs. " + rank_name(game["home"]) + " originally scheduled for" + spaceday(game,sayToday=True) + " " + game_loc(game) + " is " + game["gameState"] + "."
		elif game["gameState"] in ("delayed"):
			status = rank_name(game["away"]) + " vs. " + rank_name(game["home"]) + " " + game_loc(game) + " is " + game["gameState"] + "."
		
			
	return sentenceCap(status)


def get(team,forceReload=False,debug=False,file=None):
	
	global __MOD

	tkey = team.lower().strip()
	
	#sb = get_scoreboard()
	if debug:
		print("tkey: " + tkey + ", ", end="")
	
	"""if (tkey in iaa) or (tkey in ncaaNickDict and ncaaNickDict[tkey] in iaa):
		if debug: 
			print ("I-AA load: ", end="")
		sb = get_scoreboard(iaa=True,debug=debug)
	elif tkey not in validFbSet:
		raise NoTeamException(tkey + " is not a valid team.")
	"""
	if 0 == 1:
		pass
	else:
		if forceReload \
				or ("ncaafsb" not in __MOD) \
				or (("ncaafsbdt" in __MOD) and (datetime.utcnow() - __MOD["ncaafsbdt"] > timedelta(minutes=1))) \
				or (("ncaafsb" in __MOD) and (("ncaaffile" not in __MOD) or (file != __MOD["ncaaffile"]))):
			if debug:
				print ("fresh load: ", end="")
			__MOD["ncaaffile"] = file
			__MOD["ncaafsb"] = get_scoreboard(debug=debug,file=file)
			__MOD["ncaafsbdt"] = datetime.utcnow()
		else:
			if debug:
				print ("cached: ", end="")
			pass

		sb = __MOD["ncaafsb"]
	
	
	game = find_game(sb,team)
	
	if game:
		return status(game)
	"""elif (tkey in ncaaNickDict):
		if (ncaaNickDict[tkey].__class__ == list):
			return "For " + team + ", please choose " + joinOr(ncaaNickDict[tkey]) + "."
		else:
			game = find_game(sb,ncaaNickDict[tkey])
			if game:
				return status(game)
	"""
	
	# fallthru
	ret = "No game this week for " + team
	if ret[-1] != ".":
		ret += "."
		
	raise NoGameException(ret)

	
