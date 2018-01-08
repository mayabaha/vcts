#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from coincheck import market
import sys


if __name__ == "__main__":
	mkt = market.Market()
	ticker = mkt.ticker()
	print(ticker)

	sys.exit(0)

