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
		pass

	def fetch_ticker():
		""" fetch the latest trade information
	  - 'last' : last price
	  - 'bid' : the highest price of current buy order
	  - 'ask' : the lowest price of current sell order
	  - 'high' : the highest price in 24hr
	  - 'low' : the lowest price in 24hr
	  - 'volume' : the amount of transactions in 24hr
	  - 'timestamp' : current time
		"""
		req = requests.get("https://coincheck.com/api/ticker")
		if req.status_code == 200:
			item = req.json()
			item['datetime'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
			return item
		else:
			print("ERROR: error in fetching ticker, errcd=%d\n" % r.status_code)
			return


	def fetch_trades():
		""" fetch the latest trade history """
		req = requests.get("https://coincheck.com/api/trades")
		if req.status_code == 200:
			items = req.json()
			return items
		else:
			print("ERROR: error in fetching trades, errcd=%d\n" % r.status_code)
			return


	def fetch_order_books():
		""" fetch order book information
		 - asks : sell order information
		 - bids : buy order information
		"""
		req = requests.get("https://coincheck.com/api/order_books")
		if req.status_code == 200:
			item = req.json()
			return item
		else:
			print("ERROR: error in fetching order books, errcd=%d\n" % r.status_code)
			return


	def ticker2str(ticker):
		""" convert ticker object to string """
		line = "%(datetime)s,%(last)s,%(bid)s,%(ask)s,%(high)s,%(low)s,%(volume)s,%(timestamp)s" % ticker
		return line


	def trade2str(trade):
		""" convert trade object to string """
		line = "%(id)s,%(datetime)s,%(amount)s,%(rate)s,%(order_type)s,%(created_at)s" % trade
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
	                    required=False, action="store_true", default=True,
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
		# terminate because of no work
		sys.exit(0)

	# fetch from coincheck
	tickers = []  # sum of ticker
	books = []    # sum of book
	trades = []   # sum of trades

	while True:
		try:
			if args.count == -1:		# infinite loop is specified
				lpcnt = 1;

			if lpcnt > 0:
				if args.f_ticker == True:
					ticker = coincheck.fetch_ticker()
					print(ticker)
					tickers.append(ticker.copy())
  
				if args.f_trade == True:
					trade = coincheck.fetch_trades()
					print(trade)
					trades.append(trade.copy())
  
				if args.f_book == True:
					book = coincheck.fetch_order_books()
					print(book)
					books.append(book.copy())

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
			outfile = args.outdir + "trade.csv"
			coincheck.export_trade_csv(trades, outfile)
  
		if len(books) > 0:
			outfile = args.outdir + "book.csv"
			coincheck.export_order_book_csv(books, outfile)

	sys.exit(0)


