#!/usr/bin/env python
#encoding: utf-8

#import urllib.request, urllib.error, urllib.parse, 
import json, time
from urllib.request import Request, urlopen
from datetime import datetime, timedelta
from .reset_lib import joinOr, sentenceCap, toOrdinal, NoGameException, NoTeamException, DabException, RESET_TEXT, RESET_RICH_SLACK
from string import capwords

intRolloverUtcTime = 1000

TZ_USE_EASTERN = True

#SCOREBOARD_URL_JSON = "https://statsapi.web.nhl.com/api/v1/schedule?startDate=YYYY-MM-DD&endDate=YYYY-MM-DD&expand=schedule.teams,schedule.linescore,schedule.broadcasts.all,schedule.ticket,schedule.game.content.media.epg,schedule.radioBroadcasts,schedule.decisions,schedule.scoringplays,schedule.game.content.highlights.scoreboard,team.leaders,schedule.game.seriesSummary,seriesSummary.series&leaderCategories=points,goals,assists&leaderGameTypes=R&site=en_nhl&teamId=&gameType=&timecode="
SCOREBOARD_URL_JSON = "https://api-web.nhle.com/v1/schedule/YYYY-MM-DD"
SCORENOW_URL_JSON = "https://api-web.nhle.com/v1/score/now"

DEBUG_LEVEL = "DEBUG"

GAME_RESET = "RESET"
GAME_ISFINAL = "GAME_ISFINAL"
GAME_PK = "GAME_PK"
GAME_IS_WIN_FOR_TEAM = "GAME_IS_WIN_FOR_TEAM"

validTeams = ("rangers","islanders","capitals","flyers","penguins","blue jackets","hurricanes","devils",
    "red wings","sabres","maple leafs","senators","canadiens","bruins","panthers","lightning",
    "predators","blackhawks","blues","wild","jets","stars","avalanche",
    "oilers","flames","canucks","sharks","kings","ducks","golden knights","kraken","utahhc"
)

dabBacks = {
    "ny":["Rangers","Islanders"]
}

TEAM_ID_TO_OUTPUT = {11: 'Thrashers', 34: 'Whalers', 31: 'North Stars', 32: 'Nordiques', 33: 'Jets (1979)', 35: 'Rockies', 36: 'Senators (1917)', 37: 'Tigers', 
                     38: 'Pirates', 39: 'Quakers', 40: 'Cougars', 41: 'Wanderers', 42: 'Bulldogs', 43: 'Maroons', 44: 'Americans', 45: 'Eagles', 46: 'Seals', 
                     47: 'Flames', 48: 'Scouts', 49: 'Barons', 50: 'Falcons', 51: 'Americans', 1: 'Devils', 56: 'Golden Seals', 57: 'Arenas', 58: 'St. Patricks', 
                     99: 'NHL', 17: 'Red Wings', 6: 'Bruins', 52: 'Jets', 28: 'Sharks', 5: 'Penguins', 14: 'Lightning', 4: 'Flyers', 10: 'Maple Leafs', 7: 'Sabres', 
                     12: 'Hurricanes', 53: 'Coyotes', 20: 'Flames', 8: 'Canadiens', 15: 'Capitals', 26: 'Kings', 23: 'Canucks', 21: 'Avalanche', 18: 'Predators', 
                     24: 'Ducks', 54: 'Golden Knights', 55: 'Kraken', 25: 'Stars', 27: 'Coyotes', 16: 'Blackhawks', 3: 'Rangers', 29: 'Blue Jackets', 13: 'Panthers', 
                     22: 'Oilers', 30: 'Wild', 19: 'Blues', 9: 'Senators', 2: 'Islanders', 59: 'Utah HC'}

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

    'CAR':["hurricanes","carolina","canes","car","jerks","whale","whalers","hartford","brass bonanza","carolina hurricanes"],
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
    #'ARI':["coyotes",'phx','ari','arizona','yotes',"phoenix"],
    'UTA':["utahhc","utah","utah hockey club","utah hc","hockey club","hc"],
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

