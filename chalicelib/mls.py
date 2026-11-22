#!/usr/bin/env python

# MLS via ESPN's unofficial site API (issue #17):
#   https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard?dates=YYYYMMDD
# Soccer only accepts a single date, not a range. "Today" is the US Eastern date, like the other leagues.

import re
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from .reset_lib import NoGameException, NoTeamException, DabException, sentenceCap, RESET_TEXT

SCOREBOARD_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/scoreboard"
TEAMS_URL = "https://site.api.espn.com/apis/site/v2/sports/soccer/usa.1/teams"
LEAGUE_TZ = ZoneInfo("America/New_York")
CACHE_INTERVAL = timedelta(minutes=1)
# a match that kicks off late in the West can go final after midnight Eastern; monitors look back a day until then
LATE_FINAL_CUTOFF_HOUR = 6

# alias -> ESPN abbreviation. Names ESPN already gives (abbreviation, displayName, shortDisplayName,
# nickname) also match, via _match_team; this adds what people actually type.
ALIASES = {
    "atlanta": "ATL", "atlanta united": "ATL", "atl utd": "ATL", "atlutd": "ATL",
    "austin": "ATX", "austin fc": "ATX",
    "montreal": "MTL", "cf montreal": "MTL", "impact": "MTL",
    "charlotte": "CLT", "charlotte fc": "CLT",
    "chicago": "CHI", "fire": "CHI", "chicago fire": "CHI",
    "colorado": "COL", "rapids": "COL",
    "columbus": "CLB", "crew": "CLB", "columbus crew": "CLB",
    "dc": "DC", "dc united": "DC", "dcu": "DC", "d.c. united": "DC",
    "cincinnati": "CIN", "fc cincinnati": "CIN", "fcc": "CIN",
    "dallas": "DAL", "fc dallas": "DAL", "fcd": "DAL",
    "houston": "HOU", "dynamo": "HOU",
    "miami": "MIA", "inter miami": "MIA",
    "galaxy": "LA", "la galaxy": "LA",
    "lafc": "LAFC",
    "minnesota": "MIN", "minnesota united": "MIN", "loons": "MIN", "mnufc": "MIN",
    "nashville": "NSH", "nashville sc": "NSH",
    "new england": "NE", "revs": "NE", "revolution": "NE",
    "nycfc": "NYC", "nyc": "NYC", "new york city": "NYC", "nyc fc": "NYC",
    "orlando": "ORL", "orlando city": "ORL",
    "philadelphia": "PHI", "philly": "PHI", "union": "PHI",
    "portland": "POR", "timbers": "POR",
    "rsl": "RSL", "real salt lake": "RSL", "salt lake": "RSL",
    "red bulls": "RBNY", "rbny": "RBNY", "red bull": "RBNY", "ny red bulls": "RBNY",
    "san diego": "SD", "sdfc": "SD",
    "san jose": "SJ", "quakes": "SJ", "earthquakes": "SJ",
    "seattle": "SEA", "sounders": "SEA",
    "skc": "SKC", "kansas city": "SKC", "sporting": "SKC", "sporting kc": "SKC",
    "st louis": "STL", "stl city": "STL", "city sc": "STL",
    "toronto": "TOR", "tfc": "TOR", "toronto fc": "TOR",
    "vancouver": "VAN", "whitecaps": "VAN", "caps": "VAN",
}
KNOWN_ABBRS = set(ALIASES.values())
# names that fit more than one club: ask which
AMBIGUOUS = {
    "united": ["D.C. United", "Atlanta United FC", "Minnesota United FC"],
    "new york": ["New York City FC", "Red Bull New York"],
    "ny": ["New York City FC", "Red Bull New York"],
    "la": ["LA Galaxy", "LAFC"],
    "los angeles": ["LA Galaxy", "LAFC"],
}

_cache = {}


def _norm(name):
    """lowercase, no accents or punctuation: 'D.C. United' -> 'dc united', 'CF Montréal' -> 'cf montreal'"""
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", name.lower())).strip()


