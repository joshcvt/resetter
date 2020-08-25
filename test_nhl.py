#!/usr/bin/env python

from chalicelib.nhl import get
from chalicelib.reset_lib import NoGameException

print("Should see: full scoreboard, then a couple single games or attempts, for three days. 'Today' starts at rolloverTime.\n")

testTeams = ["scoreboard","canes","canadiens","Washington","NYR"]
# scoreboard for all, canes for lookup table, canadiens for direct team name

print("yesterday:")
for t in testTeams:
	try:
		print(str(get(t,rewind=True)) + "\n")
	except NoGameException:
		print("No game for " + t)
	except Exception as e:
		print(str(e))

print("today:")
for t in testTeams:
	try:
		print(str(get(t)) + "\n")
	except NoGameException:
		print("No game for " + t)
	except Exception as e:
		print(str(e))

print("tomorrow:")
for t in testTeams:
	try:
		print(str(get(t,ffwd=True)) + "\n")
	except NoGameException:
		print("No game for " + t)
	except Exception as e:
		print(str(e))

print("bad team:")
try:
	print(str(get("asdfas")))
except Exception as e:
	print(repr(e))