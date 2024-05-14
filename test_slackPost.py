#!/usr/bin/env python

from chalicelib.main import postSlack

slacks = ["mlb 2024-09-06","nhl 2024-04-06"]
print("")
for slack in slacks:
	print("posting Slack %s..." % (slack))
	postSlack(slack,banner="Banner",channel="backtalk")#,useColumnarPost=True)


print("Done!")