def league_today():
    return datetime.now(LEAGUE_TZ).date()


def get_scoreboard(day):
    """events for one Eastern date, cached for a minute"""
    key = day.isoformat()
    hit = _cache.get(key)
    if hit and datetime.now(timezone.utc) - hit[0] < CACHE_INTERVAL:
        return hit[1]
    resp = requests.get(SCOREBOARD_URL, params={"dates": day.strftime("%Y%m%d")}, timeout=10)
    resp.raise_for_status()
    events = resp.json().get("events", [])
    _cache[key] = (datetime.now(timezone.utc), events)
    return events


def _competitors(event):
    comps = event["competitions"][0]["competitors"]
    home = next(c for c in comps if c["homeAway"] == "home")
    away = next(c for c in comps if c["homeAway"] == "away")
    return home, away


def _espn_team_names():
    """normalized name -> abbreviation for every name ESPN gives each club. Fetched once per Lambda instance,
    and only when ALIASES doesn't know a name, so new clubs work without a code change."""
    if "teams" not in _cache:
        resp = requests.get(TEAMS_URL, timeout=10)
        resp.raise_for_status()
        names, display = {}, {}
        for entry in resp.json()["sports"][0]["leagues"][0]["teams"]:
            t = entry["team"]
            display[t["abbreviation"]] = t["displayName"]
            for k in ("abbreviation", "displayName", "shortDisplayName", "location", "name", "nickname"):
                if t.get(k):
                    names[_norm(t[k])] = t["abbreviation"]
        _cache["teams"], _cache["display"] = names, display
    return _cache["teams"]


def _resolve(team):
    """team string -> ESPN abbreviation, or raise DabException / NoTeamException"""
    key = _norm(team)
    if key in AMBIGUOUS:
        raise DabException(AMBIGUOUS[key])
    if key.upper() in KNOWN_ABBRS:
        return key.upper()
    if key in ALIASES:
        return ALIASES[key]
    abbr = _espn_team_names().get(key)
    if not abbr:
        raise NoTeamException(team + " is not an MLS team.")
    return abbr


def _display_name(abbr):
    """club name for 'No MLS match today for ...': ESPN's full display name, e.g. 'D.C. United'"""
    _espn_team_names()
    return _cache["display"].get(abbr, abbr)


def _match_team(events, team):
    """events involving team, with the team's abbreviation (for win/loss)"""
    abbr = _resolve(team)
    return [(e, abbr) for e in events if abbr in (side["team"]["abbreviation"] for side in _competitors(e))]


def _name(side):
    """full club name, as soccer writes it: 'FC Cincinnati', not 'Cincinnati'"""
    return side["team"].get("displayName") or side["team"]["shortDisplayName"]


def _in_city(event):
    """' in Foxborough'. ESPN sometimes puts the venue name in the city field (FC Dallas: 'Toyota Stadium'),
    and then ' at Toyota Stadium' reads right."""
    venue = event["competitions"][0].get("venue") or {}
    city = ((venue.get("address") or {}).get("city") or "").split(",")[0].strip()
    if city and city != venue.get("fullName"):
        return " in " + city
    return (" at " + venue["fullName"]) if venue.get("fullName") else ""


def _kickoff(event):
    """'at 7:30 PM ET' today, or 'Sunday at 4:00 PM ET' on another day"""
    start = datetime.strptime(event["date"], "%Y-%m-%dT%H:%MZ").replace(tzinfo=timezone.utc).astimezone(LEAGUE_TZ)
    clock = "at " + start.strftime("%I:%M %p").lstrip("0") + " ET"
    if start.date() == league_today():
        return clock
    return start.strftime("%A") + " " + clock


def _scoreline(event):
    """home first, whatever the score, as soccer writes it: 'FC Cincinnati 1, Nashville SC 2'"""
    home, away = _competitors(event)
    return "%s %s, %s %s" % (_name(home), home.get("score", "0"), _name(away), away.get("score", "0"))


def _shootout_note(event):
    comp = event["competitions"][0]
    for note in comp.get("notes") or []:
        if "penalt" in (note.get("headline") or "").lower():
            return note["headline"]
    home, away = _competitors(event)
    if "shootoutScore" in home and "shootoutScore" in away:
        winner = home if home.get("winner") else away
        loser = away if winner is home else home
        return "%s win %s-%s on penalties" % (_name(winner), winner["shootoutScore"], loser["shootoutScore"])
    return None


def phrase_match(event):
    status = event["competitions"][0]["status"]
    stype = status["type"]
    state, name = stype.get("state"), stype.get("name", "")
    home, away = _competitors(event)

    if state == "pre":
        if name == "STATUS_SCHEDULED":
            if stype.get("detail", "").upper() == "TBD":
                return "%s vs. %s%s, time TBD." % (_name(home), _name(away), _in_city(event))
            return "%s vs. %s %s%s." % (_name(home), _name(away), _kickoff(event), _in_city(event))
        # delayed, etc.
        return "%s vs. %s%s is %s." % (_name(home), _name(away), _in_city(event), stype.get("description", "delayed").lower())

    if state == "post":
        if not stype.get("completed"):
            # postponed, canceled, abandoned
            return "%s vs. %s%s is %s." % (_name(home), _name(away), _in_city(event), stype.get("description", "off").lower())
        ret = "Full time%s, %s" % (_in_city(event), _scoreline(event))
        if name == "STATUS_FINAL_AET":
            ret += " after extra time"
        shootout = _shootout_note(event) if name == "STATUS_FINAL_PEN" else None
        if shootout:
            ret += "; " + shootout
        return ret + "."

    # in progress
    desc = stype.get("description", "")
    if name == "STATUS_HALFTIME":
        where = "at halftime"
    elif status.get("displayClock") and name not in ("STATUS_SHOOTOUT",):
        where = status["displayClock"]
    else:
        where = desc.lower() or "in progress"
    return "%s, %s%s." % (_scoreline(event), where, _in_city(event))


def _events_for(ffwd=False, date=None):
    if date and ffwd:
        raise NoGameException("I can take either a date or tomorrow, but not both.")
    day = date or league_today()
    if ffwd:
        day += timedelta(days=1)
    return day, get_scoreboard(day)


def get(team, ffwd=False, date=None, gameFormat=RESET_TEXT, inOverride=False, rewind=False, **kwargs):
    """reset text for a team's match (or every match, for 'scoreboard') on the day asked for"""
    day, events = _events_for(ffwd=ffwd or False, date=date or None)
    when = "today" if day == league_today() else ("tomorrow" if day == league_today() + timedelta(days=1) else "on " + day.strftime("%B %-d"))
    if team.strip().lower() in ("scoreboard", "schedule", ""):
        if not events:
            raise NoGameException("No MLS matches %s." % when)
        return "\n".join(sentenceCap(phrase_match(e)) for e in events)

    matches = _match_team(events, team)
    if not matches:
        raise NoGameException("No MLS match %s for %s." % (when, _display_name(_resolve(team))))
    return "\n".join(sentenceCap(phrase_match(e)) for e, _ in matches)


def getFinal(team):
    """monitor hook: list of (pk, reset, isFinal, isWin) for the team's completed matches, or None"""
    days = [league_today()]
    if datetime.now(LEAGUE_TZ).hour < LATE_FINAL_CUTOFF_HOUR:
        days.insert(0, days[0] - timedelta(days=1))
    finals = []
    for day in days:
        for event, abbr in _match_team(get_scoreboard(day), team):
            stype = event["competitions"][0]["status"]["type"]
            if not (stype.get("state") == "post" and stype.get("completed")):
                continue
            side = next(s for s in _competitors(event) if s["team"]["abbreviation"] == abbr)
            finals.append(("mls-" + event["id"], sentenceCap(phrase_match(event)) + " ", True, bool(side.get("winner"))))
    return finals or None
