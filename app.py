#!/usr/bin/env python

#from crypt import methods
from chalice import Chalice, Cron
from chalicelib.main import get_team
from chalicelib.main import postSlack

DEFAULT_PARAM = "WSH"
SCHEDULED_POST_CHANNEL = "general"
SCHEDULED_POSTS = [
	{"request":"nhl","banner":"Last night's scores:"},
	{"request":"nhl tomorrow","banner":"Tonight's games"}
]
# note: to disable this you must also comment out the @app.schedule line below
SCHEDULED_POST_SCHEDULE = Cron(0, 13, "*", "*", "?", "*")

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
		postSlack(sp["request"],banner=sp["banner"],channel=SCHEDULED_POST_CHANNEL)
