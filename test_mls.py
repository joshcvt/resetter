#!/usr/bin/env python

from chalicelib.main import get_team

print("Should see: MLS scoreboard and team lookups for today and tomorrow, then ambiguous and bad names.\n")

for req in ["mls", "mls tomorrow", "mls dc united", "mls revs", "mls new england revolution", "red bulls mls",
            "soccer seattle", "mls lafc tomorrow", "mls united", "mls la", "mls new york", "mls garbage"]:
	try:
		print("REQUEST: " + req)
		print(get_team(req))
	except Exception as e:
		print("BONK: " + str(e))

print("Done!")
