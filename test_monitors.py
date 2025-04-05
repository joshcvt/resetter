#!/usr/bin/env python

from chalicelib.monitors import doMonitors

testConfig = '[{"sport":"mlb","team":"WSH","notifier":"bsky","notifierUser":"journeybot.on29.net","winOnly":"true","message":"AND NOW IT\'S TIME FOR SOME JOURNEY! https://www.youtube.com/watch?v=LatorN4P9aA"}]'

print("doing monitors for test config ",testConfig)

doMonitors(testConfig)
