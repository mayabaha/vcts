#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os
import sys
import time
import requests
import pandas as pd
import datetime
import argparse

class coincheck:
	"""
	coincheck API module
	see the following for details:
	 https://coincheck.com/ja/documents/exchange/api#public
	"""

	def __init__(self):
		""" constructor """
		self.endpoint = "https://coincheck.com/"

		""" set of ticker """
		self.tickers = []
    
		""" set of boos """
		self.books = []
    
		""" set of trade """
		self.trades = []

	def get(self, api):
		""" invoke API to coincheck by GET method """
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

	def fetchTicker(self):
		""" fetch the latest trade information
	  - 'last' : last price
	  - 'bid' : the highest price of current buy order
	  - 'ask' : the lowest price of current sell order
	  - 'high' : the highest price in 24hr
	  - 'low' : the lowest price in 24hr
	  - 'volume' : the amount of transactions in 24hr
	  - 'timestamp' : current time
		"""

		api = "api/ticker"
		item = self.get(api)
		if item is not None:
			item['datetime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			self.tickers.append(item.copy())

		return item

	def fetchTrades(self):
		""" fetch the latest trade history """
		api = "api/trades"

		api = api + "?pair=btc_jpy"
		items = self.get(api)

		if items["success"] == False:
			return

		for item in items["data"]:
			# print(item)
			# self.books.append(item.copy())
			self.books.append(item)

		return items


	def fetchOrderBooks(self):
		""" fetch order book information
		 - asks : sell order information
		 - bids : buy order information
		"""
		
		api = "api/order_books"
		item = self.get(api)
	
		if item is not None:
			item['datetime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			# print(item)
			self.books.append(item.copy())

		return item


	def ticker2str(ticker):
		""" convert ticker object to string """
		line = "%(datetime)s,%(last)s,%(bid)s,%(ask)s,%(high)s,%(low)s,%(volume)s,%(timestamp)s" % ticker
		return line

	def trade2str(trade):
		""" convert trade object to string """
		# print(trade)
		line = "%(created_at)s,%(id)s,%(amount)s,%(rate)s,%(order_type)s" % trade
		return line

	def trades2str(trades):
		line = ""
		for trade in trades["data"]:
			line = line + coincheck.trade2str(trade) + '\n'
		return line

	def book2str(books):
		line = "%(datetime)s" % books
		line = line + ",[ask]"
		for ask in books["asks"]:
			line = line + "(price=%.1f,volume=%.8f)" % (float(ask[0]), float(ask[1]))
			# print(ask[0], ask[1])

		line = line + ",[bid]"
		for bid in books["bids"]:
			line = line + "(price=%.1f,volume=%.8f)" % (float(bid[0]), float(bid[1]))
			# print(bid[0], bid[1])

		return line

	def export_ticker_csv(tickers, outfile):
		""" export ticker data to csv """
		if not os.path.exists(outfile):
			fp = open(outfile, "w")
			fp.write("# datetime,last,bid,ask,high,low,volume,timestamp\n")

		with open(outfile, "a") as fp:
			for item in tickers:
				fp.write(coincheck.ticker2str(item) + '\n')
			

	def export_trade_csv(trades, outfile):
		""" export trade history to csv """
		""" TODO: implementation """
		pass


	def export_order_book_csv(book, outfile):
		""" export book information to csv """
		""" TODO: implementation """
		pass

################################################################################

if __name__ == "__main__":
	parser = argparse.ArgumentParser(description='coincheck API fetch module')
	parser.add_argument('-o', '--output-dir', metavar='dir', dest='outdir',
	                    type=str, required=False, default='',
	                    help='output directory for .csv file')
	parser.add_argument('-i', '--interval', metavar='val', dest='interval', 
	                    type=int, required=False, default=1,
	                    help='polling interval [sec]')
	parser.add_argument('-c', '--count', metavar='count', dest='count',
	                    type=int, required=False, default=-1,
	                    help='fetch count')
	parser.add_argument('-t', '--fetch-ticker', dest='f_ticker',
	                    required=False, action="store_true", default=False,
	                    help='fetch ticker')
	parser.add_argument('-b', '--fetch-book', dest='f_book',
	                    required=False, action="store_true", default=False,
	                    help='fetch order books')
	parser.add_argument('-H', '--fetch-trade-history', dest='f_trade',
	                    required=False, action="store_true", default=False,
	                    help='fetch trade history')
	args = parser.parse_args()

	# interval check
	if args.interval <= 0:
		print("ERROR: interval is NOT natural number")
		sys.exit(1)

	lpcnt = args.count
	processingflg = args.f_ticker | args.f_trade | args.f_book
	if processingflg == False:
		processingflg = args.f_ticker = True

	# create coincheck instance
	co = coincheck()

	while True:
		try:
			if args.count == -1:		# infinite loop is specified
				lpcnt = 1;

			if lpcnt > 0:
				if args.f_ticker == True:
					ticker = co.fetchTicker()
					print(coincheck.ticker2str(ticker))
  
				if args.f_trade == True:
					trades = co.fetchTrades()
					print(coincheck.trades2str(trades))
  
				if args.f_book == True:
					book = co.fetchOrderBooks()
					print(coincheck.book2str(book))

				lpcnt -= 1
				time.sleep(args.interval)
			else:
				break

		except KeyboardInterrupt:
			break

	# export csv file if output option is selected
	if len(args.outdir) > 0:
		if not os.path.exists(args.outdir):
			# output directory check
			try:
				print("INFO: output directory %s not found. create..." % args.outdir)
				os.mkdir(args.outdir)
				if not os.path.exists(args.outdir):
					print("ERROR: cannot create output directory")
			except:
				raise
  
		if len(tickers) > 0:
			outfile = args.outdir + "/ticker.csv"
			coincheck.export_ticker_csv(tickers, outfile)
  
		if len(trades) > 0:
			outfile = args.outdir + "/trade.csv"
			coincheck.export_trade_csv(trades, outfile)
  
		if len(books) > 0:
			outfile = args.outdir + "/book.csv"
			coincheck.export_order_book_csv(books, outfile)

	sys.exit(0)


