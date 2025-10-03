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
                                'basic'         :{ 'detail' : 'Basic Bitch of the group',                           'method': self.DayTradeBasic},
                                'basic1'        :{ 'detail' : 'Basic Bitch of the group based on 1 min candles',    'method': self.DayTradeBasic_1Min},
                                'basic5'        :{ 'detail' : 'Basic Bitch of the group based on 5 min candles',    'method': self.DayTradeBasic_5Min},
                                'basic10'       :{ 'detail' : 'Basic Bitch of the group based on 10min candles',    'method': self.DayTradeBasic_10Min},
                                'basic15'       :{ 'detail' : 'Basic Bitch of the group based on 15min candles',    'method': self.DayTradeBasic_15Min},
                                'basicXm'       :{ 'detail' : 'Basic Bitch of the group based on Varying candles',  'method': self.DayTradeBasic_Xm},
                                'opening_range' :{ 'detail' : 'Use first candle to provide range of interest',      'method': self.OpeningRange} 
                          }

        self.Stocks     = {
                            'Stock' : {
                                    'Price'         :   {'Previous': 0, 'Slope' : 0, 'Bought' : 0, 'High' : 0, 'Occur' : 0},
                                    'Volume'        :   {'Previous': 0, 'Slope' : 0, 'Bought' : 0 },
                                    'Indicators'    :   {'MVA' : {}}   
                                }
                         }
                    
        self.StrategyName = ""

         
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


    def Set( self, strategy :str , account : object   )  -> bool :
        """
            Do the overhead for the specific strategy 
        """
        targetGoal  = 0.025  #  This needs to be tied to the strategy so it can change, this is not the right place for it 

        
        if not ( strategy in self.Strategies.keys() ):
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Strategy does not exist : ", strategy )
            return False
        
        self.StrategyName =strategy
        account.SetTargetGoal( targetGoal  )
        
        return True


            
    def Run( self,  ticker_row : list, account : object, configs : dict  ) -> bool :
        """
            Switching station to control which strategy gets used
            ARGS  :
                    ticker_row : list of fields for stock quote
                    account    : initiated account object
                    configs    : dictionary of configurations 
            RETURNS:
                    success : True/False
        """
        if not ( self.StrategyName in  self.Strategies.keys() ):
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Strategy does not exist : ", self.StrategyName )
            return False 
        
        return self.Strategies[ self.StrategyName  ]['method'] ( ticker_row, account, configs )

            
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
        trigger_price       = previous_price - ( profit * risk_percent )

         
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
                   "risk_percent"           : 0.0015,   # Useful when price starts to fall and need to know when to bail 
                   "time_interval"          : 60,       # Standard Time interval to use
                   "time_interval_bought"   : 60,       # After buying do we need to change time_interval 
                   "crash_out_percent"      : 0.97,     # If the price is crashing this percent of the price we purchased for, then bail ( 100 * .97 => 97 less than or equal we bail 
                   "price_move_change"      : 0.02,     # Price needs to move by this much before we start doing something
                   "volume_change_ratio"    : 0.70,     # Ratio of new volume to previous volume  ( may be unnecessary  unless building out trends )
                   "volume_change_avg_ratio": -0.30,    # Quantifying the change in volume to act ( probably over thinking things )
                   "bounce_up_min"          : 1 ,       # Checks how many consecutive moves upwards before acting
                   "volume_threshold"       : 70000     # Safety net to consider when appropriate to enter a trade, but may not be necessary 
                }




    def DayTradeBasic ( self, ticker_row : list, account : object , configs : dict ) -> (bool, str) :
        """
            Set the params for the DayTrade 15 min  version  , then call the function
            ARGS  :
                        ticker_row ( list ) information about the stock and current price and volume
                        account    ( TradeAccount )  the trading account for BUYS and SELLS
                        configs    (  dict)    configurations 
            RETURNS:
                        bool: True/False - in case something breaks or could not complete    
        """
        params = self.BaseParams()
        params['time_interval']         = 900
        params['time_interval_bought']  = 900
        params['volume_threshold']      = configs['volume_threshold']
        
        #print("\t *Strategy : basic bitch 15 min ")
        return self.DayTradeBasicModule ( ticker_row , account, params  )


    
    def DayTradeBasic_1Min ( self, ticker_row : list, account : object, configs : dict ) -> (bool, str) :
        """
            Set the params for the DayTrade 1 min  version  , then call the function
            ARGS  :
                        ticker_row ( list ) information about the stock and current price and volume
                        account    ( TradeAccount )  the trading account for BUYS and SELLS
                        configs    (  dict)    configurations                   
            RETURNS    :
                        bool: True/False - in case something breaks or could not complete                                    
        """
        params = self.BaseParams()
        params['time_interval']         = 60
        params['time_interval_bought']  = 60
        params['volume_threshold']      = configs['volume_threshold']
        
        
        #print("\t *Strategy : basic bitch 1 min ")
        return self.DayTradeBasicModule ( ticker_row , account, params     )



    def DayTradeBasic_5Min ( self, ticker_row : list, account : object, configs : dict) -> (bool, str) :
        """
              Set the params for the DayTrade 5 min  version  , then call the function
            ARGS  :
                        ticker_row    ( list ) information about the stock and current price and volume
                        account       ( TradeAccount )  the trading account for BUYS and SELLS
                        configs       (  dict)    configurations                   
            RETURNS    :
                        bool: True/False - in case something breaks or could not complete                         
        """
        params = self.BaseParams()
        params['time_interval']         = 300
        params['time_interval_bought']  = 300
        params['volume_threshold']      = configs['volume_threshold']
        
        
        #print("\t *Strategy : basic bitch 5 min ")
        return self.DayTradeBasicModule ( ticker_row , account, params    )





    def DayTradeBasic_10Min ( self, ticker_row : list, account : object, configs : dict ) -> (bool, str) :
        """
              Set the params for the DayTrade 10 min  version  , then call the function
            ARGS  :
                        ticker_row        ( list ) information about the stock and current price and volume
                        account           ( TradeAccount )  the trading account for BUYS and SELLS
                        configs           (  dict)    configurations                   
            RETURNS    :
                        bool: True/False - in case something breaks or could not complete                         
        """
        params = self.BaseParams()
        
        params['time_interval']             = 600
        params['time_interval_bought']      = 600
        params['crash_out_percent']         = 0.85 
        params['volume_threshold']          = configs['volume_threshold']
        params['volume_change_avg_ratio']   = 0.10 

        #print("\t *Strategy : basic bitch 10 min ")
        return self.DayTradeBasicModule ( ticker_row , account, params    )



    def DayTradeBasic_15Min ( self, ticker_row : list, account : object, configs : dict ) -> (bool, str) :
        """
            ARGS  :
                        ticker_row        ( list ) information about the stock and current price and volume
                        account           ( TradeAccount )  the trading account for BUYS and SELLS
                        configs           (  dict)    configurations                   
            RETURNS    :
                        bool: True/False - in case something breaks or could not complete                         
        """
        params = self.BaseParams()
        
        params['time_interval']             = 900
        params['time_interval_bought']      = 900
        params['crash_out_percent']         = 0.85 
        params['volume_threshold']          = configs['volume_threshold']
        params['volume_change_avg_ratio']   = 0.10 

        #print("\t *Strategy : basic bitch 15 min ")
        return self.DayTradeBasicModule ( ticker_row , account, params    )




    def DayTradeBasic_Xm ( self, ticker_row : list, account : object, configs : dict ) -> (bool, str) :
        """
            Sets the limits for the account -> 5 m to 1 min

            PARAMETER  :
                        ticker_row        ( list ) information about the stock and current price and volume
                        account           ( TradeAccount )  the trading account for BUYS and SELLS
                        configs           (  dict)    configurations                   
            RETURNS    :
                        bool: True/False - in case something breaks or could not complete                         
        """
        params = self.BaseParams()
        params['time_interval']         = 300
        params['time_interval_bought']  = 60
        params['volume_threshold']      = configs['volume_threshold']
        
        
        #print("\t *Strategy : basic bitch 5 -> 1 min ")
        return self.DayTradeBasicModule ( ticker_row , account, params    )
        


    
    def DayTradeBasicModule ( self, ticker_row : list, account : object, params : dict  ) -> (bool, str) :
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
        
        try :
            #account.SetLimit( limit )

            # if volume is less than 1M there is no point in playing with it --  SHOULD THIS ONLY BE FOR THE BUYS / STOP FROM BUYING WHEN VOLUME IS TOO LOW ???
            if ticker_row[volumePos] < int(params['volume_threshold'])   and float(self.Stocks[ symbol]['Price']['Bought']) == 0  : 
                print(f"\t\t\t -> DayTradeStrategy:: DayTradeBasic () -> volume too low  {ticker_row[volumePos] } " )
                return False, action, time_interval

            # ADD STOCK ENTRY IF NOT INPLAY
            if not ( symbol in self.Stocks.keys() ) :
                data = account.History ( symbol = symbol, time_period =200 )           # GET HISTORICAL INFOR FOR SYMBOL 
                indicators = Indicators ( symbol= symbol, data= data )                 # CALCULATE THE INDICATORS 
                self.Stocks[ symbol ]  = {                        
                                    'Price'         : {'Previous': ticker_row[ closePos ], 'Slope' : 1 , 'Bought' : 0, 'High':ticker_row[ highPos ], 'Occur' : 0 },
                                    'Volume'        : {'Previous': ticker_row[ volumePos], 'Slope' : 1 , 'Bought' : 0},
                                    'Indicators'    : indicators
                             }
            #BUY : if the price goes from neg to positive  by $0.10 and volume is higher
            #print(f" Volume percent : {(float(ticker_row[volumPos])  /  float(self.Stocks[ symbol]['Volume']['Previous'] ) )}")
            if float(self.Stocks[ symbol]['Price']['Bought']) == 0 and (#float(ticker_row[ closePos ]) > 568  and 
                    ( float(ticker_row[ closePos]) -  float(self.Stocks[ symbol]['Price']['Previous']) > params["price_move_change"] )  and  # Atleast a $0.02 move before entering into a new position
                        (float(ticker_row[volumePos])  /  float(self.Stocks[ symbol]['Volume']['Previous'] ) ) > params["volume_change_ratio"]  ):                        
                volume_increase = (float( ticker_row[ volumePos]) - float(self.Stocks[ symbol]['Volume']['Previous'] ) ) / float(self.Stocks[ symbol]['Volume']['Previous'] )                
                if volume_increase  < params["volume_change_avg_ratio"] : # 85% starts to see good results, but dont want to be too strict or too loose 
                    print( f"\t\t\t  *  BUY:: Volume increase isnt enough : {ticker_row[ volumePos ]}  from {self.Stocks[ symbol]['Volume']['Previous'] } ==> {volume_increase} " )
                    self.Stocks[ symbol]['Price']['Occur'] = 0 
                    return False, action, time_interval
                if ( float(ticker_row[closePos]) <  float(ticker_row[openPos]) ) :  #  PRICE CLOSED LOWER THAN IT OPENED
                    print( f"\t\t\t  *  BUY:: PRICE CLOSED LOWER THAN IT OPENED : CLOSED={ticker_row[ closePos ]} OPENED={ticker_row[openPos] }   LOW={ticker_row[lowPos] }  HIGH={ticker_row[highPos] }  " )
                    self.Stocks[ symbol]['Price']['Occur'] = 0 
                    return False, action, time_interval
                self.Stocks[ symbol]['Price']['Occur']  += 1
                if self.Stocks[symbol]['Price']['Occur']  < params["bounce_up_min"] :  # TWO consecutive upward moves with appropriate volume 
                    print( f"\t\t\t  *  BUY:: Consecutive upward moves with volues : {self.Stocks[ symbol]['Price']['Occur']} " )
                    return False, action, time_interval
                #print( "\t\t * BUY SIGNAL " ) 
                print( f"\t\t\t  *  BUY:: Volume increase OKAY : {ticker_row[ volumePos ]} from previous  {float(ticker_row[ closePos ]) -  float(self.Stocks[ symbol]['Price']['Previous'])}   Volume :  from {self.Stocks[ symbol]['Volume']['Previous'] } ==> {volume_increase} " ) 
                if  account.Buy( stock=symbol , price=float(ticker_row[ closePos ])  , current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ) , volume = ticker_row[volumePos], volume_threshold = params['volume_threshold'])  :
                    success = True
                    self.Stocks[ symbol ]['Price' ]['Bought'] =  ticker_row[ closePos ]
                    self.Stocks[ symbol ]['Volume']['Bought'] =  ticker_row[volumePos]
                    action          = "bought"
                    
            

            #SELL : In profit territory 
            if action != 'bought' and float(self.Stocks[ symbol]['Price']['Bought']) > 0 and (float(ticker_row[ closePos ]) >  float(self.Stocks[ symbol]['Price']['Bought']) ) : 
                 profit_trail_stop      =  self.ProfitTrailStop( symbol, risk_percent  )
                 strike_price_stop      =  self.StrikePriceStop( symbol, risk_percent  )
                 print( f"\t\t\t  * SELL SIGNAL : PROFIT_STOP :{ profit_trail_stop }   STRIKE_PRICE_STOP : { strike_price_stop}   BOUGHT : {self.Stocks[ symbol]['Price']['Bought']}   NEW PRICE : {ticker_row[ closePos ]} "   )
                 if ( float(ticker_row[highPos]) - float(ticker_row[closePos]) ) < ( float( ticker_row[openPos]) - float(ticker_row[lowPos]) ):  # More upward pressure than down
                     print( f"\t\t\t  \\-> SELL SIGNAL :  More upward than downward pressure : {float(ticker_row[highPos]) - float(ticker_row[closePos])} -> {float( ticker_row[openPos]) - float(ticker_row[lowPos])} "  )
                 #ticker_row[volumePos] < self.Stocks[ symbol ]['Volume' ]['Bought'] :  # VOLUME IS STILL MOVING UP SO DONT SELL RIGHT NOW
                     return False, action, params["time_interval"]
                    
                 if ( ( float(ticker_row[ closePos ])  >=  profit_trail_stop     )   ) : # or   ( profit_trail_stop >  float(ticker_row[ closePos ]) )  ):
                     print( f"\t\t\t   \\-> SELL SIGNAL : {self.Stocks[ symbol]['Price']['Bought']}  > {ticker_row[ closePos]}  : Profit_Trail_Stop : {profit_trail_stop} " )
                     if  account.Sell( stock=symbol, new_price=float(ticker_row[ closePos ])  , current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ) )  :
                         success = True
                         self.Stocks[ symbol ]['Price' ]['Bought'] = 0
                         self.Stocks[ symbol ]['Price' ]['High']   = 0
                         self.Stocks[ symbol ]['Volume']['Bought'] = 0
                         action          = "closed"
                        
        

            #SELL : TRAILING STOPS  Current price less than previous price or less than bought price   
            if action != 'bought' and float(self.Stocks[ symbol]['Price']['Bought']) > 0 and( ( (float(ticker_row[ closePos ]) <  float(self.Stocks[ symbol]['Price']['Bought']) )  or
                     (float(ticker_row[ closePos ]) <  float(self.Stocks[symbol]['Price']['Previous']) )  )  and
                         (float(ticker_row[ volumePos ]) <  float(self.Stocks[ symbol]['Volume']['Previous']) ) ):
                 print( f"\t\t\t  \\-> SELL SIGNAL (SAFETY) : Current price is below what we bought for  or  ( lower than previous and the volume is lower than previous) "   )
                 profit_trail_stop      =  self.ProfitTrailStop( symbol, risk_percent  )
                 strike_price_stop      =  self.StrikePriceStop( symbol, risk_percent  )
                 crash_trail_stop       =  crash_out_percent * float(self.Stocks[ symbol]['Price']['Bought'])
                 # dont sell unless crashing AND atleast 80% purchase, try to wait it out , BOXL fell fast and did not trigger this  so need to FIX
                 print( f"\t\t\t  \\-> SELL SIGNAL (SAFETY) : CHECKING PROFIT_STOP :  STRIKE_PRICE_STOP : { strike_price_stop}   profit_trail_stop: { profit_trail_stop}   CRASH_TRAIL_STOP: { crash_trail_stop}   BOUGHT : {self.Stocks[ symbol]['Price']['Bought']}   NEW PRICE : {ticker_row[ closePos ]} "   )
                 if  (float(ticker_row[ closePos ]) <= crash_trail_stop  ) or ( float(ticker_row[ closePos ] ) <=  strike_price_stop    ):
                     print( f"\t\t\t  \\-> SELL SIGNAL (SAFETY) : PROFIT_STOP : SAFETY SELL  -> { profit_trail_stop }   STRIKE_PRICE_STOP : { strike_price_stop}    CRASH_TRAIL_STOP: { crash_trail_stop}   BOUGHT : {self.Stocks[ symbol]['Price']['Bought']}   NEW PRICE : {ticker_row[ closePos ]} "   )
                     if  account.Sell( stock=symbol, new_price=float(ticker_row[ closePos ]) , current_time=str( ticker_row[timePos] if account.Mode.lower() =="test" else datetime.now()   ) )  :
                         success = True
                         self.Stocks[ symbol ]['Price' ]['Bought'] = 0
                         self.Stocks[ symbol ]['Price' ]['High']   = 0
                         self.Stocks[ symbol ]['Volume']['Bought'] = 0
                         action          = "closed"
                        
            
            # Update the indicators for the next go round
            entry ={0:{'close': ticker_row[closePos], 'open' : ticker_row[openPos] ,'low' : ticker_row[lowPos], 'high' : ticker_row[highPos],
                       'datetime' : (datetime.strptime( ticker_row[timePos][:19], Date_Format) ).timestamp()  * 1000 , 'volume' : ticker_row[volumePos]}}
            self.Stocks[ symbol ]['Indicators'].Update( entry = entry)
            
            # holding and what happens when price moves but voume is level , increasing  or decreasing ?     


            # UPDATE THE STOCK INFO WITH THE CURRENT PRICE / VOLUME
            if action != "bought" :
                self.Stocks[ symbol ]['Price' ]['Previous'] =  ticker_row[ closePos]
                self.Stocks[ symbol ]['Volume']['Previous'] =  ticker_row[volumePos]
                if float(ticker_row[ closePos]) > float(self.Stocks[ symbol ]['Price']['High']) :
                    self.Stocks[ symbol ]['Price']['High'] = float(ticker_row[ highPos])

            # CHANGE TO 5 MINUTE INFO TO JUMP IN AND OUT MOREL ACCURATELY
            if float(self.Stocks[ symbol]['Price']['Bought']) > 0 :
                time_interval   = params['time_interval_bought']
            else:
                time_interval   = params['time_interval']
                

            
        except:
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )

        finally :
            return success , action, time_interval 






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























