#!/usr/bin/env python

import json
from string import capwords
from os import getenv
import traceback

MONITOR_ENV_VAR = "MONITOR_SET_JSON"

from .mlbstatsapi import get as get_mlb
from .ncaaf_espn import get as get_ncaaf
from .nhl import getFinal as getFinalNHL
from .reset_lib import getDdb, setDdb
from .networks import sendSlack, sendBsky

sportMonitors = {}
notifiers = {}

sportMonitors['nhl'] = getFinalNHL
notifiers['bsky'] = sendBsky

def doMonitors():
    monList = json.loads(getenv(MONITOR_ENV_VAR))
    # expected contents: [{'sport':'nhl','team':'CAR','notifier':'bsky','notifierUser':'testuser.on29.net','message':'RAISE UP'{,'winOnly':'anyvalueimpliestrue'}]
    
    for mon in monList:
        if sportMonitors[mon['sport']]:
            finalSet = sportMonitors[mon['sport']](mon['team'])
            # expected: (pk, reset, isFinal, isWin)
            # nominally, if we get None it's safe to assume game is not final. but let's allow for future variation.
            if finalSet:
                (pk, reset, isFinal, isWin) = finalSet
                notifPk = '%s-%s-%s-%s' % (pk,mon['notifier'],mon['notifierUser'],mon['message'])
                print('monitor got result for for %s %s' % (pk, reset))
                if not isFinal:
                    print('Somehow we got results even for not final, PANIC and next')
                    next
                # check if we already have a tombstone in the ddb
                gameDdb = getDdb(notifPk)
                if gameDdb:
                    print('gameDdb found for %s, nexting' % notifPk)
                    next
                if isWin or ('winOnly' not in mon):
                    notifiers[mon['notifier']](message=mon['message'],username=mon['notifierUser'])
                    # if we're still here and not excepted out, it succeeded...
                    setDdb(notifPk,reset)
                    