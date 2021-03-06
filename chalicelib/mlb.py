#!/usr/bin/python

import urllib2, json, traceback # ConfigParser, argparse	     #, logging
from datetime import timedelta, datetime, date
from string import join
import xml.etree.ElementTree as ET
from os import sys

from .nat_lib import *
from .reset_lib import NoGameException, NoTeamException, DabException

intRolloverLocalTime = 1000		# for resetter this is UTC because Lambda runs in UTC

#logLevel = logging.DEBUG
#logFN = "resetter.log"

def findGameNodes(msTree,team):
	if team.lower() in ("schedule","scoreboard"):
		ret = msTree.getroot().findall("./game")
		return ret
	else:
		return (msTree.getroot().findall("./game[@away_name_abbrev='" + team + "']") + msTree.getroot().findall("./game[@home_name_abbrev='" + team + "']"))


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

	loc = g.get("location").split(",")[0]
	if not loc:
		reset = "at " + g.get("venue") 
	elif loc == "Bronx":
		reset = "in the Bronx"
	else:
		reset = "in " + loc

	reset +=  ", "
	
	# score
	hruns = g.find("linescore/r").attrib["home"]
	aruns = g.find("linescore/r").attrib["away"]
	if int(hruns) > int(aruns):
		reset += (g.attrib["home_team_name"] + " " + hruns + ", " + g.attrib["away_team_name"] + " " + aruns)
	else:
		reset += (g.attrib["away_team_name"] + " " + aruns + ", " + g.attrib["home_team_name"] + " " + hruns)
	
	return reset

def is_doubleheader(g):
	return (g.get("double_header_sw") in ("Y","S"))


def getReset(g,team,fluidVerbose):
	if g == None:
		return "No game today."

	statNode = g.find("status")
	stat = statNode.get("status")
	reset = ""
	
	is_dh = is_doubleheader(g)
	
	if stat in PREGAME_STATUS_CODES:
		if fluidVerbose:
			reset += getProbables(g,team)
		else:
			reset += g.attrib["away_team_name"] + " at " + g.attrib["home_team_name"]
			if is_dh:
				reset += ' (game ' + str(g.attrib["game_nbr"]) + ')'
			reset += " starts at " + g.attrib["time"] + " " + g.attrib["time_zone"] + "."
		if stat in ANNOUNCE_STATUS_CODES:	# delayed start
			reset = reset[:-1] + " (" + stat.lower() + ")."
	
	if stat in UNDERWAY_STATUS_CODES:
		
		inningState = statNode.get("inning_state").lower()
		reset = placeAndScore(g) + ", " + inningState + " of the " + divOrdinal(statNode.get("inning")) + ". "
		
		# might have at, might have in as the front.		
		if is_dh:
			reset = "Game " + g.get("game_nbr") + " " + reset
		else:
			reset = reset[0].upper() + reset[1:]
						
		if inningState in ("top","bottom"): 	#in play
			obstrs = { "0": "",	# don't need to say anything
						"1": "Runner on first. ",
						"2": "Runner on second. ",
						"3": "Runner on third. ",
						"4": "Runners on first and second. ",
						"5": "Runners on first and third. ",
						"6": "Runners on second and third. ",
				 		"7": "Bases loaded. "}
			onBaseStatus = g.find("runners_on_base").attrib["status"]
			reset += obstrs[onBaseStatus]
			
			outs = statNode.get("o")
			if outs == "0":
				reset += "No outs. "
			elif outs == "1":
				reset += outs + " out. "
			else:
				reset += outs + " outs. "
	
	if stat in FINAL_STATUS_CODES:
		reset += "Final "
		if is_dh:
			reset += "of game " + g.get("game_nbr") + " "
		reset += placeAndScore(g)
		if (int(statNode.get("inning")) != 9):
			reset += " in " + statNode.get("inning") + " innings"
		reset += ". "
	
	if (len(reset) == 0):
		# give up
		reset = g.attrib["away_team_name"] + " at " + g.attrib["home_team_name"] 
		if is_dh:
			reset += ' (game ' + str(g.attrib["game_nbr"]) + ')'
		reset += " is " + stat.lower() 
		
		if stat in POSTPONED_STATUS_CODES:
			try:
				desc = g.attrib["description"]
				if desc and len(desc.strip()) > 0:
					reset += " (" + desc + ")"
			except:
				pass
		
		reset += "."
		
	return reset
	
	
def loadMasterScoreboard(msURL,scheduleDT):
	
	#logging.debug( "Running scoreboard for " + scheduleDT.strftime("%Y-%m-%d"))
	scheduleUrl = scheduleDT.strftime(msURL)
	
	try:
		usock = urllib2.urlopen(scheduleUrl,timeout=10)
		msTree = ET.parse(usock)
		return msTree

	#except socket.timeout as e:
	except urllib2.HTTPError as e:
		print( "HTTP " + str(e.code) + " on URL: " + scheduleUrl)
		#if e.code in (404,403,500,410):
		#elif e.code != 200:
	#except urllib2.URLError as e:
	except Exception as e:
		print ("WENT WRONG: " + e.__module__ + "." + e.__class__.__name__)
	
	return None

def getPitcher(g,ah):
	if ah not in ("away","home"):
		return None
	
	try:
		pitcher = g.find(ah + "_probable_pitcher")
		pstr = pitcher.get("name_display_roster")
	except:
		return None
	if "," in pstr:
		pstr = pstr + "."
	if pstr == "":
		pstr = "TBA"
	else:
		pstr = pstr + " " + pitcher.get("wins") + "-" + pitcher.get("losses") + ", " + pitcher.get("era")
	return (g.get(ah + "_team_city") + " (" + pstr + ")")
	

def getProbables(g,tvTeam=None):
	if g == None:
		return None
	
	awayAbbr = g.attrib["away_name_abbrev"]
	homeAbbr = g.attrib["home_name_abbrev"]
	
	runningStr = getPitcher(g,"away") + " at " + getPitcher(g,"home")
	
	if is_doubleheader(g):
		runningStr += ' (game ' + str(g.attrib["game_nbr"]) + ')'
	
	runningStr += " starts at " + g.attrib["time"] + " " + g.attrib["time_zone"] + "."
	
	if tvTeam and (tvTeam not in ("suppress","scoreboard","schedule")):
		# lazy default here
		bc = "home"
		if tvTeam == awayAbbr:
			bc = "away"
		try:
			bcast = g.find("broadcast").find(bc).find("tv").text
			if bcast:
				runningStr += " TV broadcast is on " + bcast + "."
			else:
				runningStr += " No TV."
		except Exception as e:
			print ("bcast exception:" + str(e))
			pass	
	
	return runningStr


def launch(team,fluidVerbose=True,rewind=False,ffwd=False):

	#logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',filename=logFN, level=logLevel)
	
	localRollover = intRolloverLocalTime
	
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
	todayStr = todayDT.strftime("%Y-%m-%d")

	masterScoreboardUrl = leagueAgnosticMasterScoreboardUrl.replace("LEAGUEBLOCK","mlb")
	masterScoreboardTree = loadMasterScoreboard(masterScoreboardUrl,todayDT)
	
	if masterScoreboardTree:
		gns = findGameNodes(masterScoreboardTree,vtoc[team])
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
	
	return rv


