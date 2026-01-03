## ###################################################################################################################
##  Program :   Day Trade Strategies 
##  Author  :   Sean Burner
##  Detail  :   Class that holds multiple strategies as methods 
##  Install :   
##  Example :
##              python3 
##              python3 
##  Notes   :   https://docs.python.org/3/tutorial/classes.html
## ###################################################################################################################
import os
import re
import sys
import time
import math
import pandas as pd
import numpy  as np 
import getpass
import inspect
import platform
import argparse
import functools
import requests


from datetime       import datetime
from Indicators     import Indicators
from TradeAccount   import TradeAccount


Date_Format     = "%Y-%m-%d %H:%M:%S"

class DayTradeStrategy:
    OpenRange  = { 'high': 0, 'low': 0 , 'vwap' : 0}
    Occurrence = 0 
    AvgVolume  = 0
    WatchAlert = ''

    
    def __init__(self) :
        """
            Initialize the variables for the Trading Account class 
        """
        self.Strategies = {
                                'basic'         :{ 'detail' : 'Basic Bitch of the group',                                               'method': self.DayTradeBasic},
                                'ema9'          :{ 'detail' : 'Use the EMA 9 to decide to buy and sell',                                'method': self.DayTradeEMA9},
                                'simple'        :{ 'detail' : 'Three candle rule with Chop Index consideration',                        'method': self.DayTradeSimple},
                                'simple1'       :{ 'detail' : 'Three candle rule with Chop Index consideration - CODE COMPARISON',      'method': self.DayTradeSimple1},
                                'opening_range' :{ 'detail' : 'Use first candle to provide range of interest',                          'method': self.OpeningRange} # still needs to be worked 
                          }
        self.Interval   = 1
        self.Stocks     = {}
       
        self.StrategyName = ""
        
        self.isORBBuild = False 
        

         
    def List( self) -> str  :
        """
            Visually appealing list of available strategies
            PARAMETERS :
                            Nothing 
            RETURNS    :
                            string 
        """
        contents = "\t\t ========== Strategies ===============\n"
        for key in self.Strategies.keys() :
            contents += f'\t\t  {key:<15} : {self.Strategies[key]["detail"]}\n'

        return contents


    def Set( self, strategy :str , interval : int , account : TradeAccount   )  -> bool :
        """
            Do the overhead for the specific strategy
            ARGS    :
                        strategy  ( str )          - name fo the strategy
                        interval  ( int )          - time frame ( minutes )  to use for strategy
                        account   ( TradeAccount ) - trade account for  buy/sell 
            RETURNS :
                        true/false ( bool )  - indication of success
        """
        targetGoal  = 0.025  #  This needs to be tied to the strategy so it can change, this is not the right place for it 

        
        if not ( strategy in self.Strategies.keys() ):
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Strategy does not exist : ", strategy )
            return False
        
        self.StrategyName   = strategy
        self.Interval       = interval
        account.SetTargetGoal( targetGoal  )
        
        return True

    
    def PrimeStockEntry( self, symbol : str, ticker_df : pd.DataFrame, ticker_row : list, current_time : datetime,
                                 account : TradeAccount, closePos : int = 3, highPos : int = 6, volumePos : int = 5 ) -> dict :
        """
            Set the Stock object entry for a new stock symbol
            ARGS  :
            RETURNS :
                    dictionary of values for the self.Stock objec 
        """
        data            = None
        seed_df         = None
        ticker_df       = None 
        time_range      = 200
        today_date      = str(current_time)[:10]
        stock_entry     = {}
        
        try:
            print( f"PrimeStockEntry :: {symbol} - DATA   , SET UP RULES FOR MONDAYS ON HISTORY")
            data        = account.History ( symbol = symbol, time_range=time_range , today= current_time)           # GET HISTORICAL INFO FOR SYMBOL
            print( "PrimeStockEntry :: SEED ")
            seed_df     = account.History( symbol=symbol, time_range=1, period_type="day", time_period='minute')
            #print(f"DATA : {data}")    
            if not isinstance(seed_df, pd.DataFrame) or len(seed_df) == 0:
                seed_df = data
            #print(f"SEED : {seed_df}")    
            seed_df['full_date'] = seed_df['datetime'].apply( lambda x: datetime.fromtimestamp(x/1000))                    
            seed_df = seed_df[seed_df['full_date'] < f"{today_date} 10:00:00"]                
            
            # Previous Day's High/Low            
            indicators = Indicators ( symbol= symbol ,data= data, seed_df=seed_df )                 # CALCULATE THE INDICATORS 
            stock_entry = {
                                    'Previous'      : [0,0,0,0,0,0,0],
                                    'Previous1'     : [0,0,0,0,0,0,0],
                                    'Previous2'     : [0,0,0,0,0,0,0],
                                    'Previous3'     : [0,0,0,0,0,0,0],
                                    'Previous4'     : [0,0,0,0,0,0,0],
                                    'Price'         : {
                                                        'Previous'  : ticker_row[ closePos ],
                                                        'Slope'     : 1 , 'Bought'  : 0,
                                                        'High'      : ticker_row[ highPos ],
                                                        'Upward' : 0 , 'Downward': 0,
                                                        'HighSinceBought' : 0
                                                       },
                                    'Volume'        : {'Previous': ticker_row[ volumePos], 'Slope' : 1 , 'Bought' : 0},
                                    'AvgNumMoves'   : [],
                                    'AvgAmount'     : [],
                                    'AvgOccurrVol'  : 0,
                                    'Indicators'    : indicators,
                                    'Losses'        : 0,
                                                           
                                    "PrevDayHigh"   : ticker_df[ :-1]['high'].to_string(index=False) if ticker_df != None else ticker_row[2] ,
                                    "PrevDayLow"    : ticker_df[ :-1]['low'].to_string(index=False)  if ticker_df != None else ticker_row[6] ,
                                    "ORB_L"         : ticker_row[2] if ticker_row else 0,
                                    "ORB_H"         : ticker_row[6] if ticker_row else 0
                                    
                             }
        except: 
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )


        return stock_entry 

    def SetORB ( self , symbols : str ,account : TradeAccount, current_time : datetime , use_name : str = None) -> None :
        """
            Gets the high/low from the previous day and gets the high/low from current day's opening
            NOTE L Includes a waiting loop if before 10am 
            ARGS  :
                    symbol       ( str )               stock symbol(s)
                    account      ( TradeAccount )      trading account
                    current_time ( datetime.datetime)  current time of running
            RETURNS:
                    nothing 
        """        
        ticker_df       = None
        ticer_row       = None
        today_date      = None 
        date_format     = "%Y-%m-%d %H:%M:%S"

        try:
            if self.isORBBuild :
                return
            
            print("\t\t\t * Building ORB levels ")
            if ( current_time.hour < 10  and current_time.minute < 59 ) :  # Pause until 10
                time_to_sleep = ( 60 - current_time.minute ) *60 #(( 10 - current_time.hour) * 60 * 60) - ( 60 - current_time.minute ) 
                print(f" Pausing for   { time_to_sleep}")
                if time_to_sleep > 0 :
                    print ( f" From {current_time} -> 10am - sleep :{ time_to_sleep }   "+
                                f"HOURS: {((current_time.hour - 10) * 60)}  MINUTE : {( 60 - current_time.minute )}")
                    if account.Mode.upper() == "TRADE" :# or account.Mode.upper() == "TEST" :
                        time.sleep( time_to_sleep )
            else:
                print(f"No Need to pause  {current_time}")
            
            today_date  = str(current_time)[:10]
            symbols     = [ symbols ] if isinstance( symbols, str) else symbols            
            for symbol in symbols:          
                current_time    = datetime.strptime( f"{today_date} 10:00:00", date_format)
                print( "SetORB :: TICKER DF ")
                ticker_df       = account.History( symbol=symbol, time_range=1, today=current_time)
                print( "SetORB :: TICKER ROW ")
                ticker_row      = account.QuoteByInterval ( symbols= symbol,  frequency= 60*30, endDate = current_time)
                stock_entry     = self.PrimeStockEntry(  symbol, ticker_df, ticker_row, current_time ,
                                                     account , closePos = 3, highPos = 6, volumePos = 5 )
                self.Stocks.update( { (symbol if use_name ==None else use_name) : stock_entry } )
                

            self.isORBBuild = True 

        except:
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )

        print (f"STOCKS : {self.Stocks}")

            
    def Run( self,  ticker_row : list, account : TradeAccount, configs : dict  ) -> (bool, str, int, TradeAccount) :
        """
            Switching station to control which strategy gets used
            ARGS  :
                    ticker_row  ( list )         list of fields for stock quote
                    account     ( TradeAccount)  initiated account object
                    configs      ( dictionary )  configurations 
            RETURNS:
                    success : True/False
        """
        if not ( self.StrategyName in  self.Strategies.keys() ):
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Strategy does not exist : ", self.StrategyName )
            return False 
        
        return self.Strategies[ self.StrategyName  ]['method'] ( ticker_row, account, configs  )


            
    def ProfitTrailStop( self, stock : str, risk_percent : float) -> float :
        """
            Calculates the profit  at the previous price so can see how much of a loss dealing with now

            PARAMETERS :
                            stock           : string  -  the name of the stock
                            risk_percent    : float  - how much tolerance in price action 
                            
            RETURNS    : 
        """
        previous_price      = float(self.Stocks[ stock ]['Price']['Previous'])
        strike_price        = float(self.Stocks[ stock ]['Price']['Bought']) 
        profit              = previous_price - strike_price
        trigger_price       = strike_price + ( profit * risk_percent )

         
        #print(f"\t\t\t --  Trigger price : { trigger_price}     Previous Price : { previous_price}     Strike : { strike_price} " )
        return  trigger_price 



            
    def StrikePriceStop(  self, stock : str, risk_percent : float) -> float :
        """
            Calculates the trigger price when below the strike price 

            PARAMETERS :
                            stock           : string  -  the name of the stock 
                            risk_percent    : float  - how much tolerance in price action 
                            
            RETURNS    : 
        """
        bought_price        = float(self.Stocks[ stock ]['Price']['Bought'])        
        trigger_price       = bought_price - (risk_percent * bought_price )

         
        #print(f"\t\t\t --  Trigger price : { trigger_price}     Bought : { bought_price} " )
        return  trigger_price 





    def BaseParams (self ) -> dict :
        """
            Provide the params dictionary with base values
            ARGS   :
                    nothing
            RETURNS:
                    params (dict) - standard values for the day trading parameters 
        """
        return {  
                   "limit"                  : 0.20,     # DO NOT EXCEED 10% OF THE ACCOUNT.FUNDS ON ANY ONE PURCHASE
                   "timePos"                : 1,        # Time position in Ticker Row
                   "lowPos"                 : 2 ,       # Quote Low Price Position
                   "closePos"               : 3,        # THE CLOSE PRICE LOCATION INTHE TICKER ROW
                   "openPos"                : 4 ,       # Opening Price 
                   "highPos"                : 6,        # THE HIGH PRICE LOCATION INTHE TICKER ROW
                   "volumePos"              : 5 ,       # VOLUME POSITION  IN TICKER
                   "numOfLosses"            : 2 ,       # Number of losses to tolerate before stop trading 
                   "risk_percent"           : 0.0015,   # Useful when price starts to fall and need to know when to bail 
                   "time_interval"          : 60,       # Standard Time interval to use
                   "time_interval_bought"   : 60,       # After buying do we need to change time_interval 
                   "crash_out_percent"      : 0.97,     # If the price is crashing this percent of the price we purchased for, then bail ( 100 * .97 => 97 less than or equal we bail 
                   "price_move_change"      : 0.02,     # Price needs to move by this much before we start doing something
                   "volume_change_ratio"    : 0.70,     # Ratio of new volume to previous volume  ( may be unnecessary  unless building out trends )
                   "volume_change_avg_ratio": -0.30,    # Quantifying the change in volume to act ( probably over thinking things )
                   "bounce_up_min"          : 2 ,       # Checks how many consecutive moves upwards before acting
                   "volume_threshold"       : 70000     # Safety net to consider when appropriate to enter a trade, but may not be necessary 
                }

    def DayTradeEMA9( self, ticker_row : list, account : TradeAccount , configs : dict ) -> (bool, str,int,TradeAccount) :
        """
            Set the params for the DayTrade  version  , then call the function
            ARGS  :
                        ticker_row ( list ) information about the stock and current price and volume
                        account    ( TradeAccount )  the trading account for BUYS and SELLS
                        configs    (  dict)    configurations 
            RETURNS:
                        bool: True/False - in case something breaks or could not complete    
        """
        matrix      = {     0  : { 'numOfLosses' : 1 , 'time_interval' : 900 , 'time_interval_bought' : 900 },
                            1  : { 'numOfLosses' : 2 , 'time_interval' : 60 , 'time_interval_bought' : 60 },
                            3  : { 'numOfLosses' : 2 , 'time_interval' : 180 , 'time_interval_bought' : 180 },
                            5  : { 'numOfLosses' : 2 , 'time_interval' : 300 , 'time_interval_bought' : 300 },
                            10 : { 'numOfLosses' : 2 , 'time_interval' : 600 , 'time_interval_bought' : 600 , 'volume_change_avg_ratio' : 0.10 , 'crash_out_percent' :0.85},
                            15 : { 'numOfLosses' : 2 , 'time_interval' : 900 , 'time_interval_bought' : 900 , 'volume_change_avg_ratio' : 0.10 , 'crash_out_percent' :0.85},
                            16 : { 'numOfLosses' : 2 , 'time_interval' : 300 , 'time_interval_bought' : 60 }
                         }
        params      = self.BaseParams()
        interval    = int( configs.get('interval',1) )

        try:
            for key in matrix[ interval ].keys():
                params[key]           =  matrix[ interval ][key]
            
            params['volume_threshold']      = configs['volume_threshold']
        
            #print(f"\t *Strategy : Simple {configs['interval']} min ")
        except:
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )

                
        return self.DayTradeEMA9Module ( ticker_row , account, params  )






    def DayTradeSimple ( self, ticker_row : list, account : TradeAccount , configs : dict ) -> (bool, str,int,TradeAccount) :
        """
            Set the params for the DayTrade 15 min  version  , then call the function
            ARGS  :
                        ticker_row ( list ) information about the stock and current price and volume
                        account    ( TradeAccount )  the trading account for BUYS and SELLS
                        configs    (  dict)    configurations 
            RETURNS:
                        bool: True/False - in case something breaks or could not complete    
        """
        matrix      = {     0  : { 'numOfLosses' : 1 , 'time_interval' : 900 , 'time_interval_bought' : 900 },
                            1  : { 'numOfLosses' : 2 , 'time_interval' : 60 , 'time_interval_bought' : 60 },
                            3  : { 'numOfLosses' : 2 , 'time_interval' : 180 , 'time_interval_bought' : 180 },
                            5  : { 'numOfLosses' : 2 , 'time_interval' : 300 , 'time_interval_bought' : 300 },
                            10 : { 'numOfLosses' : 2 , 'time_interval' : 600 , 'time_interval_bought' : 600 , 'volume_change_avg_ratio' : 0.10 , 'crash_out_percent' :0.85},
                            15 : { 'numOfLosses' : 2 , 'time_interval' : 900 , 'time_interval_bought' : 900 , 'volume_change_avg_ratio' : 0.10 , 'crash_out_percent' :0.85},
                            16 : { 'numOfLosses' : 2 , 'time_interval' : 300 , 'time_interval_bought' : 60 }
                         }
        params      = self.BaseParams()
        interval    = int( configs.get('interval',1) )

        try:
            for key in matrix[ interval ].keys():
                params[key]           =  matrix[ interval ][key]
            
            params['volume_threshold']      = configs['volume_threshold']
        
            #print(f"\t *Strategy : Simple {configs['interval']} min ")
        except:
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )

                
        return self.DayTradeSimpleModule ( ticker_row , account, params  )




    def DayTradeSimple1 ( self, ticker_row : list, account : TradeAccount , configs : dict ) -> (bool, str,int, TradeAccount) :
        """
            Set the params for the DayTrade 15 min  version  , then call the function
            ARGS  :
                        ticker_row ( list ) information about the stock and current price and volume
                        account    ( TradeAccount )  the trading account for BUYS and SELLS
                        configs    (  dict)    configurations 
            RETURNS:
                        bool: True/False - in case something breaks or could not complete    
        """
        matrix      = {     0  : { 'numOfLosses' : 1 , 'time_interval' : 900 , 'time_interval_bought' : 900 },
                            1  : { 'numOfLosses' : 2 , 'time_interval' : 60 , 'time_interval_bought' : 60 },
                            3  : { 'numOfLosses' : 2 , 'time_interval' : 180 , 'time_interval_bought' : 180 },
                            5  : { 'numOfLosses' : 2 , 'time_interval' : 300 , 'time_interval_bought' : 300 },
                            10 : { 'numOfLosses' : 2 , 'time_interval' : 600 , 'time_interval_bought' : 600 , 'volume_change_avg_ratio' : 0.10 , 'crash_out_percent' :0.85},
                            15 : { 'numOfLosses' : 2 , 'time_interval' : 900 , 'time_interval_bought' : 900 , 'volume_change_avg_ratio' : 0.10 , 'crash_out_percent' :0.85},
                            16 : { 'numOfLosses' : 2 , 'time_interval' : 300 , 'time_interval_bought' : 60 }
                         }
        params      = self.BaseParams()
        interval    = int( configs.get('interval',1) )

        try:
            for key in matrix[ interval ].keys():
                params[key]           =  matrix[ interval ][key]
            
            params['volume_threshold']      = configs['volume_threshold']
        
            #print(f"\t *Strategy : Simple {configs['interval']} min ")
        except:
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )

                
        return self.DayTradeSimpleModule1 ( ticker_row , account, params  )   




    def DayTradeBasic ( self, ticker_row : list, account : TradeAccount , configs : dict ) -> (bool, str, int, TradeAccount) :
        """
            Set the params for the DayTrade 15 min  version  , then call the function
            ARGS  :
                        ticker_row ( list ) information about the stock and current price and volume
                        account    ( TradeAccount )  the trading account for BUYS and SELLS
                        configs    (  dict)    configurations 
            RETURNS:
                        bool: True/False - in case something breaks or could not complete    
        """
        matrix      = {     0  : { 'numOfLosses' : 1 , 'time_interval' : 900 , 'time_interval_bought' : 900 },
                            1  : { 'numOfLosses' : 2 , 'time_interval' : 60 , 'time_interval_bought' : 60 },
                            5  : { 'numOfLosses' : 2 , 'time_interval' : 300 , 'time_interval_bought' : 300 },
                            10 : { 'numOfLosses' : 2 , 'time_interval' : 600 , 'time_interval_bought' : 600 , 'volume_change_avg_ratio' : 0.10 , 'crash_out_percent' :0.85},
                            15 : { 'numOfLosses' : 2 , 'time_interval' : 900 , 'time_interval_bought' : 900 , 'volume_change_avg_ratio' : 0.10 , 'crash_out_percent' :0.85},
                            16 : { 'numOfLosses' : 2 , 'time_interval' : 300 , 'time_interval_bought' : 60 }
                         }
        params      = self.BaseParams()
        interval    =  int( configs.get('interval',1) )

        

        try:        
            for key in matrix[ interval ].keys():
                params[key]           =  matrix[ interval ][key]
            
            params['volume_threshold']      = configs['volume_threshold']
        
            #print("\t *Strategy : basic bitch 15 min ")
        except:
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )

                
        return self.DayTradeBasicModule ( ticker_row , account, params  )




      

    def ResetStock( self , symbol : str,  stockClose : float , stockVolume : int , stockHigh : float  ) -> None :
        """
            Resets the self.Stock element before returning from method
            ARGS   :
                        symbol      ( str )  - stock symbol  
                        stockClose  ( float) - close price of stock
                        stockVolume ( int )  - volume of stock
                        stockHigh   ( float) - high price of stock 
            RETURNS:
                    nothing 
        """
        try:
            self.Stocks[ symbol ]['Price' ]['Previous'] =  stockClose
            self.Stocks[ symbol ]['Volume']['Previous'] =  stockVolume
            if stockClose > float(self.Stocks[ symbol ]['Price']['High']) :
                self.Stocks[ symbol ]['Price']['High'] = stockHigh
                
            if stockClose > self.Stocks[ symbol ]['Price']['HighSinceBought'] :
                print(f"RESETTING HighSinceBought: {self.Stocks[ symbol ]['Price']['HighSinceBought']} -> {stockClose}")
                self.Stocks[ symbol ]['Price']['HighSinceBought'] = stockClose
            
        except:
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )


    def DayTradeEMA9Module ( self, ticker_row : list, account : TradeAccount, params : dict  ) -> (bool, str, TradeAccount) :
        """
            When CLOSE PRICE is above the EMA9 buy, when closes below SELL while the ChopIndex < 60 , 70 >  RSI > 10 , 70 > ADX >20
            
            ARGS  :
                        ticker_row        ( list ) information about the stock and current price and volume
                        account           ( TradeAccount )  the trading account for BUYS and SELLS
                        volume_threshold  ( int )  the lower limit for volume activity to engage in buy/sell ( may not be important after all )
                        params            ( dicts ) parameters to customize the run 
            RETURNS    :
                        bool: True/False - in case something breaks or could not complete                         
        """
        limit               = params['limit']        # DO NOT EXCEED 10% OF THE ACCOUNT.FUNDS ON ANY ONE PURCHASE
        profit              = 0
        action              = ""
        success             = False
        symbol              = ticker_row[0]
        lowPos              = params['lowPos']
        timePos             = params['timePos']
        openPos             = params['openPos']
        highPos             = params['highPos']
        closePos            = params['closePos']
        volumePos           = params['volumePos']
        emaPos              = highPos + 1 
        risk_percent        = params['risk_percent']
        time_interval       = params['time_interval']
        crash_out_percent   = params['crash_out_percent']      # IF PRICE IS FALLING FAST, DONT SELL IF BELOW THIS PERCENT OF THE PURCHASE, TAKE RISK AND WAIT FOR REBOUND 
        max_num_of_losses   = params["numOfLosses"]

        try:
            # Update the indicators            
            entry ={0:{'close': ticker_row[closePos], 'open' : ticker_row[openPos] ,'low' : ticker_row[lowPos], 'high' : ticker_row[highPos],
                       'datetime' : (datetime.strptime( ticker_row[timePos][:19], Date_Format) ).timestamp()  * 1000 , 'volume' : ticker_row[volumePos]}}

            self.Stocks[ symbol ]['Indicators'].Update( entry = entry)           
            
            
            ticker_row.append( self.Stocks[ symbol ]['Indicators'].EMA9 )  # ADX PLACE HOLDER
                
            # NO BUYING AFTER 3:45
            current_time    = datetime.now()
            if not ( symbol in self.Stocks.keys() )  and ( current_time.hour == 15 and current_time.minute >= 45) :
                print(f"\t\t\t -> DayTradeStrategy:: DayTradeBasic () -> TOO LATE TO CONSIDER MAKING BIDS " )
                return False, action, params["time_interval"]

            # ADD MECHANISM FOR DETERMINING THE AVG NUMBER OF MOVES BEFORE PIVOTING AND THE AVG $ MOVES  BEFORE PIVOTING
         
            # ADD STOCK ENTRY IF NOT INPLAY /  THIS SHOULD MAINLY BE DONE IN SETORB (), BUT INCASE SOME GET ADDED ALONG THE WAY             
            if not ( symbol in self.Stocks.keys() ) :
                print("EMA9 - doing the PrimeEntry")
                ticker_df       = account.History( symbol=ticker_row[0], time_range=1)   
                self.Stocks[symbol] = self.PrimeStockEntry( symbol=ticker_row[0] , ticker_df=ticker_df,ticker_row=ticker_row , current_time=current_time,
                                                            account=account, closePos = closePos , highPos=highPos , volumePos=volumePos)
            
            
            
            # ARE WE TRENDING UP            
            if self.Stocks[ symbol]['Price']['Bought'] == 0:  # MEANS NO OPTION POSITIONS
                if (  (ticker_row[closePos] > ticker_row[emaPos]  and   self.Stocks[ symbol]['Previous'][closePos] > self.Stocks[ symbol]['Previous'][emaPos]  and self.Stocks[ symbol]['Previous1'][closePos] > self.Stocks[ symbol]['Previous1'][emaPos])  and 
                     self.Stocks[ symbol ]['Indicators'].ChopIndex < 63  and 
                        70 > self.Stocks[ symbol ]['Indicators'].RSI < 10 ) :
                    """
                    print(f"{symbol}- BUY TRIGGERED : SIMPLE : CHOP : { self.Stocks[ symbol ]['Indicators'].ChopIndex } < 63  and  RSI :60 > {self.Stocks[ symbol ]['Indicators'].RSI} >= 10 )   CANDLE BODY : {candle_body} >= 0.30 " +
                              f" BOLLINGER : TIME : {ticker_row[1][11:13]}   LEEWAY: { self.Stocks[ symbol ]['Indicators'].BB_Upper - ticker_row[closePos] } > 0.11  or  " +
                              f"  { self.Stocks[ symbol ]['Indicators'].BB_Upper - ticker_row[closePos] } < -0.40   " +
                              f" BOLLINGER : M{morning_bollinger} or A{afternoon_bollinger}   RSI: M{morning_rsi} A{afternoon_rsi}  dFIB :{ self.Stocks[ symbol ]['Indicators'].dFib } ")# ADX: {ticker_row[adxPos]}")             
                                    
                    print(f"\t\t\t\t\t{symbol} - It took {self.Stocks[ symbol]['Price']['Upward']} soldiers  with ChopIndex : {self.Stocks[ symbol ]['Indicators'].ChopIndex}   IS DOGEE : {is_dogee} " +
                              f"VOLATILTIY: {self.Stocks[ symbol ]['Indicators'].Summary()['VolIndex'] }  dSMA : {self.Stocks[ symbol ]['Indicators'].Summary()['dSMA']}  " +
                              f" RSI :  {self.Stocks[ symbol ]['Indicators'].RSI}  BB : {self.Stocks[ symbol ]['Indicators'].BB_Lower} -> {self.Stocks[ symbol ]['Indicators'].BB_Upper} to finally break through "+
                              f" CURRENT BODY: { (ticker_row[closePos] - ticker_row[openPos] )}   PREVIOUS: {( self.Stocks[ symbol ]['Previous'][closePos] - self.Stocks[ symbol ]['Previous'][openPos] )} ")
                    """
                    if ((( ticker_row[1][11:13] == '15' and ticker_row[1][14:16] < '45') or ( ticker_row[1][11:13] < '15' ) )  and   # DONT OPEN TRADES TOO LATE IN THE DAY
                                account.Buy( stock=symbol , price=float(ticker_row[ closePos ])  ,
                                 current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ) ,
                                    volume = ticker_row[volumePos], volume_threshold = params['volume_threshold'], indicators=self.Stocks[symbol]['Indicators']) ):
                        print(f"{symbol} - BOUGHT @ : UPWARD:{self.Stocks[ symbol]['Price']['Upward']} -> CHOP: {self.Stocks[ symbol ]['Indicators'].ChopIndex}  RSI :  {self.Stocks[ symbol ]['Indicators'].RSI}   PRICE: {ticker_row[closePos]}")
                        success     = True                                               
                        action      = "bought"
                        self.ResetStock( symbol =symbol , stockClose=ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )                    
                        self.Stocks[ symbol ]['Price' ]['Bought']   =  ticker_row[ closePos ]                            
                        self.Stocks[ symbol ]['Price' ]['Previous'] =  ticker_row[ closePos ]
                        self.Stocks[ symbol ]['Volume']['Bought']   =  ticker_row[volumePos]
                        self.Stocks[ symbol]['Price']['Upward']     =  0
                        self.Stocks[ symbol]['AvgOccurrVol']        =  0               
               
            
            if action != 'bought' and self.Stocks[ symbol]['Price']['Bought'] > 0 :                                
                print(f"INSIDE A POSITION:   BOUGHT:{self.Stocks[symbol]['Price']['Bought']} ->{ticker_row[closePos]} --> [PREVIOUS]{self.Stocks[symbol]['Previous'][closePos]} [PREVIOUS1]{self.Stocks[symbol]['Previous1'][closePos]} " +
                      f"PROFIT : {( ticker_row[closePos]  - self.Stocks[symbol]['Price']['Bought']) }    CHOP: {self.Stocks[ symbol ]['Indicators'].ChopIndex} " +
                      f"RSI: {self.Stocks[ symbol ]['Indicators'].RSI}  " +
                      f" BB :  {self.Stocks[ symbol ]['Indicators'].BB_Lower} -> {self.Stocks[ symbol ]['Indicators'].BB_Upper} " )#  ATR : {self.Stocks[ symbol ]['Indicators'].AvgTrueRange()} ")               
                
                
                if (  ticker_row[closePos] < ticker_row[emaPos]   or ticker_row[closePos] <= (  self.Stocks[ symbol ]['Price' ]['Bought'] - 0.16) ) :
                      print( f"TIME TO SELL PRICE: {ticker_row[closePos]} -> {(self.Stocks[symbol]['Previous'][closePos] - 0.16)} or {( self.Stocks[symbol]['Price']['Bought'] - 0.16 )  } or { (self.Stocks[symbol]['Price']['HighSinceBought'] - 0.16)}  "+
                             f" VOLUME: {ticker_row[volumePos]} -> { 0.80 * self.Stocks[symbol]['Previous'][volumePos] }  " +
                              f"VOLATILTIY: {self.Stocks[ symbol ]['Indicators'].Summary()['VolIndex'] }  dSMA : {self.Stocks[ symbol ]['Indicators'].Summary()['dSMA']}  " +
                             f" HARDCODE PRICE : { ticker_row[closePos]  - self.Stocks[symbol]['Price']['Bought'] } or {self.Stocks[symbol]['Price']['Bought'] - ticker_row[closePos]  } "+
                             f" CHOP :{self.Stocks[ symbol ]['Indicators'].ChopIndex}  RSI:{self.Stocks[ symbol ]['Indicators'].RSI}  ")                      
                      
                      if  account.Sell( stock=symbol, new_price=float(ticker_row[ closePos ]) ,
                                           current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ),
                                       ask_volume=float(ticker_row[ volumePos ] ), indicators=self.Stocks[symbol]['Indicators'] )  :
                         success        = True
                         action         = "closed"
                         self.Stocks[ symbol ]['Price' ]['Bought'] = 0
                         self.Stocks[ symbol ]['Price' ]['High']   = 0
                         self.Stocks[ symbol ]['Volume']['Bought'] = 0
                         self.Stocks[ symbol ]['Volume']['HighSinceBought'] = 0
                         #self.Stocks[symbol]['Losses']    += 1

                         for trade in account.Trades[symbol]:
                             #print(f"\t\t\t   Indicators [IN ] : {trade['indicators_in']}  [OUT] {trade['indicators_out']}  ")
                             print(f"\t\t\t   TIME: {trade['bidTime']}  P&L: {trade['p_l']} ")

            #CLEAN UP
            """  MOVED TO THE TOP  
            # Update the indicators            
            entry ={0:{'close': ticker_row[closePos], 'open' : ticker_row[openPos] ,'low' : ticker_row[lowPos], 'high' : ticker_row[highPos],
                       'datetime' : (datetime.strptime( ticker_row[timePos][:19], Date_Format) ).timestamp()  * 1000 , 'volume' : ticker_row[volumePos]}}

            self.Stocks[ symbol ]['Indicators'].Update( entry = entry)
            
            print(f"ADX: {type( self.Stocks[ symbol ]['Indicators'].ADX)}  SHAPE : { self.Stocks[ symbol ]['Indicators'].ADX.shape[1]}")
            """  
            
            # UPDATE THE STOCK INFO WITH THE CURRENT PRICE / VOLUME
            self.ResetStock( symbol =symbol , stockClose= ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )
            self.Stocks[ symbol ]['Previous2']         =  self.Stocks[ symbol ]['Previous1']
            self.Stocks[ symbol ]['Previous1']         =  self.Stocks[ symbol ]['Previous']
            self.Stocks[ symbol ]['Previous']          =  ticker_row
            
            # CHANGE TO 5 MINUTE INFO TO JUMP IN AND OUT MOREL ACCURATELY
            if float(self.Stocks[ symbol]['Price']['Bought']) > 0 :
                time_interval   =  params['time_interval_bought']  # DROP FROM 5 -> 1 or 3 inside of position 
            else:
                if action =='closed' :
                    print("Taking a breathe")
               #     time.sleep(params['time_interval'] ) # After closing a position , take a pause 
                    
                time_interval   = params['time_interval']
                
        except: 
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )


        return success , action, time_interval , account
    
    
    def DayTradeSimpleModule ( self, ticker_row : list, account : TradeAccount, params : dict  ) -> (bool, str, TradeAccount) :
        """
            Look for three candles that are update , with the second's body equal or greater than 1st wick, and the 3rd body equal or greater than second ,
            while the ChopIndex < 60
            
            ARGS  :
                        ticker_row        ( list ) information about the stock and current price and volume
                        account           ( TradeAccount )  the trading account for BUYS and SELLS
                        volume_threshold  ( int )  the lower limit for volume activity to engage in buy/sell ( may not be important after all )
                        params            ( dicts ) parameters to customize the run 
            RETURNS    :
                        bool: True/False - in case something breaks or could not complete                         
        """
        limit               = params['limit']        # DO NOT EXCEED 10% OF THE ACCOUNT.FUNDS ON ANY ONE PURCHASE
        profit              = 0
        action              = ""
        success             = False
        symbol              = ticker_row[0]
        lowPos              = params['lowPos']
        timePos             = params['timePos']
        openPos             = params['openPos']
        highPos             = params['highPos']
        closePos            = params['closePos']
        volumePos           = params['volumePos']
        adxPos              = 6 
        risk_percent        = params['risk_percent']
        time_interval       = params['time_interval']
        crash_out_percent   = params['crash_out_percent']      # IF PRICE IS FALLING FAST, DONT SELL IF BELOW THIS PERCENT OF THE PURCHASE, TAKE RISK AND WAIT FOR REBOUND 
        max_num_of_losses   = params["numOfLosses"]

        try:
            # Update the indicators            
            entry ={0:{'close': ticker_row[closePos], 'open' : ticker_row[openPos] ,'low' : ticker_row[lowPos], 'high' : ticker_row[highPos],
                       'datetime' : (datetime.strptime( ticker_row[timePos][:19], Date_Format) ).timestamp()  * 1000 , 'volume' : ticker_row[volumePos]}}

            self.Stocks[ symbol ]['Indicators'].Update( entry = entry)

            print(f"9 EMA : { self.Stocks[ symbol ]['Indicators'].EMA9} " )

            # CURRENT PRICE RANGE  30 MIN - BEFORE INTEGRATING THE CURRENT ENTRY
            time_frame = 20 #30
            rangeHigh  = self.Stocks[ symbol ]['Indicators'].Data['high'].rolling(window=time_frame).max().dropna().max()
            rangeLow   = self.Stocks[ symbol ]['Indicators'].Data['low'].rolling(window=time_frame).min().dropna().min()
            rangeMean  = self.Stocks[ symbol ]['Indicators'].Data['close'].rolling(window=time_frame).mean().dropna().mean()
            rangeMedian  = self.Stocks[ symbol ]['Indicators'].Data['close'].rolling(window=time_frame).median().dropna().median()
            if np.isnan( rangeLow ) or np.isnan( rangeHigh ) or rangeLow == 0:
                rangeLow  = np.min( [self.Stocks[symbol]['Previous1'][lowPos],self.Stocks[symbol]['Previous2'][lowPos],self.Stocks[symbol]['Previous3'][lowPos],self.Stocks[symbol]['Previous4'][lowPos]] )
                rangeHigh = np.max( [self.Stocks[symbol]['Previous1'][highPos],self.Stocks[symbol]['Previous2'][highPos],self.Stocks[symbol]['Previous3'][highPos],self.Stocks[symbol]['Previous4'][highPos]] )
                rangeMean = np.mean( [self.Stocks[symbol]['Previous1'][closePos],self.Stocks[symbol]['Previous2'][closePos],self.Stocks[symbol]['Previous3'][closePos],self.Stocks[symbol]['Previous4'][closePos]] )
                rangeMedian = np.median( [self.Stocks[symbol]['Previous1'][closePos],self.Stocks[symbol]['Previous2'][closePos],self.Stocks[symbol]['Previous3'][closePos],self.Stocks[symbol]['Previous4'][closePos]] )
            
            rangeBand  = rangeHigh - rangeLow
            print( rangeHigh )
            if rangeBand <= 0.50 and ticker_row[closePos] < rangeHigh:
                print(f"NARROW RANGING - Should not trade : LOW : { rangeLow} - HI: {rangeHigh} = {rangeHigh - rangeLow}   PRICE : {ticker_row[closePos]}    MEAN : {rangeMean}  MEDIAN: {rangeMedian} ")                
            else:
                print(f"WIDER RANGING OR PRICE OUTSIDE RANGE - CAN  trade : LOW : { rangeLow} - HI: {rangeHigh} = {rangeHigh - rangeLow}   PRICE : {ticker_row[closePos]}  MEAN : {rangeMean}   MEDIAN: {rangeMedian}")
            
            
            
            if  self.Stocks[ symbol ]['Indicators'].ADX.shape[0] > 3 : 
                ticker_row.append( self.Stocks[ symbol ]['Indicators'].ADX.iloc[ -1 ]['ADX']  ) # ticker_row[ len( ticker_row ) - 1] = self.Stocks[ symbol ]['Indicators'].ADX.iloc[ -1 ]['ADX']             else:
                ticker_row.append( 0 )  # ADX PLACE HOLDER
            ticker_row.append( self.Stocks[ symbol ]['Indicators'].RSI )
            ticker_row.append( self.Stocks[ symbol ]['Indicators'].ChopIndex ) 
            print( ticker_row )

            
            # NO BUYING AFTER 3:45
            current_time    = datetime.now()
            if not ( symbol in self.Stocks.keys() )  and ( current_time.hour == 15 and current_time.minute >= 45) :
                print(f"\t\t\t -> DayTradeStrategy:: DayTradeBasic () -> TOO LATE TO CONSIDER MAKING BIDS " )
                return False, action, params["time_interval"]

            # ADD MECHANISM FOR DETERMINING THE AVG NUMBER OF MOVES BEFORE PIVOTING AND THE AVG $ MOVES  BEFORE PIVOTING
         
            # ADD STOCK ENTRY IF NOT INPLAY /  THIS SHOULD MAINLY BE DONE IN SETORB (), BUT INCASE SOME GET ADDED ALONG THE WAY             
            if not ( symbol in self.Stocks.keys() ) :
                print("SIMPLE - doing the PrimeEntry")
                ticker_df       = account.History( symbol=ticker_row[0], time_range=1)   
                self.Stocks[symbol] = self.PrimeStockEntry( symbol=ticker_row[0] , ticker_df=ticker_df,ticker_row=ticker_row , current_time=current_time,
                                                            account=account, closePos = closePos , highPos=highPos , volumePos=volumePos)
            
            is_dogee                = ((ticker_row[closePos]-ticker_row[openPos]) <= 0.03)
            candle_body             = (ticker_row[closePos] - ticker_row[openPos])
            candle_body1            = ( self.Stocks[symbol]['Previous'][closePos] - self.Stocks[symbol]['Previous'][openPos] )
            candle_body2            = ( self.Stocks[symbol]['Previous1'][closePos] - self.Stocks[symbol]['Previous1'][openPos] )
            candle_body3            = ( self.Stocks[symbol]['Previous2'][closePos] - self.Stocks[symbol]['Previous2'][openPos] )
            candle_body4            = ( self.Stocks[symbol]['Previous3'][closePos] - self.Stocks[symbol]['Previous3'][openPos] )
            candle_body5            = ( self.Stocks[symbol]['Previous4'][closePos] - self.Stocks[symbol]['Previous4'][openPos] )
            candle_is_big_enough    = ((ticker_row[closePos] - ticker_row[openPos])  >= 0.30)           
            morning_rsi             = ( ticker_row[1][11:13] < '11' and  100 > self.Stocks[ symbol ]['Indicators'].RSI  ) 
            afternoon_rsi           = ( ticker_row[1][11:13] >= '11' and  60 > self.Stocks[ symbol ]['Indicators'].RSI >= 10 )    
            morning_bollinger       = ( (  ticker_row[1][11:13] < '11' )  and  math.isnan(self.Stocks[ symbol ]['Indicators'].BB_Upper ) )
            afternoon_bollinger     = ( ( ticker_row[1][11:13] >= '11' )  and
                                        ( ( self.Stocks[ symbol ]['Indicators'].BB_Upper - ticker_row[closePos]) > 0.11  or
                                            (self.Stocks[ symbol ]['Indicators'].BB_Upper - ticker_row[closePos]) < -0.40 ) )             
            
            upward_pressure        =  round( ticker_row[highPos]  - ticker_row[closePos], 3)
            downward_pressure      =  round( ticker_row[openPos] - ticker_row[lowPos] , 3)

            # ATTEMPT TO MAKE A BETTER CHOP INDEX 
            groups =  [[candle_body5,candle_body4], [candle_body3,candle_body2]]
            pattern = ""
            for group in groups:
                p = 0
                for candle in group:
                    if candle < 0 :
                        p -= 1
                    else:
                        p += 1
                pattern += f"{p},"
            print( f"PATTERN : {pattern} CANDLES : {candle_body5} , {candle_body4}, {candle_body3},{candle_body2} ")

            # IF RSI DROPS BY 17 POINTS TREND IS OVER 
            
            volume_increase        =  (  (float( ticker_row[ volumePos]) - float(self.Stocks[ symbol]['Previous'][volumePos] ) ) / float(self.Stocks[ symbol]['Previous'][volumePos] )  if self.Stocks[ symbol]['Previous'][volumePos] > 0 else 0 )
            still_trading_time     = (( ticker_row[1][11:13] == '15' and ticker_row[1][14:16] < '45') or ( ticker_row[1][11:13] < '15' ) ) 
            impulsiveCandles       = ( self.Stocks[ symbol ]['Indicators'].ChopIndex < 70  and ( 71 > self.Stocks[ symbol ]['Indicators'].RSI >= 10 ) and   # CHANGED RSI from 10 -> 20 and 72 ->71
                                        (   candle_body2 >= 0.11 and candle_body > 0.75*candle_body1  and   candle_body1 > 0.75*candle_body2    ) and                  #   candle_body2  >= 0.12  and  candle_body3 >= 0.12) and                              <- IMPULSIVE NEED ONLY TWO CANDLES TO CONFIRM
                                  #         ( round(self.Stocks[ symbol]['Previous1'][highPos],2) > round(self.Stocks[ symbol]['Previous2'][highPos],2) and round(self.Stocks[ symbol]['Previous'][highPos],2) > ticker_row[highPos] ) and
                                   #    (ticker_row[adxPos] >= 35) and
                                                  (
                                                      ( ticker_row[closePos ] >= self.Stocks[ symbol ]['Previous'][closePos]  )  or
                                                        (ticker_row[highPos] >= self.Stocks[ symbol ]['Previous'][highPos] >= self.Stocks[ symbol ]['Previous1'][highPos] )
                                                ) #and
                                           #(pattern != "0,0," and pattern != "0,-2,")
                                       )
                                           #AVERAGE THE LAST 2 candles and see if the 3rd is 1.5X or less than 0.75
            floaterCandles         = (
                                        is_dogee and  upward_pressure < candle_body  and 
                                        self.Stocks[ symbol ]['Indicators'].ChopIndex < 70  and ( 82 > self.Stocks[ symbol ]['Indicators'].RSI >= 10 ) and   # RSI  72 -> 82
                                        (    candle_body >= candle_body1  ) and # candle_body1 >= candle_body2     and
                                        ( ticker_row[closePos ] >= self.Stocks[ symbol ]['Previous'][closePos]  )   and  ( self.Stocks[ symbol ]['Previous'][closePos] >= self.Stocks[ symbol ]['Previous1'][closePos]  )                 
                                     )
            candle_size_compare    = (
                                            (ticker_row[closePos] - ticker_row[openPos] ) >= ( self.Stocks[ symbol ]['Previous'][closePos] - self.Stocks[ symbol ]['Previous'][openPos] ) and
                                                ticker_row[closePos] -  self.Stocks[ symbol ]['Previous'][closePos]  >= 0.05
                                        )
            basicCriteria           = ( ( round(ticker_row[closePos], 2)  > round(float(self.Stocks[ symbol]['Previous'][closePos]),2) > round(float(self.Stocks[ symbol]['Previous1'][closePos]),2) ) and
                                        ( ticker_row[volumePos] >= int(params['volume_threshold'])  and   volume_increase  >= params["volume_change_avg_ratio"]  ) and
                                        ( round(ticker_row[closePos], 2 ) >=  round(ticker_row[openPos],2 ) ) and
                                        ( self.Stocks[symbol]['Price']['Upward']  >= params["bounce_up_min"]  ) and
                                        ( upward_pressure > downward_pressure  )  and 
                                        (  (round(ticker_row[ closePos],2) -  round(self.Stocks[ symbol]['Previous'][closePos],2) >= params["price_move_change"] )  and 
                                                   ( ticker_row[volumePos]  /  self.Stocks[ symbol]['Previous'][volumePos] ) > params["volume_change_ratio"]) )
                                                    
            peiCriteria             = ( ( candle_body >= 0.75* candle_body1  and not is_dogee ) and
                                        ( morning_rsi or afternoon_rsi )   and self.Stocks[ symbol ]['Indicators'].ChopIndex < 63  and ( morning_bollinger or afternoon_bollinger)  and
                                        (   
                                            (  ticker_row[volumePos] >=  0.75 * self.Stocks[ symbol]['Previous'][volumePos] ) and  self.Stocks[ symbol ]['Indicators'].ADX.iloc[ -1 ]['ADX']  > 30 and 
                                            (  self.Stocks[ symbol]['Previous'][volumePos] >=  0.75 * self.Stocks[ symbol]['Previous1'][volumePos] )
                                            
                                        ) and
                                        (
                                           round(ticker_row[closePos],2)   >  round( self.Stocks[symbol]['Previous'][highPos] - 0.05,2)    and # <- was 0.10
                                          self.Stocks[ symbol]['Previous'][closePos]  > self.Stocks[ symbol]['Previous1'][highPos]  and
                                          self.Stocks[ symbol]['Previous1'][closePos]  > self.Stocks[ symbol]['Previous2'][highPos]  
                                        ) and
                                        (
                                            ticker_row[closePos] - ticker_row[openPos]  >= 0.05 and
                                            self.Stocks[ symbol]['Previous'][closePos] - self.Stocks[ symbol]['Previous'][openPos] >= 0.05 and
                                            self.Stocks[ symbol]['Previous1'][closePos] - self.Stocks[ symbol]['Previous1'][openPos] >= 0.05
                                        )
                                     )
            
            """
                add to peiCriteria or make a new one
                ( self.Stocks[ symbol]['Price']['Upward']  > 3  and  not is_dogee and ( morning_bollinger or afternoon_bollinger)  and
                          candle_size_compare and     self.Stocks[ symbol ]['Indicators'].ChopIndex < 63   and ticker_row[closePos] > self.Stocks[ symbol ]['Previous'][closePos] and
                           25 >= ticker_row[adxPos] >= self.Stocks[symbol]['Previous'][adxPos] and 
                                ( morning_rsi or afternoon_rsi or candle_body >= 0.40)   and
                                     ( ticker_row[volumePos] > (0.60 * self.Stocks[symbol]['Previous'][volumePos])   )): #0.9*(self.Stocks[ symbol]['AvgOccurrVol']/(self.Stocks[ symbol]['Price']['Upward'] - 1)) ): # SAN PEI AND CHOPINDEX < 60 and volume


                (not candle_is_big_enough or  ticker_row[closePos]-ticker_row[openPos] < -0.20)  or
                                                 (
                                                     (  ticker_row[volumePos] <  0.75 * self.Stocks[ symbol]['Previous'][volumePos] ) and
                                                    (  self.Stocks[ symbol]['Previous'][volumePos] <  0.75 * self.Stocks[ symbol]['Previous1'][volumePos] )
                                                  ) or 
                                              (  ticker_row[volumePos] <  0.5 *  self.Stocks[ symbol]['Previous'][volumePos])
            """
            
            # ARE WE TRENDING UP            
            if self.Stocks[ symbol]['Price']['Bought'] == 0:  # MEANS NO OPTION POSITIONS
                self.Stocks[ symbol ]['Price']['HighSinceBought'] = 0
               
                
                #print( f"{symbol} - INDICATOR : CHOP: {self.Stocks[ symbol ]['Indicators'].ChopIndex}   RSI: {self.Stocks[ symbol ]['Indicators'].RSI} ")
                candleDrift = False
                """(( 60 > self.Stocks[ symbol ]['Indicators'].RSI >= 10 ) and
                                           self.Stocks[ symbol ]['Indicators'].ChopIndex < 56  and
                                   ( ticker_row[closePos ] > self.Stocks[ symbol ]['Previous'][closePos]  > self.Stocks[ symbol ]['Previous1'][closePos] >self.Stocks[ symbol ]['Previous2'][closePos] ) )
                """
                #NOT ALLOWED TO GO IN ON A DOGEE - MAY NEED SPECIAL RULES FOR BIG IMPULSIVE MOVES
                print(f"CANDLES : {  candle_body} >= 0.12  -> " +
                          f"  {  candle_body1} >= 0.12  ->  {  candle_body2} >= 0.12  -> {  candle_body3} >= 0.12  -> " +
                           f" CHOP :  {self.Stocks[ symbol ]['Indicators'].ChopIndex} RSI :  {self.Stocks[ symbol ]['Indicators'].RSI}  DOGEE: {is_dogee}  ")#ADX: {ticker_row[adxPos]}"
                print(f"FLOATER: [DOGEE]{is_dogee}   UP WICK vs Candle:{ upward_pressure} < {candle_body}  CHOP: {self.Stocks[ symbol ]['Indicators'].ChopIndex} < 70    RSI:( 82 > {self.Stocks[ symbol ]['Indicators'].RSI} >= 10 )  " +
                      f"\n\t  CANDLES: {candle_body} >= {candle_body1}   and {candle_body1} >= {candle_body2} and  PRICE: [NEW] {ticker_row[closePos ]} >= {self.Stocks[ symbol ]['Previous'][closePos] } " )

                if  ( impulsiveCandles or floaterCandles or 
                             peiCriteria or
                                  basicCriteria ) :
                    if basicCriteria:
                        if volume_increase  < params["volume_change_avg_ratio"] : # 85% starts to see good results, but dont want to be too strict or too loose 
                            print( f"\t\t\t  *  BUY:: Volume increase isnt enough : {ticker_row[ volumePos ]}  from {self.Stocks[ symbol]['Volume']['Previous'] } ==> {volume_increase}    ***   RETURNING  ***" )
                            # THIS SHOULD BE A SUB FUNCTION
                            self.ResetStock( symbol =symbol ,stockClose= ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )
                            return False, action, time_interval, account
            
                        if ( round(ticker_row[closePos], 2 ) <  round(ticker_row[openPos],2 )  and round(ticker_row[closePos],2) == round(ticker_row[highPos],2)) :  #  PRICE CLOSED LOWER THAN IT OPENED with upward pressure
                            print( f"\t\t\t  *  BUY:: PRICE CLOSED LOWER THAN IT OPENED WITH NO UPWARD PRESSURE  : CLOSED={ round(ticker_row[ closePos ],5)}  " +
                                           f"OPENED={ round(ticker_row[openPos], 5) }   LOW={ round(ticker_row[lowPos],5) }  HIGH={ round(ticker_row[highPos],5) }      ***   RETURNING  ***" )                    
                            self.ResetStock( symbol =symbol , stockClose= ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )                    
                            return False, action, time_interval ,account           
                
                        if self.Stocks[symbol]['Price']['Upward']  < params["bounce_up_min"] :  # TWO consecutive upward moves with appropriate volume 
                            print( f"\t\t\t  *  BUY [TEST SIGNAL ]:: Consecutive upward moves with volumes : {self.Stocks[ symbol]['Price']['Upward']}     ***   RETURNING  ***" )
                            self.ResetStock( symbol =symbol , stockClose= ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )
                            return False, action, time_interval, account
                    reason = "UNKNOWN"
                    if impulsiveCandles:
                        reason = "IMPULSIVE" 
                    elif peiCriteria :
                        reason = "PEI" 
                    elif floaterCandles :
                        reason = "FLOATER" 
                    elif basicCriteria :
                        reason = "BASIC" 
                        
                    print( f"\t\t\t  BUY TRIGGERED - {reason} CRITERIA *  BUY:: Volume increase OKAY : {ticker_row[ volumePos ]} " +
                           f"\n\t\t\t\t   FROM newPrice - previous = ${round( round(float(ticker_row[ closePos ]),5) -  round(float(self.Stocks[ symbol]['Price']['Previous']), 5) , 5) } " +
                           f"\n\t\t\t\t   Volume :  from { round( self.Stocks[ symbol]['Volume']['Previous'] , 5)  } ==> { round(volume_increase, 5 ) } " +
                           f"\n\t\t\t\t   PRESSURE :  upward : { round(upward_pressure,5)} ==>  downward :{ round(downward_pressure,5)} " +
                           f"\n\t\t\t\t   OCCUR : {self.Stocks[symbol]['Price']['Upward'] }  -> {params['bounce_up_min'] } " +
                           f"\n\t\t\t\t   BODY vs WICK : {round( (ticker_row[closePos] - ticker_row[openPos]) ,5 ) } --> { round( (ticker_row[highPos] - ticker_row[closePos]) , 5 )}   PATTERN: {pattern}  RANGE: [BAND] {rangeBand} -> [MEAN]{rangeMean}->[MEDIAN]{rangeMedian}")#  ADX: {ticker_row[adxPos]}"    )                            

                    # 2025-10-21  Playing around to get best results 
                    if ( still_trading_time  and   # DONT OPEN TRADES TOO LATE IN THE DAY
                          (  (rangeBand <= 0.50 and ticker_row[closePos] >= rangeMean) or rangeBand > 0.50 ) and 
                                account.Buy( stock=symbol , price=float(ticker_row[ closePos ])  ,
                                 current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ) ,
                                    volume = ticker_row[volumePos], volume_threshold = params['volume_threshold'], indicators=self.Stocks[symbol]['Indicators']) ) :
                        print(f"{symbol} - BOUGHT @ : UPWARD:{self.Stocks[ symbol]['Price']['Upward']} -> CHOP: {self.Stocks[ symbol ]['Indicators'].ChopIndex}  RSI :  {self.Stocks[ symbol ]['Indicators'].RSI}   PRICE: {ticker_row[closePos]} ADX: { self.Stocks[ symbol ]['Indicators'].ADX.iloc[ -1 ]['ADX']}")
                        success     = True                                               
                        action      = "bought"
                        self.ResetStock( symbol =symbol , stockClose=ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )                    
                        self.Stocks[ symbol ]['Price' ]['Bought']   =  ticker_row[ closePos ]                            
                        self.Stocks[ symbol ]['Price' ]['Previous'] =  ticker_row[ closePos ]
                        self.Stocks[ symbol ]['Volume']['Bought']   =  ticker_row[volumePos]
                        self.Stocks[ symbol]['Price']['Upward']     =  0
                        self.Stocks[ symbol]['AvgOccurrVol']        =  0
                    else:
                        print(f"{symbol} - BUY NOT Triggered : PAST BUYING TIME or RangeBand : {rangeLow} -> {rangeHigh} = {rangeBand}   PRICE :{ticker_row[closePos]}")
            

            rsiFlipSell         = ( self.Stocks[ symbol ]['Indicators'].RSI > 70  and candle_body < 0.30  and ticker_row[closePos] <= (self.Stocks[symbol]['Previous'][closePos] - 0.16) )
            trailStopSell       = (ticker_row[closePos] < ( self.Stocks[symbol]['Price']['Bought'] - 0.16 ) )
            impulsiveCandleSell = ( self.Stocks[ symbol ]['Indicators'].RSI > 80  and candle_body > 0.30  and ticker_row[closePos] <= (self.Stocks[symbol]['Previous'][closePos] - 0.16) )
            pressureImbalanceSell   = 0#downward_pressure/( upward_pressure if downward_pressure >0 else 1 )
            
            #CONSIDER SELLING   -  spike up in volume ( 2x)  and price 
            if  action != 'bought' and self.Stocks[ symbol]['Price']['Bought'] > 0:  # INSIDE OF A POSITION
                    
                print(f"INSIDE A POSITION:   BOUGHT:{self.Stocks[symbol]['Price']['Bought']} ->{ticker_row[closePos]} --> [PREVIOUS]{self.Stocks[symbol]['Previous'][closePos]} [PREVIOUS1]{self.Stocks[symbol]['Previous1'][closePos]} " +
                      f"PROFIT : {( ticker_row[closePos]  - self.Stocks[symbol]['Price']['Bought']) }    CHOP: {self.Stocks[ symbol ]['Indicators'].ChopIndex} " +
                      f"RSI: {self.Stocks[ symbol ]['Indicators'].RSI}   ADX: { self.Stocks[ symbol ]['Indicators'].ADX.iloc[ -1 ]['ADX']}" +
                      f" BB :  {self.Stocks[ symbol ]['Indicators'].BB_Lower} -> {self.Stocks[ symbol ]['Indicators'].BB_Upper}   PRESSURE: UPPER:{pressureImbalanceSell} ==> {upward_pressure} -> {downward_pressure} " +
                      f" HIGH SINCE BOUGHT: {self.Stocks[ symbol ]['Price']['HighSinceBought']} ->{((self.Stocks[ symbol ]['Price']['HighSinceBought'] - self.Stocks[symbol]['Price']['Bought']) /3 )}" )#  ATR : {self.Stocks[ symbol ]['Indicators'].AvgTrueRange()} ")

                highSinceBoughtTrailStop = ((self.Stocks[ symbol ]['Price']['HighSinceBought'] - self.Stocks[symbol]['Price']['Bought']) /2 )
                #(self.Stocks[ symbol ]['Price']['HighSinceBought'] - () #(self.Stocks[ symbol ]['Price']['HighSinceBought'] - 0.15) # (self.Stocks[ symbol ]['Price']['HighSinceBought'] - ((self.Stocks[ symbol ]['Price']['HighSinceBought'] - self.Stocks[symbol]['Price']['Bought']) /2 ))
                if highSinceBoughtTrailStop <  0.10 : 
                    highSinceBoughtTrailStop = self.Stocks[ symbol ]['Price']['HighSinceBought'] - 0.16
                elif highSinceBoughtTrailStop > 0.40 :
                    highSinceBoughtTrailStop = self.Stocks[ symbol ]['Price']['HighSinceBought'] - 0.40
                else:
                     highSinceBoughtTrailStop = self.Stocks[ symbol ]['Price']['HighSinceBought'] - highSinceBoughtTrailStop 
                """
                if ( ( ticker_row[closePos] < (self.Stocks[symbol]['Previous'][closePos] - 0.16) ) or
                         self.Stocks[ symbol ]['Indicators'].ChopIndex > 70  or
                         ( self.Stocks[ symbol ]['Indicators'].RSI > 70  and candle_body < 0.40) or 
                      ( ( ticker_row[closePos] < self.Stocks[symbol]['Previous'][closePos] )  and ( self.Stocks[symbol]['Previous1'][closePos] < self.Stocks[symbol]['Previous1'][closePos] )  ) or
                        (ticker_row[closePos] < ( self.Stocks[symbol]['Price']['Bought'] - 0.16 ) ) or
                         #(ticker_row[closePos] < (self.Stocks[symbol]['Price']['HighSinceBought'] - 0.15))  or
                       ( (ticker_row[volumePos] < 0.80 * self.Stocks[symbol]['Previous'][volumePos] )  and (self.Stocks[symbol]['Previous'][volumePos] < self.Stocks[symbol]['Previous1'][volumePos] ) ) or  
                         ((ticker_row[volumePos] < 0.80 * self.Stocks[symbol]['Previous'][volumePos] )  and  (  0.05 < ( ticker_row[closePos]  - self.Stocks[symbol]['Price']['Bought']   )  ) ) or          # $0.07 take profit                          
                              (  0.12 < (self.Stocks[symbol]['Price']['Bought'] - ticker_row[closePos]  )  )       ) :   #AS SOON AS PRICE DIPS -> SELL
                """
                if (  ( impulsiveCandles and impulsiveCandleSell) or
                      ( not impulsiveCandles and
                        (
                          rsiFlipSell or 
                            ( ticker_row[closePos] < (self.Stocks[symbol]['Previous'][closePos] - 0.15) ) or # this might be obsolete and duplication                
                            ( ticker_row[closePos] < highSinceBoughtTrailStop ) or  (self.Stocks[symbol]['Previous'][closePos] - ticker_row[closePos] > 0.35 ) or (ticker_row[closePos] - self.Stocks[symbol]['Previous'][closePos]  > 0.45 ) or #BIG MOVES ARENT SUSTAINABLE
                             self.Stocks[ symbol ]['Indicators'].ChopIndex > 70 or                    
                            ( ( ticker_row[closePos] < self.Stocks[symbol]['Previous'][closePos] )  and ( self.Stocks[symbol]['Previous1'][closePos] < self.Stocks[symbol]['Previous1'][closePos] )  ) or
                     #   pressureImbalanceSell >= 20 or 
                            trailStopSell or
                            ticker_row[adxPos] < 30 and  # SOMETHING ABOUT THIS WITH THE VOLUMEPOS TO ELIMINATE THE -4 PROFIT ; MAYBE SHIFT FROM 0.80 -> 0.65 ???
                           ( (ticker_row[volumePos] < 0.80 * self.Stocks[symbol]['Previous'][volumePos] )  ) and (self.Stocks[symbol]['Previous'][volumePos] < self.Stocks[symbol]['Previous1'][volumePos] )  or  
                         #((ticker_row[volumePos] < 0.80 * self.Stocks[symbol]['Previous'][volumePos] )  and  (  0.05 < ( ticker_row[closePos]  - self.Stocks[symbol]['Price']['Bought']   )  ) ) or          # $0.07 take profit                          
                              (  0.12 < (self.Stocks[symbol]['Price']['Bought'] - ticker_row[closePos]  )  )
                          )
                        )
                    ):   #AS SOON AS PRICE DIPS -> SELL
                      print( f"TIME TO SELL PRICE: {ticker_row[closePos]} -> {(self.Stocks[symbol]['Previous'][closePos] - 0.16)} or {( self.Stocks[symbol]['Price']['Bought'] - 0.16 )  } or { (self.Stocks[symbol]['Price']['HighSinceBought'] - 0.16)} or SLIDING  : {highSinceBoughtTrailStop} "+
                             f" VOLUME: {ticker_row[volumePos]} -> { 0.80 * self.Stocks[symbol]['Previous'][volumePos] }  " +
                              f"VOLATILTIY: {self.Stocks[ symbol ]['Indicators'].Summary()['VolIndex'] }  dSMA : {self.Stocks[ symbol ]['Indicators'].Summary()['dSMA']}  " +
                             f" HARDCODE PRICE : { ticker_row[closePos]  - self.Stocks[symbol]['Price']['Bought'] } or {self.Stocks[symbol]['Price']['Bought'] - ticker_row[closePos]  } "+
                             f" CHOP :{self.Stocks[ symbol ]['Indicators'].ChopIndex}  RSI:{self.Stocks[ symbol ]['Indicators'].RSI}  CANDLE BODY: {candle_body}  ")
                      
                      if ( impulsiveCandles and impulsiveCandleSell):
                          print (f"->SELL - IMPULSIVE CANDLE; RSI : {self.Stocks[ symbol ]['Indicators'].RSI} > 80  and CANDLE : {candle_body} > 0.30  and CLOSE: {ticker_row[closePos]} <= {(self.Stocks[symbol]['Previous'][closePos] - 0.16)}" )
                      elif self.Stocks[ symbol ]['Indicators'].ChopIndex > 70 :
                          print (f"->SELL - CHOP INDEX:  {self.Stocks[ symbol ]['Indicators'].ChopIndex} > 70  RSI : {self.Stocks[ symbol ]['Indicators'].RSI} > 80  and CANDLE : {candle_body} > 0.30  and CLOSE: {ticker_row[closePos]} <= {(self.Stocks[symbol]['Previous'][closePos] - 0.16)}" )
                      elif rsiFlipSell:
                          print (f"->SELL - RSI FLIP CANDLE;  RSI : {self.Stocks[ symbol ]['Indicators'].RSI} > 80  and CANDLE : {candle_body} > 0.30  and CLOSE: {ticker_row[closePos]} <= {(self.Stocks[symbol]['Previous'][closePos] - 0.16)}" )
                      elif pressureImbalanceSell:
                          print (f"->SELL - PressureImbalance :  RSI : {self.Stocks[ symbol ]['Indicators'].RSI} > 80  and CANDLE : {candle_body} > 0.30  and CLOSE: {ticker_row[closePos]} <= {(self.Stocks[symbol]['Previous'][closePos] - 0.16)}  PRESSURE: {pressureImbalanceSell} ==> {upward_pressure} -> {downward_pressure}" )
                      elif trailStopSell:
                          print(f"->SELL - TRAIL STOP : CLOSE : {ticker_row[closePos]} <  {( self.Stocks[symbol]['Price']['Bought'] - 0.16 )}  ")
                      elif ticker_row[ adxPos] < 35:
                          print(f"->SELL - ADX <35 : CLOSE : {ticker_row[closePos]} <  {( self.Stocks[symbol]['Price']['Bought'] - 0.16 )}   ADX : { ticker_row[adxPos]} ")
                      elif (ticker_row[volumePos] < 0.80 * self.Stocks[symbol]['Previous'][volumePos] ) and (self.Stocks[symbol]['Previous'][volumePos] < self.Stocks[symbol]['Previous1'][volumePos] ) :
                          print(f"->SELL - VOLUME DROP : CLOSE : {ticker_row[volumePos]} <  { 0.80 * self.Stocks[symbol]['Previous'][volumePos]}   ADX : { ticker_row[adxPos]} ")
                      elif  ( ( ticker_row[closePos] < self.Stocks[symbol]['Previous'][closePos] )  and ( self.Stocks[symbol]['Previous1'][closePos] < self.Stocks[symbol]['Previous1'][closePos] )  ):
                          print(f"->SELL - PRICE DROP: CLOSE : {ticker_row[closePos]} < {self.Stocks[symbol]['Previous'][closePos]} ->  { self.Stocks[symbol]['Previous1'][closePos]} < {self.Stocks[symbol]['Previous1'][closePos]} ")
                      elif  highSinceBoughtTrailStop :
                          print(f"->SELL - BELOW HIGH-SINCE-BOUGHT: CLOSE : {ticker_row[closePos]}  HIGH/BOUGHT {self.Stocks[ symbol ]['Price']['HighSinceBought']} ->  {highSinceBoughtTrailStop} ")
                      elif  (  0.12 < (self.Stocks[symbol]['Price']['Bought'] - ticker_row[closePos]  )  )  :
                          print(f"->SELL - BELOW  BOUGHT: CLOSE : {ticker_row[closePos]} BOUGHT {self.Stocks[symbol]['Price']['Bought']} ->  {(self.Stocks[symbol]['Price']['Bought'] - ticker_row[closePos]  )} ")
                      

                      
                      if  account.Sell( stock=symbol, new_price=float(ticker_row[ closePos ]) ,
                                           current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ),
                                       ask_volume=float(ticker_row[ volumePos ] ), indicators=self.Stocks[symbol]['Indicators'] )  :
                         success        = True
                         action         = "closed"
                         if self.Stocks[ symbol ]['Price' ]['Bought']  > ticker_row[closePos]:
                             self.Stocks[symbol]['Losses']    += 1
                             
                         self.Stocks[ symbol ]['Price' ]['Bought'] = 0
                         self.Stocks[ symbol ]['Price' ]['High']   = 0
                         self.Stocks[ symbol ]['Volume']['Bought'] = 0
                         self.Stocks[ symbol ]['Price']['HighSinceBought'] = 0
                         

                         for trade in account.Trades[symbol]:
                             #print(f"\t\t\t   Indicators [IN ] : {trade['indicators_in']}  [OUT] {trade['indicators_out']}  ")
                             print(f"\t\t\t   TIME: {trade['bidTime']}  P&L: {trade['p_l']} ")

            #CLEAN UP            
            # UPDATE THE STOCK INFO WITH THE CURRENT PRICE / VOLUME
            self.ResetStock( symbol =symbol , stockClose= ticker_row[ closePos]  , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )  # other calls to RESETSTOCK in this method is redundant 
            self.Stocks[ symbol ]['Previous4']         =  self.Stocks[ symbol ]['Previous3']
            self.Stocks[ symbol ]['Previous3']         =  self.Stocks[ symbol ]['Previous2']
            self.Stocks[ symbol ]['Previous2']         =  self.Stocks[ symbol ]['Previous1']
            self.Stocks[ symbol ]['Previous1']         =  self.Stocks[ symbol ]['Previous']
            self.Stocks[ symbol ]['Previous']          =  ticker_row
            
            # CHANGE TO 5 MINUTE INFO TO JUMP IN AND OUT MOREL ACCURATELY
            if float(self.Stocks[ symbol]['Price']['Bought']) > 0 :
                time_interval   =  params['time_interval_bought']  # DROP FROM 5 -> 1 or 3 inside of position 
            else:
                if action =='closed' :
                    print(f"Taking a breathe   LOSSES : {self.Stocks[ symbol ]['Losses']}")
                    self.Stocks[ symbol ]['Price']['HighSinceBought'] = 0
               #     time.sleep(params['time_interval'] ) # After closing a position , take a pause 
                    
                time_interval   = params['time_interval']
                
        except: 
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )


        return success , action, time_interval , account
    

    
    def DayTradeSimpleModule1 ( self, ticker_row : list, account : object, params : dict  ) -> (bool, str,int, TradeAccount) :  #USE AS COMPARISON CODE 
        """
            Look for three candles that are update , with the second's body equal or greater than 1st wick, and the 3rd body equal or greater than second ,
            while the ChopIndex < 60
            
            ARGS  :
                        ticker_row        ( list ) information about the stock and current price and volume
                        account           ( TradeAccount )  the trading account for BUYS and SELLS
                        volume_threshold  ( int )  the lower limit for volume activity to engage in buy/sell ( may not be important after all )
                        params            ( dicts ) parameters to customize the run 
            RETURNS    :
                        bool: True/False - in case something breaks or could not complete                         
        """
        limit               = params['limit']        # DO NOT EXCEED 10% OF THE ACCOUNT.FUNDS ON ANY ONE PURCHASE
        profit              = 0
        action              = ""
        success             = False
        symbol              = ticker_row[0]
        lowPos              = params['lowPos']
        timePos             = params['timePos']
        openPos             = params['openPos']
        highPos             = params['highPos']
        closePos            = params['closePos']
        volumePos           = params['volumePos']
        risk_percent        = params['risk_percent']
        time_interval       = params['time_interval']
        crash_out_percent   = params['crash_out_percent']      # IF PRICE IS FALLING FAST, DONT SELL IF BELOW THIS PERCENT OF THE PURCHASE, TAKE RISK AND WAIT FOR REBOUND 
        max_num_of_losses   = params["numOfLosses"]

        try:            
            # NO BUYING AFTER 3:45
            current_time    = datetime.now()
            if not ( symbol in self.Stocks.keys() )  and ( current_time.hour == 15 and current_time.minute >= 45) :
                print(f"\t\t\t -> DayTradeStrategy:: DayTradeBasic () -> TOO LATE TO CONSIDER MAKING BIDS " )
                return False, action, params["time_interval"],account

            # ADD MECHANISM FOR DETERMINING THE AVG NUMBER OF MOVES BEFORE PIVOTING AND THE AVG $ MOVES  BEFORE PIVOTING
         
            # ADD STOCK ENTRY IF NOT INPLAY /  THIS SHOULD MAINLY BE DONE IN SETORB (), BUT INCASE SOME GET ADDED ALONG THE WAY             
            if not ( symbol in self.Stocks.keys() ) :
                print("SIMPLE - doing the PrimeEntry")
                ticker_df       = account.History( symbol=ticker_row[0], time_range=1)   
                self.Stocks[symbol] = self.PrimeStockEntry( symbol=ticker_row[0] , ticker_df=ticker_df,ticker_row=ticker_row , current_time=current_time,
                                                            account=account, closePos = closePos , highPos=highPos , volumePos=volumePos)
            
            is_dogee               = ((ticker_row[closePos]-ticker_row[openPos]) <= 0.05)  
            candle_body            = (ticker_row[closePos] - ticker_row[openPos]) 
            candle_is_big_enough   = ((ticker_row[closePos] - ticker_row[openPos])  >= 0.20)
            previous_candle_body   = ( self.Stocks[symbol]['Previous'][closePos] - self.Stocks[symbol]['Previous'][openPos] ) 
            # ARE WE TRENDING UP            
            if self.Stocks[ symbol]['Price']['Bought'] == 0:  # MEANS NO OPTION POSITIONS
                if ( (round(ticker_row[closePos],2) < round(self.Stocks[symbol]['Previous'][closePos] - 0.10,2)  and self.Stocks[ symbol]['Price']['Upward'] > 0) or ( self.Stocks[ symbol]['Price']['Upward'] >= 5) ):
                    self.Stocks[ symbol]['Price']['Upward']     = 1
                    self.Stocks[ symbol]['AvgOccurrVol']        = ticker_row[volumePos]
                    print(f"\t\t\t\t\t{symbol} - PRICE DIPPED - RESET SOLDIERS :: {ticker_row[closePos]} -> { self.Stocks[symbol]['Previous'][closePos] - 0.10 } OR {self.Stocks[ symbol]['Price']['Upward']}")                  
                elif round(ticker_row[closePos],2) >= round(self.Stocks[symbol]['Previous'][closePos] - 0.5,2)  or candle_is_big_enough: #only look at $0.20+ candles
                    self.Stocks[ symbol]['Price']['Upward']  += 1
                    self.Stocks[ symbol]['AvgOccurrVol']     += ticker_row[volumePos]
                    if  self.Stocks[ symbol]['Price']['Upward']  == 1 :
                        print(f"\t\t\t\t\t{symbol} - SIMPLE : FIRST SOLDIER ")                        

                    #OBSOLETE     
                    if self.Stocks[ symbol]['Price']['Upward']  == 2 : #RESHIFT THE SIGNAL CANDLE 
                        if (round(ticker_row[closePos],2) < round(self.Stocks[symbol]['Previous'][highPos] - 0.10,2) ) and (not candle_is_big_enough or is_dogee):
                            self.Stocks[ symbol]['Price']['Upward']  -= 1
                            self.Stocks[ symbol]['AvgOccurrVol'] -= ( self.Stocks[ symbol]['AvgOccurrVol'] - ticker_row[volumePos] )
                            print(f"\t\t\t\t\t{symbol} - DAYTRADESIMPLE::Second Soldier Failed  Candle Body : { candle_body} == {ticker_row[closePos] - ticker_row[openPos]}  {candle_is_big_enough}")
                        #else:
                        #    print(f"{symbol} - DAYTRADESIMPLE::Second Soldier  ")
                        
                    # MAKE SURE NOT A DOGEE - 1% diff high low 
                    if self.Stocks[ symbol]['Price']['Upward']  > 3 :
                        if (( candle_body < 0.5*( previous_candle_body )  and
                                 round(ticker_row[closePos],2)   <  round( self.Stocks[symbol]['Previous'][highPos] - 0.10,2)   ) and not candle_is_big_enough ) : #or
                                     #ticker_row[closePos]   <  self.Stocks[symbol]['Previous'][closePos]  or  
                                      #   ticker_row[volumePos]   <  (0.75* self.Stocks[symbol]['Previous'][volumePos] )  ) :
                            self.Stocks[ symbol]['Price']['Upward']     = 1
                            self.Stocks[ symbol]['AvgOccurrVol']        = ticker_row[volumePos]
                            print(f"{symbol} - DAYTRADESIMPLE::San Pei failed  CANDLE BODY : {candle_body} -> {0.5*( previous_candle_body ) } Candle Is BIG :{candle_is_big_enough} "+
                                  f"CANDLE WICK : {ticker_row[closePos]}   <  {0.99 *self.Stocks[symbol]['Previous'][highPos]}   VOLUME: {ticker_row[volumePos]} -> {0.75*( self.Stocks[symbol]['Previous'][volumePos] ) }" +
                                  f" CHOP :  {self.Stocks[ symbol ]['Indicators'].ChopIndex} RSI :  {self.Stocks[ symbol ]['Indicators'].RSI} ")
                        #else:
                        #    print(f"{symbol} - DAYTRADESIMPLE::San Pei  ")
                    
                    print( f"{symbol} - INDICATOR : CHOP: {self.Stocks[ symbol ]['Indicators'].ChopIndex}   RSI: {self.Stocks[ symbol ]['Indicators'].RSI} ")

                    #CAN GO IN ON  A DOGEE 
                    if ( self.Stocks[ symbol]['Price']['Upward']  > 3  and
                             self.Stocks[ symbol ]['Indicators'].ChopIndex < 60   and
                                 (( 70 > self.Stocks[ symbol ]['Indicators'].RSI >= 10 ) or candle_body > 0.40 ) and
                                     ( ticker_row[volumePos] > (0.60 * self.Stocks[symbol]['Previous'][volumePos])   )  ) : #0.9*(self.Stocks[ symbol]['AvgOccurrVol']/(self.Stocks[ symbol]['Price']['Upward'] - 1)) ): # SAN PEI AND CHOPINDEX < 60 and volume 
                        print(f"\t\t\t\t\t{symbol} - It took {self.Stocks[ symbol]['Price']['Upward']} soldiers  with ChopIndex : {self.Stocks[ symbol ]['Indicators'].ChopIndex} "+
                              f"VOLATILTIY: {self.Stocks[ symbol ]['Indicators'].Summary()['VolIndex'] }  dSMA : {self.Stocks[ symbol ]['Indicators'].Summary()['dSMA']}  " +
                              f" RSI :  {self.Stocks[ symbol ]['Indicators'].RSI}  BB :  {self.Stocks[ symbol ]['Indicators'].BB_Lower} -> {self.Stocks[ symbol ]['Indicators'].BB_Upper}  to finally break through ")
                        if ( account.Buy( stock=symbol , price=float(ticker_row[ closePos ])  ,
                                 current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ) ,
                                    volume = ticker_row[volumePos], volume_threshold = params['volume_threshold'], indicators=self.Stocks[symbol]['Indicators'])   ) :
                            print(f"{symbol} - BOUGHT @ : UPWARD:{self.Stocks[ symbol]['Price']['Upward']} -> CHOP: {self.Stocks[ symbol ]['Indicators'].ChopIndex} RSI :  {self.Stocks[ symbol ]['Indicators'].RSI}  PRICE: {ticker_row[closePos]}")
                            success     = True                                               
                            action      = "bought"
                            self.ResetStock( symbol =symbol , stockClose=ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )                    
                            self.Stocks[ symbol ]['Price' ]['Bought']   =  ticker_row[ closePos ]                            
                            self.Stocks[ symbol ]['Price' ]['Previous'] =  ticker_row[ closePos ]
                            self.Stocks[ symbol ]['Volume']['Bought']   =  ticker_row[volumePos]
                            self.Stocks[ symbol]['Price']['Upward']     =  0
                            self.Stocks[ symbol]['AvgOccurrVol']        =  0
                    else:
                        if self.Stocks[ symbol]['Price']['Upward']  > 3 :
                            print(f"{symbol} - BUY NOT Triggered : {self.Stocks[ symbol]['Price']['Upward']} -> {self.Stocks[ symbol ]['Indicators'].ChopIndex} " +
                                  f"VOLUME :{ticker_row[volumePos]} -> {0.80 * self.Stocks[symbol]['Previous'][volumePos] } ::" +
                                  f"{self.Stocks[ symbol]['Price']['Upward']} -> {self.Stocks[ symbol]['AvgOccurrVol']}   RSI : {self.Stocks[ symbol ]['Indicators'].RSI}")
                else:
                    self.Stocks[ symbol]['Price']['Upward']  = 1
                    self.Stocks[ symbol]['AvgOccurrVol']     = ticker_row[volumePos]
                    print(f"\t\t\t\t\t{symbol} - PRICE DIPPED - SOLDIERS NULLIFIED  : {self.Stocks[ symbol]['Price']['Upward']} -> {self.Stocks[ symbol ]['Indicators'].ChopIndex} " +
                          f"PRICE : {self.Stocks[ symbol]['Previous'][closePos]} ->{ticker_row[closePos]}  ->{ round( ticker_row[closePos] - self.Stocks[ symbol]['Previous'][closePos] ,5 ) }")
            
            if action != 'bought' and self.Stocks[ symbol]['Price']['Bought'] > 0 :                
                upward_pressure        =  ( round( float(ticker_row[highPos])  - float(ticker_row[closePos]), 3) if round( float(ticker_row[highPos])  - float(ticker_row[closePos]), 3) > 0 else 1 )
                downward_pressure      =  ( round( float( ticker_row[openPos]) - float(ticker_row[lowPos]) , 3)  if round( float( ticker_row[openPos]) - float(ticker_row[lowPos]) , 3) > 0 else 1 )
                #print( f"{symbol} - CURRENT : { round(ticker_row [closePos], 5)}   " +
                #       f"BOUGHT AT : { round(self.Stocks[ symbol]['Price']['Bought'],5)}  " +
                #       f"PREVIOUS AT: {round(self.Stocks[ symbol]['Price']['Previous'] ,5)}  " +
                #       f"OPEN: {round(ticker_row[openPos],5)}   CLOSE :{ round(ticker_row[closePos],5)} " +
                #       f" PRESSURE: {upward_pressure} -> {downward_pressure} %{upward_pressure /downward_pressure}  " )

            
            #CONSIDER SELLING   -  spike up in volume ( 2x)  and price 
            if  action != 'bought' and self.Stocks[ symbol]['Price']['Bought'] > 0:  # INSIDE OF A POSITION
                print(f"INSIDE A POSITION:   BOUGHT:{self.Stocks[symbol]['Price']['Bought']} ->{ticker_row[closePos]} --> [PREVIOUS]{self.Stocks[symbol]['Previous'][closePos]} [PREVIOUS1]{self.Stocks[symbol]['Previous1'][closePos]} " +
                      f"PROFIT : {( ticker_row[closePos]  - self.Stocks[symbol]['Price']['Bought']) }    CHOP: {self.Stocks[ symbol ]['Indicators'].ChopIndex} " +
                      f"RSI: {self.Stocks[ symbol ]['Indicators'].RSI}    CANDLE BODY : {candle_body} " +
                      f" BB :  {self.Stocks[ symbol ]['Indicators'].BB_Lower} -> {self.Stocks[ symbol ]['Indicators'].BB_Upper} ") #  ATR : {self.Stocks[ symbol ]['Indicators'].AvgTrueRange()} ")
                if ( ( ticker_row[closePos] < (self.Stocks[symbol]['Previous'][closePos] - 0.16) ) or
                         self.Stocks[ symbol ]['Indicators'].ChopIndex > 70  or
                         ( self.Stocks[ symbol ]['Indicators'].RSI > 70  and candle_body < 0.40) or 
                      ( ( ticker_row[closePos] < self.Stocks[symbol]['Previous'][closePos] )  and ( self.Stocks[symbol]['Previous1'][closePos] < self.Stocks[symbol]['Previous1'][closePos] )  ) or
                        (ticker_row[closePos] < ( self.Stocks[symbol]['Price']['Bought'] - 0.16 ) ) or
                         #(ticker_row[closePos] < (self.Stocks[symbol]['Price']['HighSinceBought'] - 0.15))  or
                       ( (ticker_row[volumePos] < 0.80 * self.Stocks[symbol]['Previous'][volumePos] )  and (self.Stocks[symbol]['Previous'][volumePos] < self.Stocks[symbol]['Previous1'][volumePos] ) ) or  
                         ((ticker_row[volumePos] < 0.80 * self.Stocks[symbol]['Previous'][volumePos] )  and  (  0.05 < ( ticker_row[closePos]  - self.Stocks[symbol]['Price']['Bought']   )  ) ) or          # $0.07 take profit                          
                              (  0.12 < (self.Stocks[symbol]['Price']['Bought'] - ticker_row[closePos]  )  )       ) :   #AS SOON AS PRICE DIPS -> SELL
                     
                      print( f"TIME TO SELL PRICE: {ticker_row[closePos]} -> {(self.Stocks[symbol]['Previous'][closePos] - 0.16)} or {( self.Stocks[symbol]['Price']['Bought'] - 0.16 )  } or { (self.Stocks[symbol]['Price']['HighSinceBought'] - 0.16)}  "+
                             f" VOLUME: {ticker_row[volumePos]} -> { 0.80 * self.Stocks[symbol]['Previous'][volumePos] }  " +
                             f"VOLATILTIY: {self.Stocks[ symbol ]['Indicators'].Summary()['VolIndex'] }  dSMA : {self.Stocks[ symbol ]['Indicators'].Summary()['dSMA']}  " +
                             f" HARDCODE PRICE : { ticker_row[closePos]  - self.Stocks[symbol]['Price']['Bought'] } or {self.Stocks[symbol]['Price']['Bought'] - ticker_row[closePos]  }  CHOP :  {self.Stocks[ symbol ]['Indicators'].ChopIndex} RSI :  {self.Stocks[ symbol ]['Indicators'].RSI} ")
                      if  account.Sell( stock=symbol, new_price=float(ticker_row[ closePos ]) ,
                                           current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ),
                                       ask_volume=float(ticker_row[ volumePos ] ), indicators=self.Stocks[symbol]['Indicators'] )  :
                         success        = True
                         action         = "closed"
                         self.Stocks[ symbol ]['Price' ]['Bought'] = 0
                         self.Stocks[ symbol ]['Price' ]['High']   = 0
                         self.Stocks[ symbol ]['Volume']['Bought'] = 0
                         self.Stocks[ symbol ]['Volume']['HighSinceBought'] = 0
                         #self.Stocks[symbol]['Losses']    += 1

                         for trade in account.Trades[symbol]:
                             #print(f"\t\t\t   Indicators [IN ] : {trade['indicators_in']}  [OUT] {trade['indicators_out']}  ")
                             print(f"\t\t\t   TIME: {trade['bidTime']}  P&L: {trade['p_l']} ")

            #CLEAN UP
            
            # Update the indicators            
            entry ={0:{'close': ticker_row[closePos], 'open' : ticker_row[openPos] ,'low' : ticker_row[lowPos], 'high' : ticker_row[highPos],
                       'datetime' : (datetime.strptime( ticker_row[timePos][:19], Date_Format) ).timestamp()  * 1000 , 'volume' : ticker_row[volumePos]}}

            self.Stocks[ symbol ]['Indicators'].Update( entry = entry)
            
            # UPDATE THE STOCK INFO WITH THE CURRENT PRICE / VOLUME
            self.ResetStock( symbol =symbol , stockClose= ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )
            self.Stocks[ symbol ]['Previous1']         =  self.Stocks[ symbol ]['Previous']
            self.Stocks[ symbol ]['Previous']          =  ticker_row
            
            # CHANGE TO 5 MINUTE INFO TO JUMP IN AND OUT MOREL ACCURATELY
            if float(self.Stocks[ symbol]['Price']['Bought']) > 0 :
                time_interval   = params['time_interval_bought']
            else:
                if action =='closed' :
                    print("Taking a breathe")
               #     time.sleep(params['time_interval'] ) # After closing a position , take a pause 
                    
                time_interval   = params['time_interval']
                
        except: 
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )


        return success , action, time_interval, account
    





    
    def DayTradeBasicModule ( self, ticker_row : list, account : object, params : dict  ) -> (bool, str, int, TradeAccount) :
        """
            Sets the limits for the account
            ARGS  :
                        ticker_row        ( list ) information about the stock and current price and volume
                        account           ( TradeAccount )  the trading account for BUYS and SELLS
                        volume_threshold  ( int )  the lower limit for volume activity to engage in buy/sell ( may not be important after all )
                        params            ( dicts ) parameters to customize the run 
            RETURNS    :
                        bool: True/False - in case something breaks or could not complete                         
        """
        limit               = params['limit']        # DO NOT EXCEED 10% OF THE ACCOUNT.FUNDS ON ANY ONE PURCHASE
        profit              = 0
        action              = ""
        success             = False
        symbol              = ticker_row[0]
        lowPos              = params['lowPos']
        timePos             = params['timePos']
        openPos             = params['openPos']
        highPos             = params['highPos']
        closePos            = params['closePos']
        volumePos           = params['volumePos']
        risk_percent        = params['risk_percent']
        time_interval       = params['time_interval']
        crash_out_percent   = params['crash_out_percent']      # IF PRICE IS FALLING FAST, DONT SELL IF BELOW THIS PERCENT OF THE PURCHASE, TAKE RISK AND WAIT FOR REBOUND 
        max_num_of_losses   = params["numOfLosses"]
        
        try :            
            # NO BUYING AFTER 3:45
            current_time    = datetime.now()
            if not ( symbol in self.Stocks.keys() )  and ( current_time.hour == 15 and current_time.minute >= 45) :
                print(f"\t\t\t -> DayTradeStrategy:: DayTradeBasic () -> TOO LATE TO CONSIDER MAKING BIDS " )
                return 

            # ADD MECHANISM FOR DETERMINING THE AVG NUMBER OF MOVES BEFORE PIVOTING AND THE AVG $ MOVES  BEFORE PIVOTING
         
            # ADD STOCK ENTRY IF NOT INPLAY /  THIS SHOULD MAINLY BE DONE IN SETORB (), BUT INCASE SOME GET ADDED ALONG THE WAY 
            if not ( symbol in self.Stocks.keys() ) :
                ticker_df       = account.History( symbol=ticker_row[0], time_range=1)   
                self.Stocks[symbol] = self.PrimeStockEntry(symbol=ticker_row[0], ticker_df=ticker_df,ticker_row=ticker_row , current_time=current_time,
                                                            account=account, closePos = closePos , highPos=highPos , volumePos=volumePos)
             
            
            # Update the indicators            
            entry ={0:{'close': ticker_row[closePos], 'open' : ticker_row[openPos] ,'low' : ticker_row[lowPos], 'high' : ticker_row[highPos],
                       'datetime' : (datetime.strptime( ticker_row[timePos][:19], Date_Format) ).timestamp()  * 1000 , 'volume' : ticker_row[volumePos]}}
            self.Stocks[ symbol ]['Indicators'].Update( entry = entry)            
            print(f"\t\t\t\t + INDICATORS:    RSI : {self.Stocks[ symbol ]['Indicators'].Summary()['RSI'] }    "+
                  f"VOLATILTIY: {self.Stocks[ symbol ]['Indicators'].Summary()['VolIndex'] }  dSMA : {self.Stocks[ symbol ]['Indicators'].Summary()['dSMA']}  " +
                  f"ChopIndex : {self.Stocks[ symbol ]['Indicators'].Summary()['ChopIndex'] } " )
            
            #IF MORE THAN 3 LOSSES THEN DONT DO ANY MORE BUYING - NEED TO ADD TO PARAMS 
            if ( not (symbol in account.InPlay) and   self.Stocks[symbol]['Losses'] > max_num_of_losses ):
                print(f"\t\t\t -> DayTradeStrategy:: DayTradeBasic () -> TOO MANY LOSSES TO TRADE :   {self.Stocks[symbol]['Losses'] } " )
                return False, action, time_interval,account
            
            # if volume is less than pre-determined threshold  there is no point in playing with it --  SHOULD THIS ONLY BE FOR THE BUYS / STOP FROM BUYING WHEN VOLUME IS TOO LOW ???
            if ticker_row[volumePos] < int(params['volume_threshold'])   and float(self.Stocks[ symbol]['Price']['Bought']) == 0  : 
                print(f"\t\t\t -> DayTradeStrategy:: DayTradeBasic () -> volume too low   {ticker_row[volumePos] } " )
                return False, action, time_interval, account
            

            #BUY : if the price goes from neg to positive  by $0.02               and volume is higher
            #print(f" Volume percent : {(float(ticker_row[volumPos])  /  float(self.Stocks[ symbol]['Volume']['Previous'] ) )}")
            #print(f"Price to Previous: {float(ticker_row[ closePos])} -  {float(self.Stocks[ symbol]['Price']['Previous'])} :: { float(ticker_row[ closePos]) -  float(self.Stocks[ symbol]['Price']['Previous'])} --> {params['price_move_change']} " +
            #       f"VOLUME : {float(ticker_row[volumePos])  -  float(self.Stocks[ symbol]['Volume']['Previous'] ) } --> {params['volume_change_ratio']} ")

            
            #account.SetLimit( limit )
            upward_pressure        =  round( float(ticker_row[highPos])  - float(ticker_row[closePos]), 3)
            downward_pressure      =  round( float( ticker_row[openPos]) - float(ticker_row[lowPos]) , 3)
            profit_trail_stop      =  round( self.ProfitTrailStop( symbol, risk_percent  ) , 5)
            strike_price_stop      =  round( self.StrikePriceStop( symbol, risk_percent  ) , 5)                
            current_to_previous    =  round(float(ticker_row[closePos]) / float(self.Stocks[ symbol ]['Price' ]['Previous'] ), 5)            
            crash_trail_stop       =  round(crash_out_percent * float(self.Stocks[ symbol]['Price']['Bought']) ,5)


            upward_pressure     =  0.001 if upward_pressure == 0   else upward_pressure
            downward_pressure   =  0.001 if downward_pressure == 0 else downward_pressure


            # INTEGRATE THE ORB VALUES  SOME HOW 

            
            #HOW MANY CONSECUTIVE TIMES THE PRICE HAS RISENS
            if ticker_row[closePos] > self.Stocks[ symbol ]['Price' ]['Previous'] :# and  ticker_row[closePos] > ticker_row[openPos]:
                    self.Stocks[ symbol]['Price']['Upward']  += 1
            else:
                self.Stocks[ symbol]['AvgNumMoves'].append( self.Stocks[ symbol]['Price']['Upward'] )
                self.Stocks[ symbol]['Price']['Upward']  = 0

            
            #CRITERIA SWITCH 
            criteria            = False
            potential_switch    = False 
            # TESTING BUYING INTO THE DIP IF HAVE UPWARD PRESSURE
            if potential_switch :
                criteria = (   ( upward_pressure > downward_pressure ) and
                                        ( ticker_row[ volumePos]  > self.Stocks[ symbol]['Volume']['Previous'] ) and
                                            (round(float(ticker_row[ closePos]),2) < round(float(self.Stocks[ symbol]['Price']['Previous']),2)) )
            else:
                criteria = (( round(float(ticker_row[ closePos]),2) -  round(float(self.Stocks[ symbol]['Price']['Previous']),2) >= params["price_move_change"] )  and 
                        (float(ticker_row[volumePos])  /  float(self.Stocks[ symbol]['Volume']['Previous'] ) ) > params["volume_change_ratio"]) 
                
            
            if (not (symbol in account.InPlay)  and   criteria ) :
                if potential_switch :
                    print(f"\t[POTENTIAL] BUY - Price : {round(float(ticker_row[ closePos]),2)}  " +
                          f" Previous: {round(float(self.Stocks[ symbol]['Price']['Previous']),2)}  " +
                              f" Upward: {round(upward_pressure, 5) }  Down : {  round(downward_pressure, 5 ) }" )
                else:
                    print(f"\t[REGULAR] BUY - Price : {round(float(ticker_row[ closePos]),2)}  " +
                          f" Previous: {round(float(self.Stocks[ symbol]['Price']['Previous']),2)}  " +
                              f" Upward: {round(upward_pressure, 5) }  Down : {  round(downward_pressure, 5 ) }" )
                volume_increase = (float( ticker_row[ volumePos]) - float(self.Stocks[ symbol]['Volume']['Previous'] ) ) / float(self.Stocks[ symbol]['Volume']['Previous'] )                
                if volume_increase  < params["volume_change_avg_ratio"] : # 85% starts to see good results, but dont want to be too strict or too loose 
                    print( f"\t\t\t  *  BUY:: Volume increase isnt enough : {ticker_row[ volumePos ]}  from {self.Stocks[ symbol]['Volume']['Previous'] } ==> {volume_increase} " )
                    # THIS SHOULD BE A SUB FUNCTION
                    self.ResetStock( symbol =symbol ,stockClose= ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )
                    return False, action, time_interval,account
            
                if ( round(ticker_row[closePos], 2 ) <  round(ticker_row[openPos],2 )  and round(ticker_row[closePos],2) == round(ticker_row[highPos],2)) :  #  PRICE CLOSED LOWER THAN IT OPENED with upward pressure
                    print( f"\t\t\t  *  BUY:: PRICE CLOSED LOWER THAN IT OPENED WITH NO UPWARD PRESSURE  : CLOSED={ round(ticker_row[ closePos ],5)}  " +
                               f"OPENED={ round(ticker_row[openPos], 5) }   LOW={ round(ticker_row[lowPos],5) }  HIGH={ round(ticker_row[highPos],5) }  " )                    
                    self.ResetStock( symbol =symbol , stockClose= ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )                    
                    return False, action, time_interval,account
            
                
                if self.Stocks[symbol]['Price']['Upward']  < params["bounce_up_min"] :  # TWO consecutive upward moves with appropriate volume 
                    print( f"\t\t\t  *  BUY [TEST SIGNAL ]:: Consecutive upward moves with volumes : {self.Stocks[ symbol]['Price']['Upward']} " )
                    self.ResetStock( symbol =symbol , stockClose= ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )
                    return False, action, time_interval,account
                
                
                print( f"\t\t\t  *  BUY:: Volume increase OKAY : {ticker_row[ volumePos ]} from" +
                       f" newPrice - previous = ${round( round(float(ticker_row[ closePos ]),5) -  round(float(self.Stocks[ symbol]['Price']['Previous']), 5) , 5) } " +
                       f" Volume :  from { round( self.Stocks[ symbol]['Volume']['Previous'] , 5)  } ==> { round(volume_increase, 5 ) } " +
                       f" PRESSURE :  upward : { round(upward_pressure,5)} ==>  downward :{ round(downward_pressure,5)} " +
                       f" OCCUR : {self.Stocks[symbol]['Price']['Upward'] }  -> {params['bounce_up_min'] } " +
                       f" BODY vs WICK : {round( (ticker_row[closePos] - ticker_row[openPos]) ,5 ) } --> { round( (ticker_row[highPos] - ticker_row[closePos]) , 5 )} "    )
                # 2025-10-21  Playing around to get best results 
                if upward_pressure > downward_pressure : # (ticker_row[closePos] - ticker_row[openPos]) > (ticker_row[highPos] - ticker_row[closePos]) or upward_pressure > downward_pressure :
                    print( f"\t\t\t\t  -  BUY:: ATTEMPTING to Submit a BUY" )
                    if ( account.Buy( stock=symbol , price=float(ticker_row[ closePos ])  ,
                                 current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ) ,
                                    volume = ticker_row[volumePos], volume_threshold = params['volume_threshold'], indicators=self.Stocks[symbol]['Indicators'])   ) :
                    
                        success     = True                                               
                        action      = "bought"
                        self.ResetStock( symbol =symbol , stockClose= ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )                    
                        self.Stocks[ symbol ]['Price' ]['Bought']   =  ticker_row[ closePos ]
                        self.Stocks[ symbol ]['Price' ]['Previous'] =  ticker_row[ closePos ]
                        self.Stocks[ symbol ]['Volume']['Bought']   =  ticker_row[volumePos] 
                else:    
                    print( f"\t\t\t  *  BUY::  Upward {upward_pressure}  less than downward pressure  {downward_pressure}" )
                    
            if action != 'bought' and self.Stocks[ symbol]['Price']['Bought'] > 0 :
                print( f"CURRENT : { round(ticker_row [closePos], 5)}   " +
                       f"BOUGHT AT : { round(self.Stocks[ symbol]['Price']['Bought'],5)}  " +
                       f"PREVIOUS AT: {round(self.Stocks[ symbol]['Price']['Previous'] ,5)}  " +
                       f"OPEN: {round(ticker_row[openPos],5)}   CLOSE :{ round(ticker_row[closePos],5)} " +
                       f" PRESSURE: {upward_pressure} -> {downward_pressure} %{upward_pressure /downward_pressure}  " )


            #SELL : In profit territory 
            if ( action != 'bought' and
                     round(float(self.Stocks[ symbol]['Price']['Bought']) ,3) > 0 and
                     ( round(float(ticker_row[ closePos ]),3) >  round(float(self.Stocks[ symbol]['Price']['Bought']),3) )  ): 
                 print( f"\t\t\t  * SELL SIGNAL EVALUATION :CurrentToPrevious: {current_to_previous}  PROFIT_STOP :{ profit_trail_stop } " +
                                f"STRIKE_PRICE_STOP : { strike_price_stop}   BOUGHT : {round(self.Stocks[ symbol]['Price']['Bought'] , 3 )}    " +
                                f" NEW PRICE : { round(ticker_row[ closePos ],3) }  " +
                                f" PRESSURE: {upward_pressure} -> {downward_pressure} %{upward_pressure /downward_pressure}  "   )                 
                 #  THERE IS SOMETHING ABOUT THE UPWARD PRESSURE == 0 THAT SIGNALS A TURNAROUND TO MAXIMIZE PROFITS , FIGURE IT OUT
                 # MAYBE NEEDS ALL 3   CURRENT TO PREVIOUS > 95  AND CLOSE > OPEN AND UPPER PRESSURE MORE THAN DOWNWARD FOR IT TO TRIGGER
                 if  round(float(ticker_row[ closePos ]), 5) < round( float(self.Stocks[ symbol]['Price']['Previous']) , 5)  :
                     self.Stocks[ symbol]['Price']['Downward'] += 1
                 else:
                     self.Stocks[ symbol]['AvgNumMoves'].append( self.Stocks[ symbol]['Price']['Downward'] )
                     self.Stocks[ symbol]['Price']['Downward'] = 0
                     

                 if (   ( current_to_previous > 0.95)  and (upward_pressure /downward_pressure > 0.65) and self.Stocks[ symbol]['Price']['Downward'] < 2 ):               #and ( ticker_row[closePos] > ticker_row[openPos])         
                     print( f"\t\t\t  \\-> SELL SIGNAL [ RESCIND ] IN PROFIT  : " +
                            f" More upward than downward pressure : { round( float(ticker_row[highPos]) - float(ticker_row[closePos]), 5) } -> " +
                            f"{ round(float( ticker_row[openPos]) - float(ticker_row[lowPos]) , 5 )} "  )
                 #ticker_row[volumePos] < self.Stocks[ symbol ]['Volume' ]['Bought'] :  # VOLUME IS STILL MOVING UP SO DONT SELL RIGHT NOW
                     self.ResetStock( symbol =symbol , stockClose= ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )
                     return False, action, params["time_interval"],account
                    
                    
                # The price is now lower than the previous price and in the Profit_Trail_Stop  range    
                 if ( True or
                      ( round(float(ticker_row[ closePos ]), 5)  <  round( float(self.Stocks[ symbol]['Price']['Previous']) , 5)     ) and
                      ( round( float(ticker_row[ closePos ]) , 5 )   >=  profit_trail_stop     )   ) : # or   ( profit_trail_stop >  float(ticker_row[ closePos ]) )  ):
                     print( f"\t\t\t   \\-> SELL SIGNAL : {self.Stocks[ symbol]['Price']['Bought']}  > {ticker_row[ closePos]}  : Profit_Trail_Stop : {profit_trail_stop} " )
                     if  account.Sell( stock=symbol, new_price=float(ticker_row[ closePos ])  ,
                                       current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ) ,
                                           ask_volume=float(ticker_row[ volumePos ] ),  indicators=self.Stocks[symbol]['Indicators'])  :
                         success    = True                         
                         action     = "closed"
                         self.Stocks[ symbol ]['Price' ]['Bought'] = 0
                         self.Stocks[ symbol ]['Price' ]['High']   = 0
                         self.Stocks[ symbol ]['Volume']['Bought'] = 0
                         

                         for trade in account.Trades[symbol]:
                             #print(f"\t\t\t   Indicators [IN ] : {trade['indicators_in']}  [OUT] {trade['indicators_out']}  ")
                             print(f"\t\t\t   TIME: {trade['bidTime']}  P&L: {trade['p_l']} ")


                        
                        

            #SELL : TRAILING STOPS  Current price less than previous price or less than bought price   
            if ( action != 'bought' and round(float(self.Stocks[ symbol]['Price']['Bought']) , 5) > 0 and
                    (   ( (  round(float(ticker_row[ closePos ]) , 5 ) <  round(float(self.Stocks[ symbol]['Price']['Bought']) , 5) )  or
                             ( round(float(ticker_row[ closePos ]) ,5) <  round(float(self.Stocks[symbol]['Price']['Previous']) ,5)  ) or
                                  ( round(float(ticker_row[ closePos ]) ,5) <  round(float(ticker_row[ openPos ]) ,5) )  ))) :
                        #and
                        # (float(ticker_row[ volumePos ]) <  float(self.Stocks[ symbol]['Volume']['Previous']) ) )  ):
                 print( f"\t\t\t  \\-> SELL SIGNAL (SAFETY) : Current price is below what we bought for  or  ( lower than previous and the volume is lower than previous) "   )
                 # dont sell unless crashing AND atleast 80% purchase, try to wait it out , BOXL fell fast and did not trigger this  so need to FIX
                 print( f"\t\t\t  \\-> SELL SIGNAL (SAFETY) : CHECKING PROFIT_STOP :  STRIKE_PRICE_STOP : { strike_price_stop}   profit_trail_stop: { profit_trail_stop}   CRASH_TRAIL_STOP: { crash_trail_stop}   BOUGHT : {self.Stocks[ symbol]['Price']['Bought']}   NEW PRICE : {ticker_row[ closePos ]} "   )
                 #if  (round(float(ticker_row[ closePos ]),5) <= crash_trail_stop  ) or (  round(float(ticker_row[ closePos ] ),5) <=  strike_price_stop    ):
                 if  (round(float(ticker_row[ closePos ]),5) <= round(float(self.Stocks[ symbol]['Price']['Bought']) - 0.20 , 5)   ):
                     print( f"\t\t\t  \\-> SELL SIGNAL (SAFETY) : PROFIT_STOP : SAFETY SELL  -> { profit_trail_stop }   STRIKE_PRICE_STOP : { strike_price_stop}    CRASH_TRAIL_STOP: { crash_trail_stop}   BOUGHT : {self.Stocks[ symbol]['Price']['Bought']}   NEW PRICE : {ticker_row[ closePos ]} "   )
                     if  account.Sell( stock=symbol, new_price=float(ticker_row[ closePos ]) ,
                                           current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ),
                                       ask_volume=float(ticker_row[ volumePos ] ), indicators=self.Stocks[symbol]['Indicators'] )  :
                         success        = True
                         action         = "closed"
                         self.Stocks[ symbol ]['Price' ]['Bought'] = 0
                         self.Stocks[ symbol ]['Price' ]['High']   = 0
                         self.Stocks[ symbol ]['Volume']['Bought'] = 0
                         self.Stocks[symbol]['Losses']    += 1

                         for trade in account.Trades[symbol]:
                             #print(f"\t\t\t   Indicators [IN ] : {trade['indicators_in']}  [OUT] {trade['indicators_out']}  ")
                             print(f"\t\t\t   TIME: {trade['bidTime']}  P&L: {trade['p_l']} ")

            
            
            
            # holding and what happens when price moves but volume is level , increasing  or decreasing ?     


            # UPDATE THE STOCK INFO WITH THE CURRENT PRICE / VOLUME
            if action != "bought" :
                self.ResetStock( symbol =symbol , stockClose= ticker_row[ closePos] , stockVolume=ticker_row[ volumePos], stockHigh = ticker_row[ highPos]  )

                
            # CHANGE TO 5 MINUTE INFO TO JUMP IN AND OUT MOREL ACCURATELY
            if float(self.Stocks[ symbol]['Price']['Bought']) > 0 :
                time_interval   = params['time_interval_bought']
            else:
                if action =='closed' :
                    print("Taking a breathe")
               #     time.sleep(params['time_interval'] ) # After closing a position , take a pause 
                    
                time_interval   = params['time_interval']
                

            
        except:
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )


        return success , action, time_interval , account






    def OpeningRange ( self, ticker_row : list, account : object ) -> (bool, str) :
        """
            Sets the limits for the account

            PARAMETER  :
                        ticker_row   : information about the stock and current price and volume
                        account      : the trading account for BUYS and SELLS 
            RETURNS    :
                        bool: True/False - in case something breaks or could not complete                         
        """
        action  = ""
        success = True
        interval= 900
        
        try:
            vwap = ( ((ticker_row[2] + ticker_row[3] + ticker_row[4])/3) * ticker_row[5] ) / ticker_row[5]
            print(f"\t\t\t\t\t {ticker_row } -> {vwap}  <- {self.OpenRange['vwap']}" )
            if self.OpenRange['high'] == 0 :
                account.Performance[ticker_row[0] ] = []
                self.OpenRange['vwap']  = vwap
                self.OpenRange['low']   = float( ticker_row[2] )
                self.OpenRange['high']  = float( ticker_row[4] )
                self.AvgVolume          = float( ticker_row[5] )                
            else :
                if self.WatchAlert == '':
                    if  float(ticker_row[3]) >  self.OpenRange['high'] :
                        self.Occurrence += 1
                        interval = 300
                        self.WatchAlert = 'ALERT'
                        print( f'\t WATCHING: Broke Above  : {self.Occurrence}   {ticker_row[3]}   {ticker_row[5]}   VWAP: {vwap} <- {self.OpenRange["vwap"]}'   ) 
                    else:
                        self.Occurrence  = 0
                        print( f'\t Broke BELOW  {self.Occurrence}   {ticker_row[3]}   {ticker_row[5]}    VWAP:{vwap}<- {self.OpenRange["vwap"]}') 
                    self.AvgVolume          = (float(self.AvgVolume) + float(ticker_row[5]) ) / 2
                    if self.Occurrence > 3  and float(ticker_row[5]) > self.AvgVolume:    # should add something about the volume
                        print( 'Looks like going up : should shift to  minute or buy into this ')
                        self.WatchAlert = 'ALERT'
                    print(f"\t Volume  {self.AvgVolume}   -> {ticker_row[5]} ")
                else:
                    if  float(ticker_row[3]) <  self.OpenRange['high'] :
                        print('\t  NOT WATCHING ANYMORE '  )
                        self.WatchAlert = ''
                account.Performance[ticker_row[0] ].append( 'WIN')
            return success , action, interval                
        except:
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )























