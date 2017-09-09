#!/usr/bin/env python

import urllib2, json, time
from datetime import datetime, timedelta
from reset_lib import ncaaNickDict, displayOverrides

SCOREBOARD_URL = "http://data.ncaa.com/jsonp/scoreboard/football/fbs/2017/WHAT_WEEK/scoreboard.html?callback=ncaaScoreboard.dispScoreboard"

# these are season (year) specific before/after times in UTC
# we specify week1/week2 because Week 1 is often more than a week. 
# From this time, though, we can trust that the rest of the weeks are in fact weeks.
WEEK_1_2_FLIP_UTC = datetime(2017,9,5,16,0)

# when, during the season, we go from EDT to EST.
# correct way to do this is with tzinfo, but I'd like to avoid packaging extra libraries,
# and we have to manually set the WEEK_1_2_FLIP_UTC value every year anyway.
DST_FLIP_UTC = datetime(2017,11,5,6,0)

# what we expect the API to give us.  EST/EDT, most likely.
API_TZ_STD_DT = (-5,-4)



def what_week():
	delta = datetime.utcnow() - WEEK_1_2_FLIP_UTC
	if delta.days < 0:
		return ("%02d" % (1,))
	else:
		return ("%02d" % ((delta.days/7)+2,))

def get_scoreboard(file=None):
	"""Get scoreboard from site, or from file if specified for testing."""
	
	if not file:
		opener = urllib2.build_opener()
		opener.addheaders = [('User-agent', 'Mozilla/5.0')]
		urllib2.install_opener(opener)
		week_url = SCOREBOARD_URL.replace("WHAT_WEEK",what_week())
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
	sp = game["location"].split(",")
	if len(sp) == 3:
		return "In " + sp[1].strip()	# probably city
	else:
		# something that isn't stadium, city, state, so just return it all
		return "At " + game["location"].strip()	

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

def spaceday_if_not_today(game):
	now = datetime.utcnow()
	#system_utc_offset_hours = (time.timezone if (time.localtime().tm_isdst == 0) else time.altzone) / 60 / 60 * -1
	if (now < DST_FLIP_UTC):
		now += timedelta(hours=API_TZ_STD_DT[1])
	else:
		now += timedelta(hours=API_TZ_STD_DT[0])
	# so now is in ET to compare with the game day.
	if (now.strftime('%Y-%m-%d') == game['startDate']):
		return ''
	else:
		return ' ' + datetime.strptime(game['startDate'],'%Y-%m-%d').strftime("%A")
	

def status(game):
	
	if game["gameState"] == "final":
		(loc_word, loc_loc) = game_loc(game).split(" ",1)
		status = "Final " + loc_word.lower() + " " + loc_loc + ", " + scoreline(game) + "."
		
	elif game["gameState"] == "live":
		
		status = game_loc(game) + ", " + scoreline(game) + ", " + game["timeclock"].strip() + " to go in the " + game["currentPeriod"].strip() + ". "
		
	elif game["gameState"] == "pre":
		
		status = game_loc(game) + ", " + rank_name(game["away"]) + " plays " + rank_name(game["home"]) + " at " + game["startTime"].strip() + spaceday_if_not_today(game) + "."
	
	return status


def get(team):
	
	sb = get_scoreboard()
	game = find_game(sb,team)
	if game:
		return status(game)
	else:
		return None
		