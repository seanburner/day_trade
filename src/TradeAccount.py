## ###################################################################################################################
##  Program :   Trade Account 
##  Author  :
##  Install :   pip3 install requests  inspect platform argparse 
##  Example :
##              python3 
##              python3 
##  Notes   :   https://docs.python.org/3/tutorial/classes.html
## ###################################################################################################################
import os
import re
import sys
import time
import pandas as pd
import numpy  as np 
import getpass
import inspect
import platform
import argparse
import functools
import requests

from datetime           import datetime, timedelta, timezone
from Indicators         import Indicators 
from SchwabAccount      import SchwabAccount

OPTION_NONE = 0
OPTION_CALL = 1
OPTION_PUT  = 2

class TradeAccount:
    def __init__(self, funds : float =5000, limit : float = 0.10 , app_type = 'Schwab',app_key ="xxxxx", app_secret = "zzzzzz" ) :
        """
            Initialize the variables for the Trading Account class 
        """
        self.Mode           = ""                       # Are we Testing or Trading or something else
        self.Funds          = funds                    # ACCOUNT DOLLAR AMOUNT 
        self.Limit          = 0.0                      # MAX TO SPEND ON ANY ONE TRADE 
        self.Trades         = {}                       # COMPLETED TRADES FOR THE DAY
        self.InPlay         = {}                       # CURRENT TRADES STILL OPEN  
        self.APP_KEY        = ""
        self.LossLimit      = 0                        # HOW MUCH IS TOO MUH TO LOSE ON ONE TRADE   
        self.APP_SECRET     = ""
        self.DailyFunds     = 0                        # Use this to preserve any profits, instead of re-risking them because the LIMIT is based on percentage
        self.TargetGoal     = 0                        # Dont get greedy, when reach this amount will quit trading for day
        self.Performance    = {}                       # Keep track of wins and loses
        self.AccountTypes   = { 'SCHWAB' :  SchwabAccount }
        

        self.Conn           =  self.AccountTypes  [ app_type.upper()] ( app_key, app_secret )

        self.Funds          = self.Conn.CashForTrading()
        print(f"\t\t\t Available Cash for Trading : ${ self.Funds} " )

        self.SetLimit(limit )                           # INCASE VALUE SENT IN THROUGH CONSTRUCTOR
        
    def __str__(self ) -> str :
        """
            Returns string representation of the object 
        """
        return (f'\n\t\t |Mode : {self.Mode}' +
                f'\n\t\t |Funds : {self.Funds}\n\t\t |Limit : {self.Limit} ->{self.Limit * self.Funds} ' +
                f'\n\t\t |DailyFunds : {self.DailyFunds}' +
                f'\n\t\t |TargetGoal : {self.TargetGoal}' ) #+ f"{self.Conn}")
    
    def __iter__(self) -> object:
        """
            Iter through a collection of tradeAccounts
        """
        return self
    
    def __next__(self) -> object:
        """
            Iter through a collection of tradeAccounts
        """
        if self.index == 0:
            raise StopIteration
        self.index = self.index - 1
        return self.data[self.index]



    def ExtractQuoteEntry( self, candles : dict , timeStamp :  int ) -> dict :        
        """
            The quote info returned has a lot of entries , need to find the specific one for the proper time period
            ARGS    :
                        candles     ( dict ) - response dictionary from quote request
                        timeStamp   ( int  ) - unix formatted timestamp 
            RETURNS :
                        quote_info  ( dict ) 
        """
        pos         = 0 
        ticker_row  = None
        
        for entry in candles['candles'] :
            pos += 1
            if ( entry['datetime']/1000 == timeStamp/1000 ):
               #print (f"\t\t\t ** FOUND : {pos} -> {len(candles['candles'])}    :: " , entry )
               quote_info = entry
               #print( f"\t\t\t\t FOUND | {quote_info} -> {datetime.fromtimestamp(entry['datetime']/1000)}\n\t\t\t\t  LAST | {candles['candles'][-1]} -> {datetime.fromtimestamp(candles['candles'][-1]['datetime']/1000)}")
               quote_info['symbol'] = candles['symbol']
               ticker_row = [candles['symbol'],str(datetime.fromtimestamp( timeStamp/1000)),quote_info['low'],quote_info['close'],
                         quote_info['open'],quote_info['volume'],quote_info['high']   ]
                        
        return ticker_row



    def History( self, symbol : str , time_period : str ='daily' , time_range : int =1, period_type ="month" ) -> dict :
        """
            Get historical entries for the symbol
            ARGS  :
                    symbol       ( str )  stock symbol to lookup
                    time_range   ( int )  how many ( days ??) to go back 
                    time_period  ( str )  daily / month / year / ytd 
            RETURNS:
        """
        df              = None 
        endDate         = datetime.now()- timedelta( days = 1 )  # time delta for when working on weekend 
        timeStamp       = 0
        startDate       = None        
        quote_info      = None
        ticker_row      = None 
        periodTypes     = ["day","month","year","ytd"]
        frequencyTypes  = ["minute","daily","weekly","monthly"]
        
        
        try:
            period          = 1
            frequency       = 1
            periodType      = period_type #'month' #'day'
            frequencyType   = time_period
            
            startDate       = endDate - timedelta( days = frequency * time_range ) 

            
            response = self.Conn.QuoteByInterval( symbol=symbol, periodType=periodType, period=period,
                                              frequencyType=frequencyType, frequency=frequency, startDate= startDate, endDate =endDate)
            #print( response.text )
            if response.status_code != 200 :
                return ticker_row

            
            #print( "TradeAccount::HISTORY  response : ", response.text)
            df = pd.DataFrame( response.json()['candles'])
            df.sort_values( by=['datetime'], ascending=False , inplace=True)
            df['date'] = df['datetime'].apply( lambda x : str(datetime.fromtimestamp( x/1000))[:10] )
            df = df.reindex()
            #print("Data Frame : " , df )
                
        except:          
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )
            print(f"\t\t| Period: {period} Frequency: {frequency}  PeriodType: {periodType}  FrequencyType:{frequencyType} ")
        finally:            
            return  df



        
    def Quote ( self, symbols : list | str,  endDate : datetime = datetime.now()) -> requests.Response :
        """
            Abstraction to call the underlying client ( Schwab / ) to get a quote
            The last candle in candles:{} will be the most current one we want for frequency and timeframe
            ARGS    :
                        symbols : list 
            RETURNS :
                        request.response
        """
        ticker_row  = {}
        
        try:
            quote_response = self.Conn.Quote( symbols)
            for sym in ( [symbols] if isinstance(symbols,str) else symbols):
                if not( sym in quote_response ):
                    ticker_row.update({ sym :  [ ] })
                else:
                    details =  quote_response[sym]['quote']
                    ticker_row.update({ sym :  [ sym, str(datetime.now() ),details['lowPrice'], details['closePrice'], details["openPrice"],
                                               details["totalVolume"],details['highPrice']] })
                
        except:          
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )            
        finally:            
            return  ticker_row

        
    def QuoteByInterval ( self, symbols : list | str, frequency : int = 60, frequencyType : str = "minute" , endDate : datetime = datetime.now()) -> requests.Response :
        """
            Abstraction to call the underlying client ( Schwab / ) to get a quote by interval/time 
            The last candle in candles:{} will be the most current one we want for frequency and timeframe
            ARGS    :
                        symbols : list 
            RETURNS :
                        request.response
        """
        candles         = ""
        timeStamp       = 0
        quote_info      = None
        ticker_row      = None 
        periodTypes     = ["day","month","year","ytd"]
        frequencyTypes  = ["minute","daily","weekly","monthly"]
        
        try:
            period          = 1
            frequency       = int (15 if frequency/60 == 0 else frequency/60 )
            startDate       = endDate - timedelta( seconds = frequency * 60) 
            periodType      = 'day'
            frequencyType   = ("minute" if not( frequencyType in frequencyTypes) else frequencyType  )
            
            response = self.Conn.QuoteByInterval( symbol=symbols, periodType=periodType, period=period,
                                              frequencyType=frequencyType, frequency=frequency, startDate= startDate, endDate =endDate)
            
            if response.status_code != 200 :
                return ticker_row
            
            candles = response.json()          
            
            #print( f"\n->TradeAccount::" + str(inspect.currentframe().f_code.co_name) + f" -quote_info : { candles}")
            timeStamp = int(endDate.timestamp() * 1000)
            pos = 0
            if 'candles' in candles  and not ( candles['candles'] == [] ):
                ticker_row = self.ExtractQuoteEntry( candles , timeStamp)
                # A SECOND ATTEMPT INCASE THE FIRST WAS UNSUCCESSFUL;  using QUOTE
                #ticker_row = self.Quote ( symbols =symbols, endDate = endDate)[symbols]
                
                if ticker_row == None :
                    print( f"{symbols}  RUNNING SECOND ")
                #    ticker_row = self.Quote( symbols )[symbols]
                #    return ticker_row
                    
                    candles = self.Conn.QuoteByInterval( symbol=symbols, periodType=periodType, period=period,
                                              frequencyType=frequencyType, frequency=frequency, startDate= startDate, endDate =endDate).json()
                    if 'candles' in candles :
                        ticker_row = self.ExtractQuoteEntry( candles ,timeStamp)
           
                
                #IF PROPER STILL IS NOT FOUND, THEN GET THE LAST ENTRY IN THE SERIES /RESPONSE DICT
                if ticker_row == None :
                    print(f"{symbols}  **********  FAKING IT ************")
                    #for entry in candles['candles'] :
                    #    print( f"\t>> {entry} -> {datetime.fromtimestamp(entry['datetime']/1000)}")
                    quote_info = candles['candles'][-1]
                    quote_info['symbol'] = candles['symbol']
                    new_quote_info = {}
                    for key in quote_info.keys():                  
                        new_quote_info[key] =  float( quote_info[key]) if key in ['volume','open','close','high','low'] else quote_info[key]
                    ticker_row = [ candles['symbol'],str(datetime.fromtimestamp( timeStamp/1000)),quote_info['low'],quote_info['close'],
                                        quote_info['open'],quote_info['volume'],quote_info['high']   ]
                 
        except:            
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )                
            
        finally:
          return ticker_row  






    def SetFunds ( self, funds : float = 1000, limit : float = 0.10) -> None :
        """
            Manually set the funds values, this is usually for live testing mode
            ARGS    :
                        funds : float 
            RETURNS :
                        nothing 
        """
        self.Funds = funds
        self.SetLimit(limit )                
        
    
    def SetTargetGoal( self, target : float  ) -> None :
        """
            A decimal of how much we want to make trading ( today ) before quitting .80 ( 80% of our funds ) 

            PARAMETER :
                        target : decimal  -  percent of how much of funds we want to make in profits 
            RETURNS   :
                        Nothing 
        """
        self.TargetGoal =  self.Funds  + (target * self.Funds) # ONLY NEED 1 % AT A TIME /DAILY
        self.LossLimit  =  (target * self.Funds)

        

    def SetMode ( self, mode : str ) -> None :
        """
            Sets the mode of the application : TEST / TRADE
            ARGS   :
                        mode  ( str )  - test/live
            RETURNS:
                        nothing 
        """
        self.Mode = self.Conn.Mode = mode


        
    def SetLimit( self, limit : float ) -> None :
        """
            Sets the the limit to use for each trade.  This should be formatted as a decimal
            PARAMETERS  :
                            limit   : float
            RETURNS     :
                            Nothing 
        """
        self.Limit      =  limit
        self.DailyFunds = self.Limit * self.Funds 
        



    def GetLimit( self ) -> float :
        """
            Gets the the current limit  in dollars of the accounts 
            PARAMETERS  : 
        """
        try:
            print (f"\t\t FUNDS : {self.Funds }    Limit : {self.Limit} " ) 
            return self.Funds * self.Limit 
        except:
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )





    def Buy( self, stock : str , price : float, current_time : str = str( datetime.now()), volume : int = 0 ,
             volume_threshold : int = 0, indicators : Indicators = None )  -> bool :
        """
           Attempt to buy the stock under the confines of the limit , True = succeeded , False = failed
           Updates
               * inPlay dictionary to keep track
               * Funds
               * Limit
               
           ARGS      :
                       stock ( string )     - the stock to purchase 
                       price ( float )      - the current price
                       current_time (str )  - date time to record the purchase 
           RETURNS   :
                       bool  : True / False 
        """
        qty             = 0
        success         = False
        message_prefix  = "\t\t\t   \\-> TradeAccount::" + str(inspect.currentframe().f_code.co_name)

        try :
            # IF MADE TARGET PERCENT THEN DONT BUY ANY MORE 
            if self.TargetGoal  == 0  :#and self.Funds > self.TargetGoal :
                print(f"{message_prefix}   BUY -  Have already hit the TargetGoal  : { self.TargetGoal} " ) 
                return False

            
            # CHECK IF CAN AFFORD TO BUY
            #print( "Check : " , str( type( price )) , " : " , str( type( self.Funds * self.Limit ))   )
            if price > ( self.Funds * self.Limit ):
                print(f"{message_prefix}   Cant even buy ONE stock : {( self.Funds * self.Limit )}  " )
                return success

            # CHECK IF ALREADY HOLDING 
            if stock in self.InPlay.keys() :
                print(f"{message_prefix}   Already holding, cant take any more ")
                return success

            if not(stock  in self.Trades.keys() ) :
                self.Trades.update( { stock : [] } )
                
            #IF THE CURRENT PRICE IS BELOW THE PREVIOUS PRICE WE BOUGHT AT , SHOULD WE BE BUYING ????            
            if len( self.Trades[stock] ) > 0 :
                lenth = len( self.Trades[stock] ) - 1 
                if self.Trades[stock][ lenth]['bid'] > price :
                    print(f"{message_prefix}   Current price {price}  has fallen below previous bid {self.Trades[stock][lenth]['bid']} ")
                    return success 

            working_capital = self.DailyFunds  if  (self.DailyFunds ) <  (self.Funds * self.Limit )  else (self.Funds * self.Limit )
            print ( f"{message_prefix}   Working Capital  : {working_capital}  :  {self.Funds * self.Limit }  -> {self.DailyFunds} " )
            qty             = int (working_capital / price )       # instead of self.Funds, so we dont risk previous profits; might need to readjust if had a loss 
            # ACTUALLY BUY SOME NOW IF MODE='TRADE'
            success = self.Conn.Buy( stock , price , qty ) 

            # UPDATE INTERNAL ELEMENTS
            if self.Mode.lower() == "test" or success  :
                #print( f"FUNDS: {self.Funds} * {self.Limit} /{price} ==> {(( self.Funds * self.Limit ) / price )} ") 
                self.Funds -= qty * price            
                self.InPlay[ stock ] = {
                    'time'  : current_time,
                    'price' : price ,
                    'qty'   : qty ,
                    'volume': volume,
                    'closed': '',
                    'sold'  : 0,                    
                    'pl'    : 0,
                    'indicators_in' : indicators.Summary()
                }
                if not( stock  in self.Performance.keys() ) :
                    self.Performance[stock] = []
                
               # print ( f"{message_prefix}   BOUGHT : " , self.InPlay )
                success = True
            else:
                print("\t\t\t    --> Account level could not execute BUY properly ")
            return success 
        except: 
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )



    def Sell( self, stock : str, new_price : float, current_time : str = str( datetime.now()), ask_volume : int = 0, indicators : Indicators = None )  -> bool :
        """
           Sell the stock currently holding , True = succeeded , False = failed
           Updates
               * Move inPlay entry into Trades 
               * Remove inPlay  entry 
               * Funds
               * Limit ( auto updated ) 
               
           ARGS      :
                       stock ( string )     - the stock to purchase 
                       price ( float )      - the current price
                       current_time (str )  - date time to record the purchase 
           RETURNS   :
                       bool  : True / False 
        """
        p_l             = 0   
        success         = False
        message_prefix  = "\t\t\t* TradeAccount::" + str(inspect.currentframe().f_code.co_name) 

        try :
            # CHECK IF ALREADY HOLDING 
            if  not( stock in self.InPlay.keys() ):
                print(message_prefix + "  Not holding that stock ")
                return success

            
            # WHEN PROFITABLE , ONLY SELL WHEN MORE THAN SPECIFIC PERCENT
            if ( new_price  > self.InPlay[ stock ]['price'] ) :
                diff = (new_price  - self.InPlay[ stock ]['price'] )/self.InPlay[ stock ]['price']
                print ( f"\t\t\t    \\----> DIFF  -> {new_price }  {self.InPlay[ stock ]['price']}  {diff } ")
                if diff < 0.00016 :    # ignore profit if less than % of investment 
                    print(message_prefix + "  Not Selling - trying to be a little greedier ")
                    return False
            

            # Sell the stock IF MODE='TRADE'
            success = self.Conn.Sell( stock, new_price , self.InPlay[ stock ]['qty'] ) 
                

            if self.Mode.lower() == "test" or success:    
                print('FUNDS: ', self.Funds , ' : ' , ( self.InPlay[stock]['qty'] * new_price ), ' = ' , ( self.InPlay[stock]['qty'] * new_price )+self.Funds)    
                self.Funds += ( self.InPlay[stock]['qty'] * new_price )
                p_l         = ( self.InPlay[stock]['qty'] * new_price )  - ( self.InPlay[ stock ]['qty'] *  self.InPlay[ stock ]['price'] )
                
                self.Trades[stock].append(  {'symbol':stock, 'type': OPTION_NONE , 'bidTime':self.InPlay[ stock ]['time'],
                                             'bid':self.InPlay[ stock ]['price'],'bidVolume':self.InPlay[ stock ]['volume'], 'askVolume':ask_volume,
                                             'qty' :self.InPlay[ stock ]['qty'],'askTime':current_time, 'ask':new_price, 'p_l': p_l ,
                                             'indicators_in': self.InPlay[stock]['indicators_in'], 'indicators_out': indicators.Summary()} )
                print ( f"\t\t\t \\-> SOLD :  from {self.InPlay[stock]['price']} -> {new_price }"  )
                self.InPlay.pop( stock )    #REMOVE ENTRY FROM DICTIONARY 
                self.Performance[stock].append ( 'WIN' if p_l >0 else 'LOSS' )                
                if ( ( p_l * -1 ) > 0.01 * self.DailyFunds ) : #                     self.LossLimit) :   # WE HAVE LOST TOO MUCH ON ONE DEAL , CALL QUITS FOR TODAY
                    print( f"**Lost TOO MUCH on one deal : { p_l}  -> {self.LossLimit} ")
                    self.TargetGoal = 0 
                success = True
            else:
                print ("\t\t --> Account  level did not Execute SELL properly ") 
            
        except: 
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )                
        finally :
            return success 


    def Orders( self , time_interval : int = 0  ) -> list :
        """
            Gets the FILLED orders from the selected account for the desired time period ( days ) 
            ARGS   :
                    time_interval  ( int ) - how many days to look back
            RETURNS:
                    list of dictionary of orders  ( or df )             
        """
        orders          = None
        toTime          = None
        fromTime        = None
        date_format     = '%Y-%m-%dT%H:%M:%SZ'
        
        
        try:
            toTime      = (datetime.now(timezone.utc)).strftime( date_format)
            fromTime    = (datetime.now(timezone.utc)- timedelta( days = time_interval+1) ).strftime('%Y-%m-%dT%H:%M:%SZ')           
            
            
            orders = self.Conn.AccountOrders ( self.Conn.GetAccountHash() ,
                                fromTime =fromTime,toTime=toTime , status = "FILLED" )
            #print( f"ORDERS : {orders}")
        except:
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )
        finally:
            return orders 





    def Reconcile ( self) -> None :
        """
            Reconcile the BUY /SELL with  how they were filled by the trading platform
            ARGS   :
                    none
            RETURNS:
                    none 
            
        """
        reconcile   = {}
        temp        = self.Trades
        
        try:           
            self.Trades = {}
            for symbol in temp.keys():
                self.Trades.update( { symbol : [] } )
                for trade in temp[symbol] :
                    if self.Mode.upper() == "TEST":
                        reconcile   = {
                                        'bidReceipt': 11111111,     'bidFilled' : trade['bid'] ,
                                           'askReceipt' : 2222222,  'askFilled' : trade['ask'] ,
                                           'actualPL' : (trade['ask'] - trade['bid'] ) * trade['qty'] 
                                       }
                    else:
                        if not('bidReceipt' in trade ):
                            reconcile.update(self.Conn.Orders( symbol, enteredTime=trade['bidTime'], qty=trade['qty'],action='BUY') )
                            
                        if not('askReceipt' in trade ):
                            reconcile.update( self.Conn.Orders( symbol, enteredTime=trade['askTime'], qty=trade['qty'],action='SELL') )

                        if 'askFilled' in reconcile and 'bidFilled' in reconcile:
                            reconcile.update( { 'actualPL' : (reconcile['askFilled'] - reconcile['bidFilled'] ) * trade['qty'] } )
                            
                    trade.update( reconcile )
                    self.Trades[symbol].append(  trade  ) 
            
            
        except:
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )























