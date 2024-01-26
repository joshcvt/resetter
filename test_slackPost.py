#!/usr/bin/env python

from chalicelib.main import postSlack

slacks = ["nhl"]
print("")
for slack in slacks:
	print("posting Slack %s..." % (slack))
	postSlack(slack,channel="backtalk")

print("Done!")
