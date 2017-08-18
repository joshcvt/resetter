import urllib2, ConfigParser, json, traceback, re, argparse		 #, logging
from datetime import timedelta, datetime, date
from string import Template, join
#from xml.dom.minidom import parse
import xml.etree.ElementTree as ET
from os import sys

from chalicelib.resetter import launch

from chalice import Chalice

app = Chalice(app_name='resetter')


@app.route('/',methods=['POST','GET'])
def index():
	#body = app.current_request.to_dict()
	print "starting"
	try:
		team = app.current_request.query_params['text']
		if team == '':
			team = 'WSH'
	except:
		team = 'WSH'
	print "getting for team" + team
	retList = launch(team)
	print "we got a return"
	print retList
	if len(retList) == 1:
		return { "response_type": "in_channel", "text": retList[0] }
	else:
		return { "response_type": "in_channel", "text": join(retList," ") }


# The view function above will return {"hello": "world"}
# whenever you make an HTTP GET request to '/'.
#
# Here are a few more examples:
#
# @app.route('/hello/{name}')
# def hello_name(name):
#	# '/hello/james' -> {"hello": "james"}
#	return {'hello': name}
#
# @app.route('/users', methods=['POST'])
# def create_user():
#	 # This is the JSON body the user sent in their POST request.
#	 user_as_json = app.current_request.json_body
#	 # We'll echo the json body back to the user in a 'user' key.
#	 return {'user': user_as_json}
#
# See the README documentation for more examples.
#

