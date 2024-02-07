#!/usr/bin/env python

from chalicelib.main import get_team

for param in ["nhl 2023-2-18","nhl 2024-4-1","mlb 9/26","mlb 5/31/2012","mlb 10/6/2020"]:
	try:
		print("REQUEST: " + param)
		print(get_team(param))
	except:
		print("BONK")
	
print("Done!")
