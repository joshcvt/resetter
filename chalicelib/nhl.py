#!/usr/bin/env python
#encoding: utf-8

import urllib2, json, time
from datetime import datetime, timedelta
from reset_lib import joinOr, sentenceCap, NoGameException

intRolloverUtcTime = 1000

preferredTZ = ({"offset":-5,"tz":"EST"},{"offset":-4,"tz":"EDT"})

SCOREBOARD_URL_JSON = "https://statsapi.web.nhl.com/api/v1/schedule?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&expand=schedule.teams,schedule.linescore,schedule.broadcasts.all,schedule.ticket,schedule.game.content.media.epg,schedule.radioBroadcasts,schedule.decisions,schedule.scoringplays,schedule.game.content.highlights.scoreboard,team.leaders,schedule.game.seriesSummary,seriesSummary.series&leaderCategories=points,goals,assists&leaderGameTypes=R&site=en_nhl&teamId=&gameType=&timecode="

validTeams = ("rangers","islanders","capitals","flyers","penguins","blue jackets","hurricanes","devils",
	"red wings","sabres","maple leafs","senators","canadiens","bruins","panthers","lightning",
	"predators","blackhawks","blues","wild","jets","stars","avalanche",
	"oilers","flames","canucks","sharks","kings","ducks","coyotes","golden knights"
)

derefs = { "rangers":["nyr","blueshirts"],"islanders":["isles","nyi","brooklyn"],"capitals":["caps","nocups","no cups","was","washington","dc"],
	"flyers":["philly","phl","philadelphia"],"penguins":["pens","pittsburgh","pit","pgh"],"blue jackets":["bluejackets","lumbus","cbj","bjs","bj's","columbus"],
	"hurricanes":["carolina","canes","car","whale","whalers","hartford","brass bonanza"],"devils":["nj","njd","jersey","devs","new jersey"],
	"red wings":["wings","det","detroit"],"sabres":["buffalo","buf"],"maple leafs":["leafs","buds","toronto","tor"],
	"senators":["sens","ottawa"],"canadiens":["habs","montreal",u'montréal'],"bruins":["b's","bs","boston"],
	"panthers":["florida",'cats',"fla"],"lightning":["bolts","tb","tampa","tampa bay"],
	"predators":["preds","nashville","nsh","perds"],"blackhawks":['chi',"chicago",'hawks'],"blues":['stl',"st. louis","st louis"],"wild":['min',"minnesota"],
	"jets":["no parks","peg","winnipeg"],"stars":["dallas","northstars","north stars"],
	"avalanche":['avs','col','colorado'],
	"oilers":['edm','oil',"edmonton"],"flames":['cgy','calgary'],"canucks":['nucks','van','vancouver'],
	"sharks":['sj','san jose',u'san josé'],"kings":['la','lak',"los angeles"],"ducks":['ana','anaheim','mighty ducks'],
	"coyotes":['phx','ari','arizona','yotes',"phoenix"],"golden knights":['vegas','lv','knights',"vgk","las vegas"]
}

__MOD = {}


class TzFailedUseLocalException(Exception):
	pass

def todayIsDst(sb):
	# Using US margins, and in marginal weeks check the scoreboard to see if any games 
	# are being played in a DT zone. it's sloppy, but the only time this should get tricked 
	# is if the only game of the day is in Arizona, which is unlikely.
	# the proper way to do this is to package tzinfo in, of course, but I'd rather save
	# the resources in a non-mission-critical setting.
	
	today = datetime.utcnow() + timedelta(hours=preferredTZ[0]["offset"])
	if (today.month in (12,1,2)) or (today.month == 3 and today.day < 8) or (today.month == 11 and today.day > 7):
		return False
	elif (today.month in (4,5,6,7,8,9,10)) or (today.month == 3 and today.day > 14):
		return True
	
	try:
		for game in sb["dates"][0]["games"]:
			zone = game["teams"]["home"]["team"]["venue"]["timeZone"]
			if zone["tz"][-2] == "D":
				return True
	except:
		raise TzFailedUseLocalException
	
	return False

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
	except IndexError:
		pass	# no games today
	except Exception as e:
		print "game get blew out on something not IndexError: " + str(e)
	
	return g
		

def game_loc(game):

	try:
		if game["venue"]["name"].strip() == game["teams"]["home"]["team"]["venue"]["name"].strip():
			return "in " + game["teams"]["home"]["team"]["venue"]["city"].strip()
	except:
		pass
	
	return "at " + game["venue"]["name"].strip()

def teamDisplayName(team):
	"""we have this because Montreal venue/Montréal teamloc and St. Louis venue/St Louis shortname looks dumb."""
	overrides = {u'Montréal':'Montreal','St Louis':'St. Louis'}
	sname = team["team"]["shortName"]
	if sname in overrides:
		return overrides[sname]
	else:
		return sname

def scoreline(game):
	
	leader = game["teams"]["away"]
	trailer = game["teams"]["home"]
	if game["teams"]["home"]["score"] > game["teams"]["away"]["score"]:
		leader = game["teams"]["home"]
		trailer = game["teams"]["away"]
	# by default list away team first in a tie, because this is North American
	return teamDisplayName(leader) + " " + str(leader["score"]) + ", " + teamDisplayName(trailer) + " " + str(trailer["score"])

class ShortDelayException(Exception):
	pass

class LateStartException(Exception):
	pass

