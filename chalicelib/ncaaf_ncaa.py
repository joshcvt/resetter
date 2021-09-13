#!/usr/bin/env python

import urllib.request, urllib.error, urllib.parse, json, traceback, time
from datetime import datetime, timedelta
from .reset_lib import joinOr, sentenceCap, NoGameException, NoTeamException
from .ncaa_lib import ncaaNickDict, displayOverrides, iaa, validFbSet


# these are season (year) specific before/after times in UTC
# we specify the week1/week2 break because Week 1 is often more than a week. 
# From this time, though, we can trust that the rest of the weeks are in fact Tuesday-Monday
# weeks -- even in bowl season, at least in 2016.
WEEK_1_2_FLIP_UTC = datetime(2021,9,7,16,0)

# when, during the season, we go from EDT to EST.
# correct way to do this is with tzinfo, but I'd like to avoid packaging extra libraries,
# and we have to manually set the WEEK_1_2_FLIP_UTC value every year anyway.
DST_FLIP_UTC = datetime(2021,10,31,6,0)

# what we expect the API to give us.  EST/EDT, most likely.
API_TZ_STD_DT = (-5,-4)

SCOREBOARD_URL = "https://data.ncaa.com/casablanca/scoreboard/football/fbs/" + str(WEEK_1_2_FLIP_UTC.year) + "/WHAT_WEEK/scoreboard.json"

__MOD = {}


def what_week():
	delta = datetime.utcnow() - WEEK_1_2_FLIP_UTC
	if delta.days < 0:
		return ("%02d" % (1,))
	else:
		return ("%02d" % ((delta.days/7)+2,))

def get_scoreboard(file=None,iaa=False):
	"""Get scoreboard from site, or from file if specified for testing."""
	
	if not file:
		week_url = SCOREBOARD_URL.replace("WHAT_WEEK",what_week())
		if iaa:
			week_url = week_url.replace("fbs","fcs")
		try:
			fh = urllib.request.urlopen(week_url)
		except urllib.error.HTTPError as e:
			if e.code == 404:
				raise NoGameException("Scoreboard was HTTP 404 Not Found. This probably means the season is over.\n"+week_url)	
			else:
				raise e
	else:
		fh = open(file)
		
	json_text = fh.read().decode(encoding='utf-8')
	return json.loads(json_text)

def find_game(sb,team):
	"""Passed scoreboard dict and team string, get game."""

	for game in sb['games']:
		if test_game(game['game'],team):
			return game['game']

	return None

def test_game(game,team):
	"""Broken out so we can test for all kinds of variations once we build the variation list."""
	return (team.lower() in [game["home"]["names"]["short"].lower(),
							 game["away"]["names"]["short"].lower(),
							 game["home"]["names"]["char6"].lower(),
							 game["away"]["names"]["char6"].lower()])

def game_loc(game):
	
	return "at " + game["home"]["names"]["short"]
	# TODO TODO TODO TODO TODO TODO game_loc
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
	
	return team['names']['short']
	# TODO TODO TODO TODO TODO TODO rank_name
	"""
	raw = team["nameRaw"].strip()
	
	if raw.lower() in displayOverrides:
		pref = displayOverrides[raw.lower()]
	else:
		pref = raw
		
	if team["teamRank"] == "0":
		return pref
	else:
		return "#" + team["teamRank"].strip() + " " + pref
	"""

def scoreline(game):
	# flip home first if they're leading, otherwise away-first convention if it's tied
	if int(game["home"]["score"]) > int(game["away"]["score"]):
		gleader = game["home"]
		gtrailer = game["away"]
	else:
		gleader = game["away"]
		gtrailer = game["home"]
	
	return (rank_name(gleader) + " " + gleader["score"].strip() + ", " + rank_name(gtrailer) + " " + gtrailer["score"].strip())

