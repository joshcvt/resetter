#!/usr/bin/env python

from datetime import date
import time # so we can get epoch time for TTL
import json
import boto3

RESET_TEXT = "RESET_TEXT"
RESET_RICH_SLACK = "RESET_RICH_SLACK"
RESET_SHORT_SLACK = "RESET_SHORT_SLACK"

DYNAMO_TABLE_NAME = "resetter-game-status"
DYNAMO_DEFAULT_TTL = 60*60*24*7 # how many seconds from now to default TTL to

# check if this file exists. if it does, it's an ordered list of what for Dynamo are pks.
DYNAMO_LOCAL_CACHE_FILE = "gameCache.txt"
MAX_DYNAMO_LOCAL_CACHE_VALUES = 10

#global
ddbClient = None


def joinOr(li):
    if li.__class__ != list:
        raise Exception
    if len(li) < 2:
        return ",".join(li)
    elif len(li) == 2:
        return " or ".join(li)
    else:
        commas = ", ".join(li[:-2])
        return commas + ", " + li[-2] + ", or " + li[-1]

def sentenceCap(sen):
    if sen.__class__ != str:
        raise Exception("sen class is not string, is " + sen.__class__.__name__)
    elif len(sen) == 0:
        return sen
    elif len(sen) == 1:
        return sen.upper()
    else:
        return sen[0].upper() + sen[1:]

def toOrdinal(num):
    try:
        intver = int(num)
    except:
        return False
        
    if intver < 0:
        return str(num)
    elif intver == 0:
        return "0th"
    elif (intver % 100) in [11, 12, 13]:
        return str(num) + "th"
    elif intver % 10 == 1:
        return str(num) + "st"
    elif intver % 10 == 2:
        return str(num) + "nd"
    elif intver % 10 == 3:
        return str(num) + "rd"
    else:
        return str(num) + "th"
    return "num"

def dateParse(instr):
    # if this is a date, send it back as a Date. If anything breaks, return False
    # supported formats: YYYY-MM-dd, MM-dd-YYYY, MM-dd, MM/dd/YYYY, MM/dd
    try:
        dashed = instr.split("-")
        slashed = instr.split("/")
        splits = dashed if len(dashed) > len(slashed) else slashed
        #print("dateparse splits: " + str(splits))
        if len(splits) <= 1:
            return False
        for idx, s in enumerate(splits):
            splits[idx] = int(s)

        if len(splits) == 3:
            # is year first or last?
            if splits[0] > 1000:
                return date(splits[0],splits[1],splits[2])
            else:
                return date(splits[2],splits[0],splits[1])
        elif len(splits) == 2:
            today = date.today()
            return date(today.year,splits[0],splits[1])
    except Exception as e:
        #print("hey, dateparse blew up: " + str(e))
        return False

    return False


def rtext(retList):
    
    if not retList:
        retList = [""]
    elif (retList.__class__ != list):
        retList = [retList]
    
    if len(retList) > 1:
        rtext = '\n'.join(retList)
    else:
        rtext = " ".join(retList)
    
    return rtext

def getSsmParam(name,decrypt=True):
    from boto3 import client

    try:
        return client('ssm').get_parameter(Name=name,WithDecryption=decrypt)['Parameter']['Value']
    except Exception as e:
        print("SSM fetch for " + name + " failed: " + str(e))
        return None

#gameId is PK
#TTL is TTL
#gameStateJson is string containing JSON game state
def getDdb(pk):
    global ddbClient
    
    cache = _loadLocalCache()
    if pk in cache:
        # don't even worry about DDB.
        print("found pk in local cache")
        return pk
    
    # if failed, go to ddb.
    
    try:
        if not ddbClient:
            ddbClient = boto3.client('dynamodb')
        ddbRet = ddbClient.get_item(TableName=DYNAMO_TABLE_NAME,Key={'GameId':{'S':pk}},ProjectionExpression="GameStateJson")
        if 'Item' in ddbRet:
            # first try to write pk to the local cache, since it failed before
            print("writing pk to local cache since find failed before")
            _writeLocalCache(pk)
            return ddbRet['Item']['GameStateJson']['S']
        else:
            return None
    
    except(Exception) as e:
        print(e)
        return None
    
def setDdb(pk,dictVal):
    global ddbClient

    ttlVal = str(int(time.time()) + DYNAMO_DEFAULT_TTL)
    jsonVal = json.dumps(dictVal)

    gameItem = {
        'GameId':{'S':pk},
        'TTL':{'N':ttlVal},
        'GameStateJson':{'S':jsonVal}
    }
    
    try:
        if not ddbClient:
            ddbClient = boto3.client('dynamodb')
    
        ddbRet = ddbClient.put_item(TableName=DYNAMO_TABLE_NAME,Item=gameItem)
        print("setDdb succeeded")

    except(Exception) as e:
        print(e)
        return None
    
    # intentionally not writing local cache unless DDB succeeds
    _writeLocalCache(pk)
    
    return ddbRet

def _loadLocalCache():
    
    try:
        with open(DYNAMO_LOCAL_CACHE_FILE) as f:
            rawLines = f.readlines()
            lines = []
            for rl in rawLines:
                goodLine = rl.strip()
                if goodLine:
                    lines.append(goodLine)
        return lines
                    
    except Exception as e:
        print("loading localCache failed: ")
        print(e)
        return []

def _writeLocalCache(pk):
    try:
        lines = _loadLocalCache()
        if pk not in lines:
            lines.append(pk)
        if len(lines) > MAX_DYNAMO_LOCAL_CACHE_VALUES:
            lines = lines[-MAX_DYNAMO_LOCAL_CACHE_VALUES:]
        with open(DYNAMO_LOCAL_CACHE_FILE,"w") as f:
            linesWithEndlines = list(map(lambda x : x + '\n',lines))
            f.writelines(linesWithEndlines)
    except Exception as e:
        print("writing local pk failed, continuing " + pk)
        print(e)


class NoTeamException(Exception):
    pass

class NoGameException(Exception):
    pass

class DabException(Exception):
    def __init__(self,teamOpts=[]):
        self.teamOpts = teamOpts
