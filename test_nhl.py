#!/usr/bin/env python

from chalicelib.nhl import get

print "Should see: full scoreboard, then a couple single games or attempts, for three days. 'Today' starts at rolloverTime.\n"

print "yesterday:"
print str(get("scoreboard",rewind=True)) + "\n"
print str(get("canes",rewind=True))   # this tests the lookup table
print str(get("canadiens",rewind=True)) + "\n"

print "today:"
print str(get("scoreboard")) + "\n"
print str(get("canes"))   # this tests the lookup table
print str(get("canadiens")) + "\n"

print "tomorrow:"
print str(get("scoreboard",ffwd=True)) + "\n"
print str(get("canes",ffwd=True))   # this tests the lookup table
print str(get("canadiens",ffwd=True)) + "\n"

print "bad team:"
print str(get("asdfas"))
