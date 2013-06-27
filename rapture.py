'''
Author: Kevin Chen
Email: kvnchen@berkeley.edu
Description: A minimal high-frequency stock trading algorithm for MarketWatch.
NOTE: Does not work in real life, exploits infinite liquidity and lack
      of buying queue.

'''

import datetime
import getpass

from mw_api import *


'''Format stock_input as [['STOCK1', tradeshares1], ['STOCK2', tradeshares2], ...]
Set tradeshares as 0 if you want the maximum number of shares.'''

username = 'foo@bar.com'
password = ''
stock_input = [['NOK', 0], ['ZNGA', 1000]]
game = 'msj-2013'

if __name__ == '__main__':
    print "__________    _____ _________________________ ________________________ "
    print "\______   \  /  _  \\\\______   \__    ___/    |   \______   \_   _____/ "
    print " |       _/ /  /_\  \|     ___/ |    |  |    |   /|       _/|    __)_  "
    print " |    |   \/    |    \    |     |    |  |    |  / |    |   \|        \ "
    print " |____|_  /\____|__  /____|     |____|  |______/  |____|_  /_______  / "
    print "        \/         \/                                    \/        \/  "
    print ":::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::::: "
    if username == '':
        username = raw_input(">>username: ")
    else:
        print ">>username: %s" % username
    if password == '':
        password = getpass.getpass(">>password: ")
    print ">>authenticating..."
    portfolio = Portfolio([username, password], game, stock_input)
    update_loop()


def update_loop():
    '''Loops the algorithm until trading closes.'''

    now = datetime.datetime.now()
    normaltime = now.hour * 60 + now.minute
    while normaltime < 1198:
        try:
            update(portfolio)
            now = datetime.datetime.now()
            normaltime = now.hour * 60 + now.minute
        except Exception, e:
            print "ERROR in update_loop() :: %s" % e
            pass
    stock = portfolio.Stocks[0]
    if stock.holding:
        sleep(2)
        portfolio.update_stockholdings()
        stock.release()
    print ">>Trading is now closed, halting processes."
    sys.exit(0)

def update():
    '''Updates the bot once.'''

    for stock in portfolio.Stocks:
        '''Tracks current microtrend'''
        cp = stock.get_mw_percent()
        if cp > stock.last:
            if not(stock.trend):
                stock.low = stock.last
            stock.trend = 1
        elif cp < stock.last:
            if stock.trend:
                stock.high = stock.last
            stock.trend = 0
        stock.last = cp

        if stock.holding:
            '''Verifies gains to determine when to release a stock.'''
            portfolio.update_stockholdings(stock)
            if (stock.gains > stock.gainslast + 100000) or (stock.gains > stock.gainslow + 100000):
                stock.release()
                portfolio.update_stockcounter(stock)
            if stock.gains < stock.gainslast:
                stock.gainslow = stock.gains
            stock.gainslast = stock.gains

        else:
            '''Tracks the current trend to determine when to buy'''
            print ">>%s :: Low: %s | High: %s | Current: %s" % (stock.ticker, stock.low, stock.high, cp)
            if cp <= stock.low or cp >= stock.high:
                stock.action = (cp <= stock.low)
                print " --- %s %s shares of %s at %s ---" % (['shorting', 'buying'][stock.action], stock.tradeshares*stock.counter, stock.ticker, cp)
                try:
                    stock.gtransaction()
                except Exception, e:
                    print "ERROR in stock.gtransaction() :: %s" % e
                    pass
                print ">>waiting for all stocks to process network-side..."
                sleep(12)
                stock.holding = True
                portfolio.update_stockholdings()
                stock.gainslast = stock.gainslow = stock.gains
        try:
            sleep(1.2)
        except KeyboardInterrupt:
            stock.release()
            portfolio.update_stockcounter(stock)
            pass
