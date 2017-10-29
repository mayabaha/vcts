#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import requests
import pandas as pd
import datetime
import argparse

class bitflyer:
	"""
	bitFlyer API module
	see the following for details:
	https://lightning.bitflyer.jp/docs/api?lang=ja&type=ex&_ga=2.136056049.1965297882.1509160469-180722574.1506822122#板情報
	"""
	
	PRODUCT_CODE_BTC = 0x00000001
	PRODUCT_CODE_ETH = 0x00000002
	PRODUCT_CODE_BCH = 0x00000004

	def __init__(self, product_code_bit=0x00000000, outdir=""):
		""" constructor 
		 - product_code_bit : target product code
		                      0x00000000 = None
		                      0x00000001 = BTC_JPY
		                      0x00000002 = ETH_BTC
		                      0x00000004 = BCH_BTC
		 - outdir : output directory for .csv file(s)
		"""

		# endpoint
		self.endpoint = "https://api.bitflyer.jp"

		# market
		self.markets = []

		# set of ticker
		self.tickers_btc = []
		self.tickers_eth = []
		self.tickers_bch = []

		# set csv file for ticker
		self.tickers_csv_btc = None
		self.tickers_csv_eth = None
		self.tickers_csv_bch = None

		# open csv file
		if len(outdir) > 0:
			csv_btc_jpy = outdir + "/" + "ticker_btc_jpy.csv"
			csv_eth_btc = outdir + "/" + "ticker_eth_btc.csv"
			csv_bch_btc = outdir + "/" + "ticker_bch_btc.csv"

			header = "# timestamp,product,tick_id,best_bid,best_ask,best_bid_size,best_ask_size,total_bid_depth,total_ask_depth,ltp,volume,volume_by_product\n"
			try:
				if product_code_bit & self.PRODUCT_CODE_BTC:	# BTC_JPY
					if os.path.exists(csv_btc_jpy):
						self.tickers_csv_btc = open(csv_btc_jpy, "a")
					else:
						self.tickers_csv_btc = open(csv_btc_jpy, "w")
						self.tickers_csv_btc.write(header)
				if product_code_bit & self.PRODUCT_CODE_ETH:	# ETH_BTC
					if os.path.exists(csv_eth_btc):
						self.tickers_csv_eth = open(csv_eth_btc, "a")
					else:
						self.tickers_csv_eth = open(csv_eth_btc, "w")
						self.tickers_csv_eth.write(header)
				if product_code_bit & self.PRODUCT_CODE_BCH:	# BCH_BTC
					if os.path.exists(csv_bch_btc):
						self.tickers_csv_bch = open(csv_bch_btc, "a")
					else:
						self.tickers_csv_bch = open(csv_bch_btc, "w")
						self.tickers_csv_bch.write(header)
			except:
				raise

	def invoke(self, api):
		""" invoke API to bitFlyer """
		if len(api) == 0:
			print("ERROR: API is not specified")
			return

		# invoke
		url = self.endpoint + api
		# print("%s: URL=%s" % (sys._getframe().f_code.co_name, url))
		req = requests.get(url)
		if req.status_code != 200:
			print("ERROR: error occurred in invoking, errcd=%d\n" % req.status_code)
			return
		
		item = req.json()
		return item

	def getMarketStatus(self, product_code=""):
		""" get market status 
		 - NORMAL : active
		 - BUSY : busy (not at a high load)
		 - VERU BUSY : at a high load
		 - SUPER BUSY : extremely high load
		 - NO ORDER : cannot accept order
		 - STOP : market is inactive
		 - FAIL : could not get market status
		"""
		api = "/v1/gethealth"
		if product_code is not None:
			api = api + "?product_code=%s" % (product_code)

		# invoke 
		item = self.invoke(api)
		if item is not None:
			return item['status']
		else:
			return "FAIL"

	def getBookStatus(self, product_code=""):
		""" get book status """
		api = "/v1/getboardstate"
		if len(product_code) > 0:
			api = api + "?product_code=%s" % (product_code)

		item = self.invoke(api)
		if item is not None:
			return item

	def getMarket(self):
		""" get market list """
		items = self.invoke("/v1/getmarkets")
		if items is not None:
			# clear old status
			if len(self.markets) > 0:
				self.markets.clear()
    
			for item in items:
				status = self.getBookStatus(item['product_code'])
				market = {"product_code" : item["product_code"],
				          "state" : status["state"],
				          "health" : status["health"]}
				market["datetime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
				self.markets.append(market)
    
			return self.markets
		else:
			return
	
	def getTicker(self, product_code=""):
		""" get the latest trade information
		 - 'product_code' : product name
		 - 'timestamp' : current time (UTC)
		 - 'tick_id' : tick ID
		 - 'best_bid' : the highest price of current buy order
		 - 'best_ask' : the lowest price of current sell order
		 - 'best_bid_size" : ???
		 - 'best_ask_size" : ???
		 - 'total_bid_depth" : ???
		 - 'total_ask_depth" : ???
		 - 'ltp' : last price
		 - 'volume' : the amount of transactions in 24hr
		"""
		api = "/v1/getticker"
		if len(product_code) > 0:
			api = api + "?product_code=%s" % (product_code)
		item = self.invoke(api)
		if item is not None:
			ticker = {"timestamp"         : item["timestamp"],
			          "product"           : item["product_code"],
			          "tick_id"           : item["tick_id"],
			          "best_bid"          : item["best_bid"],
			          "best_ask"          : item["best_ask"],
			          "best_bid_size"     : item["best_bid_size"],
			          "best_ask_size"     : item["best_ask_size"],
			          "total_bid_depth"   : item["total_bid_depth"],
			          "total_ask_depth"   : item["total_ask_depth"],
			          "ltp"               : item["ltp"],
			          "volume"            : item["volume"],
			          "volume_by_product" : item["volume_by_product"]}

			try:
				if item["product_code"] == "BTC_JPY":
					self.tickers_btc.append(ticker)
					self.tickers_csv_btc.write(bitflyer.ticker2str(ticker) + "\n")
				elif item["product_code"] == "ETH_BTC":
					self.tickers_eth.append(ticker)
					self.tickers_csv_eth.write(bitflyer.ticker2str(ticker) + "\n")
				elif item["product_code"] == "BCH_BTC":
					self.tickers_bch.append(ticker)
					self.tickers_csv_bch.write(bitflyer.ticker2str(ticker) + "\n")
				else:
					pass
			except:
				raise

			return ticker
		else:
			return

	def getTickerBTC(self):
		""" get ticker of BTC-JPY """
		try:
			return self.getTicker("BTC_JPY")
		except:
			raise

	def getTickerETH(self):
		""" get ticker of ETH-BTC """
		try:
			return self.getTicker("ETH_BTC")
		except:
			raise

	def getTickerBCH(self):
		""" get ticker of BCH-BTC """
		try:
			return self.getTicker("BCH_BTC")
		except:
			raise

	def market2str(markets):
		""" convert market information to string """
		header = "# date              product         market_status board_status\n"

		line = header
		for market in markets:
			line = line + "%(datetime)s %(product_code)15s %(health)13s %(state)12s\n" % market

		return line

	def ticker2str(ticker):
		""" convert ticker to string
		    output format:
		      timestamp,product,tick_id,best_bid,best_ask,best_bid_size,best_ask_size,total_bid_depth,total_ask_depth,ltp,volume,volume_by_product"
		"""
		line = "%(timestamp)s,%(product)s,%(tick_id)s,%(best_bid)s,%(best_ask)s,%(best_bid_size)s,%(best_ask_size)s,%(total_bid_depth)s,%(total_ask_depth)s,%(ltp)s,%(volume)s,%(volume_by_product)s" % ticker
		return line

	def tickers2str(tickers):
		""" convert tickers to string """
		line = "# timestamp,product,tick_id,best_bid,best_ask,best_bid_size,best_ask_size,total_bid_depth,total_ask_depth,ltp,volume,volume_by_product\n"
		for ticker in tickers:
			line = line + bitflyer.ticker2str(ticker) + "\n"

################################################################################

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='bitFlyer API fetch module')
	parser.add_argument('-o', '--output-dir', metavar='dir', dest='outdir',
	                    type=str, required=False, default='',
	                    help='output directory for .csv file')
	parser.add_argument('-i', '--interval', metavar='val', dest='interval', 
	                    type=int, required=False, default=1,
	                    help='polling interval [sec]')
	parser.add_argument('-c', '--count', metavar='count', dest='count',
	                    type=int, required=False, default=-1,
	                    help='fetch count')
	parser.add_argument('-b', '--fetch-btc', dest='f_btc',
	                    required=False, action="store_true", default=False,
	                    help='fetch ticker of BTC_JPY')
	parser.add_argument('-e', '--fetch-eth', dest='f_eth',
	                    required=False, action="store_true", default=False,
	                    help='fetch ticker of ETH_BTC')
	parser.add_argument('-H', '--fetch-bch', dest='f_bch',
	                    required=False, action="store_true", default=False,
	                    help='fetch ticker of BCH_BTC')
	args = parser.parse_args()

	# interval check
	if args.interval <= 0:
		print("ERROR: interval is NOT natural number")
		sys.exit(1)

	# set product code bit (pcb)
	pcb = 0
	if args.f_btc == True:
		pcb = pcb | bitflyer.PRODUCT_CODE_BTC
	if args.f_eth == True:
		pcb = pcb | bitflyer.PRODUCT_CODE_ETH
	if args.f_bch == True:
		pcb = pcb | bitflyer.PRODUCT_CODE_BCH
	if pcb == 0:
		print("INFO: select BTC by default")
		pcb = bitflyer.PRODUCT_CODE_BTC

	outdir = args.outdir
	if len(outdir) == 0:
		outdir = "."

	# create bitflyer instance
	bf = bitflyer(pcb, outdir)

	print("INFO: interval=%d, count=%d, outdir=%s" % \
	      (args.interval, args.count, outdir))
	lpcnt = args.count
	while True:
		try:
			if args.count == -1:		# infinite loop is specified
				lpcnt = 1;
			
			if lpcnt > 0:
				if pcb & bitflyer.PRODUCT_CODE_BTC:
					ticker = bf.getTickerBTC()
					print(bitflyer.ticker2str(ticker))
  
				if pcb & bitflyer.PRODUCT_CODE_ETH:
					ticker = bf.getTickerETH()
					print(bitflyer.ticker2str(ticker))
  
				if pcb & bitflyer.PRODUCT_CODE_BCH:
					ticker = bf.getTickerBCH()
					print(bitflyer.ticker2str(ticker))

				lpcnt -= 1
				# print("INFO: wait for %d seconds" % args.interval)
				time.sleep(args.interval)
			else:
				break

		except KeyboardInterrupt:
			break

	sys.exit(0)

