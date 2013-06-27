'''
Author: Kevin Chen
Email: kvchen@berkeley.edu
Description: API for interfacing with the MarketWatch Virtual Stock Exchange.

'''

import json
import requests
import grequests
import sys
import re

from time import sleep

import lxml
from bs4 import BeautifulSoup



class Portfolio():
    def __init__(self, credentials, game, stock_input):
        '''Initiates a Portfolio object
        @param credentials: list formatted as [username, password]
        @param game: the current MarketWatch game
        @param stock_input: list of [stock, shares]
        '''

        self.session = self.get_session(credentials)
        self.tokens = self.session.cookies
        self.game = game
        self.trade_URL = 'http://www.marketwatch.com/game/%s/trade/submitorder?week=1' % game
        self.holdings_URL = 'http://www.marketwatch.com/game/%s/portfolio/Holdings?view=list&partial=True' % game
        Stocks = [Stock(self.session, game, info) for info in stock_input]


    def get_session(self, credentials):
        '''Obtains a Session object given credentials.
        @param credentials: list formatted as [username, password]
        '''

        s = requests.Session()
        payload = {
                        "username": credentials[0],
                        "password": credentials[1]
                    }
        s.get('https://id.marketwatch.com')
        r = s.get('https://id.marketwatch.com/auth/submitlogin.json', params = userdata)
        try:
            s.get(json.loads(r.text)['url'])
            if s.get('http://www.marketwatch.com/user/login/status').url != \
            "http://www.marketwatch.com/my":
                print ("Successfully authenticated!")
        except:
            print ("ERROR in get_session :: failed to authenticate, fatal error!")
            sys.exit(0)
        return s
        

    def update_portfolio(self):
        '''Updates the net worth and buyingpower of a Portfolio object.'''

        try:
            r = self.session.get('http://www.marketwatch.com/game/%s/portfolio/holdings?name=null' % self.game)
            soup = BeautifulSoup(r.text, 'lxml')
            cubby_worth = soup.find('ul', {'class': 'cubby worth'})
            cubby_performance = soup.find('ul', {'class': 'cubby performance'})
            self.buyingpower = float(cubby_worth.find('span', {'class': 'data'}).getText()[1:].replace(',',''))
            self.networth = float(cubby_performance.find('span', {'class': 'data'}).getText()[1:].replace(',',''))
        except Exception, e:
            print "ERROR in update_portfolio :: %s" % e
            sleep(1)
            return self.update_portfolio()

    def update_stockholdings(self, stock):
        '''Updates the number of shares and gains of a currently held
        stock.
        @param stock: a currently held Stock object
        '''

        try:
            r = self.session.get(self.holdings_URL)
            soup = BeautifulSoup(r.text, 'lxml').find('tr', {'data-symbol': stock.symbol, 'data-type': ['Short', 'Buy'][stock.action]})
            stock.holdingshares = int(float(soup['data-shares']))
            stock.gains = float(soup.find('td',{'class': re.compile('marketgain*')}).getText().replace(',','').replace('M','e6'))
            print "%s: %s shares at gain of %s" % (stock.ticker, stock.holdingshares, stock.gains)
        except Exception, e:
            print "ERROR in get_sharesgains :: %s" % e
            sleep(1)
            self.get_sharesgains(stock)

    def update_stockcounter(self, stock):
        '''Updates the maximum number of times a stock can be bought
        given the Portfolio buying power.
        @param stock: a Stock object
        '''

        bg = stock.get_mw_price()
        self.update_portfolio()
        stock.counter = int(float(self.buyingpower / bg / stock.tradeshares))
        print " --- Updated Net Worth: %s | Buying Power: %s ---" % (self.networth, self.buyingpower)

    

