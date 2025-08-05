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

#from flask      import Request
from loguru     import logger
from datetime   import datetime



from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

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

        self.Endpoints = {
                            "login"   : f"https://api.schwabapi.com/v1/oauth/authorize?client_id={self.APP_KEY}&redirect_uri=127.0.0.1",
                            "refresh" :  "https://api.schwabapi.com/v1/oauth/token"
                        } 
        credentials , returned_url  = "","" #self.Authenticate ()
        self.RefreshToken(credentials , returned_url)
        print ("\t\t Schwab Account Initiated ") 



    def Authenticate( self ) -> bool :
        """
            Authenticate this connection to the Schwab account using OAuth
            PARAMETERS :
                           Nothing   
            RETURNS    :
                           bool -> True / False  
        """
        intermediate_url = ""
        #webbrowser.open(self.Endpoints['login'])    
        #returned_url        = input()
        #print( returned_url )
        service = ChromeService(ChromeDriverManager().install())
        returned_url = ""
        try:
            options = webdriver.ChromeOptions()
            driver = webdriver.Chrome(service=service, options=options)
            print( 'Endpoint : ', self.Endpoints['login'] )
            driver.get( self.Endpoints['login'] )
            time.sleep(2)
            intermediate_url = driver.current_url
            print( intermediate_url ) 
            WebDriverWait(driver, 20).until(
                    EC.url_changes(  intermediate_url )
                )
            returned_url = driver.current_url
            print( returned_url )
        except TimeoutException :
            print ( 'Using this url : ', intermediate_url )
        except:
            print("\t\t|EXCEPTION: SchwabAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )            
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )

        
        if  returned_url.find('code=') == -1 :
            print ('\t\t Registration process failed : ', returned_url )
            return False
        
        credentials         = f"{self.APP_KEY}:{self.APP_SECRET}"
        response_code       = f"{returned_url[returned_url.index('code=') + 5: returned_url.index('%40')]}@"
        base64_credentials  = base64.b64encode(credentials.encode("utf-8")).decode("utf-8" )

        headers             = {
                                "Authorization": f"Basic {base64_credentials}",
                                "Content-Type": "application/x-www-form-urlencoded",
                            }
        payload             = {
                                "grant_type": "authorization_code",
                                "code": response_code,
                                "redirect_uri": "https://127.0.0.1",
                            }

        print ( crdentials , response_code ) 
        return True

    def RefreshToken(self, credentials , refresh_token_value):
        """
            code=C0.b2F1dGgyLmJkYy5zY2h3YWIuY29t.KfJBeHrK-MsvlzeOpJpWTUfsWEsoYD8dhW-gOeXJxG8%40&session=97c8048b-b555-46ec-903b-f24cdab497be

        """
        logger.info("Initializing...")
        # You can pull this from a local file,
        # Google Cloud Firestore/Secret Manager, etc.
        returned_url = "code=C0.b2F1dGgyLmJkYy5zY2h3YWIuY29t.0KfYtT0_PM9qhcIj157qejO7EI9j7IobOkmIxuf3OAg%40&session=7e847b43-0513-4e68-9459-86f486758502"
        refresh_token_value = f"{returned_url[returned_url.index('code=') + 5: returned_url.index('%40')]}@"
        print( ' Converted Token: ' , refresh_token_value )
        payload = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token_value,
    }
        auth_string = f"{self.APP_KEY}:{self.APP_SECRET}"
        encoded_auth_string = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
        headers = {
                "Authorization": f"Basic {encoded_auth_string}",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        #headers = {
        #"Authorization": f'Basic {base64.b64encode(f"{self.APP_KEY}:{self.APP_SECRET}".encode()).decode()}',
        #"Content-Type": "application/x-www-form-urlencoded",
    #}

        refresh_token_response = requests.post(
        url="https://api.schwabapi.com/v1/oauth/token",
        headers=headers,
        data=payload,
    )
        print( refresh_token_response )
        if refresh_token_response.status_code == 200:
            logger.info("Retrieved new tokens successfully using refresh token.")
        else:
            logger.error(
            f"Error refreshing access token: {refresh_token_response.text}"
        )
            return None

        refresh_token_dict = refresh_token_response.json()

        logger.debug(refresh_token_dict)

        logger.info("Token dict refreshed.")

        return "Done!"




        
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
