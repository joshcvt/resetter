#!/usr/bin/env python
#encoding: utf-8

#import urllib.request, urllib.error, urllib.parse, 
import json, time
from urllib.request import Request, urlopen
from datetime import datetime, timedelta
from .reset_lib import joinOr, sentenceCap, NoGameException, NoTeamException, DabException
from string import capwords

intRolloverUtcTime = 1000

preferredTZ = ({"offset":-5,"tz":"EST"},{"offset":-4,"tz":"EDT"})

#SCOREBOARD_URL_JSON = "https://statsapi.web.nhl.com/api/v1/schedule?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&expand=schedule.teams,schedule.linescore,schedule.broadcasts.all,schedule.ticket,schedule.game.content.media.epg,schedule.radioBroadcasts,schedule.decisions,schedule.scoringplays,schedule.game.content.highlights.scoreboard,team.leaders,schedule.game.seriesSummary,seriesSummary.series&leaderCategories=points,goals,assists&leaderGameTypes=R&site=en_nhl&teamId=&gameType=&timecode="
SCOREBOARD_URL_JSON = "https://api-web.nhle.com/v1/schedule/YYYY-MM-DD"
SCORENOW_URL_JSON = "https://api-web.nhle.com/v1/score/now"

DEBUG_LEVEL = "DEBUG"

validTeams = ("rangers","islanders","capitals","flyers","penguins","blue jackets","hurricanes","devils",
    "red wings","sabres","maple leafs","senators","canadiens","bruins","panthers","lightning",
    "predators","blackhawks","blues","wild","jets","stars","avalanche",
    "oilers","flames","canucks","sharks","kings","ducks","coyotes","golden knights","kraken"
)

dabBacks = {
    "ny":["Rangers","Islanders"]
}

NHL_TEAMNAME_AS_PLACENAME = ["Rangers","Islanders"]

# scoreboard for the new API only reliably gives you "id","abbrev","placeName"["default"]
abbrDerefs = {
    'MTL':["canadiens","habs","montreal",'montréal'],
    'TOR':["maple leafs","leafs","buds","toronto","tor"],
    'OTT':["senators","sens","ottawa"],
    'FLA':["panthers","florida",'cats',"fla"],
    'TBL':["lightning","bolts","tb","tampa","tampa bay"],
    'BUF':["sabres","buffalo","buf"],
    'BOS':["bruins","b's","bs","boston"],
    'DET':["red wings","wings","det","detroit"],

    'CAR':["hurricanes","carolina","canes","car","jerks","whale","whalers","hartford","brass bonanza"],
    'WSH':["capitals","caps","was","washington","dc"],
    'NYR':["rangers","nyr","blueshirts"],
    'NYI':["islanders","isles","nyi","brooklyn"],
    'NJD':["devils","nj","njd","jersey","devs","new jersey"],
    'PHI':["flyers","philly","phl","philadelphia"],
    'PIT':["penguins","pens","pittsburgh","pit","pgh"],
    'CBJ':["blue jackets","bluejackets","lumbus","cbj","bjs","bj's","columbus"],

    'MIN':["wild",'min',"minnesota"],
    'WPG':["jets","no parks","peg","winnipeg"],
    'CHI':["blackhawks",'chi',"chicago",'hawks'],
    'NSH':["predators","preds","nashville","nsh","perds"],
    'DAL':["stars","dallas","northstars","north stars"],
    'ARI':["coyotes",'phx','ari','arizona','yotes',"phoenix"],
    'STL':["blues",'stl',"st. louis","st louis"],
    'COL':["avalanche",'avs','col','colorado'],

    'LAK':["kings",'la','lak',"los angeles"],
    'VGK':["golden knights",'vegas','lv','knights',"vgk","las vegas"],
    'SJS':[ "sharks",'sj','san jose','san josé'],
    'ANA':["ducks",'ana','anaheim','mighty ducks'],
    'EDM':["oilers",'edm','oil',"edmonton"],
    'VAN':["canucks",'nucks','van','vancouver'],
    'CGY':["flames",'cgy','calgary'],
    'SEA':["kraken",'sea','seattle','krak']
}

__MOD = {}


class TzFailedUseLocalException(Exception):
    pass

def debug(text):
    if DEBUG_LEVEL == "DEBUG":
        print(text)
    return

