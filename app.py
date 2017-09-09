#!/usr/bin/env python

from string import join

from chalicelib.resetter import launch as get_mlb

from chalice import Chalice

DEFAULT_PARAM = "WSH"

app = Chalice(app_name='resetter')


@app.route('/',methods=['GET'])
def index():
	try:
		team = app.current_request.query_params['text']
		if team == '':
			team = DEFAULT_PARAM
	except:
		team = DEFAULT_PARAM
	print "getting for team " + team
	retList = get_mlb(team,True)
	
	if retList == None:
		rtext = "I'm sorry, I can't reset " + team + "."
	elif len(retList) == 1:
		rtext = retList[0]
	else:
		rtext = join(retList," ")
	
	return { "response_type": "in_channel", "text": rtext }
