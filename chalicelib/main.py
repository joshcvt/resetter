#!/usr/bin/env python

import json
from string import capwords
import traceback
from datetime import date

#import urllib3
import urllib

from .mlbstatsapi import launch as get_mlb
from .ncaaf_espn import get as get_ncaaf
from .nhl import get as get_nhl
from .reset_lib import joinOr, NoGameException, NoTeamException, DabException

global slackUrl 
slackUrl = None


class NoSportException(Exception):
	pass

def get_team(team,debug=False,inOverride=False):

	hold = None
	retList = None
	opts = []
	
	fns = {"mlb":get_mlb,"football":get_ncaaf,"nhl":get_nhl}
	fns_key_order = ["mlb","nhl","football"]

	# first, try if the sport's defined.
	try:
		linedict = sport_strip(team)
		team = linedict["team"]
		sport = linedict["sport"]
		ffwd = True if "ffwd" in linedict else False
		date = linedict["date"] if "date" in linedict else False
		if ffwd and date:
			return rtext("I'm sorry, I can't accept both ffwd and a specified date.")
		if debug:
			print("got " + team + ", " + sport)
		if sport in fns:
			if (not team or len(team.strip()) == 0):
				team = "scoreboard"
			try:
				if inOverride:
					rv = fns[sport](team,inOverride=inOverride,ffwd=ffwd,date=date)
				else:
					rv = fns[sport](team,ffwd=ffwd,date=date)
				if rv:
					return rtext(rv)
			#except NoGameException as e:
			#	hold = "No game today for " + tm + "."
			#except NoTeamException as e:
			#	hold = "No team " + tm + " found."
			except Exception as e:
				if debug:
					print("debug: got exception getting sport fn: " + e.__class__.__name__ + " " + str(e))
				hold = e
	
	# if it isn't:
	except NoSportException:
		
		for k in fns_key_order:
			if debug:
				print("calling " + k, end=' ')
			
			try:
				# this is temporary until/unless we implement inOverride across all the sport providers
				if inOverride:
					rv = fns[k](team,inOverride=inOverride)
				else:
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
		
		if team in ('scoreboard','schedule',''):
			retList = str(hold)
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
		rtext = '\n'.join(retList)
	else:
		rtext = " ".join(retList)
	
	return rtext

	
def sport_strip(team):
	"""If sport is specified either first or last, return team plus it as a tuple. If not, throw Exception."""
	line = team.strip().lower()
	splits = line.split()
	rv = {"team":""} # default in case it's a bare league scoreboard call.

	sports = ("football","nhl","mlb")
	if splits[-1] == "tomorrow":
		rv["ffwd"] = True
		splits = splits[:-1]
	dateRes = dateParse(splits[-1])
	if dateRes:
		rv["date"] = dateRes
		splits = splits[:-1]
		print("hey, I got a date " + str(dateRes))
	
	if splits[0] in sports:
		rv["sport"] = splits[0]
		if len(splits) > 1:
			rv["team"] = splits[1]
		return rv
	elif len(splits) > 1 and splits[1] in sports:
		rv["team"] = splits[0]
		rv["sport"] = splits[1]
		return rv
	else:
		raise NoSportException()


def dateParse(instr):
	# if this is a date, send it back as a Date. If anything breaks, return False
	# supported formats: YYYY-MM-dd, MM-dd-YYYY, MM-dd, MM/dd/YYYY, MM/dd
	
	try:
		dashed = instr.split("-")
		slashed = instr.split("/")
		splits = dashed if len(dashed) > len(slashed) else slashed
		#print("dateparse splits: " + str(splits))
		if len(splits) <= 1:
			return False
		for idx, s in enumerate(splits):
			splits[idx] = int(s)

		if len(splits) == 3:
			# is year first or last?
			if splits[0] > 1000:
				return date(splits[0],splits[1],splits[2])
			else:
				return date(splits[2],splits[0],splits[1])
		elif len(splits) == 2:
			today = date.today()
			return date(today.year,splits[0],splits[1])
	except Exception as e:
		#print("hey, dateparse blew up: " + str(e))
		return False

	return False

def getSlackUrl():
	from boto3 import client
	global slackUrl

	if not slackUrl:
		try:
			slackUrl = client('ssm').get_parameter(Name='/resetter/slack_web_hook_url',WithDecryption=True)['Parameter']['Value']
			
		except Exception as e:
			print("SSM fetch failed: " + str(e))
	else:
		print("lambda was warm, using cached slackUrl")
	return True


def postSlack(whichContent="nhl",channel="backtalk",banner=""):
	
	# for the moment let's just assume it's the NHL scoreboard
	
	try:
		rtext = get_team(whichContent)
		if len(banner) > 0:
			rtext = "*" + banner +"*\n" + rtext
		payloadDict = {"text":rtext}
		_sendSlack(payloadDict,channel)
	except Exception as e:
		print("postSlack failed on:\n" + str(e))



def _sendSlack(payloadDict,channel=None):
	#verbatim from natinal_bot

	global slackUrl
	if not getSlackUrl():
		print("getSlackUrl failed to populate")
		return
	
	try:
		if channel != None and channel != "":
			payloadDict["channel"] = channel

		data = urllib.parse.urlencode({"payload": json.dumps(payloadDict)}).encode('utf-8')
		req = urllib.request.Request(slackUrl, data=data)
		response = urllib.request.urlopen(req)
		print(str(response.read()))
	except Exception as e:
		print("Couldn't post for some reason:\n" + str(e))
		return
