#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import pandas as pd
import datetime
import argparse
from coincheck import market
import pybitflyer

class polling:
	"""
	polling ticker from coincheck or bitflyer.

	this module uses 'coincheck' and 'pybitflyer' module to fetch ticker.
	for more information, see the followings:
	 - https://github.com/kmn/coincheck
	 - https://github.com/yagays/pybitflyer
	"""

	def __init__(self, exch, outdir=""):
		""" constructor
		 - exch : coin exchange name
		          "coincheck"
		          "bitflyer"
		 - outdir : CSV output directory
		"""

		# control parameters
		self.MAXTICKER = 60 * 60 * 24	# 60sec * 60min * 24hr = 1day
		# self.MAXTICKER = 2	# 60sec * 60min * 24hr = 1day
		self.MAXSMA = 60 * 60 * 24
		self.MAXWMA = 60 * 60 * 24

		# set exchange
		self.exch = exch.lower()
		self.cc = None
		self.bf = None
		if self.exch == "coincheck":
			self.cc = market.Market()
		elif self.exch == "bitflyer":
			self.bf = pybitflyer.API()
		else:
			print("ERROR: invalid exchange name")
			return

		# set CSV file name
		if len(outdir) > 0:
			if not os.path.exists(outdir):
				# output directory check
				try:
					print("INFO: output directory %s not found. create..." % args.outdir)
					os.mkdir(args.outdir)
					if not os.path.exists(args.outdir):
						print("ERROR: cannot create output directory")
						return
				except:
					raise
			self.tickercsv = outdir + "/ticker_" + self.exch + ".csv"
		else:
			self.tickercsv = ""

		# initiailze ticker
		self.tickers = []
		self.readCSVticker()

		# initialize technical parameters
		self.sma30s = []
		self.sma60s = []
		self.wma30s = []
		self.wma60s = []

	def ticker(self, product):
		""" fetch ticker
		 - product : product code (BTC_JPY, ETH_BTC, FX_BTC_JPY)

		format of return object:
		 - product   : product code (BTC_JPY, ETH_BTC, etc)
		 - timestamp : timestamp
		 - best_bid  : the highest bid price at the current time
		 - best_ask  : the lowst ask price at the current time
		 - last      : last price
		"""

		currdate = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
		ticker = {}
		if self.cc is not None:	# coincheck
			tickercc = self.cc.ticker()
			if tickercc is not None:
				ticker["product"] = product
				ticker["datetime"] = currdate
				ticker["timestamp"] = tickercc["timestamp"]
				ticker["best_bid"] = tickercc["bid"]
				ticker["best_ask"] = tickercc["ask"]
				ticker["last"] = tickercc["last"]
		elif self.bf is not None:	# bitflyer
			tickerbf = self.bf.ticker(product_code=product.upper())
			if tickerbf is not None:
				ticker["product"] = product
				ticker["datetime"] = currdate
				ticker["timestamp"] = tickerbf["timestamp"]
				ticker["best_bid"] = float(tickerbf["best_bid"])
				ticker["best_ask"] = float(tickerbf["best_ask"])
				ticker["last"] = float(tickerbf["ltp"])
		else:
			pass

		return ticker


	def append(self, listp, val, maxelm=0):
		""" append value to the list and purge LRU entry """
		listp.append(val)
		
		# purge old entries
		if maxelm > 0:
			entnum = len(listp) - maxelm
			if entnum > 0:	# element count exceeds limit
				for count in range(entnum):
					del listp[0]


	def appendticker(self, ticker):
		""" append ticker to the list """
		self.append(self.tickers, ticker, self.MAXTICKER)


	def getticker(self, idx=-1):
		""" get ticker 
		 - idx : index of ticker history, -1 indicates last entry
		"""
		return self.tickers[idx]


	def readCSVticker(self):
		""" read ticker data from CSV """
		if len(self.tickercsv) <= 0:
			return

		if not os.path.exists(self.tickercsv):
			return

		df = pd.read_csv(self.tickercsv)
		if df is None:
			print("ERROR: could not read CSV file")
			return

		nrow = len(df)
		if nrow >= self.MAXTICKER:
			strow = nrow - self.MAXTICKER
			edrow = nrow - 1
		else:
			strow = 0
			edrow = nrow - 1

		for idx in range(strow, edrow):
			rdent = df.iloc[idx]
			self.tickers.append(rdent)

		del df


	def writeCSVticker(self, ticker):
		""" write ticker data to CSV """
		if len(self.tickercsv) > 0:
			if not os.path.exists(self.tickercsv):
				fp = open(self.tickercsv, "w")
				fp.write("datetime,product,last,best_bid,best_ask,timestamp\n")
    
			with open(self.tickercsv, "a") as fp:
				fp.write(self.ticker2str(ticker) + '\n')


	def ticker2str(self, ticker):
		""" convert ticker object to string """
		line = "%(datetime)s,%(product)s,%(last).1f,%(best_bid).1f,%(best_ask).1f,%(timestamp)s" % ticker
		return line


	def sma(self, count):
		""" calculate simple moving average
		 - count : number of elements for calculation
		"""

		if len(self.tickers) < count:
			return 0

		sma = 0
		for idx in range(-1, -1 - count, -1):
			ticker = self.tickers[idx]
			sma = sma + ticker["last"]
		sma = sma / count

		return sma


	def sma30(self):
		""" calculate SMA with 30 entries """
		sma = self.sma(30)
		self.append(self.sma30s, sma, self.MAXSMA)


	def sma60(self):
		""" calculate SMA with 60 entries """
		sma = self.sma(60)
		self.append(self.sma60s, sma, self.MAXSMA)


	def wma(self, count):
		""" calculate weighted Moving Average
		 - count  : number of elements for calcucation
		"""

		if len(self.tickers) < count:
			return 0

		wma = 0
		w = count
		sumweight = 0
		for idx in range(-1, -1 - count, -1):
			ticker = self.tickers[idx]
			wma = wma + ticker["last"] * w
			sumweight = sumweight + w
			w = w - 1
		wma = wma / sumweight

		return wma


	def wma30(self):
		""" calculate WMA using 30 elements """
		wma = self.wma(30)
		self.append(self.wma30s, wma, self.MAXWMA)


	def wma60(self):
		""" calculate WMA using 60 elements """
		wma = self.wma(60)
		self.append(self.wma60s, wma, self.MAXWMA)


	def pollticker(self, product, interval=1, count=-1):
		""" polling ticker """
    
		# product code check
		tmpprod = product.lower()
		if self.cc is not None:	# coincheck
			if tmpprod == "btc_jpy":
				pass
			else:
				print("ERROR: %s is not supported by coincheck" % product)
				return
		elif self.bf is not None:	# bitflyer
			if tmpprod == "btc_jpy":
				pass
			elif tmpprod == "eth_btc":
				pass
			elif tmpprod == "fx_btc_jpy":
				pass
			else:
				printf("ERROR: %s is not supported by bitflyer" % product)
				return
    
		# fetch interval
		if interval <= 0:
			print("ERROR: interval is NOT natural number")
			return
    
		# initialize loop count
		lpcnt = count
    
		# polling
		while True:
			try:
				if count == -1:		# infinite loop is specified
					lpcnt = 1;
    
				if lpcnt > 0:
					ticker = self.ticker(product)
					if ticker is not None:
						self.appendticker(ticker)
						self.writeCSVticker(ticker)
						self.sma30()
						self.sma60()
						self.wma30()
						self.wma60()

						# debug
						print("%s SMA30=%.1f SMA60=%.1f WMA30=%.1f WMA60=%.1f" % (self.ticker2str(ticker), self.sma30s[-1], self.sma60s[-1], self.wma30s[-1], self.wma60s[-1]))
					else:
						print("ERROR: could not get ticker")
    
					lpcnt -= 1
					time.sleep(interval)
				else:
					break
    
			except KeyboardInterrupt:
				break
			
################################################################################

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='cryptcoin market polling module')
	parser.add_argument('-o', '--output-dir', metavar='dir', dest='outdir',
	                    type=str, required=False, default='',
	                    help='output directory for .csv file')
	parser.add_argument('-i', '--interval', metavar='val', dest='interval', 
	                    type=int, required=False, default=1,
	                    help='polling interval [sec]')
	parser.add_argument('-c', metavar='count', dest='count',
	                    type=int, required=False, default=-1,
	                    help='fetch count. negative value stands for infinite loop')
	parser.add_argument('-e', metavar='exch', dest='exch',
	                    type=str, required=True, default='',
	                    choices=('coincheck', 'bitflyer'),
	                    help='exchange name (\'coincheck\' or \'bitflyer\')')
	parser.add_argument('-p', metavar='prod', dest='prod',
	                    type=str, required=False, default='btc_jpy',
	                    help='product name\n'
	                    '\'btc_jpy\' is available on coincheck.\n'
	                    '\'btc_jpy\' or \'eth_btc\' is available on bitflyer')
	args = parser.parse_args()

	# exchange check
	tmpexch = args.exch.lower()
	if tmpexch != "coincheck" and tmpexch != "bitflyer":
		print("ERROR: %s is not supported as exchange" % args.exch)
		sys.exit(1)

	poll = polling(args.exch, args.outdir)

	# polling
	poll.pollticker(args.prod, args.interval, args.count)

	sys.exit(0)


