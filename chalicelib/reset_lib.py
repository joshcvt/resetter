#!/usr/bin/env python

from string import join

def joinOr(li):
	if li.__class__ != list:
		raise Exception
	if len(li) < 2:
		return join(li,",")
	elif len(li) == 2:
		return join(li," or ")
	else:
		commas = join(li[:-2],", ")
		return commas + ", " + li[-2] + ", or " + li[-1]

def sentenceCap(sen):
	if sen.__class__ not in (str, unicode):
		raise Exception("sen class is not string, is " + sen.__class__.__name__)
	elif len(sen) == 0:
		return sen
	elif len(sen) == 1:
		return sen.upper()
	else:
		return sen[0].upper() + sen[1:]

class NoTeamException(Exception):
	pass

class NoGameException(Exception):
	pass

class DabException(Exception):
	def __init__(self,teamOpts=[]):
		self.teamOpts = teamOpts
