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

from datetime           import datetime, timedelta
from SchwabAccount      import SchwabAccount 

class TradeAccount:
    def __init__(self, funds : float =5000, limit : float = 0.10 , app_type = 'Schwab',app_key ="xxxxx", app_secret = "zzzzzz" ) :
        """
            Initialize the variables for the Trading Account class 
        """
        self.AccountTypes   = { 'SCHWAB' :  SchwabAccount } 
        self.APP_KEY        = ""
        self.APP_SECRET     = ""
        self.Trades         = []                       # COMPLETED TRADES FOR THE DAY
        self.InPlay         = {}                       # CURRENT TRADES STILL OPEN  
        self.Funds          = funds                    # ACCOUNT DOLLAR AMOUNT 
        self.Limit          = 0.0                      # MAX TO SPEND ON ANY ONE TRADE 
        self.TargetGoal     = 0                        # Dont get greedy, when reach this amount will quit trading for day
        self.Mode           = ""                       # Are we Testing or Trading or something else
        self.Performance    = {}                       # Keep track of wins and loses  

        self.Conn           =  self.AccountTypes  [ app_type.upper()] ( app_key, app_secret )

        self.Funds          = self.Conn.CashForTrading()

        self.SetLimit(limit )                           # INCASE VALUE SENT IN THROUGH CONSTRUCTOR
        
    def __str__(self ) -> str :
        """
            Returns string representation of the object 
        """
        return f'\n\t\t |Funds : {self.Funds}\n\t\t |Limit : {self.Limit * self.Funds}'
    
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




  
    def Quote ( self, symbols : list | str, frequency : int = 60, frequencyType : str = "minute" , endDate : datetime = datetime.now()) -> requests.Response :
        """
            Abstraction to call the underlying client ( Schwab / ) to get a quote
            The last candle in candles:{} will be the most current one we want for frequency and timeframe
            ARGS    :
                        symbols : list 
            RETURNS : 
        """
        candles         = ""
        quote_info      = None
        periodTypes     = ["day","month","year","ytd"]
        frequencyTypes  = ["minute","daily","weekly","monthly"]
        timeStamp       = 0
        try:
            #return self.Conn.Quote( stocks)
            periodType      = 'day'
            period          = 1
            frequencyType   = ("minute" if not( frequencyType in frequencyTypes) else frequencyType  )
            frequency       = int (15 if frequency/60 == 0 else frequency/60 )
            startDate       = endDate - timedelta( seconds = frequency * 60) #datetime.now() - timedelta( seconds = frequency * 60)
            #endDate         = datetime.now()  
            #print( f"Frequency : {frequency} ->  {frequency }"  )
            candles = self.Conn.QuoteByInterval( symbol=symbols, periodType=periodType, period=period,
                                              frequencyType=frequencyType, frequency=frequency, startDate= startDate, endDate =endDate).json()
           
            
            #print( f"\n->TradeAccount::" + str(inspect.currentframe().f_code.co_name) + f" -quote_info : { candles}")
            timeStamp = int(endDate.timestamp() * 1000)
            pos = 0
            if 'candles' in candles :
                for entry in candles['candles'] :
                    pos += 1
                    if ( entry['datetime'] == timeStamp ):
                        # print (f"\t\t\t ** FOUND : {pos} -> {len(candles['candles'])}    :: " , entry )
                         quote_info = entry
                         quote_info['symbol'] = candles['symbol']
                         return quote_info
                        
                quote_info = candles['candles'][-1]
                quote_info['symbol'] = candles['symbol']
                new_quote_info = {}
                for key in quote_info.keys():                  
                    new_quote_info[key] =  float( quote_info[key]) if key in ['volume','open','close','high','low'] else quote_info[key]

         
        except:            
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )
                
            print(f"\n-> ERROR: {candles}")
        finally:
            return quote_info






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


        

    def SetMode ( self, mode : str ) -> None :
        """
            Sets the mode of the application : TEST / TRADE 
        """
        self.Mode = mode


        
    def SetLimit( self, limit : float ) -> None :
        """
            Sets the the limit to use for each trade.  This should be formatted as a decimal
            PARAMETERS  :
                            limit   : float
            RETURNS     :
                            Nothing 
        """
        self.Limit =  limit 
        



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


    def Buy( self, stock : str , price : float)  -> bool :
        """
           Attempt to buy the stock under the confines of the limit , True = succeeded , False = failed
           Updates
               * inPlay dictionary to keep track
               * Funds
               * Limit
               
           PARAMETER :
                       stock : string 
           RETURNS   :
                       bool  : True / False 
        """
        qty             = 0
        success         = False
        message_prefix  = "\t\t\t* TradeAccount::" + str(inspect.currentframe().f_code.co_name) 

        try :
            # IF MADE TARGET PERCENT THEN DONT BUY ANY MORE 
            if self.Funds > self.TargetGoal :
                return False

            
            # CHECK IF CAN AFFORD TO BUY
            #print( "Check : " , str( type( price )) , " : " , str( type( self.Funds * self.Limit ))   )
            if price > ( self.Funds * self.Limit ):
                print(message_prefix + f" Cant even buy ONE stock : {( self.Funds * self.Limit )}  " )
                return success

            # CHECK IF ALREADY HOLDING 
            if stock in self.InPlay.keys() :
                print(message_prefix + "  Already holding, cant take any more ")
                return success

            # ACTUALLY BUY SOME NOW IF MODE='TRADE'
            if self.Mode.upper()  == "TRADE " :
                print("\t\t\t  ->  - We are trading so sending commands to Brokerage" )

            # UPDATE INTERNAL ELEMENTS     
            qty = int (( self.Funds * self.Limit ) / price )
            self.Funds -= qty * price            
            self.InPlay[ stock ] = {
                    'time'  : str( datetime.now() ) ,
                    'price' : price ,
                    'qty'   : qty ,
                    'volume': 'not sure if needed ',
                    'closed': '',
                    'sold'  : 0,
                    'pl'    : 0 
                }
            if not( stock  in self.Performance.keys() ) :
                self.Performance[stock] = []
                
            print ( "\t\t\t  \-> BOUGHT : " , self.InPlay )
            success = True 
            return success 
        except: 
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )



    def Sell( self, stock : str, new_price : float)  -> bool :
        """
           Sell the stock currently holding , True = succeeded , False = failed
           Updates
               * Move inPlay entry into Trades 
               * Remove inPlay  entry 
               * Funds
               * Limit ( auto updated ) 
               
           PARAMETER :
                       stock : string 
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
                print ( f"\t\t\t   -> DIFF  -> {new_price }  {self.InPlay[ stock ]['price']}  {diff } ")
                if diff < 0.00016 :    # ignore profit if less than % of investment 
                    print(message_prefix + "  Not Selling - trying to be a little greedier ")
                    return False
            

            # Sell the stock IF MODE='TRADE'
            if self.Mode.upper()  == "TRADE " :
                print("\t\t - We are trading so sending commands to Brokerage" )
                
            self.Funds += ( self.InPlay[stock]['qty'] * new_price )
            p_l         = ( self.InPlay[stock]['qty'] * new_price )  - ( self.InPlay[ stock ]['qty'] *  self.InPlay[ stock ]['price'] )  
            self.Trades.append(  [ stock, self.InPlay[ stock ]['time'],  self.InPlay[ stock ]['price'],  self.InPlay[ stock ]['qty'],
                             str(datetime.now()), new_price, p_l ] )
            print ( f"\t\t\t \-> SOLD :  from {self.InPlay[stock]['price']} -> {new_price }"  )
            self.InPlay.pop( stock )    #REMOVE ENTRY FROM DICTIONARY 
            self.Performance[stock].append ( 'WIN' if p_l >0 else 'LOSS' )
            success = True
            
            return success
        except: 
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )






























