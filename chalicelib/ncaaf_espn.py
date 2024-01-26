#!/usr/bin/env python

import urllib.request, urllib.error, urllib.parse, json, traceback, time
from datetime import datetime, timedelta
from .reset_lib import joinOr, sentenceCap, NoGameException, NoTeamException, toOrdinal
from .ncaa_espn_lib import ncaaNickDict, displayOverrides, iaa, validFbSet

SCOREBOARD_ROOT_URL = "http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard"
# start with this to get weeks, then customize for this week and full scoreboard
#http://site.api.espn.com/apis/site/v2/sports/football/college-football/scoreboard?week=4&groups=80&limit=388&1577314600

# global for caching
__MOD = {}

# cache time for scoreboard
CACHE_INTERVAL = timedelta(minutes=1)

def get_scoreboard(file=None,iaa=False,debug=False):
	"""Get scoreboard from site, or from file if specified for testing."""
	
	FBS_GROUPS = "80"
	FCS_GROUPS = "81"
	
	SB_FORMAT_TAIL = '?week=%s&groups=%s&limit=388&%s'
	SB_FORMAT_NOWEEKTAIL = '?groups=%s&limit=388&%s'

	if file:
		print ("Using scoreboard from file: " + file)
		with open(file) as f:
			sb = json.load(f)
	else:
		
		if debug:
			print("Root: " + SCOREBOARD_ROOT_URL)
		
		try:
			scoreboardWeekUrl = "unconstructed"
			with urllib.request.urlopen(SCOREBOARD_ROOT_URL) as fh:
				sb = json.load(fh)
			
			now = datetime.now()
			if not sb:
				raise Exception("No scoreboard data returned.")
			elif sb['season']['type'] == 3:	
				if debug:
					print("Season is post-season.")
				scoreboardWeekUrl = SCOREBOARD_ROOT_URL + SB_FORMAT_NOWEEKTAIL % (FBS_GROUPS, now.timestamp().__str__())
			else:
				# get the week-based scoreboard
				
				for week in sb['leagues'][0]['calendar'][0]['entries']:			
					if datetime.strptime(week['endDate'],'%Y-%m-%dT%H:%MZ') > now:
						weekValue = week['value']
						break

				# scoreboardWeekUrl = SCOREBOARD_ROOT_URL + "?week=" + str(weekValue) + "&groups=" + FBS_GROUPS + "&limit=388&" + now.timestamp().__str__()
				if iaa:
					scoreboardWeekUrl = SCOREBOARD_ROOT_URL + SB_FORMAT_TAIL % (str(weekValue), FCS_GROUPS, now.timestamp().__str__())
				else:
					scoreboardWeekUrl = SCOREBOARD_ROOT_URL + SB_FORMAT_TAIL % (str(weekValue), FBS_GROUPS, now.timestamp().__str__())
				if debug:
					print("URL: " + scoreboardWeekUrl)
				with urllib.request.urlopen(scoreboardWeekUrl) as fh:
					sb = json.load(fh)
			# we still don't have I-AA postseason scoreboard.
		except urllib.error.HTTPError as e:
			if e.code == 404:
				raise NoGameException("Scoreboard HTTP 404. This probably means the season is over. Root = " + SCOREBOARD_ROOT_URL + ", week " + scoreboardWeekUrl + "\n")	
			else:
				raise e
		except Exception as e:
			raise e
		finally:
			fh.close()

	return sb

def find_game(sb,team,debug=False):
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
	
	return "in " + game["competitions"][0]["venue"]["address"]["city"]
	# probably want to get stadium and city for neutral-site games

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
	(now, utcnow) = (datetime.now(),datetime.utcnow())
	utcdiff = (utcnow - now).seconds
	startLocal = datetime.strptime(game['competitions'][0]['startDate'], "%Y-%m-%dT%H:%MZ") - timedelta(seconds=utcdiff)
	if startLocal.date() == now.date():
		if sayToday:
			return ' today'
		else:
			return ''
	else:
		return ' ' + startLocal.strftime("%A")
	

