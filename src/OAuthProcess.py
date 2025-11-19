## ###################################################################################################################
##  Program :   Register Process
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

from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException

class OAuthProcess:

    def __init__(self, app_key : str,  app_secret : str , username : str , password : str, ) -> None :
        """
            Initialize the variables for the Trading Account class 
        """
        self.APP_KEY        = app_key
        self.APP_SECRET     = app_secret
        self.USERNAME       = username
        self.PASSWORD       = password
        self.Credentials    = f"{self.APP_KEY}:{self.APP_SECRET}"
        self.Endpoints = {
                            "login"   : f"https://api.schwabapi.com/v1/oauth/authorize?client_id={self.APP_KEY}&redirect_uri=https://127.0.0.1",
                            "refresh" :  "https://api.schwabapi.com/v1/oauth/token"
                        } 
        #self.Credentials , returned_url  = self.Authenticate ()
        
        #self.RefreshToken(self.Credentials , returned_url)
        #print ("\t\t Schwab Account Initiated ") 
        self.GrantApproval ()




        def GrantApproval( self ) :
            """
                Grants the approval for the app to access the account 
            """
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








        def BuildCredentials( self )  -> str : 
            """
                Build the credentials with base64 
            """
            pass 













            