def local_game_time(game):
	
	global __MOD	
			
	gameutc = datetime.strptime(game['gameDate'],'%Y-%m-%dT%H:%M:%SZ')
	startdelay = datetime.utcnow() - gameutc
	
	if (__MOD["dst"] == "local"):
		# tz is name, offset is hrs off
		homezone = game["teams"]["home"]["team"]["venue"]["timeZone"]
	else:
		if __MOD["dst"]:
			idx = 1
		else:
			idx = 0
		homezone = preferredTZ[idx]		
	
	gamelocal = gameutc + timedelta(hours=(homezone["offset"]))
	printtime = gamelocal.strftime("%I:%M %p") + " " + homezone["tz"]	

	if printtime[0] == '0':
		printtime = printtime[1:]
	if startdelay > timedelta(minutes=15):
		raise LateStartException(printtime)
	elif startdelay > timedelta(minutes=0):
		raise ShortDelayException
	else:
		return printtime 
	

def game_time_set(game):

	trem = game["linescore"]["currentPeriodTimeRemaining"].strip()
	if trem.startswith("0"):
		trem = trem[1:]
	pd = game["linescore"]["currentPeriodOrdinal"].strip()
	if trem == '20:00':
		return "start of the " + pd
	elif trem == 'END':
		
		if pd == "3rd":
			return "at the end of regulation"
		elif game["linescore"]["intermissionInfo"]["inIntermission"]:
			if pd in ("1st","2nd"):
				return "at the " + pd + " intermission"
			else:
				print "intermission but it's overtime/so, LOOK AT THIS"
				print json.dumps(game,sort_keys=True, indent=4, separators=(',', ': '))
				return "at the " + pd + " intermission"
		else:
			if pd == "OT":
				# you might catch a situation where the game's over, but they don't know it yet
				if game["teams"]["home"]["score"] != game["teams"]["away"]["score"]:
					return "final in overtime"
				else:
					return "after overtime"
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
	elif game["linescore"]["currentPeriodOrdinal"] == "SO":
		return " in a shootout"
	elif game["linescore"]["currentPeriod"] > 3:
		print "this is weird: period is " + game["linescore"]["currentPeriodOrdinal"]
		return " in " + game["linescore"]["currentPeriodOrdinal"]
	else:
		return ""
		
def fix_for_delay(ret):

	ret = ret.replace("plays","vs.")
	ret = ret.replace("play","vs.")
	ret = ret.replace("visits","at")
	ret = ret.replace("visit","at")
	return ret				
	

def phrase_game(game):

	status = int(game["status"]["statusCode"])
	
	if status in (1,2):		# scheduled, pregame
		loc = game_loc(game)
		if loc.startswith("at"):	# unusual venue
			ret = teamDisplayName(game["teams"]["away"])
			ret += " play " if (ret.startswith("NY") and ret.endswith("s")) else " plays "
			ret += teamDisplayName(game["teams"]["home"]) + " " + game_loc(game)
		else:
			ret = teamDisplayName(game["teams"]["away"])
			ret += " visit " if (ret.startswith("NY") and ret.endswith("s")) else " visits "
			ret += teamDisplayName(game["teams"]["home"])
		
		try:
			gametime = local_game_time(game)
			ret += " at " + gametime + "."
		except ShortDelayException:
			ret = fix_for_delay(ret)
			ret += " will be underway momentarily."
		except LateStartException as lse:
			ret = fix_for_delay(ret)
			ret += ", scheduled for " + str(lse) + ", is delayed (or the league web site has no data)."
		
		return ret
		
	elif status in (3,4):	# in progress, in progress - critical
		base = game_loc(game) + ", " + scoreline(game)
		timeset = game_time_set(game)
		if not timeset.startswith("at "):
			base += ","
		return base + " " + timeset + "."
	
	elif status in (5,6,7):	# final, game over
		# final
		return "Final " + game_loc(game) + ", " + scoreline(game) + final_qualifier(game) + "."
	else:
		return "HELP, I don't understand gamestatus " + str(status) + " " + game["status"]["detailedState"] + " yet for " + game["teams"]["away"]["team"]["teamName"] + " at " + game["teams"]["home"]["team"]["teamName"]
	
		
def get(team,fluidVerbose=False,rewind=False,ffwd=False):

	global __MOD

	vtoc = buildVarsToCode()
	#print vtoc
	sb = get_scoreboard(fluidVerbose=fluidVerbose,rewind=rewind,ffwd=ffwd)
	#print json.dumps(sb, sort_keys=True, indent=4, separators=(',', ': '))
	try:
		__MOD["dst"] = todayIsDst(sb)
	except TzFailedUseLocalException:
		__MOD["dst"] = "local"
	
	tkey = team.lower().strip()
	
	ret = ""
	
	if tkey == "scoreboard":
		try:
			game = sb["dates"][0]["games"]
		except IndexError:
			game = []
		except Exception as e:		# keyerror or index error means scoreboard is blown out
			print "full scoreboard get blew out, not IndexError\n" + str(e)	# for logging
			game = []
	
	elif not (tkey in vtoc):
		return None
	
	else:
		game = get_game(sb,vtoc[tkey])
	
	if not game:	# valid for game = [] as well
		if game.__class__ == list:
			ret = "No games today."
		else:	
			ret = "No game today for the " + vtoc[tkey].capitalize() + "."
		raise NoGameException(ret)
	
	elif game.__class__ == list:	# full scoreboard or preseason split-squad
		ret = ""
		for g in game:
			ret += sentenceCap(phrase_game(g)) + "\n"
		if len(ret) > 0:
			ret = ret[:-1]
	else:
		ret = sentenceCap(phrase_game(game))
		
	return ret