def todayIsDst(sb):
    try:
        return (sb['gameWeek'][0]['games'][0]['easternUTCOffset'] == "-04:00")
    except:
        raise TzFailedUseLocalException
    
    return False

def buildVarsToCode():
    vtoc = {}
    
    for k in abbrDerefs:
        for var in abbrDerefs[k]:
            
            if var.lower() in vtoc:
                raise Exception("OOPS: trying to duplicate pointer " + var + " as " + k + ", it's already " + vtoc[var])
            else:
                vtoc[var.lower()] = k
        # and before we go, do k = k too
        vtoc[k.lower()] = k    # it's already upper
    
    #print(vtoc)
    return vtoc

def get_scoreboard(file=None,fluidVerbose=False,rewind=False,ffwd=False):
    """Get scoreboard from site, or from file if specified for testing."""

    global __MOD

    if file:
        # we're just going to use this as scoreboard rather than scorenow for the moment.
        fh = open(file)
        sb = json.loads(fh.read())
        __MOD["date"] = sb['gameWeek'][0]['date']
    else:
        localRollover = intRolloverUtcTime

        if not (rewind or ffwd):
            todayScoreboardUrl = SCORENOW_URL_JSON
        else:    
            if rewind:
                # force yesterday's games by making the rollover absurd.
                localRollover += 2400
            if ffwd:
                localRollover -= 2400
        
            todayDT = datetime.utcnow() - timedelta(minutes=((localRollover/100)*60+(localRollover%100)))
            __MOD["date"] = todayDT.strftime("%Y-%m-%d")
            todayScoreboardUrl = SCOREBOARD_URL_JSON.replace("YYYY-MM-DD",__MOD["date"])

        req = Request(todayScoreboardUrl)
        req.add_header('User-agent', 'Mozilla/5.0')
        raw = json.loads(urlopen(req).read())
    
    if (rewind or ffwd):
        return raw["gameWeek"][0]["games"]
    else:
        return raw["games"]

def get_game(sb,teamAbbr):
    # teamAbbr from table above; date is YYYY-mm-dd
    
    g = None
    
    try:
        for game in sb:
            if teamAbbr.upper() in (game["awayTeam"]["abbrev"], game["homeTeam"]["abbrev"]):
                if not g:
                    g = game
                elif g.__class__ != list:    # preseason split squad can trigger this
                    g = [g, game]
                else:
                    g.append(game)
    except IndexError:
        pass    # no games today
    except Exception as e:
        print("get_game blew out on something not IndexError: " + str(e))
    
    return g

def game_loc(game):
    loc = "at " + game["venue"]["default"].strip()
    return loc


def teamDisplayName(team):
    if "name" in team.keys():
        return team["name"]["default"]
    # else the scoreboard version which has placeName but not name
    #"""we have this because Montreal venue/Montréal teamloc and St. Louis venue/St Louis shortname looks dumb."""
    overrides = {'Montréal':'Montreal','St Louis':'St. Louis'}
    sname = team["placeName"]["default"]
    if sname in overrides:
        return overrides[sname]
    else:
        return sname

def scoreline(game):
    
    leader = game["awayTeam"]
    trailer = game["homeTeam"]
    if game["homeTeam"]["score"] > game["awayTeam"]["score"]:
        leader = game["homeTeam"]
        trailer = game["awayTeam"]
    # by default list away team first in a tie, because this is North American
    return teamDisplayName(leader) + " " + str(leader["score"]) + ", " + teamDisplayName(trailer) + " " + str(trailer["score"])

class ShortDelayException(Exception):
    pass

class LateStartException(Exception):
    pass

