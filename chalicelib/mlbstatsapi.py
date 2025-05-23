#!/usr/bin/python

import urllib.request, urllib.error, urllib.parse, json, traceback 
from datetime import timedelta, datetime, date, timezone
import dateutil.parser
from zoneinfo import ZoneInfo
from os import sys

from .nat_lib import *
from .reset_lib import NoGameException, NoTeamException, DabException,RESET_RICH_SLACK,RESET_TEXT,RESET_SHORT_SLACK

ROLLOVER_LOCALTIME_INT = 1000        # for resetter this is UTC because Lambda runs in UTC
PLAYOFF_GAME_TYPES = ['F','D','L','W']
FILTER_STANDARD = "FILTER_STANDARD"
FILTER_OVERRIDETV = "FILTER_OVERRIDETV"
STAT_MISS = "STAT_MISS"

#logLevel = logging.DEBUG
#logFN = "resetter.log"

vtoc = None

def iso8601toLocalTZ(isoUTC,preferredTZName="America/New_York"):

    gameTime = dateutil.parser.parse(isoUTC)
    localGameTime = gameTime.replace(tzinfo=timezone.utc).astimezone(ZoneInfo(preferredTZName))
    return localGameTime.strftime("%-I:%M %p ").replace(" PM","") + localGameTime.tzname()

"""Find relevant game nodes (to team or "schedule"/"scoreboard") and filter out the rest."""
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
    local_vtoc  = {"schedule":"schedule", "scoreboard":"scoreboard"}
    for k in codeToVariants:
        for var in codeToVariants[k]:
            if var in local_vtoc :
                raise Exception("OOPS: trying to duplicate pointer " + var + " as " + k + ", it's already " + local_vtoc [var])
            else:
                local_vtoc [var] = k
                local_vtoc [var.lower()] = k
                local_vtoc [var.upper()] = k
        # and before we go, do k = k too
        local_vtoc [k] = k
        local_vtoc [k.lower()] = k    # it's already upper
        
    return local_vtoc 

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


def getReset(g,team,fluidVerbose,filterMode=FILTER_STANDARD,gameFormat=RESET_TEXT,returnFinalTuple=False):
    if g == None:
        return "No game today."

    stat = g["status"]["detailedState"]
    reset = ""
    is_dh = is_doubleheader(g)
    if (team in ["scoreboard","schedule"]):
        homeaway = "national"
    else:
        homeaway = "away" if team == g["teams"]["away"]["team"]["abbreviation"] else "home"
        

    if filterMode == FILTER_OVERRIDETV:
        if team not in (g["teams"]["away"]["team"]["abbreviation"],g["teams"]["home"]["team"]["abbreviation"]):
            # in this situation, we want to return TV only if it's a national game. 
            # If there's no TV coming back, eventually this game will get discarded.
            team = "scoreboard"

    if stat in PREGAME_STATUS_CODES:
        #reset += getProbables(g,team,verbose=fluidVerbose)
        reset += getProbables(g,team,verbose=fluidVerbose,gameFormat=gameFormat)

        if stat in ANNOUNCE_STATUS_CODES:    # delayed start
            reset = reset[:-1] + " (" + stat.lower() + ")."

    elif stat in UNDERWAY_STATUS_CODES:
        
        inningState = g["linescore"]["inningState"].lower()
        reset = placeAndScore(g) + ", " + inningState + " of the " + g["linescore"]["currentInningOrdinal"] + ". "
        
        # might have at, might have in as the front.        
        if is_dh:
            reset = "Game " +str(g["gameNumber"]) + " " + reset
        else:
            reset = reset[0].upper() + reset[1:]
                        
        if inningState in ("top","bottom"):     #in play
            
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
            
            outs = str(g["linescore"]["outs"])
            if outs == "0":
                reset += "No outs. "
            elif outs == "1":
                reset += outs + " out. "
            else:
                reset += outs + " outs. "

    elif stat in FINAL_STATUS_CODES:
        reset += "Final "
        if is_dh:
            reset += "of game " + str(g["gameNumber"]) + " "
        reset += placeAndScore(g)
        if (g["linescore"]["currentInning"] != 9):
            reset += " in " + str(g["linescore"]["currentInning"]) + " innings"
        reset += ". "
    elif stat not in POSTPONED_STATUS_CODES and "TV" not in reset:
        # if it's not final, we want TV. National at least, local if it's a team we specifically requested.
        reset += STAT_MISS
        tvNets = getTVNets(g,homeaway)
        reset += (' TV: ' + tvNets + '. ') if (tvNets != None and tvNets != "") else ""
    
    if (len(reset) == 0):
        reset = STAT_MISS

    if (STAT_MISS in reset):
        # common path for various weird statuses with a specific cutout for postponed
        reset = reset.replace(STAT_MISS, g["teams"]["away"]["team"]["teamName"] + " at " + g["teams"]["home"]["team"]["teamName"] )
        
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
    if filterMode == FILTER_OVERRIDETV and "TV: " not in reset:
        return None
    
    if returnFinalTuple:
        # (pk, reset, isFinal, isWin)
        isFinal = False
        isWin = False
        if (stat in FINAL_STATUS_CODES):
            isFinal = True
            hruns = g["linescore"]["teams"]["home"]["runs"]
            aruns = g["linescore"]["teams"]["away"]["runs"]
            isWin = (((hruns > aruns) and (homeaway == "home")) or ((aruns > hruns) and (homeaway == "away")))

        return (g["gamePk"],reset,isFinal,isWin)
    else:
        return reset
    
    
