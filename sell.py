#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import time
from multiprocessing import Queue
import signal
import logging
import re

from coincheck import order
import pybitflyer


class sell:
	""" sell class """

	def __init__(self, exch, apikey, apisec, logdir, loglv, poll_reqq, poll_rspq, stop_flag, q_get_tov):
		""" constructor

		 - exch      : exchange ("coincheck" or "bitflyer")
		 - apikey    : API key
		 - apisec    : API secret
		 - logdir    : log directory
		 - loglv     : log level
		 - poll_reqq : request queue to polling module
		 - poll_rspq : response queue from polling module
		 - stop_flag : stop flag to terminate this process
		"""
		self.exch = exch
		self.apikey = apikey
		self.apisecret = apisec
		self.logdir = logdir
		self.q_get_tov = q_get_tov
	
		# set logger
		try:
			self.logger = logging.getLogger("sell")
			self.logger.setLevel(loglv)

			if len(logdir) > 0:
				logfile = logdir + "/sell.log"
			else:
				logfile = "sell.log"
			fh = logging.FileHandler(logfile)

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
		""" get ticker from polling module """
		if self.poll_reqq is None or self.poll_rspq is None:
			return

		req = {"cmd" : "get ticker"}
		self.poll_reqq.put(req)
		ticker = self.poll_rspq.get(timeout=self.q_get_tov)

		#debug
		# self.logger.debug("ticker=%s" % str(ticker))

		return ticker


	def getExecutions(self, prod):
		""" get my executions 
		 - id
		 - child_order_id
		 - side, "BUY" or "SELL"
		 - price
		 - size
		 - commission
		 - exec_date : execution date
		 - child_order_acceptance_id
		"""

		if self.ccprivate is not None:
			return
		elif self.bfprivate is not None:
			prod = prod.upper()
			ret = self.bfprivate.getexecutions(product_code=prod, count=500, before=0, after=0)
			if len(ret) == 0:
				self.logger.debug("getExecutions: no execution")
				return
			elif len(ret) == 3:
				if ret['status'] != 200:
					self.logger.error("%s '%s'" % (ret['error_message'], prod))
					return
				else:
					return ret
			else:
				# self.logger.debug("getExecutions: prod=%s, ret=%s" % (prod, str(ret)))
				return ret
		else:
			return


	def getPosition(self, prod):
		""" get my position
		 - prod : product code "BTC_JPY", "ETH_BTC", "FX_BTC_JPY"

		return format:
		 - product_code : "FX_BTC_JPY"
		 - side         : "BUY" or "SELL"
		 - price 
		 - size
		 - commision
		 - swap_point_accumulate
		 - require_collateral
		 - open_date
		 - leverage
		 - pnl
		"""

		if self.ccprivate is not None:
			return
		elif self.bfprivate is not None:
			prod = prod.upper()
			ret = self.bfprivate.getpositions(product_code=prod)
			self.logger.debug("getPosition: prod=%s, ret=%s" % (prod, str(ret)))
			if len(ret) == 0:
				return
			elif len(ret) == 3:
				if ret['status'] != 200:
					self.logger.error("%s '%s'" % (ret['error_message'], prod))
					return
				else:
					return ret
			else:
				return ret
		else:
			return


	def placeOrder(self, prod, ordtype, side, size):
		""" place order
		 - prod    : product code, "BTC_JPY", "ETH_BTC", "FX_BTC_JPY"
		 - ordtype : "LIMIT" or "MARKET"
		 - side    : "BUY" or "SELL"
		 - size    : amount of order
		"""

		if self.bfprivate is not None:
			"""
			odr = self.bfprivate.sendchildorder(product_code=prod,
			                                    child_order_type=ordtype,
			                                    side=side,
			                                    size=size)
			if odr is not None:
				return True
			else:
				return False
			"""
			return True

		elif self.ccprivate is not None:
			# TBD
			return True

		else:
			return False


	def checkPosition(self, prod, profit_border, cut_border, size):
		""" check position
		 - prod          : product code, "BTC_JPY", "FX_BTC_JPY", "ETH_BTC"
		 - profit_border : border line for profit [%]
		 - cut_border    : cut line for 'stop-loss'
		 - size          : amount of order
		"""

		try:
			# get my position
			matchob = re.search("fx_", prod.lower())
			if matchob:
				poss = self.getPosition(prod)
				if poss is None:
					return
				else:
					self.logger.debug("%d positions found." % len(poss))
			else:
				poss = self.getExecutions(prod)
				if poss is None:
					return
				else:
					self.logger.debug("%d executions found." % len(poss))
    
			# judge whether my positions should be selled or not
			for pos in poss:
				ticker = self.getTicker()
    
				upper_price = float(pos['price']) * profit_border
				lower_price = float(pos['price']) * cut_border
				self.logger.debug("last_price=%.1f, border_price=%.1f, cut_price=%.1f" % 
				                  (ticker['last'], upper_price, lower_price))
    
				if ticker['last'] > float(pos['price']):
					if ticker['last'] > upper_price:
						# secure profit
						self.logger.info("write sell code, short entry")
						self.placeOrder(prod, "MARKET", "SELL", size)
					else:
						self.logger.info("though position is positive, hold position, position_price=%.1f, last_price=%.1f" %
						                 (pos['price'], ticker['last']))
				else:
					if ticker['last'] < lower_price:
						# stop-less
						self.logger.info("write sell code, short entry")
						self.placeOrder(prod, "MARKET", "SELL", size)
					else:
						self.logger.info("since your position is negative, hold position, position_price=%.1f, last_price=%.1f" % (pos['price'], ticker['last']))
		except:
			raise

	
	def runsell(self, prod, interval, size, profit_border, cut_border):
		""" polling my position and issue sell order """

		# ignore interrupt
		signal.signal(signal.SIGINT, signal.SIG_IGN)
		signal.signal(signal.SIGTERM, signal.SIG_IGN)

		while True:
			# terminate if stop flag is set
			if self.stop_flag.is_set():
				self.logger.debug("terminate signal received, bye")
				break

			try:
				self.checkPosition(prod, profit_border, cut_border, size)
			except pybitflyer.exception.AuthException as e:
				self.logger.error(str(e))
			except JSONDecodeError:
				# communication error occurred
				self.logger.warning("JSON Decode Error has occurred")
			except:
				raise

			time.sleep(interval)

