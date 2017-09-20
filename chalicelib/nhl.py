#!/usr/bin/env python
#encoding: utf-8

import urllib2, json, time
from datetime import datetime, timedelta
from reset_lib import joinOr, sentenceCap

intRolloverUtcTime = 1200

SCOREBOARD_URL_JSON = "https://statsapi.web.nhl.com/api/v1/schedule?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&expand=schedule.teams,schedule.linescore,schedule.broadcasts.all,schedule.ticket,schedule.game.content.media.epg,schedule.radioBroadcasts,schedule.decisions,schedule.scoringplays,schedule.game.content.highlights.scoreboard,team.leaders,schedule.game.seriesSummary,seriesSummary.series&leaderCategories=points,goals,assists&leaderGameTypes=R&site=en_nhl&teamId=&gameType=&timecode="

validTeams = ("rangers","islanders","capitals","flyers","penguins","blue jackets","hurricanes","devils",
	"red wings","sabres","maple leafs","senators","canadiens","bruins","panthers","lightning",
	"predators","blackhawks","blues","wild","jets","stars","avalanche",
	"oilers","flames","canucks","sharks","kings","ducks","coyotes","golden knights"
)

derefs = { "rangers":["nyr","blueshirts"],"islanders":["isles","nyi"],"capitals":["caps","nocups","was","washington","dc"],
	"flyers":["philly","phl"],"penguins":["pens","pittsburgh","pit","pgh"],"blue jackets":["bluejackets","lumbus","cbj","bjs","bj's"],
	"hurricanes":["carolina","canes"],"devils":["nj","njd","jersey","devs","new jersey"],
	"red wings":["wings","det","detroit"],"sabres":["buffalo"],"maple leafs":["leafs","buds","toronto"],
	"senators":["sens","ottawa"],"canadiens":["habs","montreal",u'montréal'],"bruins":["b's","bs"],
	"panthers":["florida",'cats'],"lightning":["bolts","tb","tampa","tampa bay"],
	"predators":["preds","nashville"],"blackhawks":['chi','hawks'],"blues":['stl'],"wild":['min'],
	"jets":["no parks","peg","winnipeg"],"stars":["dallas","northstars"],
	"avalanche":['avs','col','colorado'],
	"oilers":['edm','oil'],"flames":['cgy','calgary'],"canucks":['nucks','van','vancouver'],
	"sharks":['sj','san jose',u'san josé'],"kings":['la','lak'],"ducks":['ana','anaheim','mighty ducks'],
	"coyotes":['phx','ari','arizona','yotes'],"golden knights":['vegas','lv','knights']
}

def buildVarsToCode():
	vtoc = {}
	
	for k in derefs:
		for var in derefs[k]:
			if var.lower() in vtoc:
				raise Exception("OOPS: trying to duplicate pointer " + var + " as " + k + ", it's already " + vtoc[var])
			else:
				vtoc[var.lower()] = k
		# and before we go, do k = k too
		vtoc[k.lower()] = k	# it's already upper
	
	return vtoc

def get_scoreboard(file=None,fluidVerbose=False,rewind=False,ffwd=False):
	"""Get scoreboard from site, or from file if specified for testing."""

	if file:
		fh = open(file)
	else:
		localRollover = intRolloverUtcTime
	
		if rewind:
			# force yesterday's games by making the rollover absurd.
			localRollover += 2400
		if ffwd:
			localRollover -= 2400
	
		#

		todayDT = datetime.utcnow() - timedelta(minutes=((localRollover/100)*60+(localRollover%100)))
		todayScoreboardUrl = SCOREBOARD_URL_JSON.replace("YYYY-MM-DD",todayDT.strftime("%Y-%m-%d"))
	
		#opener = urllib2.build_opener()
		#opener.addheaders = [('User-agent', 'Mozilla/5.0')]
		#urllib2.install_opener(opener)
		fh = urllib2.urlopen(todayScoreboardUrl)	
	
	raw = fh.read()
	return json.loads(raw)