def local_game_time(game):
    
    global __MOD    
            
    gameutc = datetime.strptime(game['startTimeUTC'],'%Y-%m-%dT%H:%M:%SZ')
    startdelay = datetime.utcnow() - gameutc
    if (__MOD["dst"] == "local"):
        # tz is name, offset is hrs off
        homezoneName = game["venueTimezone"]
        homezoneOffset = game["venueUTCOffset"].split(':')[0]
    else:
        if __MOD["dst"]:
            idx = 1
        else:
            idx = 0
        homezoneOffset = preferredTZ[idx]["offset"]
        homezoneName = preferredTZ["name"]
    
    homezoneOffset = int(homezoneOffset)
    gamelocal = gameutc + timedelta(hours=(homezoneOffset))
    printtime = gamelocal.strftime("%I:%M %p") + " " + homezoneName 

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
                print("intermission but it's overtime/so, LOOK AT THIS")
                print(json.dumps(game,sort_keys=True, indent=4, separators=(',', ': ')))
                return "at the " + pd + " intermission"
        else:
            if pd == "OT":
                # you might catch a situation where the game's over, but they don't know it yet
                if game["homeTeam"]["score"] != game["awayTeam"]["score"]:
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
    
    if game["gameState"]:
        # TODO TODO TODO TODO TODO THIS IS JUST TO GET US OUT OF HERE
        return ""
    elif game["linescore"]["currentPeriodOrdinal"] == "OT":
        return " in overtime"
    elif game["linescore"]["currentPeriodOrdinal"] == "SO":
        return " in a shootout"
    elif game["linescore"]["currentPeriod"] > 3:
        print("this is weird: period is " + game["linescore"]["currentPeriodOrdinal"])
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

    status = game["gameState"]

    if status in ("PRE","FUT"):        # scheduled, pregame
        loc = game_loc(game)
        ret = teamDisplayName(game["awayTeam"])
        homeTeam = teamDisplayName(game["homeTeam"])
        ret += " visit " if (ret in NHL_TEAMNAME_AS_PLACENAME) else " visits "
        ret += " the " if homeTeam in NHL_TEAMNAME_AS_PLACENAME else "" 
        ret += homeTeam
        if game["neutralSite"]:    # unusual venue
            ret = (ret.replace(" play"," visit") + game_loc(game))

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
        
    elif status in ("LIVE"):    # in progress, ??in progress - critical TODO TODO TODO TODO TODO
        base = game_loc(game) + ", " + scoreline(game)
        timeset = game_time_set(game)
        if not timeset.startswith("at "):
            base += ","
        return base + " " + timeset + "."
    
    elif status in ("FINAL","OFF"):    # final, official
        ret = "Final " + game_loc(game) + ", " + scoreline(game) + final_qualifier(game) + "."
        return ret
        
    elif (status == 9): # postponed TODO TODO TODO TODO TODO TODO
        ret = teamDisplayName(game["awayTeam"])
        loc = game_loc(game)
        if loc.startswith("at"):
            ret += " vs. "
        else:
            ret += " at "
        ret += teamDisplayName(game["homeTeam"])
        if loc.startswith("at"):
            ret += " " + game_loc(game)
        ret += " is postponed."
        return ret
        
    else:
        return "HELP, I don't understand gamestatus " + str(status) + " yet for " + game["awayTeam"]["placeName"]["default"] + " at " + game["homeTeam"]["placeName"]["default"]
    
        
def get(team,fluidVerbose=False,rewind=False,ffwd=False):

    global __MOD
    
    vtoc = buildVarsToCode()
    #print vtoc
    
    tkey = team.lower().strip()
    
    if tkey in dabBacks:
        raise DabException(dabBacks[tkey])
    
    if not ((tkey == "scoreboard") or (tkey in vtoc)):
        raise NoTeamException
    
    sb = get_scoreboard(fluidVerbose=fluidVerbose,rewind=rewind,ffwd=ffwd)
    # what we should have now is the ["games"] list. which is fine raw if it's "scoreboard" but needs processing if 
    #print json.dumps(sb, sort_keys=True, indent=4, separators=(',', ': '))
    try:
        __MOD["dst"] = todayIsDst(sb)
    except TzFailedUseLocalException:
        __MOD["dst"] = "local"
    
    ret = ""
    
    if tkey == "scoreboard":
        game = sb
    else:
        game = get_game(sb,vtoc[tkey])
    
    if not game:    # valid for game = [] as well
        if game.__class__ == list:
            ret = "No games today."
        else:    
            ret = "No game today for the " + capwords(vtoc[tkey]) + "."
        raise NoGameException(ret)
    
    elif game.__class__ == list:    # full scoreboard or preseason split-squad
        ret = ""
        for g in game:
            ret += sentenceCap(phrase_game(g)) + "\n"
        if len(ret) > 0:
            ret = ret[:-1]
    else:
        ret = sentenceCap(phrase_game(game))
        
    return ret
