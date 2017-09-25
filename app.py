#!/usr/bin/env python

from string import join

from chalicelib.resetter import launch as get_mlb
from chalicelib.ncaaf_ncaa import get as get_ncaaf


from chalice import Chalice

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

	print "getting for team " + team
	rtext = get_team(team)
	
	return { "response_type": "in_channel", "text": rtext }


def get_team(team):
	"Generic fetch prioritization"
	
	if team.strip().lower().endswith("football"):
		retList = get_ncaaf(team[:-8].strip())
				
	else:	
		retList = get_mlb(team,True)
		if retList == None:
			# try football?
			retList = get_ncaaf(team)
	
	if retList and (retList.__class__ != list):
		retList = [retList]
	
	if retList == None:
		rtext = "I'm sorry, I can't reset " + team + "."
	elif len(retList) == 1:
		rtext = retList[0]
	else:
		rtext = join(retList," ")
	
	return rtext