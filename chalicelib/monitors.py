#!/usr/bin/env python

import json
from string import capwords
from os import getenv
import traceback

MONITOR_ENV_VAR = "MONITOR_SET_JSON"

from .mlbstatsapi import get as get_mlb, getFinal as getFinalMLB
from .ncaaf_espn import get as get_ncaaf
from .nhl import getFinal as getFinalNHL
from .reset_lib import getDdb, setDdb
from .networks import sendSlack, sendBsky

sportMonitors = {}
notifiers = {}

sportMonitors['nhl'] = getFinalNHL
sportMonitors['mlb'] = getFinalMLB
notifiers['bsky'] = sendBsky

def doMonitors(monList=None):
    if not monList:
        monList = getenv(MONITOR_ENV_VAR)
    monList = json.loads(monList)
    # expected contents: [{'sport':'nhl','team':'CAR','notifier':'bsky','notifierUser':'testuser.on29.net','message':'RAISE UP','winOnly':'anyvalueimpliestrue'}]
    
    for mon in monList:
        if sportMonitors[mon['sport']]:
            finals = sportMonitors[mon['sport']](mon['team'])
            # expected: (pk, reset, isFinal, isWin)
            # nominally, if we get None it's safe to assume game is not final. but let's allow for future variation.
            if finals:
                for finalSet in finals:
                    try:
                        (pk, reset, isFinal, isWin) = finalSet
                    except:
                        # it didn't parse, keep going
                        continue
                    notifPk = '%s-%s-%s-%s' % (pk,mon['notifier'],mon['notifierUser'],mon['message'])
                    if mon['message']:
                        reset += mon['message']
                    print('monitor got result for for %s %s' % (pk, reset))
                    if not isFinal:
                        print('Somehow we got results even for not final, PANIC and next')
                        continue

                    if isWin or ('winOnly' not in mon):
                        # we're in the notifier conditions, so check if we already have a tombstone in the ddb
                        gameDdb = getDdb(notifPk)
                        if gameDdb:
                            print('gameDdb found for %s, nexting' % notifPk)
                            continue
                        try:
                            notifiers[mon['notifier']](message=reset,username=mon['notifierUser'])
                        except:
                            print("excepted out of notifier:", e)
                            continue
                        # if we're still here and not excepted out, it succeeded...
                        setDdb(notifPk,reset)
                    else:
                        print("notifier conditions not met")
                    