#!/usr/bin/env python

from chalicelib.main import get_team

teams = ["Toronto","Washington","NY","NYR","NYY","LA","Miami","garbage","my aneurysm"]

for t in teams:
	print "Calling " + t
	try:
		rval = get_team(t)
		print "Final return: " + rval
	except Exception as e:
		print str(e)

print "Done!"
