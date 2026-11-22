#!/usr/bin/env python

#from crypt import methods
from chalice import Chalice, Cron, Rate
from chalicelib.main import get_team, postResetToSlack
from chalicelib.monitors import doMonitors, doTestPost

from datetime import date, datetime, timedelta, timezone
import json
import os
import uuid

# /reset test-journeybot-post: queue a real Bluesky post from monitorChecker, at most once per UTC hour
TEST_POST_COMMAND = "test-journeybot-post"
TEST_POST_EVENT_SOURCE = "resetter.test-post"
# off unless this env var is a true-ish string ("true", "1", "yes", "on", any case)
TEST_POST_ENV_VAR = "ENABLE_TEST_POST"


def testPostEnabled():
    return os.environ.get(TEST_POST_ENV_VAR, "").strip().lower() in ("true", "1", "yes", "on")

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
MONITOR_CRON_SCHEDULE = Cron("*/5","*","*","*","?","*")

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

    if team.strip().lower() == TEST_POST_COMMAND:
        if not testPostEnabled():
            return {"response_type": "ephemeral", "text": "Test posting is turned off (set %s to true in the Chalice config)." % TEST_POST_ENV_VAR}
        return triggerTestPost()

    print("getting for team " + team)
    rtext = get_team(team,inOverride=inOverride)
    
    return { "response_type": "in_channel", "text": rtext }


def triggerTestPost():
    """Async-invoke monitorChecker with a test event, so the post runs with that function's memory/timeout
    and Slack's 3-second reply limit doesn't matter."""
    import boto3
    from chalicelib.reset_lib import getDdb, setDdb

    now = datetime.now(timezone.utc)
    cooldownPk = "testpost-cooldown-" + now.strftime("%Y-%m-%dT%H")
    if getDdb(cooldownPk):
        return {"response_type": "ephemeral", "text": "A test post was already queued this hour (UTC). Try again next hour."}

    # api handler is "<app>-<stage>"; chalice names the schedule function "<app>-<stage>-monitorChecker"
    target = os.environ["AWS_LAMBDA_FUNCTION_NAME"] + "-monitorChecker"
    # shaped like a CloudWatch event because chalice wraps schedule handlers in CloudWatchEvent
    event = {"version": "0", "id": str(uuid.uuid4()), "detail-type": "resetter test post",
             "source": TEST_POST_EVENT_SOURCE, "account": "", "time": now.isoformat(),
             "region": "", "resources": [], "detail": {}}
    boto3.client("lambda").invoke(FunctionName=target, InvocationType="Event", Payload=json.dumps(event).encode())
    setDdb(cooldownPk, {"runId": event["id"]})
    print("queued test post run", event["id"], "on", target)
    return {"response_type": "in_channel",
            "text": "Queued a test Bluesky post (run %s). Check the account, or CloudWatch logs for %s." % (event["id"][:8], target)}

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
    if event.source == TEST_POST_EVENT_SOURCE:
        # checked here too, so a queued or retried test event can't post after the flag is turned off
        if testPostEnabled():
            doTestPost(runId=event.event_id)
        else:
            print("test post event ignored: %s is not enabled" % TEST_POST_ENV_VAR)
        return
    doMonitors()
