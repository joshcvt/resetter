#!/usr/bin/env python

from chalicelib.main import get_team

teams = ["nhl toronto", "mlb toronto", "mlb", "football miami", "nhl", "nhl scoreboard", "nhl tomorrow", "Toronto","Washington","canes","NY","NYR","NYY","LA","Miami","garbage","my aneurysm"]

print("\n\n")
for t in teams:
	print("Calling " + t) 
	try:
		rval = get_team(t,debug=True)
		print("Final return: " + rval)
	except Exception as e:
		print(e.__class__.__name__, str(e))
	print("")

print("Done!")
