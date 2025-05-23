import json
from string import capwords
from os import getenv
import traceback
import threading

import urllib

from .reset_lib import getSsmParam
from boto3 import client

# globals
slackUrl = None
bskyCreds = {}

def getSlackUrl():
    from boto3 import client
    global slackUrl

    if not slackUrl:
        slackUrl = getSsmParam('/resetter/slack_web_hook_url')
    else:
        print("lambda was warm, using cached slackUrl")
    if slackUrl:
        return True
    else:
        return None

def getBsky(usernameSsm='/resetter/bsky_username',passwordSsm='/resetter/bsky_apppassword'):
    global bskyUsername
    global bskyPassword

    if not bskyUsername:
        bskyUsername = getSsmParam(usernameSsm,decrypt=False)
    else:
        print("lambda was warm, using cached bskyUsername")
    if not bskyPassword:
        bskyPassword = getSsmParam(passwordSsm)
    else:
        print("lambda was warm, using cached bskyPassword")
    
    if (bskyUsername and bskyPassword):
        return True
    else:
        return None

def getBskyCredsForUsername(username):
    global bskyCreds
    
    if not bskyCreds: # it's None or empty
        bskyCreds = {}
    
    if username not in bskyCreds:
        ssmPath = '/resetter/bsky/%s' % username
        try:
            appPassword = getSsmParam(ssmPath)
        except Exception as e:
            print("fetching ssm param failed",ssmPath,e)
            return None
        if not appPassword:
            return None
        else:
            bskyCreds[username] = appPassword
            print("Got bsky creds from SSM for username", username)
            return True
    else:
        print("bskyCreds already set for username",username)



def sendSlack(payloadDict,channel=None):
    #verbatim from natinal_bot

    global slackUrl
    if not getSlackUrl():
        print("getSlackUrl failed to populate")
        return
    
    try:
        if channel != None and channel != "":
            payloadDict["channel"] = channel

        data = urllib.parse.urlencode({"payload": json.dumps(payloadDict)}).encode('utf-8')
        req = urllib.request.Request(slackUrl, data=data)
        response = urllib.request.urlopen(req)
        print(str(response.read()))
    except Exception as e:
        print("Couldn't post for some reason:\n" + str(e))
        return

def sendBsky(message,username,timeoutSeconds=20):
    global bskyCreds

    if not getBskyCredsForUsername(username):
        print("getBskyCredsForUsername failed to populate values")
        return
    
    print("got bskyCreds, preparing to login:",message)
    from atproto import Client as BskyClient
    from .bsky_post import post_with_preview

    client = BskyClient(base_url='https://bsky.social')

    #loginThread = threading.Thread(target=client.login(username,bskyCreds[username]))
    #loginThread.start()
    #loginThread.join(timeout=timeoutSeconds)
    #if loginThread.is_alive():
    #    raise Exception("loginThread timed out")
    client.login(username,bskyCreds[username])
    print("successful bsky login, sending")
    #postThread = threading.Thread(target=client.send_post(message))
    #postThread = 
    post_with_preview(client, message)
    #postThread.start()
    #postThread.join(timeout=timeoutSeconds)
    #if postThread.is_alive():
    #    raise Exception("postThread timed out")
    print("returning from sendBsky successfully")
    return True

