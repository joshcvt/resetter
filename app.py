#!/usr/bin/env python

from crypt import methods
from chalice import Chalice
from chalicelib.main import get_team

DEFAULT_PARAM = "WSH"

app = Chalice(app_name='resetter')


@app.route('/',methods=['GET'])
def index():
	"""Route used for Slack"""
	try:
		team = app.current_request.query_params['text']
		if team == '':
			team = DEFAULT_PARAM
	except:
		team = DEFAULT_PARAM
	
	# allows /scoreboard
	try:
		team = app.current_request.query_params['override']
	except:
		pass

	print("getting for team " + team)
	rtext = get_team(team)
	
	return { "response_type": "in_channel", "text": rtext }

@app.route('tv-wsh',methods=['GET'])
def tvScoreboard():
	# let's not mince words, this is a horrible, hacky way to do this
	alllines = get_team("scoreboard").split('\n')
	filt = list(filter(lambda a: "TV" in a, alllines))
	rtext = '\n'.join(filt)
	return { "response_type": "in_channel", "text": rtext }