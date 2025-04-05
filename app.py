#!/usr/bin/env python

#from crypt import methods
from chalice import Chalice, Cron, Rate
from chalicelib.main import get_team, postResetToSlack
from chalicelib.monitors import doMonitors

from datetime import date, timedelta

# what if we just hit /reset?
DEFAULT_PARAM = "WSH"

SCHEDULED_POST_CHANNEL = "general"
# the reason to do this with explicit dates is that it gets you around when the league rolls over what it thinks "today" is.
# note this trusts UTC date to be the same as you think the date is when you call it. to fix that you need this module to be
# timezone aware. That's... a future issue.
TODAY = date.today()
YESTERDAY = TODAY - timedelta(days=1)
SCHEDULED_POSTS = [
    {"request":"nhl "+ YESTERDAY.isoformat(),"banner":"Last night's NHL scores: "},
    {"request":"nhl "+ TODAY.isoformat(),"banner":"Tonight's NHL games: "},
    {"request":"mlb "+ YESTERDAY.isoformat(),"banner":"Last night's MLB scores: "},
    {"request":"mlb "+ TODAY.isoformat(),"banner":"Tonight's MLB games: "} #,"useColumnarPost":True}
]
# note: to disable this you must also comment out the @app.schedule annotation below
SCHEDULED_POST_SCHEDULE = Cron(0, "12", "*", "*", "?", "*")

#GAME_OVER_CRON_RATE = Rate(1,unit=Rate.MINUTES)
# in DST which covers the entire baseball season, this is 1200-0600 -- should catch everything 
MONITOR_CRON_SCHEDULE = Cron("*","0-10,16-24","*","*","?","*")

app = Chalice(app_name='resetter')


@app.route('/',methods=['GET'])
def index():
    """Route used for Slack"""
    inOverride = False
    try:
        team = app.current_request.query_params['text']
        if team == '':
            team = DEFAULT_PARAM
    except:
        team = DEFAULT_PARAM
    
    # allows /scoreboard
    try:
        team = app.current_request.query_params['override']
        if "tv-" in team:
            team = team.strip().split("-")[1]
            inOverride = "tv"
    except:
        pass

    print("getting for team " + team)
    rtext = get_team(team,inOverride=inOverride)
    
    return { "response_type": "in_channel", "text": rtext }

# schedules are in UTC. which means they're not ready for prime time in DST-using places
# one correct way to do this would be a double schedule and then check if it's DST in the zone you care about to decide which hour to run.
# either that or stick the real schedule in a parameter, then run a scheduler lambda on */5 to parse it.
# don't forget to run the terraform in terraform/slackkey to put the webhook in SSM Parameter Store!
@app.schedule(SCHEDULED_POST_SCHEDULE)
def scoreboardPoster(event):
    for sp in SCHEDULED_POSTS:
        postResetToSlack(sp["request"],banner=sp["banner"],channel=SCHEDULED_POST_CHANNEL,useColumnarPost=(sp["useColumnarPost"] if ("useColumnarPost" in sp) else False))


@app.schedule(MONITOR_CRON_SCHEDULE)
def monitorChecker(event):
    doMonitors()
