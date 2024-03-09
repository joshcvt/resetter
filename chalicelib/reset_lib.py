#!/usr/bin/env python

RESET_TEXT = "RESET_TEXT"
RESET_RICH_SLACK = "RESET_RICH_SLACK"

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


class NoTeamException(Exception):
	pass

class NoGameException(Exception):
	pass

class DabException(Exception):
	def __init__(self,teamOpts=[]):
		self.teamOpts = teamOpts
