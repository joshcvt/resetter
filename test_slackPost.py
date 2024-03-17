#!/usr/bin/env python

from chalicelib.main import postSlack

slacks = ["nhl 2024-03-21","mlb 2024-03-21"]
print("")
for slack in slacks:
	print("posting Slack %s..." % (slack))
	postSlack(slack,channel="backtalk")

print("Done!")
