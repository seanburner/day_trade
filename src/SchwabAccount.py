## ###################################################################################################################
##  Program :   Schwab Account 
##  Author  :
##  Install :   pip3 install requests  inspect platform argparse 
##  Example :
##              python3 
##              python3 
##  Notes   :   https://docs.python.org/3/tutorial/classes.html
##              Schwab API   : https://www.reddit.com/r/Schwab/comments/1c2ioe1/the_unofficial_guide_to_charles_schwabs_trader/
##                              https://developer.schwab.com/products/trader-api--individual/details/documentation/Retail%20Trader%20API%20Production
## ###################################################################################################################
import os
import re
import sys
import time
import webbrowser
import base64
#import pandas       as pd
#import numpy        as np 
import getpass
import inspect
import platform
#import argparse
#import functools
import requests
import pickle

#from flask      import Request
from loguru     import logger
from datetime   import datetime, timedelta



from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

ACCNT_TOKENS_FILE = "../files/account_tokens"

class SchwabAccount :
    
    def __init__(self, app_key : str,  app_secret : str ) -> None :
        """
            Initialize the variables for the Trading Account class 
        """
        self.APP_KEY        = app_key
        self.APP_SECRET     = app_secret
        self.Trades         = []                       # COMPLETED TRADES FOR THE DAY
        self.InPlay         = {'STOCK':{}}             # CURRENT TRADES STILL OPEN  
        #self.Funds          = funds                    # ACCOUNT DOLLAR AMOUNT 
        self.Limit          = 0.0                      # MAX TO SPEND ON ANY ONE TRADE 
        self.TargetGoal     = 0                        # Dont get greedy, when reach this amount will quit trading for day
        self.Mode           = ""                       # Are we Testing or Trading or something else
        self.Endpoints      = {
                            "login"   : f"https://api.schwabapi.com/v1/oauth/authorize?client_id={self.APP_KEY}&redirect_uri=https://127.0.0.1",
                            "refresh" :  "https://api.schwabapi.com/v1/oauth/token"
                        }
        self.Accounts       = {}
        self.Tokens         = {}
        self.Type           = "Schwab"



        #self.UpdateTokensFile()
        self.Tokens = self.LoadTokensFile()
       # print( self.Tokens ) 
       # self.Tokens['refresh_expires_at'] = datetime.now() + timedelta( seconds=900*96*5 ) 
        self.CheckAccessTokens()
       # self.UpdateTokensFile()
        
        print ("\t\t Schwab Account Initiated ") 
        
        self._base_api_url = "https://api.schwabapi.com"
        self.Timeout = 1800
       
        self.LinkedAccounts()
        self.AccountDetails()
        self.AccountID = list(self.Accounts.keys())[0]

        """
        print ("\t\t\t -> Orders ")
        statuses = ['AWAITING_PARENT_ORDER', 'AWAITING_CONDITION', 'AWAITING_STOP_CONDITION', 'AWAITING_MANUAL_REVIEW',
                  'ACCEPTED', 'AWAITING_UR_OUT', 'PENDING_ACTIVATION', 'QUEUED', 'WORKING','REJECTED', 'PENDING_CANCEL',
                  'CANCELED', 'PENDING_REPLACE', 'REPLACED', 'FILLED', 'EXPIRED', 'NEW', 'AWAITING_RELEASE_TIME',
                  'PENDING_ACKNOWLEDGEMENT', 'PENDING_RECALL','UNKNOWN']
        for accnt in self.Accounts.keys() :
            print ("\t\t\t   |  ", accnt )
            for status in statuses:
                print ("\t\t\t\t   \\->  ", status)
                self.AccountOrders ( self.Accounts[accnt]['hashValue'], "2025-08-07T23:43:02.120605Z","2025-09-07T23:43:02.120605Z",status) #str( datetime.now()) , str( datetime.now()) ,  status  = "open"  )

        """




    def _params_parser(self, params: dict):
        """
                Removes None (null) values

                Args:
                    params (dict): params to remove None values from

                Returns:
                    dict: params without None values

                Example:
                    params = {'a': 1, 'b': None}
                    client._params_parser(params)
                    {'a': 1}
        """
        for key in list(params.keys()):
            if params[key] is None: del params[key]
        return params


