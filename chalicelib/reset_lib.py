#!/usr/bin/env python

RESET_TEXT = "RESET_TEXT"
RESET_RICH_SLACK = "RESET_RICH_SLACK"
RESET_SHORT_SLACK = "RESET_SHORT_SLACK"

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


class NoTeamException(Exception):
	pass

class NoGameException(Exception):
	pass

class DabException(Exception):
	def __init__(self,teamOpts=[]):
		self.teamOpts = teamOpts
