#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from multiprocessing import Queue
import logging
import signal

from coincheck import market
from coincheck import order
import pybitflyer

class scalping:
	""" scalping class """

	def __init__(self, exch, apikey, apisec, outdir, loglv, poll_reqq, poll_rspq, stop_flag, q_get_tov):
		""" constructor
		
		 - exch      : exchange ("coincheck" or "bitflyer")
		 - apikey    : API key
		 - apisec    : API secret
		 - outdir    : output directory
		 - loglv     : log level
		 - poll_reqq : request-to-polling queue
		 - poll_rspq : response-from-polling queue
		 - stop_flag : stop flag
		 - q_get_tov : TOV getting from queue
		"""

		self.exch = exch
		self.apikey = apikey
		self.apisecret = apisec
		self.outdir = outdir
		self.q_get_tov = q_get_tov
		
		# set logger
		try:
			self.logger = logging.getLogger("scalping")
			self.logger.setLevel(loglv)

			if len(outdir) > 0:
				outfile = outdir + "/scalping.log"
			else:
				outfile = "scalping.log"
			fh = logging.FileHandler(outfile)

			self.logger.addHandler(fh)
			sh = logging.StreamHandler()
			# self.logger.addHandler(sh)
			formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
			fh.setFormatter(formatter)
			sh.setFormatter(formatter)
		except:
			raise

		# set exchange
		self.ccpublic = None
		self.ccprivate = None
		self.bfpublic = None
		self.bfprivate = None
		if self.exch == "bitflyer":
			self.bfpublic = pybitflyer.API()
			self.bfprivate = pybitflyer.API(api_key=self.apikey, api_secret=self.apisecret)
		elif self.exch == "coincheck":
			self.ccpublic = market.Market()
			self.ccprivate = order.Order(access_key=self.apikey, secret_key=self.apisecret)
		else:
			self.logger.error("invalid exchange name")
			return

		# set request/response queue for polling object
		self.poll_reqq = poll_reqq
		self.poll_rspq = poll_rspq

		# set stop flag
		self.stop_flag = stop_flag


	def getTicker(self):
		""" get ticker from polling object """

		if self.poll_reqq is None or self.poll_rspq is None:
			return

		req = {"cmd" : "get ticker"}
		self.poll_reqq.put(req)
		ticker = self.poll_rspq.get(timeout=self.q_get_tov)

		#debug
		# self.logger.debug("ticker=%s" % str(ticker))

		return ticker

	
	def getSMA30(self, ticker=None):
		""" get SMA using 30 entries from ticker """
		if ticker is None:
			ticker = self.getTicker()

		if ticker is not None:
			return ticker["sma30"]
		else:
			return 0.0


	def getSMA60(self, ticker=None):
		""" get SMA using 60 entries from ticker """
		if ticker is None:
			ticker = self.getTicker()

		if ticker is not None:
			return ticker["sma60"]
		else:
			return 0.0


	def getWMA30(self, ticker=None):
		""" get WMA using 30 entries from ticker """
		if ticker is None:
			ticker = self.getTicker()

		if ticker is not None:
			return ticker["wma30"]
		else:
			return 0.0


	def getWMA60(self, ticker=None):
		""" get WMA using 60 entries from ticker """
		if ticker is None:
			ticker = self.getTicker()

		if ticker is not None:
			return ticker["wma60"]
		else:
			return 0.0


	def getMidPrice(self, ticker=None):
		""" get mid price of ask and bid """
		if ticker is None:
			ticker = self.getTicker()

		if ticker is not None:
			minprice = min(ticker["best_ask"], ticker["best_bid"])
			diffprice = abs(ticker["best_ask"] - ticker["best_bid"])
			return (minprice + (diffprice / 4.0))
			# return ((ticker["best_ask"] + ticker["best_bid"]) / 2.0)
		else:
			return 0.0


	def isHealth(self):
		""" determine whether exchange status is normal or not """
		try:
			if self.ccpublic is not None:
				# since API is not supported, assume always normal
				return True
			elif self.bfpublic is not None:
				status = self.bfpublic.gethealth();
				if status['status'] != "NORMAL":
					self.logger.debug("server status = %s" % status['status'])
					return False
				else:
					return True
			else:
				return True
					
		except JSONDecodeError:
			# communication error occurred
			self.logger.warning("could not get server status")
			return False


	def entryLong(self, prod, price, size, expiredate):
		""" order limit buy
		
		 - prod       : product code ("BTC_JPY", "ETH_BTC", "FX_BTC_JPY")
		 - price      : buying price
		 - size       : amount of order
		 - expiration : expiration date of order
		"""

		if self.bfprivate is not None:
			try:
				""" kari for debug
				self.bfprivate.sendchildorder(product_code = prod,
				                              child_order_type = "LIMIT",
				                              side = "BUY",
				                              price = price,
				                              size = size,
				                              minute_to_expire = expiredate,
				                              time_in_force = "GTC")
				"""
				return True
			except pybitflyer.exception.AuthException as e:
				self.logger.error(str(e))
				return False
			except:
				raise
		elif self.ccprivate is not None:
			# NOP (TBD)
			return True


	def runscalp(self, prod="", interval=1, size=0, expiredate=0):
		""" run scalping 
		
		 - prod       : product code ("BTC_JPY", "ETH_BTC" or "FX_BTC_JPY")
		 - interval   : interval (unit=second)
		 - size       : amount of buy/sell
		 - expiredate : expiration date of buy/sell order
		"""

		# ignore interrupt
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		signal.signal(signal.SIGTERM, signal.SIG_IGN)

		midprice = 0
		before_midprice = 0
		# pos = 0 # Long : 1, Short : -1, No position : 0
		
		while True:
			try:
				time.sleep(interval)
				# self.logger.debug(str(pos))

				# terminate if stop flag is set
				if self.stop_flag.is_set():
					self.logger.debug("terminate signal received, bye")
					break

				# get medium price
				midprice = self.getMidPrice()
				
				# get server status (bitFlyer ONLY because coincheck does not support this)
				if self.isHealth() == False:
					continue

				# 前回の観測点より価格が高く、ノーポジの時
				if midprice - before_midprice > 0:
					self.logger.info("Entry Long, midprice=%.1f, side=Long" % midprice)
					if self.entryLong(prod, midprice, size, expiredate) is False:
						self.logger.error("could not get position")

				# 前回の観測点よりも価格が低い場合はスルー
				if before_midprice - midprice > 0:
					self.logger.debug("Time to Short. Do nothing, midprice=%.1f, side=Short" % midprice)

				before_midprice = midprice

			except KeyboardInterrupt:
				break

