#!/usr/bin/env python

import urllib2, json, time
from datetime import datetime, timedelta
from reset_lib import joinOr, sentenceCap, NoGameException
from ncaa_lib import ncaaNickDict, displayOverrides, iaa, validFbSet

SCOREBOARD_URL = "http://data.ncaa.com/jsonp/scoreboard/football/fbs/2017/WHAT_WEEK/scoreboard.html?callback=ncaaScoreboard.dispScoreboard"

# these are season (year) specific before/after times in UTC
# we specify the week1/week2 break because Week 1 is often more than a week. 
# From this time, though, we can trust that the rest of the weeks are in fact Tuesday-Monday
# weeks -- even in bowl season, at least in 2016.
WEEK_1_2_FLIP_UTC = datetime(2017,9,5,16,0)

# when, during the season, we go from EDT to EST.
# correct way to do this is with tzinfo, but I'd like to avoid packaging extra libraries,
# and we have to manually set the WEEK_1_2_FLIP_UTC value every year anyway.
DST_FLIP_UTC = datetime(2017,11,5,6,0)

# what we expect the API to give us.  EST/EDT, most likely.
API_TZ_STD_DT = (-5,-4)

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
		opener = urllib2.build_opener()
		opener.addheaders = [('User-agent', 'Mozilla/5.0')]
		urllib2.install_opener(opener)
		week_url = SCOREBOARD_URL.replace("WHAT_WEEK",what_week())
		if iaa:
			week_url = week_url.replace("fbs","fcs")
		fh = urllib2.urlopen(week_url)	
	else:
		fh = open(file)
	
	raw = fh.read()
	# now throw away the function call wrapper
	js = raw[raw.index('(')+1:raw.rindex(');')]
	return json.loads(js)

def find_game(sb,team):
	"""Passed scoreboard dict and team string, get game."""
	
	for day in sb["scoreboard"]:
		for game in day["games"]:
			if test_game(game,team):
				return game

	return None

def test_game(game,team):
	"""Broken out so we can test for all kinds of variations once we build the variation list."""
	return (game["home"]["nameRaw"].strip().lower() == team.lower() or game["away"]["nameRaw"].strip().lower() == team.lower())
	
def game_loc(game):
	sp = game["location"].rsplit(",",2)
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
		

def rank_name(team):
	
	raw = team["nameRaw"].strip()
	
	if raw.lower() in displayOverrides:
		pref = displayOverrides[raw.lower()]
	else:
		pref = raw
		
	if team["teamRank"] == "0":
		return pref
	else:
		return "#" + team["teamRank"].strip() + " " + pref

def scoreline(game):
	if int(game["home"]["currentScore"]) > int(game["away"]["currentScore"]):
		gleader = game["home"]
		gtrailer = game["away"]
	else:
		gleader = game["away"]
		gtrailer = game["home"]
	
	return (rank_name(gleader) + " " + gleader["currentScore"].strip() + ", " + rank_name(gtrailer) + " " + gtrailer["currentScore"].strip())

def spaceday(game,sayToday=False):
	now = datetime.utcnow()
	#system_utc_offset_hours = (time.timezone if (time.localtime().tm_isdst == 0) else time.altzone) / 60 / 60 * -1
	if (now < DST_FLIP_UTC):
		now += timedelta(hours=API_TZ_STD_DT[1])
	else:
		now += timedelta(hours=API_TZ_STD_DT[0])
	# so now is in ET to compare with the game day.
	if (now.strftime('%Y-%m-%d') == game['startDate']):
		if sayToday:
			return ' today'
		else:
			return ''
	else:
		return ' ' + datetime.strptime(game['startDate'],'%Y-%m-%d').strftime("%A")
	

def status(game):

	if game == None:
		return None
	
	elif game["gameState"] == "final":
		status = "Final " + game_loc(game) + ", " + scoreline(game) 
		if game["scoreBreakdown"][-1].strip() not in ("1","2","3","4"):
			status += " in " + game["scoreBreakdown"][-1].strip()
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
	
	else:
		status = "HELP! I don't understand game state '" + game["gameState"] + "' for " + rank_name(game["away"]) + " vs. " + rank_name(game["home"]) + "."
	
	return sentenceCap(status)


def get(team,forceReload=False):
	
	global __MOD

	tkey = team.lower().strip()
	
	#sb = get_scoreboard()
	if (tkey in iaa) or (tkey in ncaaNickDict and ncaaNickDict[tkey] in iaa):
		print "loading I-AA scoreboard from NCAA"
		sb = get_scoreboard(iaa=True)
	elif tkey not in validFbSet:
		return None
	else:
		if forceReload or ("sb" not in __MOD) or (("sbdt" in __MOD) and (datetime.utcnow() - __MOD["sbdt"] > timedelta(minutes=1))):
			print "loading scoreboard from NCAA"
			__MOD["sb"] = get_scoreboard()
			__MOD["sbdt"] = datetime.utcnow()
		else:
			print "using cached scoreboard"
			
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

	
