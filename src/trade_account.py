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
from datetime import datetime


class TradeAccount:
    def __init__(self, funds : float =5000, limit : float = 0.10 ) :
        """
            Initialize the variables for the Trading Account class 
        """
        self.API_KEY = ""
        self.Trades  = []                       # COMPLETED TRADES FOR THE DAY
        self.InPlay  = {'STOCK':{}}             # CURRENT TRADES STILL OPEN  
        self.Funds   = funds                    # ACCOUNT DOLLAR AMOUNT 
        self.Limit   = funds * limit            # MAX TO SPEND ON ANY ONE TRADE 
        
    def __str__(self ) -> str :
        """
            Returns string representation of the object 
        """
        return f'\t |Funds : {self.Funds},\n\t |Limmit : {self.Limit}'
    
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


    def SetLimit( self, limit : float ) -> None :
        """
            Sets the the limit to use for each trade.  This should be formatted as a decimal
            PARAMETERS  : 
        """
        try:
            self.Limit = self.Funds * limit 
        except:
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )

    def Buy( self, stock : str )  -> bool :
        """
           Attempt to buy the stock under the confines of the limit , True = succeeded , False = failed
           Updates
               * inPlay dictionary to keep track
               * Funds
               
           PARAMETER :
                       stock : string 
           RETURNS   :
                       bool  : True / False 
        """
        success = False

        try :
            return success
        except: 
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )

