#!/usr/bin/env python

import json
from string import capwords
import traceback


from .mlbstatsapi import get as get_mlb
from .ncaaf_espn import get as get_ncaaf
from .nhl import get as get_nhl
from .reset_lib import joinOr, dateParse, rtext, NoGameException, NoTeamException, DabException, RESET_RICH_SLACK, RESET_TEXT, RESET_SHORT_SLACK
from .networks import sendSlack
# magic text
NO_GAMES = "no games"


class NoSportException(Exception):
	pass

def get_team(team,debug=False,inOverride=False,gameFormat=RESET_TEXT):

	hold = None
	retList = None
	opts = []
	
	fns = {"mlb":get_mlb,"football":get_ncaaf,"nhl":get_nhl}
	fns_key_order = ["mlb","nhl","football"]

	# first, try if the sport's defined.
	try:
		linedict = sport_strip(team)
		print("linedict after sport_strip: " + str(linedict))
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
					rv = fns[sport](team,inOverride=inOverride,ffwd=ffwd,date=date,gameFormat=gameFormat)
				else:
					rv = fns[sport](team,ffwd=ffwd,date=date,gameFormat=gameFormat)
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

def postResetToSlack(whichContent="nhl",channel="backtalk",banner="",useColumnarPost=False):
	
	try:
		rtext = get_team(whichContent,gameFormat=(RESET_SHORT_SLACK if useColumnarPost else RESET_RICH_SLACK))
		if NO_GAMES in rtext.lower():
			return	# skip slack if there's no games
		
		if not useColumnarPost:
			if len(banner) > 0:
				rtext = "*" + banner +"*\n" + rtext
			payloadDict = {"text":rtext}
		else:
			# what we get back is splittable on `\n`
			lines = rtext.split("\n")
			# but if it's more than 10 items, we have to recombine.
			if len(lines) > 10:
				divider = round(len(lines)/ 2)
				set1 = "\n".join(lines[0:divider])
				set2 = "\n".join(lines[divider:len(lines)])
				lines = [set1,set2]
			payloadDict = {"blocks":[]}
			if banner:
				payloadDict["blocks"].append({"type": "header","text": {"type": "plain_text","text": banner}})
			if lines:
				fields = []
				for ln in lines:
					fields.append({"type": "plain_text","text": ln,"emoji": True})
				payloadDict["blocks"].append({"type":"section","fields":fields})
		print("DEBUG: payloadDict:\n" + json.dumps(payloadDict))
		sendSlack(payloadDict,channel)
	except Exception as e:
		print("postSlack failed on:\n" + str(e))