def spaceday(game,sayToday=False):
	now = datetime.utcnow()
	#system_utc_offset_hours = (time.timezone if (time.localtime().tm_isdst == 0) else time.altzone) / 60 / 60 * -1
	if (now < DST_FLIP_UTC):
		now += timedelta(hours=API_TZ_STD_DT[1])
	else:
		now += timedelta(hours=API_TZ_STD_DT[0])
	# so now is in ET to compare with the game day.
	if (now.strftime('%d-%m-%Y') == game['startDate']):
		if sayToday:
			return ' today'
		else:
			return ''
	else:
		return ' ' + datetime.strptime(game['startDate'],'%d-%m-%Y').strftime("%A")
	

def status(game):

	if game == None:
		return None
	
	elif game["gameState"] == "final":
		status = "Final " + game_loc(game) + ", " + scoreline(game) 
		if game["finalMessage"].endswith("OT)"):
			status += game.finalMessage.split()[-1]
		status += "."
		
	elif game["gameState"] == "live":
		
		status = scoreline(game) 
		if game["currentPeriod"].strip() == "Halftime":
			status += " at halftime "
		elif game["currentPeriod"].startswith("End"):
			status += ", " + game["currentPeriod"].strip().lower() + " quarter "
		elif game["currentPeriod"].strip().endswith("OT"):
			status += " in " + game["currentPeriod"].strip() + " "
		else:
			status += ", " + game["timeclock"].strip() + " to go in the " + game["currentPeriod"].strip() + " quarter "
		status += game_loc(game) + "."
		
	elif game["gameState"] == "pre":
		
		status = rank_name(game["away"]) + " plays " + rank_name(game["home"]) + " at " + game["startTime"].strip() + spaceday(game) + " " + game_loc(game) + "."
	
	elif game["gameState"] in ("cancelled","postponed"):
		status = rank_name(game["away"]) + " vs. " + rank_name(game["home"]) + " originally scheduled for" + spaceday(game,sayToday=True) + " " + game_loc(game) + " is " + game["gameState"] + "."
	
	elif game["gameState"] in ("delayed"):
		status = rank_name(game["away"]) + " vs. " + rank_name(game["home"]) + " " + game_loc(game) + " is " + game["gameState"] + "."
	
	else:
		status = "HELP! I don't understand game state '" + game["gameState"] + "' for " + rank_name(game["away"]) + " vs. " + rank_name(game["home"]) + "."
	
	return sentenceCap(status)


def get(team,forceReload=False,debug=False):
	
	global __MOD

	tkey = team.lower().strip()
	
	#sb = get_scoreboard()
	if debug:
		print("tkey: " + tkey + ", ", end="")
	
	if (tkey in iaa) or (tkey in ncaaNickDict and ncaaNickDict[tkey] in iaa):
		if debug: 
			print ("loading I-AA scoreboard from NCAA")
		sb = get_scoreboard(iaa=True)
	elif tkey not in validFbSet:
		raise NoTeamException(tkey + " is not a valid team.")
	else:
		if forceReload or ("sb" not in __MOD) or (("sbdt" in __MOD) and (datetime.utcnow() - __MOD["sbdt"] > timedelta(minutes=1))):
			if debug:
				print ("loading scoreboard from NCAA")
			__MOD["sb"] = get_scoreboard()
			__MOD["sbdt"] = datetime.utcnow()
		else:
			if debug:
				print ("using cached scoreboard")
			pass

		sb = __MOD["sb"]
	
	
	game = find_game(sb,team)
	
	if game:
		return status(game)
	elif (tkey in ncaaNickDict):
		if (ncaaNickDict[tkey].__class__ == list):
			return "For " + team + ", please choose " + joinOr(ncaaNickDict[tkey]) + "."
		else:
			game = find_game(sb,ncaaNickDict[tkey])
			if game:
				return status(game)
	
	# fallthru
	ret = "No game this week for " + team
	if ret[-1] != ".":
		ret += "."
		
	raise NoGameException(ret)

	
