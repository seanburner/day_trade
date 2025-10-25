## ###################################################################################################################
##  Program :   Indicators
##  Author  :
##  Install :   pip3 install requests  inspect platform argparse 
##  Example :
##              python3 
##              python3 
##  Notes   :   https://docs.python.org/3/tutorial/classes.html
##              
##              
## ###################################################################################################################
import os
import re
import sys
import json
import time
import base64
import getpass
import inspect
import warnings
import platform

import pandas       as      pd
import numpy        as      np


from datetime       import  datetime 

warnings.filterwarnings('ignore')


class Indicators :
    def __init__( self, symbol : str , data : dict , seed_df : pd.DataFrame  ) -> None :
        """
            INITIALIZE THE VARIABLES TO WORK WITH THIS CLASS 
            ARGS   :
                        symbol  ( str )    - stock symbol 
                        data    (Dataframe ) - historical entries for the selected stock symbol 
                        seed_df ( DataFrame) - Open Range Entries - quotes from the first 30 minutes of market open 
            RETURNS:
                        nothing 
        """
        self.SMA        = 0
        self.ATH        = 0
        self.ATL        = 0
        self.Fib        = {}
        self.RSI        = 0
        self.dSMA       = {}
        self.VWAP       = 0
        self.dFib       = {}
        self.Symbol     = symbol
        self.BB_Lower   = 0
        self.BB_Upper   = 0
        self.VolIndex   = 0
        
        self.Set( data, seed_df )
        

                               
    def __str__(self) -> str :
        """
            Formats the class to print out in string format 
        """
        contents  = (f"Symbol : {self.Symbol}  "+ "\n Daily SMA : " + str( self.dSMA) + "\n VWAP : " + str(self.VWAP)+
                         "\n RSI : " + str(self.RSI) + "\n Volatility : " +str( self.VolIndex)  + "\n SMA : " +str( self.SMA)  +
                        f"\nAT [H/L] : {self.ATH} /{self.ATL}" + f"\n d_FIb: {self.dFib} " + f"\n FIb: {self.Fib} "+
                         f"\nBollinger Bands : {self.BB_Lower} -> {self.BB_Upper}" )
        
        return contents 


    def Summary ( self ) -> dict :
        """
            Format all the indicators into a dicctionary for easier external handling
            ARGS    :
                    nothing
            RETURNS :
                    dictionary of the formatted indicators 
        """
        fibs = ['dFib','Fib']
        summary = self.SMA
        summary |= {'HIGH': self.High, 'LOW':self.Low, 'VWAP':self.VWAP, 'RSI':self.RSI,
                    'VolIndex' : self.VolIndex, 'dSMA' : self.dSMA ,'ATH': self.ATH, 'ATL':self.ATL}
        for pos,fib in enumerate( [self.dFib, self.Fib]):
            for key in fib.keys():
                summary.update( {  fibs[pos]+"_"+key : fib[key] } ) 

        summary |= { 'BB_Lower' : self.BB_Lower, 'BB_Upper' :self.BB_Upper }
        
        #summary |= { 'DFib' : self.dFib, 'FIB' :self.Fib }
        #print( "SUMMARY:", summary )

        return summary



    def Set ( self, data : pd.DataFrame, seed_df : pd.DataFrame ) -> None :  
        """
            Initial data set will begin the calculations of the indicators  for later updating
            ARGS   :
                        data    (Dataframe ) - historical entries for the selected stock symbol
                        seed_df ( DataFrame) - Open Range Entries - quotes from the first 30 minutes of market open 
            RETURNS:
                        nothing 
        """
        data = data.reset_index( drop=True)
        self.Data = data
        
        # DAILY SMA  Averages; only needs to be done once 
        self.CalculateDailySMA()

        # ALL TIME HIGH / LOW
        self.ATH = self.Data['close'].max()
        self.ATL = self.Data['close'].min()
        
        #FIB LEVELS - All TIME
        self.Fib = self.CalculateFibonacci( self.ATH  , self.ATL  )
        
        # Calculate the rest that are based on daily entries 
        self.Calculate()
        self.Data = self.Data.sort_values( by=["date"], ascending=True)
        self.Data = pd.DataFrame(self.Data.iloc[-1]).T              # FUTURE CALCULATIONS BASED ON ONE PREVIOUS DATA PLUS TODAY'S ENTRIES

        self.Data = pd.concat([self.Data, seed_df ])
        self.Data = self.Data.dropna().reset_index(drop=True)
        



            
    def Update ( self , entry : dict   ) -> None :
        """
            Add a price history entry to the internal dataframe , then recalculate indicators 
            ARGS   :
                        entry ( list ) - values needed to upate the indicators 
            RETURNS:
                        dict - MVA
            
        """        
        try:
            df = pd.DataFrame(entry).T
            df['date'] = df['datetime'].apply( lambda x: str(datetime.fromtimestamp(x/1000))[:10])

            self.Data = self.Data.dropna()
            self.Data = pd.concat( [df, self.Data ],  ignore_index=True).reset_index( drop=True)
            if 0 in self.Data.columns :
                self.Data = self.Data.drop(0, axis=1)
            
            
            self.Calculate()
        except:
            print("\t\t|EXCEPTION: Indicators::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )
        
                
        
    def Calculate( self ) -> None :
        """
            Calculate the indicators
            TODO - Identify which are based on Daily data ( MVA) and which on quote entries
            ARGS   :
                    nothing 
            RETURNS:
                    nothing 
        """
        try:
            #print( f"\t\t\t** {self.Symbol}  INDICATORS SETTING ")
            # SMA for just the day
            self.dSMA  =  self.Data['close'].mean()
            self.High  =  self.Data['close'].max()
            self.Low   =  self.Data['close'].min()
            
            # VWAP
            self.Data['Typical_Price']       = (self.Data['high'] + self.Data['low'] + self.Data['close']) / 3
            self.Data['Price_Volume']        = self.Data['Typical_Price'] * self.Data['volume']
            self.Data['Cumulative_PV']       = self.Data['Price_Volume'].cumsum()
            self.Data['Cumulative_Volume']   = self.Data['volume'].cumsum()
            self.Data['VWAP']                = self.Data['Cumulative_PV'] / self.Data['Cumulative_Volume']
            self.VWAP                        = self.Data['VWAP'][0]
            
            #RSI            Using the last 14 days            
            thisData = pd.Series(self.Data[:14].sort_values(by=['datetime'],ascending=True)['close'])            
            self.RSI                 = self.CalculateRSI( data = thisData )

            #Volatility 
            self.VolIndex            = self.CalculateVolatility(df = pd.DataFrame( {'close':list(self.Data["close"])}, index=self.Data["date"]) )

            # Fibonacci
            self.dFib               = self.CalculateFibonacci( self.Data['close'].max() , self.Data['close'].min() )

            # Bollinger Bands
            self.CalculateBollinger()
            

        except:
            print("\t\t|EXCEPTION: Indicators::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )


    def CalculateBollinger(self ) -> None:        
        """
        Plot the Bollinger Bands from the data provides
        ARGS   :
                  data                ( Pandas.DataFrame )  timeseries data for symbol
                  look_back_interval  ( int )               context to use for data
        RETURNS:
                    dataframe with  Bollinger Bands high/low 
        """
        look_back_interval  = 15
        
        try:            
            # Calculating the moving average
            MA = self.Data['close'].rolling(window=look_back_interval).mean()
            

            # Calculating the standard deviation
            SD = self.Data['close'].rolling(window=look_back_interval).std()
            
            
            self.BB_Lower = (MA - (2 * SD)).iloc[-1]   # Lower Bollinger Band
            
            self.BB_Upper = (MA + (2 * SD)).iloc[-1]  # Upper Bollinger Band
            
        except: 
            print("\t\t|EXCEPTION: Indicators::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )
        
    
    def CalculateDailySMA( self ) -> None:
        """
            Calculate the simaple moving averages based on daily summary info / not intraday
            ARGS   :
                        nothing 
            RETURNS:
                        nothing 
        """
        try:
            #print( data['close'][:9].mean())
            self.SMA =  { 'SMA9': self.Data['close'][:9].mean(), 'SMA14': self.Data[:14]['close'].mean() ,
                                'SMA21': self.Data['close'][:21].mean(), 'SMA50': self.Data['close'][:50].mean(),
                                'SMA200': self.Data['close'][:200].mean()} 

        except:
            print("\t\t|EXCEPTION: Indicators::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )




    def CalculateFibonacci( self, high : float , low : float  ) -> dict :
        """
            Calculate the Fibonacci levels based on the high and low given
            ARGS   :
                        high ( float ) - highest value of data series
                        low  ( float ) - lowest values of data series  
            RETURNS:
                        dictionary of fib levels 
        """
        diff = high - low
        fib_levels = {
        '0%': low,
        '23.6%': high - (diff * 0.236),
        '38.2%': high - (diff * 0.382),
        '50%': high - (diff * 0.5), # 50% is commonly used but not a true Fibonacci ratio
        '61.8%': high - (diff * 0.618),
        '78.6%': high - (diff * 0.786),
        '100%': high
        }
        return fib_levels 


                
    def CalculateRSI(self, data : object , window : int =14) -> pd.Series :
        """
            Calculates the Relative Strength Index (RSI).

            Args:
                data (pd.Series): A pandas Series of closing prices.
                window (int): The period for RSI calculation (default is 14).

            Returns:
                pd.Series: A pandas Series containing the RSI values.

            RSI – Relative Strength Indicator 
                >= 70 -  possible trend reversal downward 
                <= 30 – possible trend reversal upward 
            Divergence  - when the RSI value shows something different than the price ( Price is always a distraction)
        """
        rsi = None
        try:
            delta = data.diff()

            # Separate gains (positive changes) and losses (negative changes)
            gains = delta.clip(lower=0)
            losses = -delta.clip(upper=0)

            # Calculate initial average gains and losses
            avg_gain = gains.rolling(window=window, min_periods=1).mean()
            avg_loss = losses.rolling(window=window, min_periods=1).mean()

            # Calculate subsequent average gains and losses using Wilder's smoothing
            # This loop can be optimized for performance in larger datasets
            for i in range(window, len(data)):
                avg_gain.iloc[i] = ((avg_gain.iloc[i-1] * (window - 1)) + gains.iloc[i]) / window
                avg_loss.iloc[i] = ((avg_loss.iloc[i-1] * (window - 1)) + losses.iloc[i]) / window

            # Calculate Relative Strength (RS)
            rs = avg_gain / avg_loss

            # Calculate RSI
            rsi = 100 - (100 / (1 + rs))
               
        except:
            print("\t\t|EXCEPTION: Indicators::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )                
        finally:
            self.RSI =  rsi.iloc[-1]            
            return rsi.iloc[-1]



    def CalculateVolatility( self, df : object  ) -> []:
        """
            Calculate the volatility of a stock
            ARGS   :
                        df  ( dataframe )  - the datetime and close values of the stock 
            RETURNS:
                        dataframe  modified with a new volatility column 
        """
        try:
            df = df.sort_index()
            # --- 1. Sample Data (Replace with your actual stock data) ---        
            #dates = pd.to_datetime(pd.date_range(start='2024-01-01', periods=len(data['Close']), freq='D'))
            #df = pd.DataFrame(data, index=dates)
            
            # Define the annualization factor (approx. 252 trading days)
            TRADING_MINUTES_PER_DAY = 5.5 * 60  # days per year = 252

            # --- 2. Calculate Logarithmic Daily Returns ---
            # The .shift(1) moves the price back one day, allowing for P_t / P_{t-1}
            df['Log_Return'] = np.log(df['close'] / df['close'].shift(1))

            # --- 3. Calculate Minute/Daily Volatility (Standard Deviation of Returns) ---
            # .std() calculates the standard deviation (σ)
            
            minute_volatility = df['Log_Return'].std()
            if pd.isna( minute_volatility ) :
                minute_volatility =  df.iloc[-1]['Log_Return'] 

            # --- 4. Daily/Annualize the Volatility ---
            # Volatility is annualized by multiplying the daily volatility by the square root of (5.5 * 60)     252.
            daily_volatility = minute_volatility * np.sqrt(TRADING_MINUTES_PER_DAY)

            # --- 5. Output Results ---
            """
            print("--- Daily Volatility Calculation ---")
            print(df)
            print("\nMinute Volatility (Standard Deviation of Minute Log Returns):")
            print(f"{minute_volatility:.4f}")
            print("\nDaily Historical Volatility:")
            print(f"{daily_volatility:.4f} (or {daily_volatility * 100:.2f}%)")
            """
           
        except:
            print("\t\t|EXCEPTION: Indicators::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )                
        finally:
            self.VolIndex = minute_volatility  #df["Log_Return"][-1]
            return minute_volatility #df["Log_Return"][-1]
