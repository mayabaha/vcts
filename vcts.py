#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import datetime
import argparse
import configparser
import logging
from multiprocessing import Process
from multiprocessing import Queue

import polling
import scalping


# log directory
logdir = ""

# log level
loglevel = "INFO"

class vcts:
	""" VCTS: Virtual Coin Transaction System class """

	def __init__(self, inifile="", logdir="", loglevel=""):
		""" initialize VCTS module """
		
		self.exch = ""
		self.prod = ""
		self.apikey = ""
		self.apisecret = ""

		# polling module
		self.poll = None
		self.p_poll = None
		self.pollitv = 0
		self.pollcount = 0

		# scalping module	
		self.scalp = None
		self.p_scalp = None
		self.scalpitv = 0
		self.scalpsize = 0
		self.scalpexp = 0

		# inter-processing communication
		self.poll_reqq = None
		self.poll_rspq = None

		# log info
		self.logdir = logdir
		self.loglevel = loglevel


		# read config file if specified
		if len(inifile) > 0:
			self.readConfig(inifile)


	def readConfig(self, inifile):
		""" read .ini file to configure VCTS
		
		 -  inifile : path to .ini file
		"""
		# load .ini file
		try:
			inifile = configparser.ConfigParser()
			inifile.read(args.inifile, 'UTF-8')
			
			# global parameters
			self.setExchange(inifile.get('global', 'exchange'))
			self.setProduct(inifile.get('global', 'product'))
			self.setAPIKey(inifile.get('global', 'apikey'))
			self.setAPISecret(inifile.get('global', 'apisecret'))

			# polling parameters
			self.pollitv   = int(inifile.get('polling', 'interval'))
			self.pollcount = int(inifile.get('polling', 'count'))

			# scalping parameters
			self.scalpitv  = int(inifile.get('scalping', 'interval'))
			self.scalpsize = float(inifile.get('scalping', 'size'))
			self.scalpexp  = int(inifile.get('scalping', 'expiration_date'))

		except configparser.NoSectionError as e:
			logging.critical("section '%s' not found in %s" % (e.args, args.inifile))
			sys.exit(1)
		except configparser.NoOptionError as e:
			logging.critical("option '%s' not found in section '%s'" % (e.args[0], e.args[1]))
			sys.exit(1)

		# debug
		logging.info("[global] exchange=%s, product=%s, apikey=%s, apisecret=%s" % \
		      (self.exch, self.prod, self.apikey, self.apisecret))
		logging.info("[polling]  interval=%d, count=%d" % (self.pollitv, self.pollcount))
		logging.info("[scalping] interval=%d, size=%f, expiration=%d" % (self.scalpitv, self.scalpsize, self.scalpexp))


	def setExchange(self, exch):
		""" set exchange name
		 - exch : exchange name : 'coincheck' or 'bitflyer'
		"""
		if len(exch) > 0:
			self.exch = exch.lower()


	def setProduct(self, prod):
		""" set product code
		 - exch : product code : 'BTC_JPY', 'FX_BTC_JPY' or 'ETH_BTC'
		"""
		if len(prod) > 0:
			self.prod = prod.lower()


	def setAPIKey(self, key):
		""" set API key
		 - key : API KEY of exchange
		"""
		if len(key) > 0:
			self.apikey = key.lower()


	def setAPISecret(self, sec):
		""" set API Secret
		 - sec : API Secret of exchange
		"""
		if len(sec) > 0:
			self.apisecret = sec.lower()


	def run(self):
		""" run VCTS """
		try:
			self.poll_reqq = Queue()
			self.poll_rspq = Queue()

			# execute polling module
			self.poll = polling.polling(self.exch,
			                            self.logdir, self.loglevel,
			                            self.poll_reqq,
			                            self.poll_rspq)
			self.p_poll = Process(target=self.poll.pollticker, 
		                        args=(self.prod, self.pollitv, self.pollcount))
			self.p_poll.start()

			# execute scalping module
			self.scalp = scalping.scalping(self.exch, 
			                               self.apikey,
			                               self.apisecret,
			                               self.logdir, self.loglevel,
			                               self.poll_reqq,
			                               self.poll_rspq)
			self.p_scalp = Process(target=self.scalp.runscalp,
			                       args=(self.prod, self.scalpitv, self.scalpsize, self.scalpexp))
			self.p_scalp.start()

			self.p_poll.join()
			self.p_scalp.join()
		except:
			raise


def runvcts(inifile="", logdir="", loglevel=""):
	""" run VCTS """

	# set/create log directory
	if len(logdir) > 0:
		if not os.path.exists(logdir):
			# create log directory
			try:
				logging.warning("log directory '%s' not found. create..." % logdir)
				os.mkdir(logdir)
				if not os.path.exists(logdir):
					logging.critical("cannot create log directory")
					sys.exit(1)
			except:
				raise
		logging.info("logdir=%s", logdir)

	# run VCTS
	try:
		v = vcts(inifile, logdir, loglevel)
		v.run()
	except ValueError as e:
		logging.critical(str(e))
		sys.exit(1)
	except:
		raise


################################################################################

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='virtual coin transaction system')
	parser.add_argument('--logdir', metavar='dir', dest='logdir',
	                    type=str, required=False, default='',
	                    help='log output directory')
	parser.add_argument('--log', metavar='dir', dest='loglevel',
	                    type=str, required=False, default='INFO',
	                    help='log level (CRITICAL, ERROR, WARNING, INFO or DEBUG')
	parser.add_argument('--ini', metavar='ini', dest='inifile',
	                    type=str, required=True, default='',
	                    help='path to .ini file')
	args = parser.parse_args()

	runvcts(args.inifile, args.logdir, args.loglevel.upper())

	sys.exit(0)