class Stock:
    '''Helper class for stock objects'''
    def __init__(self, session, game, info):
        '''Initiates a stock object.
        @param session: the session created in Portfolio.get_session()
        @param game: the current MarketWatch game
        @param info: params passed from stock_input
        '''

        self.ticker = info[0]

        payload =  {'search': self.ticker, 'view': 'grid', 'partial': 'true'}
        self.trade_URL = 'http://www.marketwatch.com/game/%s/trade?week=1' % game
        self.symbol = None
        while self.symbol == None:
            r = session.post(self.trade_URL, data = payload)
            soup = BeautifulSoup(r.text)
            self.symbol = soup.find('div',{'class': 'chip'})['data-symbol']

        payload = json.dumps([{'Fuid': self.symbol, 'Shares': '100000000', 'Type': 'Buy'}])
        self.headers = {'Content-Type': 'application/json; charset=utf-8'}
        resp = json.loads(session.post(self.trade_URL, data = payload, headers = self.headers).text)[:-1]
        maxshares = int([int(s) for s in resp['message'].split() if s.isdigit()][1] / 1000 * 1000)
        if info[1] > 0:
            self.tradeshares = info[1]
            if self.tradeshares > maxshares:
                self.tradeshares = maxshares
        else:
            self.tradeshares = maxshares

        self.session = session
        self.tokens = session.cookies
        self.action = 0
        self.counter = 0

        self.trend = 0
        self.low = -9000
        self.high = 9000
        self.last = self.get_mw_percent()

        self.holding = False
        self.gains = 0
        self.gainslow = 0
        self.gainslast = 0
        self.holdingshares = 0
        


    '''Data methods'''
    def get_mw_data(self):
        '''Helper method for obtaining stock data.'''

        try:
            r = requests.get('http://www.marketwatch.com/investing/stock/%s' % self.ticker)
            return BeautifulSoup(r.text, 'lxml')
        except Exception, e:
            print "ERROR in get_mw_data :: %s" % e
            return self.get_mw_data()

    def get_mw_percent(self):
        '''Obtains the current percent change of a stock.'''

        try:
            soup = self.get_mw_data()
            return float(soup.find('span', {'class': 'bgPercentChange'}).getText()[:-1])
        except Exception, e:
            print "ERROR in get_mw_percent :: %s" % e
            return self.get_mw_percent()

    def get_mw_price(self):
        '''Obtains the current price change of a stock.'''

        try:
            soup = self.get_mw_data()
            return float(soup.find('p', {'class': 'data bgLast'}).getText())
        except Exception, e:
            print "ERROR in get_mw_price :: %s" % e
            return self.get_mw_price()



    def transaction(self, shares, action):
        '''Carries out a transaction on a stock.'''

        headers = {'Content-Type': 'application/json; charset=utf-8'}
        payload = [{'Fuid': self.symbol, 'Shares': str(shares), 'Type': action}]
        resp = json.loads(self.session.post(self.trade_URL, data = json.dumps(payload), headers = headers).text)
        if resp['succeeded'] == False:
            print "ERROR in transaction for %s :: %s" % (self.ticker, resp['message'])

    def get(self, shares):
        '''Obtains a certain number of a stock.'''

        self.transaction(shares, ['Short', 'Buy'][self.action])
        print " --- %s: purchased %s shares ---" % (self.ticker, shares)

    def release(self):
        '''Releases all currently held shares of a stock.'''

        self.transaction(self.holdingshares, ['Cover', 'Sell'][self.action])
        self.holding = 0
        print " --- %s: released %s shares at gain of %s ---" % (self.ticker, self.shares, self.gains)

    def gtransaction(self):
        '''Uses gevent to simultaneously carry out the maximum number of
        transactions on a stock and beat the 1% share limit common to many
        games.
        NOTE: This may have been recently patched on their servers, and
        may result in a ban from the game.'''

        payload = [{'Fuid': self.symbol, 'Shares': str(self.tradeshares), 'Type': ['Short', 'Buy'][self.action]}]
        rmap = (grequests.post(self.trade_URL, data = json.dumps(payload), cookies = self.tokens, headers = self.headers) for i in range(self.counter))
        grequests.map(rmap, True)