def get_scoreboard(file=None,fluidVerbose=False,rewind=False,ffwd=False,date=None):
    """Get scoreboard from site, or from file if specified for testing."""

    global __MOD

    if file:
        # we're just going to use this as scoreboard rather than scorenow for the moment.
        fh = open(file)
        sb = json.loads(fh.read())
        __MOD["date"] = sb['gameWeek'][0]['date']
    
    else:
        if date:
            todayScoreboardUrl = SCOREBOARD_URL_JSON.replace("YYYY-MM-DD",date.strftime("%Y-%m-%d"))
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
        
        #now we have a todayScoreboardUrl, one way or another
        req = Request(todayScoreboardUrl)
        req.add_header('User-agent', 'Mozilla/5.0')
        raw = json.loads(urlopen(req).read())
    
    if (rewind or ffwd or date):
        # we used the scoreboard rather than scorenow
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
    overrides = {'Montréal':'Montreal','St Louis':'St. Louis',"Rangers":"NY Rangers","Islanders":"NY Islanders"}
    sname = team["placeName"]["default"]
    if sname in overrides:
        return overrides[sname]
    # in 24-25, placeName switched to just 'New York' for both teams. We have the abbreviation though.
    if team['abbrev'] == 'NYR':
        return "NY Rangers"
    elif team['abbrev'] == 'NYI':
        return "NY Islanders"
    # else...
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
    
    gameutc = datetime.strptime(game['startTimeUTC'],'%Y-%m-%dT%H:%M:%SZ')
    startdelay = datetime.utcnow() - gameutc

    if TZ_USE_EASTERN:
        homezoneOffset = game["easternUTCOffset"].split(':')[0]
        if int(homezoneOffset) == -5:
            homezoneName = "EST"
        else:
            homezoneName = "EDT"
        #homezoneName = "ET"
    else:
        # tz is name, offset is hrs off
        homezoneOffset = game["venueUTCOffset"].split(':')[0]
        homezoneName = game["venueTimezone"]
        if homezoneName.startswith("US/"):
            homezoneName = homezoneName.replace("US/","")
        # TODO they use many janky Zoneinfo names that you'd want to have a conversion map for in production
    
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

    if "clock" not in game:
        # we got a live game from the scoreboard endpoint that only has a period descriptor. 
        # This will only happen if you explicitly call with a date during live games.
        # this is unexpected so we're going to play it cheap
        if game["periodDescriptor"]["number"] == 4:
            return "in OT"
        else:
            return "in the " + toOrdinal(game["periodDescriptor"]["number"]) + " period"

    # assumption good from here: we're only getting a LIVE game here from the SCORENOW endpoint.
    if game["clock"]["inIntermission"]:
        pd = toOrdinal(game["period"])
        if pd in ("3rd","4th"):
            return "going to overtime"
        elif pd not in ("1st","2nd"):
            print("WAIT WHAT INTERMISSION IS THIS: " +pd)
        return "at the " + pd + " intermission"

    trem = game["clock"]["timeRemaining"].strip()
    if trem.startswith("0"):
        trem = trem[1:]
    pd = toOrdinal(game["period"])
    
    if trem == '20:00':
        return "start of the " + pd
    elif trem == 'END':
        if pd == "3rd":
            return "at the end of regulation"
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
        if pd == "4th":
            pd = "OT"
        elif pd != "OT":
            pd = "the " + pd
        return trem + " to go in " + pd

def final_qualifier(game):
    """return 'in overtime' or 'in a shootout' if appropriate for the 
    final score. Assume the game went there."""
    
    if game["gameOutcome"]["lastPeriodType"] == "OT":
        return " (OT)"
    elif game["gameOutcome"]["lastPeriodType"] == "SO":
        return " (SO)"
    elif game["periodDescriptor"]["number"] > 3:
        print("this is weird: period is " + game["periodDescriptor"]["number"] + ", lastPeriodType is " + game["gameOutcome"]["lastPeriodType"])
        return " in " + game["gameOutcome"]["lastPeriodType"]
    else:
        return ""

def fix_for_delay(ret):

    ret = ret.replace("plays","vs.")
    ret = ret.replace("play","vs.")
    ret = ret.replace("visits","at")
    ret = ret.replace("visit","at")
    return ret                
    

def phrase_game(game,format=RESET_TEXT):

    status = game["gameState"]
    scheduleState = game["gameScheduleState"]

    if scheduleState in ('CNCL', 'PPD'):   # weird because the gameState itself never leaves 'FUT'
        
        fullMap = {'CNCL':'cancelled','PPD':'postponed'}
        ret = teamDisplayName(game["awayTeam"])
        loc = game_loc(game)
        if loc.startswith("at"):
            ret += " vs. "
        else:
            ret += " at "
        ret += teamDisplayName(game["homeTeam"])
        if loc.startswith("at"):
            ret += " " + game_loc(game)
        ret += " is " + fullMap[scheduleState] + "."
        return ret
    
    if status in ("PRE","FUT"):        # scheduled, pregame
        loc = game_loc(game)
        ret = teamDisplayName(game["awayTeam"])
        homeTeam = teamDisplayName(game["homeTeam"])
        if (ret in NHL_TEAMNAME_AS_PLACENAME or ("placeName" not in game["awayTeam"])):
            ret = "the " + ret #+ " visit "
        #else:
        #    ret += " visits "
        ret += " at "
        ret += "the " if (homeTeam in NHL_TEAMNAME_AS_PLACENAME or ("placeName" not in game["homeTeam"])) else "" 
        ret += homeTeam
        if game["neutralSite"]:    # unusual venue
            ret = (ret.replace(" play"," visit") + " " + game_loc(game))

        try:
            gametime = local_game_time(game)
            if (format == RESET_RICH_SLACK):
                ret += ", *" + gametime + "*."
            else:
                ret += " starts at " + gametime + "."
        except ShortDelayException:
            ret = fix_for_delay(ret)
            ret += " will be underway momentarily."
        except LateStartException as lse:
            ret = fix_for_delay(ret)
            ret += ", scheduled for " + str(lse) + ", is delayed (or the league web site has no data)."
        return ret
        
    elif status in ("LIVE","CRIT"):    # in progress, critical
        base = game_loc(game) + ", " + scoreline(game)
        timeset = game_time_set(game)
        if not timeset.startswith("at "):
            base += ","
        return base + " " + timeset + "."
    
    elif status in ("FINAL","OFF"):    # final, official
        ret = "Final " + game_loc(game) + ", " + scoreline(game) + final_qualifier(game) + "."
        return ret
        
    else:
        return "HELP, I don't understand gamestatus " + str(status) + " yet for " + str(game)
    
        
def get(team,fluidVerbose=False,rewind=False,ffwd=False,date=None,gameFormat=RESET_TEXT):
    #return _getResetWithMetadata(team,fluidVerbose,rewind,ffwd,date,gameFormat)[GAME_RESET]
    return "\n".join(x[GAME_RESET] for x in _getResetWithMetadata(team,fluidVerbose,rewind,ffwd,date,gameFormat))

"""
Returns list of reset+metadata items.
"""
def _getResetWithMetadata(team,fluidVerbose=False,rewind=False,ffwd=False,date=None,gameFormat=RESET_TEXT):

    vtoc = buildVarsToCode()
    
    tkey = team.lower().strip()
    
    if tkey in dabBacks:
        raise DabException(dabBacks[tkey])
    
    if not ((tkey == "scoreboard") or (tkey in vtoc)):
        raise NoTeamException
    
    sb = get_scoreboard(fluidVerbose=fluidVerbose,rewind=rewind,ffwd=ffwd,date=date)
    
    ret = ""
    
    if tkey == "scoreboard":
        game = sb
    else:
        game = get_game(sb,vtoc[tkey])
        #print("HEY, DEBUGGING FOR " + vtoc[tkey] + ":\n" + str(game))
    
    if not game:    # game is None or empty list 
        if game.__class__ == list:
            ret = "No games today."
        else:    
            ret = "No game today for the " + capwords(vtoc[tkey]) + "."
        raise NoGameException(ret)
    
    elif game.__class__ != list:    # full scoreboard or preseason split-squad
        game = [game]
    ret = []
    for g in game:
        try:
            gmeta = {
                GAME_RESET: sentenceCap(phrase_game(g,gameFormat)),
                GAME_ISFINAL:(('gameState' in g) and (g['gameState'] in ('FINAL','OFF'))),
                GAME_PK:g['id'],
                GAME_IS_WIN_FOR_TEAM: isGameWinForTeam(g,(tkey if tkey == "scoreboard" else vtoc[tkey]))            
            }
        except Exception as e:
            print("Exception in game " + str(g['id']))
            print(e)
        #print ("for team " + (tkey if tkey == "scoreboard" else vtoc[tkey]) + ": " + str(gmeta))
        ret.append(gmeta)
        
    return ret


def getFinal(team,fluidVerbose=False,rewind=False,ffwd=False,date=None,gameFormat=RESET_TEXT):
    # for the given team, if their game is final, get a primary key, a reset, and if it's a win. If it isn't final, return None.
    # primary key is because there can be split-squad games preseason, and we'd like to reuse the framework for baseball doubleheaders too.
    try:
        gameMeta = _getResetWithMetadata(team,fluidVerbose,rewind,ffwd,date,gameFormat)
        if gameMeta[GAME_ISFINAL]:
            return(gameMeta[GAME_PK],gameMeta[GAME_RESET])
        else:
            return None

    except NoGameException as e:
        return None
    except Exception as e:
        return None

def isGameWinForTeam(game,team):
    if team == "scoreboard":
        return False
    
    # first clear the non-final case
    if not (('gameState' in game) and (game['gameState'] in ('FINAL','OFF'))):
        return False
    
    if game['homeTeam']['abbrev'] == team:
        thisTeam = game['homeTeam']
        otherTeam = game['awayTeam']
    else:
        thisTeam = game['awayTeam']
        otherTeam = game['homeTeam']
    
    return thisTeam['score'] > otherTeam['score']