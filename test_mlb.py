#!/usr/bin/env python

from chalicelib.mlb import launch

print "Should see: standard, verbose for each game. 'Today' starts at rolloverTime.\n"

for (rew, ff, day) in [(True, False, "yesterday"),(False,False,"today"),(False,True,"tomorrow")]:
	print ("\n" + day + ":")
	for team in ["WSH","SD"]:
		for fv in [False,True]:
			try:
				print str(launch(team,rewind=rew,ffwd=ff,fluidVerbose=fv))
			except Exception as e:
				print str(e)
				

print "\nbad team:"
print str(launch("asdfas"))
