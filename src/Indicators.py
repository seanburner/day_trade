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
import talib    # Calculate ADX
import base64
import getpass
import inspect
import warnings
import platform


import pandas       as      pd
import numpy        as      np


from datetime           import datetime
from pythonnet import load
#import clr
#from stock_indicators   import indicators


warnings.filterwarnings('ignore')
"""
try:
    # Explicitly load the CoreCLR runtime for Linux
    os.environ['DOTNET_ROOT'] = "/usr/lib64/dotnet/"
    print(f"Set DOTNET_ROOT to: {os.environ['DOTNET_ROOT']}")
    load("coreclr") 
    print("CoreCLR runtime loaded successfully.")
    
except Exception as e:
    # This block should now be rare, but indicates a path/environment issue.
    print(f"Error loading CoreCLR runtime: {e}") 
    print("Please verify the DOTNET_ROOT environment variable.")
    
# --- STEP 2: Now perform the reference/import ---
import clr
from stock_indicators import indicators
print("stock-indicators successfully imported.")
"""
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
        self.EMA9       = None 
        self.Symbol     = symbol
        self.BB_Lower   = 0
        self.BB_Upper   = 0
        self.VolIndex   = 0
        self.ChopIndex  = 0
        self.ADX        = 0
        self.Data       = None 
        
        self.Set( data, seed_df )
        

                               
    def __str__(self) -> str :
        """
            Formats the class to print out in string format 
        """
        contents  = (f"Symbol : {self.Symbol}  "+ "\n Daily SMA : " + str( self.dSMA) + "\n VWAP : " + str(self.VWAP)+
                         "\n RSI : " + str(self.RSI) + "\n Volatility : " +str( self.VolIndex)  + "\n SMA : " +str( self.SMA)  +
                        f"\nAT [H/L] : {self.ATH} /{self.ATL}" + f"\n d_FIb: {self.dFib} " + f"\n FIb: {self.Fib} "+
                         f"\nBollinger Bands : {self.BB_Lower} -> {self.BB_Upper}    Chop_Index : {self.ChopIndex}" ) #.iloc[-1]
        
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

        summary |= { 'BB_Lower' : self.BB_Lower, 'BB_Upper' :self.BB_Upper  , "ChopIndex" : self.ChopIndex} #.iloc[-1]}
        
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
        
        self.Data = pd.DataFrame({}) #Wipe out the dataframe
        
        



            
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

            #self.Data = self.Data.dropna()
            self.Data = pd.concat( [df, self.Data ],  ignore_index=True).reset_index( drop=True)
            #print( f"DATA: {self.Data} ")
            
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

            # Chop Index
            self.CalculateChop()

            # ADX
            self.CalculateADX()

            # 9 EMA
            self.EMA9 = self.Data['close'].ewm(span=9, adjust=False).mean().iloc[-1]



            # CURRENT PRICE RANGE  30 MIN
            """
            self.RangeHigh  = self.Data['high'].rolling(window=30).max()
            self.RangeLow   = self.Data['low'].rolling(window=30).min()
            self.RangeMean  = self.Data['close'].rolling(window=30).mean()
            """
        except:
            print("\t\t|EXCEPTION: Indicators::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )




    def AvgTrueRange( self ) -> float :
        return (self.Data['close'] - self.Data['open']).mean().iloc[-1]




    def CalculateChop( self ) -> None :
        """
        Calculate the symbol's chop index ( without dependent library ) 
        ARGS   :
                nothing 
        RETURNS:
                nothing 
        """
        chop   = None 
        period = 4
        try:
            # Calculate True Range (TR)            
            high_low        = self.Data['high'] - self.Data['low']
            high_close_prev = abs(self.Data['high'] - self.Data['close'].shift())
            low_close_prev  = abs(self.Data['low'] - self.Data['close'].shift())
            tr              = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    
            # Calculate the sum of ATR(1) over n periods (which is SUM(TR, n))
            sum_tr = tr.rolling(window=period).sum()
    
            # Calculate the highest high and lowest low over n periods
            max_high    = self.Data['high'].rolling(window=period).max()
            min_low     = self.Data['low'].rolling(window=period).min()
    
            # Apply the CHOP formula
            # CHOP = 100 * LOG10( SUM(ATR(1), n) / ( MaxHi(n) - MinLo(n) ) ) / LOG10(n)
            numerator = sum_tr / (max_high - min_low)
            # Handle cases where max_high - min_low is zero to avoid division by zero or log(0)
            numerator = numerator.replace([np.inf, -np.inf], np.nan).fillna(0) 

            chop            = 100 * np.log10(numerator) / np.log10(period)            
            #print(f"CHOP : {chop}")
            
            if chop.shape[0] <= 3 :
                self.Chop = 50
            else:
                self.ChopIndex  = round(chop.iloc[3], 2)
           
            
        except:            
            print("\t\t|EXCEPTION: Indicators::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )
            print(f"CHOP : {chop.shape}")




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
            
            
            self.BB_Lower = round( (MA - (2 * SD)).iloc[-1] , 2)  # Lower Bollinger Band
            
            self.BB_Upper = round( (MA + (2 * SD)).iloc[-1] , 2)  # Upper Bollinger Band
            
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
            rsi = round ( 100 - (100 / (1 + rs)) , 2 ) 
               
        except:
            print("\t\t|EXCEPTION: Indicators::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )                
        finally:
            self.RSI =  round( rsi.iloc[-1] , 2 )
            return round( rsi.iloc[-1] ,2 )



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

        self.VolIndex = round ( minute_volatility , 4 ) #df["Log_Return"][-1]
        return round ( minute_volatility , 4 )          #df["Log_Return"][-1]



    def CalculateADX(self,  period : int =14) -> None :
        """
            Calculate ADX to verify trend strength 
        """
        """
        # 1. Calculate True Range (TR)
        self.Data['High-Low']       = self.Data['high'] - self.Data['low']
        self.Data['High-PrevClose'] = abs(self.Data['high'] - self.Data['close'].shift(1))
        self.Data['Low-PrevClose']  = abs(self.Data['low'] - self.Data['close'].shift(1))
        self.Data['TR']             = self.Data[['High-Low', 'High-PrevClose', 'Low-PrevClose']].max(axis=1)

        # 2. Calculate Directional Movement (DM)
        self.Data['UpMove']     = self.Data['high'].diff()
        self.Data['DownMove']   = self.Data['low'].diff().mul(-1) # Make down move positive

        self.Data['+DM'] = np.where((self.Data['UpMove'] > self.Data['DownMove']) & (self.Data['UpMove'] > 0), self.Data['UpMove'], 0)
        self.Data['-DM'] = np.where((self.Data['DownMove'] > self.Data['UpMove']) & (self.Data['DownMove'] > 0), self.Data['DownMove'], 0)

        # 3. Smoothed TR, +DM, -DM (using Wilder's smoothing)
        # Wilder's smoothing is like an EMA with alpha=1/period
        self.Data['SmoothedTR']     = self.Data['TR'].ewm(alpha=1/period, adjust=False).mean()
        self.Data['Smoothed+DM']    = self.Data['+DM'].ewm(alpha=1/period, adjust=False).mean()
        self.Data['Smoothed-DM']    = self.Data['-DM'].ewm(alpha=1/period, adjust=False).mean()

        # 4. Calculate Directional Indicators (+DI, -DI)
        self.Data['+DI'] = (self.Data['Smoothed+DM'] / self.Data['SmoothedTR']) * 100
        self.Data['-DI'] = (self.Data['Smoothed-DM'] / self.Data['SmoothedTR']) * 100

        # 5. Calculate Directional Index (DX)
        self.Data['DX'] = (abs(self.Data['+DI'] - self.Data['-DI']) / (self.Data['+DI'] + self.Data['-DI'])) * 100

        # 6. Calculate ADX (EMA of DX)
        self.Data['DX'] = self.Data['DX'].ewm(alpha=1/period, adjust=False).mean()
        self.ADX  = self.Data[['datetime','TR', '+DM', '-DM', '+DI', '-DI', 'DX'] ]

        #print( f"ADX: { self.ADX[['TR', '+DM', '-DM', '+DI', '-DI', 'DX'] ][:0] } " )
        #print( self.Data.columns)
        """
        df = self.Data[:self.Data.shape[0]-1].sort_values(by=['datetime'],ascending=True).reset_index()
        df['ADX'] = talib.ADX(df['high'], df['low'], df['close'], timeperiod=7)
        self.ADX = df[['ADX','datetime']]
        self.ADX['full_date'] = self.ADX['datetime'].apply( lambda x : datetime.fromtimestamp( x/1000) )
        
        #print ( self.ADX )

