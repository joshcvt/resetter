#!/usr/bin/env python

from string import join

from chalicelib.resetter import launch

from chalice import Chalice

app = Chalice(app_name='resetter')


@app.route('/',methods=['GET'])
def index():
	print "starting"
	try:
		team = app.current_request.query_params['text']
		if team == '':
			team = 'WSH'
	except:
		team = 'WSH'
	print "getting for team " + team
	retList = launch(team,True)
	print "we got a return: " + str(retList)
	if len(retList) == 1:
		rtext = retList[0]
	else:
		rtext = join(retList," ")
	
	if rtext.startswith("I'm sorry, I didn't recognize team"):
		rtext = rtext.replace("I'm sorry, I didn't recognize team","I'm sorry, I can't reset")

	return { "response_type": "in_channel", "text": rtext }