def get_game(sb,nickname):
	# nickname is lowercase team nick.
	
	g = None
	
	try:
		for game in sb["dates"][0]["games"]:
			if nickname in (game["teams"]["away"]["team"]["teamName"].lower(), game["teams"]["home"]["team"]["teamName"].lower()):
				if not g:
					g = game
				elif g.__class__ != list:	# preseason split squad can trigger this
					g = [g, game]
				else:
					g.append(game)
	except Exception as e:
		print e
	
	return g
		

def game_loc(game):

	try:
		if game["venue"]["name"].strip() == game["teams"]["home"]["team"]["venue"]["name"].strip():
			return "in " + game["teams"]["home"]["team"]["venue"]["city"].strip()
	except:
		pass
	
	return "at " + game["venue"]["name"].strip()


def scoreline(game):
	
	leader = game["teams"]["away"]
	trailer = game["teams"]["home"]
	if game["teams"]["home"]["score"] > game["teams"]["away"]["score"]:
		leader = game["teams"]["home"]
		trailer = game["teams"]["away"]
	# by default list away team first in a tie, because this is North American
	return leader["team"]["shortName"] + " " + str(leader["score"]) + ", " + trailer["team"]["shortName"] + " " + str(trailer["score"])

def local_game_time(game):

	return ""

def game_time_set(game):

	trem = game["linescore"]["currentPeriodTimeRemaining"].strip()
	if trem.startswith("0"):
		trem = trem[1:]
	pd = game["linescore"]["currentPeriodOrdinal"].strip()
	if trem == '20:00':
		return "start of the " + pd
	elif trem == 'END':
		if game["linescore"]["intermissionInfo"]["inIntermission"]:
			if pd in ("1st","2nd"):
				return "at the " + pd + " intermission"
			elif pd == "3rd":
				return "at the end of regulation"
			else:
				print "oh hell, it's overtime/so"
				print json.dumps(game,sort_keys=True, indent=4, separators=(',', ': '))
		else:
			return "end of the " + pd
	else:
		if pd != "OT":
			pd = "the " + pd
		return trem + " to go in " + pd

def final_qualifier(game):
	"""return 'in overtime' or 'in a shootout' if appropriate for the 
	final score. Assume the game went there."""
	
	if game["linescore"]["currentPeriodOrdinal"] == "OT":
		return " in overtime"
	elif game["linescore"]["currentPeriod"] > 3:
		return " in " + game["linescore"]["currentPeriodOrdinal"]
	else:
		return ""

def phrase_game(game):

	status = int(game["status"]["statusCode"])
	
	if status in (1,2):		# scheduled, pregame
		return game["teams"]["away"]["team"]["teamName"] + " plays " + game["teams"]["home"]["team"]["teamName"] + " " + game_loc(game) + " at " + local_game_time(game) + "."
	
	elif status in (3,4):	# in progress, in progress - critical
		base = game_loc(game) + ", " + scoreline(game)
		timeset = game_time_set(game)
		if not timeset.startswith("at "):
			base += ","
		return base + " " + timeset + "."
	
	elif status in (5,6):	# final, game over
		# final
		return "Final " + game_loc(game) + ", " + scoreline(game) + final_qualifier(game) + "."
	else:
		return "HELP, I don't understand gamestatus " + str(status) + " " + game["status"]["detailedState"] + " yet for " + game["teams"]["away"]["team"]["teamName"] + " at " + game["teams"]["home"]["team"]["teamName"]
	
		
def get(team,fluidVerbose=False,rewind=False,ffwd=False):

	vtoc = buildVarsToCode()
	#print vtoc
	
	sb = get_scoreboard(fluidVerbose,rewind,ffwd)
	#print json.dumps(sb, sort_keys=True, indent=4, separators=(',', ': '))
	
	tkey = team.lower().strip()
	
	if not (tkey in vtoc):
		return None
	
	game = get_game(sb,vtoc[tkey])
	
	ret = ""
	
	if not game:
		ret = "No game today for the " + vtoc[tkey].capitalize() + "."
	elif game.__class__ == list:	# basically for preseason split-squad
		ret = ""
		for g in game:
			ret += sentenceCap(phrase_game(g)) + "\n"
		if len(ret) > 0:
			ret = ret[:-1]
	else:
		ret = sentenceCap(phrase_game(game))
		
	return ret