def status(game):

	if game == None:
		return None
	
	statusnode = game["competitions"][0]["status"]
	
	if statusnode["type"]["name"] == "STATUS_FINAL":
		status = "Final " + game_loc(game) + ", " + scoreline(game) 
		if statusnode["type"]["detail"].endswith("OT)"):
			status += statusnode["type"]["detail"].split("/")[1]
		status += "."
		
	elif statusnode["type"]["name"] == "STATUS_SCHEDULED":
		
		status = rank_name(game["competitions"][0]['competitors'][1]) + " plays " + rank_name(game["competitions"][0]['competitors'][0]) + " at " + game["status"]["type"]["shortDetail"].split(' - ')[1] + spaceday(game) + " " + game_loc(game) + "."
	
	elif statusnode["type"]["name"] == "STATUS_POSTPONED":
		status = rank_name(game["competitions"][0]['competitors'][1]) + " vs. " + rank_name(game["competitions"][0]['competitors'][0]) + " is postponed."
	elif statusnode["type"]["name"] == "STATUS_CANCELED":
		status = rank_name(game["competitions"][0]['competitors'][1]) + " vs. " + rank_name(game["competitions"][0]['competitors'][0]) + " has been cancelled."
	
	else:
		status = scoreline(game)
		
		if statusnode["type"]["name"] == "STATUS_HALFTIME":
			status += " at halftime "
		elif statusnode["type"]["name"] == "STATUS_IN_PROGRESS" and statusnode["type"]["detail"].endswith("OT"):
			status += " in " + statusnode["type"]["detail"] + " "
		elif statusnode["type"]["name"] == "STATUS_IN_PROGRESS" and toOrdinal(statusnode["period"]) and (int(statusnode["period"]) > 4):
			status += " start of " + (statusnode["period"]) + "OT "
		elif (statusnode["type"]["name"] == "STATUS_END_PERIOD") or ((statusnode["type"]["name"] == "STATUS_IN_PROGRESS") and (statusnode["displayClock"].strip() == "0:00")):
			status += ", end of the " + toOrdinal(statusnode["period"]) + " quarter "
		elif (statusnode["type"]["name"] == "STATUS_IN_PROGRESS") and (statusnode["displayClock"].strip() == "15:00"):
			status += ", start of the " + toOrdinal(statusnode["period"]) + " quarter "
		elif statusnode["type"]["name"] == "STATUS_IN_PROGRESS":			
			status += ", " + statusnode["displayClock"].strip() + " to go in the " + toOrdinal(statusnode["period"]) + " quarter "
		
		else: # just dump it
			status += ", " + statusnode["type"]["name"] + ' '
		

		status += game_loc(game) + "."
	
	if 0:
		if 1:
			pass
		elif game["gameState"] in ("cancelled","postponed"):
			status = rank_name(game["away"]) + " vs. " + rank_name(game["home"]) + " originally scheduled for" + spaceday(game,sayToday=True) + " " + game_loc(game) + " is " + game["gameState"] + "."
		elif game["gameState"] in ("delayed"):
			status = rank_name(game["away"]) + " vs. " + rank_name(game["home"]) + " " + game_loc(game) + " is " + game["gameState"] + "."
		
			
	return sentenceCap(status)


def get(team,forceReload=False,debug=False,file=None,ffwd=None):
	
	global __MOD

	tkey = team.lower().strip()
	
	if debug:
		print("tkey: " + tkey + ", ", end="")
	
	if (tkey in iaa) or (tkey in ncaaNickDict and ncaaNickDict[tkey] in iaa):
		# we're going to be lazy about caching and just always reload for I-AA games
		if debug: 
			print ("I-AA load: ", end="")
		sb = get_scoreboard(iaa=True,debug=debug)
	elif tkey not in validFbSet:
		raise NoTeamException(tkey + " is not a valid team.")
	
	else:	# main I-A schedule cycle
		if forceReload \
				or ("ncaafsb" not in __MOD) \
				or (("ncaafsbdt" in __MOD) and (datetime.utcnow() - __MOD["ncaafsbdt"] > CACHE_INTERVAL)) \
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
	
	
	game = find_game(sb,team,debug)
	
	if game:
		return status(game)
	elif (tkey in ncaaNickDict):
		if (ncaaNickDict[tkey].__class__ == list):
			return "For " + team + ", please choose " + joinOr(ncaaNickDict[tkey]) + "."
		else:
			game = find_game(sb,ncaaNickDict[tkey],debug)
			if game:
				return status(game)
	
	# fallthru
	ret = "No game this week for " + team
	if ret[-1] != ".":
		ret += "."
		
	raise NoGameException(ret)

	