#    def _time_convert(self, dt=None, format: str | TimeFormat = "") -> str | int | None:
#        """
#        Convert time to the correct format, passthrough if a string, preserve None if None for params parser

#        Args:
#            dt (datetime.datetime): datetime object to convert
#            form (str): format to convert to (check source for options)

#        Returns:
#            str | None: converted time (or None passed through)
#        """
#        if dt is None or not isinstance(dt, datetime.datetime):
#            return dt
#        match format:
#            case TimeFormat.ISO_8601 | TimeFormat.ISO_8601.value:
#                return f"{dt.isoformat().split('+')[0][:-3]}Z"
#            case TimeFormat.EPOCH | TimeFormat.EPOCH.value:
#                return int(dt.timestamp())
#            case TimeFormat.EPOCH_MS | TimeFormat.EPOCH_MS.value:
#                return int(dt.timestamp() * 1000)
#            case TimeFormat.YYYY_MM_DD | TimeFormat.YYYY_MM_DD.value:
#                return dt.strftime('%Y-%m-%d')
#            case _:
#                raise ValueError(f"Unsupported time format: {format}")


    def __str__(self ) -> str :
        """
            Returns string representation of the object
        """
        contents = "ACCOUNT  \t\t "
        
        for accnt in self.Accounts.keys():
            contents += accnt + str(self.Accounts[accnt]['details'].keys())
            
        return "" #contents
    

    def CheckAccessTokens(self) -> bool :
        """
            Check if the connection is still valid  before making a request
            ARGS    :
            RETURNS :
                        Nothing 
        """
        success  : bool  = False
        
        # Needs to add expires at for refresh token
        if self.Tokens['refresh_expires_at'] < datetime.now()  or 'error' in self.Tokens:
            success = self.Authenticate() 
        elif self.Tokens['expires_at'] < datetime.now() :          
            success = self.RefreshToken("refresh_token",  self.Tokens['refresh_token'])             
        else:
            #print ( " Tokens still good :" , self.Tokens['expires_at'] )
            success = True
            
        return success 


    def QuoteByInterval(self, symbol: str, periodType: str | None = None, period: str | None = None, frequencyType: str | None = None, frequency: int = 15, startDate: datetime | str | None = None,
                      endDate: datetime | str  = None, needExtendedHoursData: bool | None = None, needPreviousClose: bool | None = None) -> requests.Response:
        """
            Gets the price history of a stock, this seems more useful for the 15 / 5 / 1 min candles than getting the quotes 

            Args:
                symbol                (str): ticker symbol
                periodType            (str): period type ("day"|"month"|"year"|"ytd")
                period                (int): period
                frequencyType         (str): frequency type ("minute"|"daily"|"weekly"|"monthly")
                frequency             (int): frequency (frequencyType: options), (minute: 1, 5, 10, 15, 30), (daily: 1), (weekly: 1), (monthly: 1)
                startDate             (datetime.pyi | str): start date
                endDate               (datetime.pyi | str): end date
                needExtendedHoursData (bool): need extended hours data (True|False)
                needPreviousClose     (bool): need previous close (True|False)

            Returns:
                request.Response: Dictionary containing candle history
        """
        response = ""
        
        try:
            self.CheckAccessTokens() 
            #print( f"\t\t >> AGAIN Comparing {startDate}  -> { endDate}")
            #print(" Now TimeStamp : " , int(datetime.now().timestamp()  * 1000) )
            response =requests.get(f'{self._base_api_url}/marketdata/v1/pricehistory',
                            headers={'Authorization': f'Bearer {self.Tokens["access_token"]}'},
                            params=self._params_parser({'symbol': symbol,
                                                        'periodType': periodType,
                                                        'period': period,
                                                        'frequencyType': frequencyType,
                                                        'frequency': frequency,
                                                        'startDate': int(startDate.timestamp() * 1000 ),
                                                        'endDate':  int(endDate.timestamp() * 1000 ) ,
                                                        'needExtendedHoursData': needExtendedHoursData,
                                                        'needPreviousClose': needPreviousClose}),
                            timeout=self.Timeout)
        
            #print(f"Schwab:QuoteByInterval - {response} - {response.text}")
            return response
        
        except:   
            print("\t\t|EXCEPTION: SchwabAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )

            print(f"\n-> ERROR: {response.text}")


  
    def Quote ( self, stocks :  list  ) -> requests.Response :
        """
            Gets the quote for list of stocks
            ARGS    :
                        stocks : list of stock abbrev
            RETURNS :
                        dictionary of stock quote information 
        """
        self.CheckAccessTokens() 
        response = requests.get(f'{self._base_api_url}/marketdata/v1/quotes',
                            headers={'Authorization': f'Bearer {self.Tokens["access_token"]}'},
                            params={'symbols': str(stocks),
                                 'fields': ['quote','regular'],
                                 'indicative': False},
                            timeout=self.Timeout)
        
        #print(f"Schwab:Quote - {response} - {response.text}")

        return response.json()

        
    def CashForTrading( self ) -> float :
        """
            Return the amount of cash in the account for trading ( defaults to the first account ) 
            ARGS   :
            RETURNS: 
        """
        if len( self.Accounts) > 0 :
            #print(self.Accounts[ list( self.Accounts.keys())[0]])
            return self.Accounts[ list( self.Accounts.keys())[0]]['details'][ 'initialBalances'  ]['cashAvailableForTrading' ]
        else:
            return 0.0

    def LinkedAccounts( self ) -> None :
        """
            Obtains the linked accounts for
            ARGS:
                    Nothing 
            RETURNS:
                    Nothing 
        """
        temp  = requests.get(f'{self._base_api_url}/trader/v1/accounts/accountNumbers',
                            headers={'Authorization': f'Bearer {self.Tokens["access_token"]}'},
                            timeout=self.Timeout).json()
        if 'errors' in temp :
            print(f'\t\t\t SchwabAcccount::LinkedAccounts() - returned error from request : {temp} - Re-Authorizing')
            success = self.Authenticate()
            temp  = requests.get(f'{self._base_api_url}/trader/v1/accounts/accountNumbers',
                            headers={'Authorization': f'Bearer {self.Tokens["access_token"]}'},
                            timeout=self.Timeout).json()
             
            
        for entry in temp:
            self.Accounts[ entry['accountNumber'] ] = {'hashValue' : entry['hashValue'], 'details' : None }
            
        

        
    def  AccountDetails( self) -> None :
        """
            Details on each of the linked accounts
            ARGS    :
            RETURNS :
        """
        fields = None
        temp = ""
        try:
            print("\t\t * Linked Accounts ") 
            temp = requests.get(f'{self._base_api_url}/trader/v1/accounts/',
                            headers={'Authorization': f'Bearer {self.Tokens["access_token"]}'},
                            params="", #self._params_parser({'fields': fields}),
                            timeout=self.Timeout).json()
            if 'errors' in temp :
                print(f'\t\t\t SchwabAcccount::AccountDetails() - returned error from request : {temp}')
                return

            for accntDetail in temp :
             #   print( f"ACCOUNTDETAIL  {accntDetail}  ") 
             #   print( f"ACCOUNTDETAIL  KEYS {accntDetail.keys()}  ") 
                for accntType in accntDetail.keys():   
             #       print( f"ACCOUNT TYPE  {accntType} -> {accntDetail[accntType]} ")                  
                    for accnt in self.Accounts.keys() :
                        if ( ( 'accountNumber' in accntDetail[accntType] ) and (accnt == accntDetail[accntType]['accountNumber']) ) :
              #              print( f"{accntType} -> {accnt}  ") 
                            self.Accounts[ accnt ]['details'] = accntDetail[accntType]
                            continue 
        except:
            print("\t\t|EXCEPTION: SchwabAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )
        """        
        for entry in temp:
            for currentKey in entry.keys():                
                for accntKey in self.Accounts.keys():                
                    if ( ('accountNumber' in entry[currentKey]) and (accntKey == entry[currentKey]['accountNumber'] ) ):
                        self.Accounts[ accntKey ] ['AccountType'] = currentKey
                        for key in entry[currentKey].keys() :
                            self.Accounts[accntKey][key] = entry[currentKey][key]
        """       


    def AccountOrders ( self, accountHash : str , fromTime : str , toTime : str , status : str = "open"  ) -> {}:
        """
            Get the orders for a specific account
            ARGS   :
                    account  - account hashid as str
            RETURNS:
                    dictionary of orders for account 
        """
        
        temp = requests.get(f'{self._base_api_url}/trader/v1/accounts/{accountHash}/orders',
                            headers={"Accept": "application/json", 'Authorization': f'Bearer {self.Tokens["access_token"]}'},
                            params={'maxResults': 50,
                                 'fromEnteredTime': fromTime ,#str( datetime.now() - timedelta( days = 30) ),
                                 'toEnteredTime'  : toTime, # str( datetime.now() ),
                                 'status': status},
                            timeout=self.Timeout)
        print("\t\t\t\t      * ", temp.json() )
        


        

    def UpdateTokensFile( self ) -> bool :
        """
            Serialize the Tokens structure and send to file for future use
            ARGS    :
                        nothing 
            RETURNS :
                        bool of success True/False 
        """       
        with open( ACCNT_TOKENS_FILE, 'wb') as file :
            pickle.dump( self.Tokens, file )

        #print ( "Updated the tokens file ", self.Tokens)
        return True



    def LoadTokensFile( self ) -> bool :
        """
            Load Serialize file into Tokens structure 
            ARGS    :
                        nothing 
            RETURNS :
                        bool of success True/False 
        """       
        
        if os.path.exists( ACCNT_TOKENS_FILE ):
            print( "Reading from Tokens file ")
            with open( ACCNT_TOKENS_FILE, 'rb') as file :
                self.Tokens = pickle.load(  file )
        else:
            self.Tokens = {'expires_in': 0, 'token_type': 'Bearer', 'scope': 'api',
                               'expires_at' : datetime.now(),
                                'refresh_token': '',
                                   'access_token': '',
                                       'id_token': '',
                                       'refresh_expires_at':''
                           }
        
        return self.Tokens



                         
    def Authenticate( self ) -> bool :
        """
            Authenticate this connection to the Schwab account using OAuth
            PARAMETERS :
                           Nothing   
            RETURNS    :
                           bool -> True / False  
        """        
        service = ChromeService(ChromeDriverManager().install())       
        try:
            service = ChromeService(ChromeDriverManager().install())
            options = webdriver.ChromeOptions()
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(  self.Endpoints['login'])
            print(   self.Endpoints['login'])
            returned_code = input("\t\t Follow the prompts in the web browser, then copy and paste the final address location here : " )         
        except:
            print("\t\t|EXCEPTION: SchwabAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )            
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )

       
        success = self.RefreshToken("authorization_code",  returned_code)
        self.Tokens['refresh_expires_at'] = datetime.now() + timedelta( seconds=900*96*7 )  # MARK EXPIRATION FOR 7 DAYS FROM NOW ( 15 MINS * ( 4 * 24 ) * 7 )
        return success 




    def RefreshToken(self, grant_type : str = "authorization_code", code :str = 'code=C0.b2F1dGgyLmNkYy5zY2h3YWIuY29t.2ZbKajZihU0qBU2xipFUp7_cy9OAf76YXqP6ve7p_fA%40&session=368390b2-754e-43a8-9580-6f300d318520') -> bool:
        """
            Depends on the grant_type if getting the initial authorization or getting a refresh
            ARGS    :
                        grant_type  = 'authorization_code" / "refresh_code"
                        code        = code from the web browser interaction or refresh_token from initial authorization   
            RETURNS :

        """
        refresh_current_expire =  self.Tokens['refresh_expires_at'] 
        if "code=" in code :
            code = f"{code[code.index('code=') + 5:code.index('%40')]}@"
        
            
        headers = {'Authorization': f'Basic {base64.b64encode(bytes(f"{self.APP_KEY}:{self.APP_SECRET}", "utf-8")).decode("utf-8")}',
                   'Content-Type': 'application/x-www-form-urlencoded'}

     
        if grant_type == 'authorization_code':  # gets access and refresh tokens using authorization code
            data = {'grant_type':  grant_type,
                    'code': code,
                    'redirect_uri': "https://127.0.0.1"}
        elif grant_type == 'refresh_token':  # refreshes the access token
            data = {'grant_type':  grant_type,
                    'refresh_token': code}
        else:
            raise Exception("Invalid grant type; options are 'authorization_code' or 'refresh_token'")
        
        try:
            response = requests.post('https://api.schwabapi.com/v1/oauth/token', headers=headers, data=data)    
            
            self.Tokens                         = response.json()
            self.Tokens['expires_at']           = datetime.now() +  timedelta(seconds=1750)
            self.Tokens['refresh_expires_at']   = datetime.now() +  timedelta(hours=23.45*7)
           
        except:
            print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )
        
        return  self.UpdateTokensFile(  )





    def Buy( self, symbol : str , price : float, qty : int  ) -> bool :
        """
            Interface with Schwab account to place a BUY order for the symbol
            ARGS    :
                        symbol (str )   - stock symbol to buy
                        price  ( float) - price to buy stock for
                        qty    ( int )  - number of shares of the stock to purchase 
            RETURNS  :
                        True/False ( success ) 
        """
        success = False 
        if self.Mode.lower()  == "test":
            print( "\t\t\t   \\-> BUY Command : in test mode ")
            return True
        
        accnt =  self.AccountID #list(self.Accounts.keys())[0] 
        buy_order = {
            "orderType"                 : "MARKET",
            "session"                   : "NORMAL",
            "duration"                  : "DAY",            
            "price"                     : price,
            "orderStrategyType"         : "SINGLE",
        #    "complexOrderStrategyType"  : "NONE",
            "orderLegCollection"        : [
                    {
                        "instruction"   : "BUY",
                        "quantity"      : qty,  # Number of shares
                        "instrument"    : {
                                                "symbol": symbol,
                                                "assetType": "EQUITY"
                                            }
                        }
                    ]
            }
        print ( buy_order )
        try:            
            buy_response = requests.post(f'{self._base_api_url}/trader/v1/accounts/{ accnt}/orders', # self.Accounts[accnt]["hashValue"]}
                            headers={"Accept": "application/json", 'Authorization': f'Bearer {self.Tokens["access_token"]}',"Content-Type": "application/json"},
                            data=buy_order)            
            print(f"\t\t * BUY ORDER Response: {buy_response.json()} " )
            success = True 
        except Exception as e:                      
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )   

        return success




    def Sell( self, symbol : str , price : float, qty : int  ) -> bool :
        """
            Interface with Schwab account to place a SELL order for the symbol
            ARGS    :
                        symbol (str )   - stock symbol to SELL
                        price  ( float) - price to SELL stock for
                        qty    ( int )  - number of shares of the stock to purchase 
            RETURNS  :
                        True/False ( success ) 
        """
        success = False 
        if self.Mode.lower()  == "test":
            print( "\t\t\t   \\-> SELL Command : in test mode ")
            return True
        
        accnt =  self.AccountID  #list(self.Accounts.keys())[0] 
        sell_order = {
                    "orderType"                 : "LIMIT",
                    "session"                   : "NORMAL",
                    "duration"                  : "DAY",
                    "price"                     : price,
                    "orderStrategyType"         : "SINGLE",
                    "complexOrderStrategyType"  : "NONE",
                    "orderLegCollection": [
                        {
                                "instruction"       : "SELL",
                                "quantity"          : qty,  # Number of shares
                                "instrument"        : {
                                                "symbol"    : symbol,
                                                "assetType" : "EQUITY"
                                }
                        }
                    ]
            }
        try:            
            sell_response = requests.post(f'{self._base_api_url}/trader/v1/accounts/{ accnt}/orders', # self.Accounts[accnt]["hashValue"]}
                            headers={"Accept": "application/json", 'Authorization': f'Bearer {self.Tokens["access_token"]}',"Content-Type": "application/json"},
                            data=sell_order)            
            print(f"\t\t * SELL ORDER  Response: {sell_response} " )
            success = True 
        except Exception as e:                      
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )   

        return success




    
        
    def __str__(self ) -> str :
        """
            Returns string representation of the object 
        """
        return f'\n\t\t |Funds : {self.APP_KEY}\n\t\t |Limit : {self.APP_SECRET}'


    
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
