#!/usr/bin/env python

#from crypt import methods
from chalice import Chalice, Cron, Rate
from chalicelib.main import get_team, postResetToSlack
from chalicelib.monitors import doMonitors, doTestPost

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
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

# The scheduled scoreboard posts run at SCHEDULED_POST_LOCAL_HOUR in SCHEDULER_TIMEZONE, all year.
# These live here rather than in .chalice/config.json because `chalice deploy` builds the schedule by importing
# this file locally, where config.json's environment_variables aren't set; here, deploy and runtime always agree.
SCHEDULER_TIMEZONE = "America/New_York"
SCHEDULED_POST_LOCAL_HOUR = 8
SCHEDULER_TZ = ZoneInfo(SCHEDULER_TIMEZONE)

# the request is built from explicit dates in SCHEDULER_TIMEZONE, which gets you around when each league
# rolls over what it thinks "today" is. "{yesterday}"/"{today}" are filled in when the post runs.
SCHEDULED_POSTS = [
    {"request":"nhl {yesterday}","banner":"Last night's NHL scores: "},
    {"request":"nhl {today}","banner":"Tonight's NHL games: "},
    {"request":"mlb {yesterday}","banner":"Last night's MLB scores: "},
    {"request":"mlb {today}","banner":"Tonight's MLB games: "} #,"useColumnarPost":True}
]


def utcHoursForLocalHour(tz, localHour):
    """Every UTC hour that can be localHour:00 in tz over a year: (12, 13) for 8 AM America/New_York (EDT, EST).
    EventBridge cron only speaks UTC, so the schedule fires on all of them and the handler keeps the right one."""
    year = datetime.now(timezone.utc).year
    hours, minutes = set(), set()
    for day in range(0, 366, 7):
        # adding a timedelta to a zoneinfo datetime keeps the wall-clock hour; astimezone applies that date's offset
        utc = (datetime(year, 1, 1, localHour, tzinfo=tz) + timedelta(days=day)).astimezone(timezone.utc)
        hours.add(utc.hour)
        minutes.add(utc.minute)
    if len(minutes) != 1:
        raise ValueError("%s's UTC offset changes by part of an hour; one cron minute can't cover it" % tz)
    return sorted(hours), minutes.pop()


SCHEDULED_POST_UTC_HOURS, SCHEDULED_POST_UTC_MINUTE = utcHoursForLocalHour(SCHEDULER_TZ, SCHEDULED_POST_LOCAL_HOUR)
# note: to disable this you must also comment out the @app.schedule annotation below
SCHEDULED_POST_SCHEDULE = Cron(SCHEDULED_POST_UTC_MINUTE, ",".join(str(h) for h in SCHEDULED_POST_UTC_HOURS), "*", "*", "?", "*")

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

def scheduledLocalTime(event):
    """When this run was scheduled for, in SCHEDULER_TIMEZONE. Uses the event's own time rather than now, so a
    late delivery or a retry still counts as the run it was meant to be."""
    try:
        when = datetime.strptime(event.time, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (AttributeError, TypeError, ValueError):
        when = datetime.now(timezone.utc)
    return when.astimezone(SCHEDULER_TZ)


# don't forget to run the terraform in terraform/slackkey to put the webhook in SSM Parameter Store!
@app.schedule(SCHEDULED_POST_SCHEDULE)
def scoreboardPoster(event):
    local = scheduledLocalTime(event)
    if local.hour != SCHEDULED_POST_LOCAL_HOUR:
        # the other UTC hour in the schedule, the one that isn't SCHEDULED_POST_LOCAL_HOUR at this time of year
        print("skipping: scheduled for %s, posts go out at %d:00 %s" % (local.isoformat(), SCHEDULED_POST_LOCAL_HOUR, SCHEDULER_TIMEZONE))
        return
    dates = {"today": local.date().isoformat(), "yesterday": (local.date() - timedelta(days=1)).isoformat()}
    print("posting scoreboards for %s (%s)" % (dates["today"], SCHEDULER_TIMEZONE))
    for sp in SCHEDULED_POSTS:
        postResetToSlack(sp["request"].format(**dates),banner=sp["banner"],channel=SCHEDULED_POST_CHANNEL,useColumnarPost=(sp["useColumnarPost"] if ("useColumnarPost" in sp) else False))


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
