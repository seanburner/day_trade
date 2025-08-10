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
from datetime import datetime


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
                                'basic'         :{ 'detail' : 'Basic Bitch of the group',                       'method': self.DayTradeBasic},
                                'opening_range' :{ 'detail' : 'Use first candle to provide range of interest',  'method': self.OpeningRange} 
                          }

        self.Stocks     = {
                            'Stock' : {
                                    'Price' :  {'Previous': 0, 'Slope' : 0, 'Bought' : 0, 'High' : 0},
                                    'Volume' : {'Previous': 0, 'Slope' : 0, 'Bought' : 0 }
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
        targetGoal  = 0.05  #  This needs to be tied to the strategy so it can change, this is not the right place for it 

        
        if not ( strategy in self.Strategies.keys() ):
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Strategy does not exist : ", strategy )
            return False
        
        self.StrategyName =strategy
        account.SetTargetGoal( targetGoal  )
        
        return True

    
    def Run( self,  ticker_row : list, account : object ) -> bool :
        """
            Switching station to control which strategy gets used
            ARGS  :
                    ticker_row : list of fields for stock quote
                    account    : initiated account object
            RETURNS:
                    success : True/False
        """
        if not ( self.StrategyName in  self.Strategies.keys() ):
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Strategy does not exist : ", self.StrategyName )
            return False 
        
        return self.Strategies[ self.StrategyName  ]['method'] ( ticker_row, account )

            
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
                            stock : string  -  the name of the stock 
                            risk_percent    : float  - how much tolerance in price action 
                            
            RETURNS    : 
        """
        bought_price        = float(self.Stocks[ stock ]['Price']['Bought'])        
        trigger_price       = bought_price - ( risk_percent * bought_price )

         
        #print(f"\t\t\t --  Trigger price : { trigger_price}     Bought : { bought_price} " )
        return  trigger_price 


    def DayTradeBasic ( self, ticker_row : list, account : object ) -> (bool, str) :
        """
            Sets the limits for the account

            PARAMETER  :
                        ticker_row   : information about the stock and current price and volume
                        account      : the trading account for BUYS and SELLS 
            RETURNS    :
                        bool: True/False - in case something breaks or could not complete                         
        """
        limit           = 0.20        # DO NOT EXCEED 10% OF THE ACCOUNT.FUNDS ON ANY ONE PURCHASE
        risk_percent    = 0.00015
        crash_out_percent = 0.85      # IF PRICE IS FALLING FAST, DONT SELL IF BELOW THIS PERCENT OF THE PURCHASE, TAKE RISK AND WAIT FOR REBOUND 
        success         = False
        profit          = 0
        index           = 3 
        action          = ""
        
        try :
            #print("basic bitch ")
            account.SetLimit( limit )

            # ADD STOCK ENTRY IF NOT INPLAY
            if not ( ticker_row[0] in self.Stocks.keys() ) :
                self.Stocks[ ticker_row[0] ]  = {                        
                                    'Price' :  {'Previous': ticker_row[ index ], 'Slope' : 1 , 'Bought' : 0, 'High':ticker_row[ index ]},
                                    'Volume' : {'Previous': ticker_row[5], 'Slope' : 1 , 'Bought' : 0}
                             }
            #BUY : if the price goes from neg to positive and volume is higher
            if float(self.Stocks[ ticker_row[0]]['Price']['Bought']) == 0 and (#float(ticker_row[ index ]) > 568  and 
                    ( float(ticker_row[ index ]) <  float(self.Stocks[ ticker_row[0]]['Price']['Previous'])  and
                                 float(ticker_row[5])  >  float(self.Stocks[ ticker_row[0]]['Volume']['Previous'] ) )  ):
                volume_increase = (float( ticker_row[ 5 ]) - float(self.Stocks[ ticker_row[0]]['Volume']['Previous'] ) ) / float(self.Stocks[ ticker_row[0]]['Volume']['Previous'] )
                if volume_increase  < 7 :  # 7 fold increase in volume seems excessive, needs more testing 
                    print( f"\t\t Volume increase isnt enough : {ticker_row[ 5 ]}  from {self.Stocks[ ticker_row[0]]['Volume']['Previous'] } ==> {volume_increase} " ) 
                    return False, action
                #print( "\t\t * BUY SIGNAL " ) 
                print( f"\t\t Volume increase OKAY : {ticker_row[ 5 ]}  from {self.Stocks[ ticker_row[0]]['Volume']['Previous'] } ==> {volume_increase} " ) 
                if  account.Buy( ticker_row[0] , float(ticker_row[ index ])  )  :
                    success = True
                    self.Stocks[ ticker_row[0] ]['Price' ]['Bought'] =  ticker_row[ index ]
                    self.Stocks[ ticker_row[0] ]['Volume']['Bought'] =  ticker_row[5]
                    action          = "bought"


            #SELL : In profit territory 
            if action != 'bought' and float(self.Stocks[ ticker_row[0]]['Price']['Bought']) > 0 and (float(ticker_row[ index ]) >  float(self.Stocks[ ticker_row[0]]['Price']['Bought']) ) : 
                 profit_trail_stop      =  self.ProfitTrailStop( ticker_row[0], risk_percent  )
                 strike_price_stop      =  self.StrikePriceStop( ticker_row[0], risk_percent  )
                 print( "\t\t * SELL SIGNAL : PROFIT : ", profit_trail_stop  )
                 if ( ( float(ticker_row[ index ])  >=  profit_trail_stop     )   ) : # or   ( profit_trail_stop >  float(ticker_row[ index ]) )  ):
                 #   print( "\t\t * SELL SIGNAL : {self.Stocks[ ticker_row[0]]['Price']['Bought']}  > {ticker_row[ index ]}  : {delta} : {0.10 *  account.GetLimit() }" )
                    if  account.Sell( ticker_row[0], float(ticker_row[ index ])   )  :
                        success = True
                        self.Stocks[ ticker_row[0] ]['Price' ]['Bought'] = 0
                        self.Stocks[ ticker_row[0] ]['Price' ]['High']   = 0
                        self.Stocks[ ticker_row[0] ]['Volume']['Bought'] = 0
                        action          = "closed"
            

        

            #SELL : TRAILING STOPS  Current price less than previous price or less than bought price   
            if action != 'bought' and float(self.Stocks[ ticker_row[0]]['Price']['Bought']) > 0 and( ( (float(ticker_row[ index ]) <  float(self.Stocks[ ticker_row[0]]['Price']['Bought']) )  or
                     (float(ticker_row[ index ]) <  float(self.Stocks[ ticker_row[0]]['Price']['Previous']) )  )  and
                         (float(ticker_row[ 5 ]) >  float(self.Stocks[ ticker_row[0]]['Volume']['Previous']) ) ):                 
                 profit_trail_stop      =  self.ProfitTrailStop( ticker_row[0], risk_percent  )
                 strike_price_stop      =  self.StrikePriceStop( ticker_row[0], risk_percent  )
                 crash_trail_stop       =  crash_out_percent * float(self.Stocks[ ticker_row[0]]['Price']['Bought'])
                 # dont sell unless crashing AND atleast 80% purchase, try to wait it out 
                 if  (float(ticker_row[ index ]) > crash_trail_stop  ) and  ( ( float(ticker_row[ index ]) <  strike_price_stop )   or   ( profit_trail_stop >  float(ticker_row[ index ]) )  ):
                 #   print( "\t\t * SELL SIGNAL : {self.Stocks[ ticker_row[0]]['Price']['Bought']}  > {ticker_row[ index ]}  : {delta} : {0.10 *  account.GetLimit() }" )
                    if  account.Sell( ticker_row[0], float(ticker_row[ index ])   )  :
                        success = True
                        self.Stocks[ ticker_row[0] ]['Price' ]['Bought'] = 0
                        self.Stocks[ ticker_row[0] ]['Price' ]['High']   = 0
                        self.Stocks[ ticker_row[0] ]['Volume']['Bought'] = 0
                        action          = "closed"
                        
        
                     
            # holding and what happens when price moves but voume is level , increasing  or decreasing ?     


            # UPDATE THE STOCK INFO WITH THE CURRENT PRICE / VOLUME
            if action != "bought" :
                self.Stocks[ ticker_row[0] ]['Price' ]['Previous'] =  ticker_row[ index ]
                self.Stocks[ ticker_row[0] ]['Volume']['Previous'] =  ticker_row[5]
                if float(ticker_row[ index]) > float(self.Stocks[ ticker_row[0] ]['Price']['High']) :
                    self.Stocks[ ticker_row[0] ]['Price']['High'] = float(ticker_row[ index])

            return success , action
            
        except:
            print("\t\t|EXCEPTION: DayTradeStrategy::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )



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