def loadSAPIScoreboard(sapiURL, scheduleDT):
    
    #print( "Running scoreboard for " + scheduleDT.strftime("%Y-%m-%d"))
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

def getPitcher(g,ah,verbose=True):
    if ah not in ("away","home"):
        return None
    
    if "probablePitcher" not in list(g["teams"][ah].keys()):
        pstr = "TBA"
    else:
        pitcher = g["teams"][ah]["probablePitcher"]
        pstr = ""
        try:
            usock = urllib.request.urlopen("http://statsapi.mlb.com" + pitcher["link"],timeout=3)
            pitcherDict = json.load(usock)
            pstr = pitcherDict["people"][0]["boxscoreName"]
        except:
            pstr = pitcher["fullName"]
        
        if "," in pstr:
            pstr = pstr + "."
        pstr = pstr + " " + getWLERA(pitcher)
    
    tNameSelector = "shortName" if verbose else "abbreviation"
    return (g["teams"][ah]["team"][tNameSelector] + " (" + pstr + ")")

def getWLERA(pitcher):
    for sg in pitcher["stats"]:
        if sg["group"]["displayName"] == "pitching" and sg["type"]["displayName"] == "statsSingleSeason":
            return str(sg["stats"]["wins"]) + "-" + str(sg["stats"]["losses"]) + " " + sg["stats"]["era"]
    return ""

def getTVNets(g,ah=None,suppressIntl=True):
    ret = []
    if not ("broadcasts" in g):
        return None
    for bc in g["broadcasts"]:
        if bc["type"] == "TV":
            if (("isNational" in list(bc.keys())) or (ah and bc["homeAway"] == ah)):
                name = bc["name"]
                if suppressIntl and name.endswith("-INT"):
                    pass
                elif name not in ret:
                    ret.append(name)
    return ", ".join(ret)

def getProbables(g,tvTeam=None,preferredTZ="America/New_York",verbose=True,gameFormat=RESET_TEXT):
    if g == None:
        return None
    
    pitcherVerbosity = False if gameFormat in (RESET_SHORT_SLACK) else True
    
    if not verbose:
        runningStr = g["teams"]["away"]["team"]["teamName"] + " at " + g["teams"]["home"]["team"]["teamName"]
    else:
        runningStr = getPitcher(g,"away",pitcherVerbosity) + " at " + getPitcher(g,"home",pitcherVerbosity)

    if is_doubleheader(g):
        runningStr += ' (game ' + str(g["gameNumber"]) + ')'
    
    startStr = ", *" + iso8601toLocalTZ(g["gameDate"]) + "*." #if ((gameFormat == RESET_SHORT_SLACK) or (not verbose)) else " starts at "
    runningStr += startStr #+ iso8601toLocalTZ(g["gameDate"]) + "."
    
    if tvTeam and (tvTeam not in ("suppress","scoreboard","schedule")):
        # we used to suppress playoff display here. I don't think we need to anymore.
        #homeAbbr if we ever want that: = g["teams"]["home"]["team"]["abbreviation"]
        homeaway = "away" if tvTeam == g["teams"]["away"]["team"]["abbreviation"] else "home"
        tvNets = getTVNets(g,homeaway)
        runningStr += (' TV: ' + tvNets + '. ') if (tvNets != None and tvNets != "") else ""
    
    return runningStr

def getGameNodesForTeam(team,rewind=False,ffwd=False,inOverride=False,date=None):
    global vtoc
    if not vtoc:
        vtoc = buildVarsToCode()
    
    #logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s',filename=logFN, level=logLevel)
    
    localRollover = ROLLOVER_LOCALTIME_INT
    if date and (rewind or ffwd):
        raise NoGameException("mlbstatsapi.get can either take a literal date or rewind/ffwd, but not both. Returning no games.")
    # for testing
    if rewind:
        # force yesterday's games by making the rollover absurd.
        localRollover += 2400
    if ffwd:
        localRollover -= 2400
    
    teamLiteral = team
    team = team.strip().lower()
    
    if team in dabList:
        #return ["Did you mean " + join(dabList[team.lower()]," or ") + "?"]
        raise DabException(dabList[team])
    elif team not in vtoc:
        raise NoTeamException
    
    if date:
        todayDT = datetime(date.year,date.month,date.day,0,0,0)
    else:
        todayDT = datetime.now() - timedelta(minutes=((localRollover/100)*60+(localRollover%100)))
    
    print("loading scoreboard request '%s' from %s %s" % (team, statsApiScheduleUrl, todayDT.strftime("%m/%d/%Y, %H:%M:%S")))
    sapiScoreboard = loadSAPIScoreboard(statsApiScheduleUrl,todayDT)
    
    if sapiScoreboard:
        # this is where it gets a little different for the override case. for override=tv, we want to
        # get a full scoreboard, but do something special with the team.
        if ("tv" == inOverride):
            gns = findGameNodes(sapiScoreboard,vtoc["scoreboard"])
        else:
            gns = findGameNodes(sapiScoreboard,vtoc[team])
    else:
        gns = []
    
    if len(gns) == 0:
        if team in ("schedule","scoreboard"):
            ngstr = "No games today in MLB."
        else:
            ngstr = "No game today for " + team + "."
        raise NoGameException(ngstr)
    
    return gns

def get(team,fluidVerbose=True,rewind=False,ffwd=False,inOverride=False,date=None,gameFormat=RESET_TEXT,returnFinalTuple=False):
    
    global vtoc
    if not vtoc:
        vtoc = buildVarsToCode()
    
    filterMode = FILTER_STANDARD
    if "tv" == inOverride:
        filterMode = FILTER_OVERRIDETV

    gns = getGameNodesForTeam(team,rewind,ffwd,inOverride,date)
    
    rv = []
    for gn in gns:
        try:
            resetVal = getReset(gn,vtoc[team],fluidVerbose, filterMode,gameFormat,returnFinalTuple)
        except Exception as resetExcept:
            print("This all blew up as " + str(resetExcept) + "\n" + str(gn))
            resetVal = None
        
        rv.append(resetVal) if resetVal else None
        #print "rv is " + str(rv)
    
    return rv

def getFinal(team):
    retTuples = get(team=team,returnFinalTuple=True)
    retSet = []
    for retTuple in retTuples:
        try:
            (pk,reset,isFinal,isWin) = retTuple
            if isFinal:
                retSet.append(retTuple)
            else:
                return None
        except Exception as e:
            print("getFinal got something it didn't expect: ", str(retTuple), e)
    return retSet

def transitionPoller(team):
    # monitor games for team occurring on the current date for status transitions. when they do, return what kind of transition it is, or None for no transition.

    # types of transitions:
    # pregame -> active
    # pregame -> delayed
    # pregame -> postponed
    # active -> suspended
    # active -> final
    # active -> postponed
    # delayed -> active
    # delayed -> suspended
    # delayed -> postponed
    # delayed -> final
    # suspended -> final
    # suspended -> postponed



    return