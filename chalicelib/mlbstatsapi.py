#!/usr/bin/python

import urllib.request, urllib.error, urllib.parse, json, traceback 
from datetime import timedelta, datetime, date, timezone
import dateutil.parser
from zoneinfo import ZoneInfo
from os import sys

from .nat_lib import *
from .reset_lib import NoGameException, NoTeamException, DabException

intRolloverLocalTime = 1000		# for resetter this is UTC because Lambda runs in UTC

#logLevel = logging.DEBUG
#logFN = "resetter.log"

def iso8601toLocalTZ(isoUTC,preferredTZName="America/New_York"):

	gameTime = dateutil.parser.parse(isoUTC)
	localGameTime = gameTime.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(preferredTZName))
	return localGameTime.strftime("%-I:%M ") + localGameTime.tzname()

def findGameNodes(sapiDict,team):
	ret = []

	if team.lower() in ("schedule","scoreboard"):
		for sapiDate in sapiDict["dates"]:
			ret = ret + sapiDate["games"]
	else:
		for sapiDate in sapiDict["dates"]:
			for gm in sapiDate["games"]:
				if ((gm["teams"]["home"]["team"]["abbreviation"] == team) or (gm["teams"]["away"]["team"]["abbreviation"] == team)):
					ret.append(gm)
	
	return ret


def buildVarsToCode():
	vtoc = {"schedule":"schedule", "scoreboard":"scoreboard"}
	for k in codeToVariants:
		for var in codeToVariants[k]:
			if var in vtoc:
				raise Exception("OOPS: trying to duplicate pointer " + var + " as " + k + ", it's already " + vtoc[var])
			else:
				vtoc[var] = k
				vtoc[var.lower()] = k
				vtoc[var.upper()] = k
		# and before we go, do k = k too
		vtoc[k] = k
		vtoc[k.lower()] = k	# it's already upper
		
	return vtoc

def placeAndScore(g):

	homeVenue = g["teams"]["home"]["team"]["venue"]["name"]
	gameVenue = g["venue"]["name"]
	
	if gameVenue != homeVenue:
		reset = "at " + gameVenue
	else:
		reset = "in " + g["teams"]["home"]["team"]["locationName"]
		if reset == "in Bronx":
			reset = "in the Bronx"

	reset +=  ", "
	
	# score
	hruns = g["linescore"]["teams"]["home"]["runs"]
	aruns = g["linescore"]["teams"]["away"]["runs"]
	if hruns > aruns:
		reset += (g["teams"]["home"]["team"]["teamName"] + " " + str(hruns) + ", " + g["teams"]["away"]["team"]["teamName"] + " " + str(aruns))
	else:
		reset += (g["teams"]["away"]["team"]["teamName"] + " " + str(aruns) + ", " + g["teams"]["home"]["team"]["teamName"] + " " + str(hruns))
	
	return reset

def is_doubleheader(g):
	return (g["doubleHeader"] in ("Y","S"))


def getReset(g,team,fluidVerbose):
	if g == None:
		return "No game today."

	stat = g["status"]["detailedState"]
	reset = ""
	
	is_dh = is_doubleheader(g)
	
	if stat in PREGAME_STATUS_CODES:
		if fluidVerbose:
			reset += getProbables(g,team)
		else:
			reset += g["teams"]["away"]["team"]["teamName"] + " at " + g["teams"]["home"]["team"]["teamName"]
			if is_dh:
				reset += ' (game ' + str(g["gameNumber"]) + ')'
			reset += " starts at " + iso8601toLocalTZ(g["gameDate"]) + "."

		if stat in ANNOUNCE_STATUS_CODES:	# delayed start
			reset = reset[:-1] + " (" + stat.lower() + ")."
	
	if stat in UNDERWAY_STATUS_CODES:
		
		inningState = g["linescore"]["inningState"].lower()
		reset = placeAndScore(g) + ", " + inningState + " of the " + g["linescore"]["currentInningOrdinal"] + ". "
		
		# might have at, might have in as the front.		
		if is_dh:
			reset = "Game " +str(g["gameNumber"]) + " " + reset
		else:
			reset = reset[0].upper() + reset[1:]
						
		if inningState in ("top","bottom"): 	#in play
			
			runners = list(g["linescore"]["offense"].keys())		
			if "first" in runners:
				if "second" in runners:
					if "third" in runners:
						reset += "Bases loaded. "
					else:
						reset += "Runners on first and second. "
				elif "third" in runners:
					reset += "Runners on first and third. "
				else:
					reset += "Runner on first. "
			elif "second" in runners:
				if "third" in runners:
					reset += "Runners on second and third. "
				else:
					reset += "Runner on second. "
			elif "third" in runners:
				reset += "Runner on third. "
			else:
				if len(runners) != 0:
					print("uh, we broke runners somehow")
			
			outs = str(g["linescore"]["outs"])
			if outs == "0":
				reset += "No outs. "
			elif outs == "1":
				reset += outs + " out. "
			else:
				reset += outs + " outs. "
	
	if stat in FINAL_STATUS_CODES:
		reset += "Final "
		if is_dh:
			reset += "of game " + str(g["gameNumber"]) + " "
		reset += placeAndScore(g)
		if (g["linescore"]["currentInning"] != 9):
			reset += " in " + str(g["linescore"]["currentInning"]) + " innings"
		reset += ". "
		
	
	if (len(reset) == 0):
		# common path for various weird statuses with a specific cutout for postponed
		reset = g["teams"]["away"]["team"]["teamName"] + " at " + g["teams"]["home"]["team"]["teamName"] 
		if is_dh:
			reset += ' (game ' + str(g["gameNumber"]) + ')'
		reset += " is " + stat.lower() 
		
		if stat in POSTPONED_STATUS_CODES:
			try:
				desc = g["description"]
				if desc and len(desc.strip()) > 0:
					reset += " (" + desc + ")"
			except:
				pass
		
		reset += "."
	
	#print "getting out of the reset with " + reset
	return reset
	
	
def loadSAPIScoreboard(sapiURL, scheduleDT):
	
	#logging.debug( "Running scoreboard for " + scheduleDT.strftime("%Y-%m-%d"))
	scheduleUrl = scheduleDT.strftime(sapiURL)
	
	try:
		usock = urllib.request.urlopen(scheduleUrl,timeout=10)
		sapiDict = json.load(usock)
		return sapiDict

	#except socket.timeout as e:
	except urllib.error.HTTPError as e:
		print("HTTP " + str(e.code) + " on URL: " + scheduleUrl)
		#if e.code in (404,403,500,410):
		#elif e.code != 200:
	#except urllib2.URLError as e:
	except Exception as e:
		print("WENT WRONG: " + e.__module__ + "." + e.__class__.__name__)
	
	return None

def getPitcher(g,ah):
	if ah not in ("away","home"):
		return None
	
	if "probablePitcher" not in list(g["teams"][ah].keys()):
		pstr = "TBA"
	else:
		pitcher = g["teams"][ah]["probablePitcher"]
		pstr = pitcher["fullName"]
		# this was for a rostername of "Soroka, M", which we don't have yet in SAPI 
		# have to get that as (http://statsapi.mlb.com + pitcher["link"])["people"][0]["boxscoreName"]
		#if "," in pstr:
		#	pstr = pstr + "."
		pstr = pstr + " " + getWLERA(pitcher)
	return (g["teams"][ah]["team"]["shortName"] + " (" + pstr + ")")

def getWLERA(pitcher):
	for sg in pitcher["stats"]:
		if sg["group"]["displayName"] == "pitching" and sg["type"]["displayName"] == "statsSingleSeason":
			return str(sg["stats"]["wins"]) + "-" + str(sg["stats"]["losses"]) + ", " + sg["stats"]["era"]
	return ""

def getTVNets(g,ah):
	ret = []
	for bc in g["broadcasts"]:
		if bc["type"] == "TV":
			if (("isNational" in list(bc.keys())) or (bc["homeAway"] == ah)):
				name = bc["name"]
				if name not in ret:
					ret.append(name)
	return ",".join(ret)

def getProbables(g,tvTeam=None,preferredTZ="America/New_York"):
	if g == None:
		return None
	
	awayAbbr = g["teams"]["away"]["team"]["abbreviation"]
	homeAbbr = g["teams"]["home"]["team"]["abbreviation"]
	
	runningStr = getPitcher(g,"away") + " at " + getPitcher(g,"home")
	
	if is_doubleheader(g):
		runningStr += ' (game ' + str(g["gameNumber"]) + ')'
	
	runningStr += " starts at " + iso8601toLocalTZ(g["gameDate"]) + "."
	
	if tvTeam and (tvTeam not in ("suppress","scoreboard","schedule")):
		# lazy default here
		homeaway = "home"
		if tvTeam == awayAbbr:
			homeaway = "away"
		try:
			bcast = getTVNets(g,homeaway)
			if bcast:
				runningStr += " TV broadcast is on " + bcast + "."
			else:
				runningStr += " No TV."
		except Exception as e:
			print("bcast exception:" + str(e))
			pass	
	
	return runningStr


def launch(team,fluidVerbose=True,rewind=False,ffwd=False):

	#logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',filename=logFN, level=logLevel)
	
	localRollover = intRolloverLocalTime
	
	# for testing
	if rewind:
		# force yesterday's games by making the rollover absurd.
		localRollover += 2400
	if ffwd:
		localRollover -= 2400
	
	vtoc = buildVarsToCode()
	
	teamLiteral = team
	team = team.strip().lower()
	
	if team in dabList:
		#return ["Did you mean " + join(dabList[team.lower()]," or ") + "?"]
		raise DabException(dabList[team])
	elif team not in vtoc:
		raise NoTeamException
	
	todayDT = datetime.now() - timedelta(minutes=((localRollover/100)*60+(localRollover%100)))
	
	sapiScoreboard = loadSAPIScoreboard(statsApiScheduleUrl,todayDT)
	
	if sapiScoreboard:
		gns = findGameNodes(sapiScoreboard,vtoc[team])
	else:
		gns = []
	
	if len(gns) == 0:
		if team in ("schedule","scoreboard"):
			ngstr = "No games today in MLB."
		else:
			ngstr = "No game today for " + team + "."
		raise NoGameException(ngstr)
	
	rv = []
	for gn in gns:
		rv.append(getReset(gn,vtoc[team],fluidVerbose))
		#print "rv is " + str(rv)
	
	return rv


