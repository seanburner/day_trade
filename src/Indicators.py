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
import platform

import pandas       as      pd
import numpy        as      np


from datetime       import  datetime 


class Indicators :
    def __init__( self, symbol : str , data : dict  ) -> None :
        """
            INITIALIZE THE VARIABLES TO WORK WITH THIS CLASS 
            ARGS   :
                        symbol  ( str )    - stock symbol 
                        data  (Dataframe ) - historical entries for the selected stock symbol 
            RETURNS:
                        nothing 
        """
        self.Symbol     = symbol
        self.MVA        = {}
        self.Set( data )
        
        
                               
    def __str__(self) -> str :
        """
            Formats the class to print out in string format 
        """
        contents  = (f"Symbol : {self.Symbol}  " + str( self.MVA) + "\n VWAP : " + str(self.VWAP)+
                         "\n RSI : " + str(self.RSI) + "\n Volatility : " +str( self.Volatility) )
        
        return contents 




    def Set ( self, data : object ) -> None :
        """
            Initial data set will begin the calculations of the indicators  for later updating
            ARGS   :
                        data  (Dataframe ) - historical entries for the selected stock symbol 
            RETURNS:
                        nothing 
        """
        self.Data = data
        self.Calculate()

            
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
            self.Data = pd.concat( [df, self.Data ],  ignore_index=True)            
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
            #print( data['close'][:9].mean())
            self.MVA.update ( { 9: self.Data['close'][:9].mean(), 14: self.Data[:14]['close'].mean() ,
                                21: self.Data['close'][:21].mean(), 50: self.Data['close'][:50].mean(), 200: self.Data['close'][:200].mean()} )
            # VWAP
            self.Data['Typical_Price']       = (self.Data['high'] + self.Data['low'] + self.Data['close']) / 3
            self.Data['Price_Volume']        = self.Data['Typical_Price'] * self.Data['volume']
            self.Data['Cumulative_PV']       = self.Data['Price_Volume'].cumsum()
            self.Data['Cumulative_Volume']   = self.Data['volume'].cumsum()
            self.Data['VWAP']                = self.Data['Cumulative_PV'] / self.Data['Cumulative_Volume']
            self.VWAP                        = self.Data['VWAP'][0]
            
            #RSI            Using the last 14 days            
            thisData = pd.Series(self.Data[:14].sort_values(by=['datetime'],ascending=True)['close'])            
            self.RSI                    = self.CalculateRSI( data = thisData )

            #Volatility 
            self.Volatility             = self.CalculateVolatility(df = pd.DataFrame( {'close':list(self.Data["close"])}, index=self.Data["date"]) )
        except:
            print("\t\t|EXCEPTION: Indicators::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )
    
    
    def CalculateRSI(self, data, window=14) -> pd.Series :
        """
            Calculates the Relative Strength Index (RSI).

            Args:
                data (pd.Series): A pandas Series of closing prices.
                window (int): The period for RSI calculation (default is 14).

            Returns:
                pd.Series: A pandas Series containing the RSI values.
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
            return rsi

    def CalculateVolatility( self, df : object  ) -> []:
        """
            Calculate the volatility of a stock
            ARGS   :
                        df  ( dataframe )  - the datetime and close values of the stock 
            RETURNS:
                        dataframe  modified with a new volatility column 
        """
        try:
            # --- 1. Sample Data (Replace with your actual stock data) ---        
            #dates = pd.to_datetime(pd.date_range(start='2024-01-01', periods=len(data['Close']), freq='D'))
            #df = pd.DataFrame(data, index=dates)

            # Define the annualization factor (approx. 252 trading days)
            TRADING_DAYS_PER_YEAR = 252

            # --- 2. Calculate Logarithmic Daily Returns ---
            # The .shift(1) moves the price back one day, allowing for P_t / P_{t-1}
            df['Log_Return'] = np.log(df['close'] / df['close'].shift(1))

            # --- 3. Calculate Daily Volatility (Standard Deviation of Returns) ---
            # .std() calculates the standard deviation (σ)
            daily_volatility = df['Log_Return'].std()

            # --- 4. Annualize the Volatility ---
            # Volatility is annualized by multiplying the daily volatility by the square root of 252.
            annualized_volatility = daily_volatility * np.sqrt(TRADING_DAYS_PER_YEAR)

            # --- 5. Output Results ---
            """
            print("--- Historical Volatility Calculation ---")
            print(df)
            print("\nDaily Volatility (Standard Deviation of Daily Log Returns):")
            print(f"{daily_volatility:.4f}")
            print("\nAnnualized Historical Volatility:")
            print(f"{annualized_volatility:.4f} (or {annualized_volatility * 100:.2f}%)")
            """
        except:
            print("\t\t|EXCEPTION: Indicators::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )                
        finally:
            return df
