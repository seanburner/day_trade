#! /usr/bin/python3
## ###################################################################################################################
##  Program :   Day Trade 
##  Author  :
##  Install :   pip3 install requests  inspect platform argparse selenium webdriver-manager reportlab pandas schwab-py matplotlib pymssql mysql-connector loguru
##  Example :
##              python3 day_trade.py --csv_config=files/config.csv --display_config 
##              python3 day_trade.py --api_key=XXXXXXXXXXXXXXX --action=download  --stock=QQQ --csv_output=../data --interval=15min --display_config
##              python3 day_trade.py --api_key=XXXXXXXXXXXXXXX --action=back_test --stock=QQQ --input_data=../data/QQQ_15min_.csv --interval=15min --display_config --account_api=xxxxxxx --strategy=basic  --list_strategies
##              python3 day_trade.py --api_key=XXXXXXXXXXXXXXX --action=back_test --interval=15min --display_config --account_api=xxxxxxx --strategy=basic  --list_strategies --input_data=../data/intraday_15min_QQQ.csv --stock=QQQ
##  Notes   :
## ###################################################################################################################
import os
import re
import sys
import time
import inspect
import platform
import argparse
import functools
import requests

import socket
import threading

import pandas               as pd
import matplotlib.pyplot    as plt


from datetime           import datetime, timedelta, timezone 
from PDFReport          import PDFReport
from TraderDB           import TraderDB
from TradeAccount       import TradeAccount
from DayTradeStrategy   import DayTradeStrategy
from OptionsTrade       import OptionsTrade

from selenium                           import webdriver
from selenium.webdriver.chrome.service  import Service as ChromeService
from webdriver_manager.chrome           import ChromeDriverManager
from selenium.webdriver.common.by       import By
from selenium.webdriver.support.ui      import WebDriverWait
from selenium.webdriver.support         import expected_conditions as EC
from selenium.common.exceptions         import TimeoutException, WebDriverException

Configs     = {'username':'Sean Burner'}
DataLock    = threading.Lock()
Strategies  = DayTradeStrategy()

def download_stock_data( configs : dict  ) -> None :
    """
        Downloads the stocks data and saves to a csv file;  defaults to OUTPUTSIZE=COMPACT  [ COMPACT= 100, FULL = 20+ yrs ]
        PARAMETERS :
                        configs ; dictionary of configuration 
        RETURNS    :
                        NONE
                
    """
    url         = ""
    data        = None 
    query       = ""
    response    = None 
        
    try:
        print( f'\t * Downloading stock data : {configs["stock"]} ' )
        
        query   = f'function=TIME_SERIES_INTRADAY&symbol={configs["stock"]}&interval={configs["interval"]}&outputsize=full&apikey={configs["api_key"]}'
        url     = f'https://www.alphavantage.co/query?{query}&datatype=csv'        
        response = requests.get(url)        
        data = response.text
        

        #ADD STOCK TO HEADER LINE AND STOCK TICKER TO EACH LINE OF DATA
        isFirst = True
        newData = ""
        for row in data.split('\n') :            
            if isFirst :
                newData += (f"stock,{ row }\n" )
                isFirst = False
            else:
                if len( row ) > 2 :
                    newData += (f'{configs["stock"]},{row}\n')
        data = newData

        with open(f'{configs["csv_output"]}/{configs["stock"]}_{configs["interval"]}_{configs["start_date"]}.csv','w') as outfile:
            outfile.write( data ) 
        
    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        print("\t\t * Writing : " , configs['csv_output'] )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )

def read_csv( fileName : str) -> object :
    """
        Read in the csv file 

        PARAMETER :
                    fileName  :  path and filename of csv file  
        RETURNS   :
                    df         : dataframe        
    """  
    df  = None 
    try:       
        if os.path.exists( fileName):
            try:
                df = pd.read_csv( fileName,header=0,encoding = "ISO-8859-1",index_col=None )  #         
            except :
                print('\t\t\t -> Problems reading into dataframe : ', fileName )
                for entry in sys.exc_info():
                    print("\t\t >>   " + str(entry) )
            return df 
        else:
            print("CSV File is not valid : " + fileName)
            return None          
    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        print("\t\t * Reading : " , fileName )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )


def blank_config() -> dict:
    """
        Provides a blank configs dictionary with default values
        PARAMETERS:
                    None 
        RETURNS   :
                    dictionary 
    """
    return {
                    'csv_output'        : "",
                    'csv_config'        : "",
                    'api_key'           : "",
                    'model'             : '',
                    'stock'             : '',
                    'action'            : '',
                    'start_date'        : "",
                    'end_date'          : '',
                    'interval'          : '',
                    'input_data'        : '',
                    'strategy'          : '',
                    'app_key'           : '',
                    'app_secret'        : '',
                    'sync_interval'     : 0,
                    'email'             : 'seanburner@gmail.com',
                    'username'          : 'seanburner',
                    'replay_date'       : '',
                    'volume_threshold'  : 70000,
                    'csv_input_fields'  : False,                    
                    'display_config'    : False,
                    'list_strategies'   : False,
                    'trading_platform'  : 'Schwab',
                    'sql_server'        : "127.0.0.1",
                    'sql_user'          : "",
                    'sql_password'      : ""
                    } 


def apply_csv_config ( configs : dict ) -> dict:
    """
        IF THE USER PROVIDED A VALID CSV CONFIG FILE , APPLY THOSE SETTINGS AND THEN LATER APPLY OTHER COMMAND LINE ARGS

        PARAMETERS :
                        configs     : configuration dictionary 
        RETURNS    :
                        configuration dictionary 
    """
    config_file = None
    config_new  = blank_config()
    try:
        if not os.path.exists(  configs['csv_config'] ) :
            print ("\t\t* Provided CSV config file was not present/readable")
            return configs

        config_file = read_csv( configs['csv_config'] )        
        for key in config_file.columns:            
            if key in config_new.keys():               
                config_new[ key] = config_file.iloc[0][key]

        # NOW APPLY WHAT WAS PARSED FROM THE COMMAND LINE         
        for key in configs.keys():
            if not ( configs[key] == '' or configs[key] == False ) :
                config_new[ key] = configs[key]
              
            
                
        
    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )        
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) ) 
    finally:
        return config_new

    
def update_args_field ( argValue , defaultValue  ) -> {} :
    """
        Updates the fields from the argument list. This way  preserves any default values
        
        PARAMETERS :
                    argValue      :  current field in the argparse
                    defaultValue  :  default value to assign if argValue is empty
        RETURNS    :
            the updated version of the configuration dictionary 
        
    """    
    if argValue or (not isinstance(argValue, bool) and argValue is not None and len( argValue) > 1):
        return argValue
    else:
        return defaultValue


def display_config(  configs : dict) -> None :
    """
        DISPLAY THE CONFIGURATION TO BE USED IN THE APPLICATION

        PARAMETERS:
                        configs    ; configuration dictionary 
        RETURNS   :
                        nothing 
    """

    try:
        print(f"\t\t Application Configuration ")
        for key in configs.keys() :
            print(f'\t\t  {key:<20} | {configs[key]} ')
    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )

def display_strategies() -> None :
    """
        SHOULD HOOK INTO A GLOBAL VARIABLE/CLASS TO HOLDS ALL THE DAY_TRADE_STRATEGIES 
        
        PARAMETERS:
                        nothing 
        RETURNS   :
                        nothing 
    """
    try:        
        print( Strategies.List() )
        
    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )


        
def display_csv_input_fields() -> None :
    """
        Print the fields for the input csv file depending on the type of upload
        
        PARAMETERS:
        RETURNS   :
    """
    line         = "" 
    grant_fields = {
        'project-title_xx'              :{ 'type':'text',       'value' :"" ,                                           'note' : '_xx  represents a counter for multiple projects'},
        'description_xx'                :{ 'type':'text',       'value' :"" ,                                           'note' :'description of the project, _xx  represents a counter for multiple projects'},
        'award_amount_currency_xx'      :{ 'type':'enumerated', 'value' :"USD" ,                                        'note' :"Currency of grant,  _xx  represents a counter for multiple projects"},
        'award_amount_value_xx'         :{ 'type':'float',      'value' :"" ,                                           'note' :"Dollar amount given to the grant without ',' or '$',  _xx  represents multiple projects "},
        'funding-type_xx_aa'            :{ 'type':'enumerated', 'value' :"contract / grant" ,                           'note' :'Type of funding to be used '},
        'funding-amount_xx_aa'          :{ 'type':'enumerated', 'value' :"USD / EUR" ,                                  'note' :'Currency of funding, _aa  represents a counter for multiple funding sources per project'},
        'funding-currency_xx_aa'        :{ 'type':'float',      'value' :"" ,                                           'note' :'dollar value without commas, _aa  represents a counter for multiple funding sources per project'},
        'funding-percentage_xx_aa'      :{ 'type':'integer',    'value' :"" ,                                           'note' :'percentage grant was funded, _aa  represents a counter for multiple funding sources per project'},
        'funding-name_xx_aa'            :{ 'type':'text',       'value' :"" ,                                           'note' :'name of organization or individual that funded grant, _aa  represents a counter for multiple funding sources'},
        'funding-id_xx_aa'              :{ 'type':'hyperlink', 'value' :"" ,                                            'note' :'doi id link,  _aa  represents a counter for multiple funding sources'},
        'funding-scheme_xx_aa'          :{ 'type':'text',       'value' :"grant" ,                                      'note' :'Type of funding applied,  _xx  represents a counter for multiple projects'},
        'award-dates_start-date_xx'     :{ 'type':'yyyy-mm-dd', 'value' :"" ,                                           'note' :'Award Start Date, _xx  represents a counter for multiple projects '},
        'award-dates_end-date_xx'       :{ 'type':'yyyy-mm-dd', 'value' :"" ,                                           'note' :'Award End Date , _xx  represents a counter for multiple projects'},
        
        'person_role_xx_yy'             :{ 'type':'enumerated', 'value' :"lead_investigator / co-lead_investigator" ,   'note' :'_yy  represents a counter for multiple people'},
        'givenName_xx_yy'               :{ 'type':'text',       'value' :"" ,                                           'note' :'_yy  represents a counter for multiple people'},
        'alternateName_xx_yy'           :{ 'type':'text',       'value' :"" ,                                           'note' :'_yy  represents a counter for multiple people'},
        'familyName_xx_yy'              :{ 'type':'text',       'value' :"" ,                                           'note' :'_yy  represents a counter for multiple people'},
        'institution_xx_yy_zz'          :{ 'type':'text',       'value' :"" ,                                           'note' :'_zz  represents a counter for multiple institutions'},
        'institution-country_xx_yy_zz'  :{ 'type':'text',       'value' :"" ,                                           'note' :'Country where institution resides, _zz  represents a counter for multiple institutions'},
        'ROR_xx_yy_zz'                  :{ 'type':'text',       'value' :"" ,                                           'note' :'_zz  represents a counter for multiple institutions'},
        'ORCHiD_xx_yy'                  :{ 'type':'hypertext',  'value' :"" ,                                           'note' :'_yy  represents a counter for multiple people'},

        'institution_xx'                :{ 'type':'text',       'value' :"" ,                                           'note' :'Institution associated with Grant, _xx  represents a counter for multiple projects '},
        'award-number'                  :{ 'type':'integer',    'value' :"" ,                                           'note' :'ID number associated with this Grant'},
        'award-start-date'              :{ 'type':'yyyy-mm-dd', 'value' :"" ,                                           'note' :'Award Payment Start Date '}, 
        
        'doi'                           :{ 'type':'text',       'value' :"" ,                                           'note' :'DOI ID '},        
        'resource'                      :{ 'type':'hyperlink',  'value' :"" ,                                           'note' :'Landing page for article or research paper '}
       }

    
    try:
        print( f'\n Fields required in the CSV input file : ' )

        print( f"\n\t==============================   GRANT  =====================================================")
        print( f"\tFIELD NAME                         TYPE                     DEFAULT                  NOTES")
        for key, value  in grant_fields.items() :
            line = "\t{:<30}{:>5}".format(  key ," ")
            for key2, value2 in value.items() :
                line +=  "{:<20}{:>5}".format( value2, "" )
            print( line) 
            
    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )


                        
def parse_arguments() -> {} :
    """
        Parse the command line arguements  for configuration info , if not use the defaults
        
        PARAMETERS:
        RETURNS   :
    """
    args        = None 
    temp        = None    
    parser      = argparse.ArgumentParser(description='Import data from Data Application tool')
    configs     = blank_config()
    matrix      = {
                        'csv_output'        : { 'help': 'Path to save data files',     	            'action' : None } ,
                        'csv_config'        : { 'help': 'Use CSV formatted configuration file',     'action' : None } ,
                        'model'             : { 'help': 'Which model to back test ',                'action' : None } ,
                        'email'             : { 'help': 'Email to send the report ',                'action' : None } ,
        		'api_key'           : { 'help': 'API KEY for endpoint' , 		    'action' : None}, 
        		'stock'             : { 'help': 'Stock ticker symbol', 		            'action' : None },
			'action'            : { 'help': 'Options: download/back_test/trade/test/live_test/sync' ,  'action' : None}, 
			'start_date'        : { 'help': 'Start date', 	                            'action' : None}, 
			'end_date'          : { 'help': 'End date' ,  			            'action' : None}, 
                        'username'          : { 'help': 'Username to associate with session',       'action' : None},
			'interval'          : { 'help': 'Time interval [ 5min / ]',           	    'action' : None },                        
                        'sync_interval'     : { 'help': 'Number or days to go back in the sync ( 0 = today)','action' : None },
			'input_data'        : { 'help': 'Data file to be used during back_test',    'action' : None },
                        'strategy'          : { 'help': 'Strategy to use [ basic/basic15/basicXm ]','action' : None },
                        'app_key'           : { 'help': 'Schwab application key ',                  'action' : None },
                        'app_secret'        : { 'help': 'Schwab application Secret ',               'action' : None },
                        'trading_platform'  : { 'help': 'Platform of your trading account [ Schwab]','action' : None},                        
                        'replay_date'       : { 'help': 'Date to pull quotes to do a replay_test',  'action' : None },
                        'volume_threshold'  : { 'help': 'Threshold for determining position entry', 'action' : None},
                        'sql_server'        : { 'help': 'The address of the sql server',            'action' : None},                        
                        'sql_user'          : { 'help': 'User account for SQL ',                    'action' : None},
                        'sql_password'      : { 'help': 'Password for SQL account',                 'action' : None},                  
			'csv_input_fields'  : { 'help': 'Display the fields for the csv file',      'action' : 'store_true'},			
			'display_config'    : { 'help': 'Display the configuration', 	            'action' : 'store_true'},
                        'list_strategies'   : { 'help': 'Display available strategies', 	    'action' : 'store_true'},
                                                
		}
    try:
        # SET DEFAULTS        
        for key in matrix.keys() :            
            parser.add_argument('--'+key     , help = matrix[key]['help'], action= matrix[key]['action'], dest=key )
        
        args = parser.parse_args()

        for key in matrix.keys() :
            configs[key]   = update_args_field (  getattr(args, key) , configs[key])
            
            # CHECK IF THE STOCK SYMBOL IS SINGULAR OR PLURAL 
            if key == 'stock' :                
                values = configs[key].split(',')
                configs[key] = list ( values )


        return configs

    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )


"""

from schwab.auth import easy_client
from schwab.client import Client
from schwab.streaming import StreamClient

import asyncio
import json



async def read_stream( stream_client):
    await stream_client.login()

    def print_message(message):
      print(json.dumps(message, indent=4))

    # Always add handlers before subscribing because many streams start sending
    # data immediately after success, and messages with no handlers are dropped.
    stream_client.add_nasdaq_book_handler(print_message)
    await stream_client.nasdaq_book_subs(['GOOG'])

    while True:
        await stream_client.handle_message()


"""


def scrape_potential_stocks() -> None :
    """
        Scrape appropriate web sites to get the trending stocks and the analyze ( according to some criteria) to keep for trading
        NOTE :  Use Investor Undergrounds Market Movers page 
    """
    service     = None
    endpoints   = {
                    'Premarket' : 'https://www.investorsunderground.com/market-movers',
                    'Interday'  : 'https://www.investorsunderground.com/market-movers/?mm=2',
                    'Afterhours': 'https://www.investorsunderground.com/market-movers/?mm=3'
                }
    data        = {}
    try :
        service = ChromeService(ChromeDriverManager().install())      
        options = webdriver.ChromeOptions()
        driver = webdriver.Chrome(service=service, options=options)
        for endpoint in endpoints.keys():
            driver.get(  endpoints[ endpoint ])
            data.update( { endpoint : [] } ) 
        
    except: 
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )



            
from Indicators  import Indicators

from MySQLConn          import MySQLConn

def system_test( configs : dict  ) -> None :
    account         = None
    date_format     = "%Y-%m-%d %H:%M:%S"    


    email       = 'seanburner@gmail.com'
    HEADER      =  "INSERT INTO orderIndicates( orderId,indicateId,bidValue,askValue ,active,createdBy,createdDate,modBy,modDate  ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s);"
    CONTENTS    =  [
                    [26, 1, 4.88, 4.88,         1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 2, 4.68071, 4.68071,   1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 3, 4.39762, 4.39762,   1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 4, 3.6724, 3.6724,     1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 5, 3.55109, 3.55109,   1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 6, 13.75277, 13.75277, 1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 9, 5.74, 5.74,         1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 10, 1.8, 1.8,          1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 11, 17.49, 17.49,      1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 12, 5.08, 5.08,        1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 14, 56.48152, 56.48152,1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 15, 0.15607, 0.15607,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 31, 14.27141, 14.27141,1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 32, 5.08, 5.08,        1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 33, 14.56124, 14.56124,1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 34, 12.74938, 12.74938,1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 35, 11.285, 11.285,    1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 36, 9.82062, 9.82062,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 37, 7.73574, 7.73574,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 38, 17.49, 17.49,      1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 39, 1.8, 1.8,          1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 40, 4.81016, 4.81016,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 41, 4.23492, 4.23492,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 42, 3.77, 3.77,        1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 43, 3.30508, 3.30508,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 44, 2.64316, 2.64316,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 45, 5.74, 5.74,        1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 46, 8.66085, 8.66085,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [26, 47, 19.8139, 19.8139,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],	
                    [27, 1, 4.88, 4.88,         1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 2, 4.68071, 4.68071,   1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 3, 4.39762, 4.39762,   1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 4, 3.6724, 3.6724,     1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 5, 3.55109, 3.55109,   1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 6, 13.75277, 13.75277, 1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 9, 5.74, 5.74,         1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 10, 1.8, 1.8,          1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 11, 17.49, 17.49,      1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 12, 5.08, 5.08,        1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 14, 56.48152, 56.48152,1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 15, 0.15607,0.15607,   1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 31, 14.27141,14.27141, 1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 32, 5.08, 5.08,        1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 33, 14.56124, 14.56124,1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 34, 12.74938, 12.74938,1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 35, 11.285, 11.285,    1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 36, 9.82062, 9.82062,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 37, 7.73574, 7.73574,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 38, 17.49, 17.49,      1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 39, 1.8, 1.8,          1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 40, 4.81016, 4.81016,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 41, 4.23492, 4.23492,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 42, 3.77, 3.77,        1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 43, 3.30508, 3.30508,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 44, 2.64316, 2.64316,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 45, 5.74, 5.74,        1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 46, 8.66085, 8.66085,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18'],
                    [27, 47, 19.8139, 19.8139,  1, 'sean', '2025-10-20 15:55:18', 'sean', '2025-10-20 15:55:18']
                   ]

                   

    account     = TradeAccount(funds=5000, limit=0.10, app_type='Schwab', app_key = configs['app_key'], app_secret = configs['app_secret'])
    sqlConn     = TraderDB( server =configs['sql_server'], userName =configs['sql_user'], password =configs['sql_password'] )

    sqlConn.CreateTables()
    return
    
    sqlConn.Conn.WriteMany( header=HEADER, contents =CONTENTS)
    return 



    try:

        while True :
            print ( "-> going round in circles ")
            time.sleep( 60 )
                    
        account     = TradeAccount(funds=5000, limit=0.10, app_type='Schwab', app_key = Configs['app_key'], app_secret = Configs['app_secret'])
        print('> Account Orders ' )

        accountHash = account.Conn.Accounts[account.Conn.AccountID]['hashValue']
        print(f"  Account : {account.Conn.Accounts[account.Conn.AccountID]}")
        fromTime    = (datetime.now(timezone.utc) - timedelta( days = 10) ).strftime('%Y-%m-%dT%H:%M:%SZ')        
        toTime      = (datetime.now(timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ')        
        openOrders= account.Conn.Reconcile ( symbol="ARBK",enteredTime= datetime.now() -timedelta( days =10), qty=397 , action="BUY")
        print( f"OpenOrders: {accountHash}   {fromTime} -> {toTime}  => {openOrders}")
        return 

        
        print('Preferences: ', account.Conn.Preference )

        time_period = 200 + (.50 * 200 )
        data = account.History( symbol=Configs['stock'], time_range=time_period  ) 
        #print( data.columns)
        indicators = Indicators( symbol=Configs['stock'], data=data )    
        print(f"Indicators : {indicators }")
        ticker = account.Quote ( symbols=Configs['stock'][0])[Configs['stock'][0]]
        timePos = 1
        lowPos = 2 
        closePos = 3
        openPos = 4 
        highPos = 6
        volumePos =  5
        print(f"*************************** Indicators  *********************************")
        ticker[timePos] = datetime.strptime( "2025-10-04 14:20:25", date_format)        
        indicators.Update( entry ={0:{'close': ticker[closePos], 'open' : ticker[openPos] ,'low' : ticker[lowPos],
                                      'high' : ticker[highPos], 'datetime' : ticker[timePos].timestamp()  * 1000 , 'volume' : ticker[volumePos]}})
        print(f"Indicators UPDATED: {indicators }")

        print(f"\n\n*************************** Indicators  *********************************")
        
        ticker[timePos] = datetime.strptime( "2025-10-05 14:20:25", date_format)        
        indicators.Update( entry ={0:{'close': ticker[closePos]+0.05, 'open' : ticker[openPos] ,'low' : ticker[lowPos],
                                      'high' : ticker[highPos], 'datetime' : ticker[timePos].timestamp()  * 1000 , 'volume' : ticker[volumePos]}})
        print(f"Indicators UPDATED: {indicators }")


        traderDB    = TraderDB( server =configs['sql_server'], userName =configs['sql_user'], password =configs['sql_password'] )
        traderDB.CheckDB()
         
    except: 
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )   



def system_test_old( configs : dict ) -> None :
    """
        Transiant - tests the integration of different code 
    """
    email       = 'seanburner@gmail.com'
    HEADER      =  "INSERT INTO orderIndicates( orderId,indicateId,bidValue,askValue ,active,createdBy,createdDate,modBy,modDate  ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s);"
    CONTENTS    =  [
                        [28, 1, 4.88, 4.88, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 2, 4.68071, 4.68071, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 3, 4.39762, 4.39762, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 4, 3.6724, 3.6724, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 5, 3.55109, 3.55109, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 6, 16.03, 16.03, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 9, 5.74, 5.74, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 10, 1.8, 1.8, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 11, 17.73, 17.73, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 12, 5.08, 5.08, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 14, 52.51877, 52.51877, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 15, 0.1458, 0.1458, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 31, 15.33702, 15.33702, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 32, 5.08, 5.08, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 33, 14.7446, 14.7446, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 34, 12.8977, 12.8977, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 35, 11.405, 11.405, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 36, 9.9123, 9.9123, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 37, 7.7871, 7.7871, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 38, 17.73, 17.73, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 39, 1.8, 1.8, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 40, 4.81016, 4.81016, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 41, 4.23492, 4.23492, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 42, 3.77, 3.77, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 43, 3.30508, 3.30508, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 44, 2.64316, 2.64316, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 45, 5.74, 5.74, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 46, 9.31682, 9.31682, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"],
                        [28, 47, 22.16452, 22.16452, 1, 'sean', "2025-10-20 15:55:18", 'sean', "2025-10-20 15:55:18"]
                    ]

    account     = TradeAccount(funds=5000, limit=0.10, app_type='Schwab', app_key = configs['app_key'], app_secret = configs['app_secret'])
    sqlConn     = TraderDB( server =configs['sql_server'], userName =configs['sql_user'], password =configs['sql_password'] )
    sqlConn.Conn.WriteMany( header=header, contents =contents)
    return 
    account.SetFunds( 5000.00, 0.50 )    
    account.SetTargetGoal( 0.025  )
    account.SetMode("LIVE")
    #print( account.Conn.Accounts['xxxxx']['hashValue'])
    #account.Conn.AccountOrders(account.Conn.Accounts[0][) 
    account.Conn.Buy( symbol ='OPEN', price=6.00, qty =1 )

    
    #traderDB    = TraderDB( server =configs['sql_server'], userName =configs['sql_user'], password =configs['sql_password'] )

    #traderDB.InsertOrderbook( orderbook = orderbook , email =email )

    #print ( "UserID : " , traderDB.InsertUser ( userName = 'seanburner', email =email )  )
    #traderDB.InsertDate( datetime.now() ) 



def send_data_to_file( configs : dict , data: dict   )   -> None :
    """
        SEND THE DATA from a live session to a data file for later replay 
        ARGS   :
                configs : configuration dictionary
                data    : dictionary of quote entries 
        RETURNS:
                Nothing 
    """        
    indx        = 0
    line        = ""
    contents    = ""

    
    try:        
        for key in data.keys():
            contents    = "SYMBOL,DATETIME,LOW,QUOTE,HIGH,CLOSE,VOLUME,INTERVAL,MSG"
            for row in data[key]:
                line = ""
                for key2 in row.keys():
                    if len( line) > 1  :
                        line += ','
                    line +=  str(row[key2] )
                contents += '\n' +line 
            with open( f"../data/{key}_{str(datetime.now())[:19]}.csv","w") as data_file:
                data_file.write( contents ) 
    except:
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )


def send_transactions_to_sql( configs : dict , trades: list  ) -> None :
    """
        Use TraderDB class to properly normalize transactions and save 
    """
    try:
        traderDB = TraderDB( server =configs['sql_server'], userName =configs['sql_user'], password =configs['sql_password'] )
        traderDB.InsertOrderbook(orderbook=trades , email=configs['email'] , username=configs['username'] )

    except:
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )




def calculate_new_poll_time( current_time : datetime = datetime.now(), time_interval : int = 900) -> datetime :
    """
        Calculate the new time to poll for quote from platform
        ARGS    :
                    current_time  : ( datetime ) the current time to use as base
                    time_interval : ( int ) the time interval to use, it must end on the quarter or on the 5  depending on time_interval 
        RETURNS :
                    datetime
    """
    deltas      = 0
    fake_time   = None 
    try:
        fake_time   = current_time + timedelta( seconds =time_interval)
        deltas      = fake_time.minute % ( time_interval /60 )        
        deltas      = time_interval - (deltas * 60 )
    except:
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )
            
    return current_time + timedelta( seconds =deltas ), deltas






def options_trading ( configs : dict  ) -> None :
    """
        Interface to allow options ( CA::/PUTS) trading
        ARGS    :
                    configs     :  dictionary of configuration info                   
        RETURNS    :
                    Nothing
    """
    optionsDlg = OptionsTrade()

    optionsDlg.Run( width=1100, height=500)






def  live_trade( configs : dict  ) -> None :
    """
        Trade live on the trading platform ( buys and sells ) - Set params to move to the next level
        ARGS   :
                    configs  ( dict ) - configuration values 
        RETURNS:
                    nothing 
    """
    params  = { 'mode' : 'TRADE' , 'time_interval' : 900, 'account_funds' : 250 , 'funds_ratio': 1.0}
    trade_center( configs , params  )



    
def  live_test ( configs : dict  ) -> None :
    """
        Test the strategy by using live data 
        Provide  charts for confirmation
        1. pull quotes 
        2. 
        ARGS   :   
                    configs     :  dictionary of configuration info                   
        RETURNS:
                    Nothing 
    """
    params  = { 'mode' : 'TEST','time_interval' : 900 , 'account_funds' : 5000 , 'funds_ratio' : 0.50}

    trade_center( configs , params  )


    
def  trade_center( configs :  dict , params : dict ) -> None :
    """
        Accept configs and params to decide to live trade or test trade
        ARGS   :
                    configs  ( dict ) - system wide configuration for trading
                    params   ( dict ) - parameters for test mode or live mode 
        RETURNS:
                    nothing 
    """    
    msg             = ""
    cont            = True
    data            = {}    
    account         = None
    success         = False
    orb_calced      = False 
    date_format     = "%Y-%m-%d %H:%M:%S"  
    

    
    try:  
        configs['stock'] = [ configs['stock'] ] if isinstance( configs['stock'], str) else configs['stock']
        
        account      = TradeAccount(funds=100, limit=0.10, app_type=configs['trading_platform'], userName = configs['username'], email=configs['email'],
                                        app_key = configs['app_key'], app_secret = configs['app_secret'] ,
                                    sqlServer =configs['sql_server'], sqlUserName =configs['sql_user'], sqlPassword =configs['sql_password'] )
        account.SetFunds( params['account_funds'], params['funds_ratio'] )  #5000.00, 0.50 )     
        account.SetMode( params['mode'] )      
        
        Strategies.Set( configs['strategy'] , account)
        print( f'\t* About to live {params["mode"]}: ', account )
        
        for stock in  configs['stock'] :
            data.update({ stock :  [] } )
         
        time_interval   = params['time_interval']
        current_time    = datetime.now()
        
        while ( cont )  :
            if (current_time.hour >= 16 ) :
                cont = False                
            elif (current_time.hour < 9  and current_time.minute < 30  ) or ( current_time.hour >= 17 ) :                
                cont = False
                print("\t\t\t\t -> Outside of market hours ")
                ## Sell whatever is InPlay
            elif ( current_time.hour == 15 and (current_time.minute  +  (time_interval / 60 )) >=  55)  :               #MARKET CLOSES AT 4PM, SELL WHAT YOU ARE HOLDING (???)
                # IF THE NEXT TIME INTERVAL CAUSES US TO BE OUTSIDE OF THE MARKET TIME THEN SELL NOW
                print("\t\t\t > Market closing ; shifting InPlay -> Trades" )
                if  account.InPlay != {} :
                    stocks = set( account.InPlay.keys() )
                    for symbol in stocks:
                        ticker_row = account.Quote ( symbols= symbol)[symbol]
                        account.Sell(stock=symbol, new_price=float(ticker_row[3])  if ticker_row != None else account.InPlay[symbol]['price'] ,
                                     ask_volume=ticker_row[5], indicators=Strategies.Stocks[symbol]['Indicators'] )
                cont = False
            elif  not orb_calced :#(current_time.hour == 9  and (current_time.minute >= 30  or current_time.minute  <= 59 ) ):    # ORB CALCULATIONS
                Strategies.SetORB(configs['stock'], account, current_time)
                orb_calced = True
            else:
                current_time    = datetime.strptime( str(current_time)[:17] +"00", date_format) 
                symbols         = [ configs['stock'] ] if isinstance( configs['stock'], str) else configs['stock']
                bought_action   = False 
                for symbol in symbols:
                    print(f"\t\t + {symbol}  @ { current_time } " )                    
                    ticker_row = account.QuoteByInterval ( symbols=symbol,  frequency=time_interval, endDate = current_time)
                    
                    if ticker_row != None:                    
                        print(f"\t\t\tTICKER_ROW :{ticker_row}")                
                        success , msg , time_interval = Strategies.Run(  ticker_row,  account, configs )
                        
                        data[symbol].append( {'stock':symbol,'datetime':f"{current_time}",'low': float(ticker_row[2]),'quote':float(ticker_row[4]),
                                            'high':float(ticker_row[6]),'close':float(ticker_row[3]),
                                              'volume':float(ticker_row[5]), 'interval': time_interval/60 , 'msg':msg } )
                        if msg.upper() == "BOUGHT" :
                            bought_action = True 
                            print(f"\t\t\t In Play - should shift from 15 -> {time_interval} min  : " )                            
                        elif msg.upper() == "CLOSED" :
                            bought_action |= False          #KEEP TRACK IF NEED TO CHANGE THE INTERVAL BECAUSE BOUGHT ONE OF THE SYMBOLS 
                            print(f"\t\t\t OUT Play - should shift from {time_interval} -> 15 min  : " )
                    else:
                        print(f"\t\t\t Did not get ticker info for symbol { symbol }, CHECK SYMBOL AND TRY AGAIN ")
                        return 
                # If TargetGoal == 0 then sleep for 30 minutes and readjust DailyFunds, TargetGoal  and Limit
                if account.TargetGoal == 0 :
                    account.SetFunds( params['account_funds'] - (params['account_funds'] * 0.10), params['funds_ratio'] - 0.10 )  #5000.00, 0.50 )
                    account.SetTargetGoal( target = 0.5  ) # Target making 50% of our funds ( SetFunds) before auto quitting 
                    current_time_temp   , sleep_interval   = calculate_new_poll_time( current_time , 1800)  # 30 ( or 15 ? ) min  cool down period 
                else:
                    current_time_temp   , sleep_interval   = calculate_new_poll_time( current_time , time_interval)                 
                
                #current_time_temp   , sleep_interval   = calculate_new_poll_time( current_time , time_interval)                 
                print(f"\t\t | Sleeping from : {sleep_interval} - { datetime.now() }",  )
                time.sleep( sleep_interval )
                print(f"\t\t \\--> AWAKE  : {time_interval} - { datetime.now() } -> {sleep_interval}",  )                
    #            else:
    #                cont = False
    #                print( 'Just received  empty ticker info ')
                    
            current_time    = datetime.now()




        
        if params['mode']  == 'TRADE':
            #RECONCILE WHAT WE LOGGED WITH HOW THE BROKERAGE EXECUTED OUR TRADES
            account.Reconcile()
            
            # SEND TRANSACTIONS TO SQL
            if len( account.Trades) > 0 :
                send_transactions_to_sql( configs, account.Trades  )

            # SEND DATA TO FILE
            send_data_to_file( configs, data )

        
        # SEND EMAIL OF PERFORMANCE
        summary_report( configs, data, account )
    except:
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )





def  replay_test( configs: dict  ) -> None :
    """
        Test the strategy by using live data from a previous day
        Provide  charts for confirmation
        1. pull quotes 
        2. 
        PARAMETERS :                    
                    configs     :  dictionary of configuration info                   
        RETURNS    :
                    Nothing 
    """
    msg             = ""
    cont            = True
    data            = {}
    isFirst         = True  # First quote requested should be on the 1 min chart 
    success         = False
    account         = TradeAccount(funds=5000, limit=0.10, app_type=configs['trading_platform'],userName = configs['username'], email=configs['email'],
                                        app_key = configs['app_key'], app_secret = configs['app_secret'] )
                                    #sqlServer =configs['sql_server'], sqlUserName =configs['sql_user'], sqlPassword =configs['sql_password'] )
    date_format     = "%Y-%m-%d %H:%M:%S"
    current_time    = ""
    
    account.SetFunds( 5000.00, 0.50 )
    try:        
        print( '\t* About to Replay test: ', account )
        Strategies.Set( configs['strategy'] , account)        
        account.SetMode( "TEST")
        for stock in ( [ configs['stock'] ] if isinstance( configs['stock'], str) else configs['stock'] ):
            data.update({ stock :  [] } )

        current_time = configs['replay_date'][:10] + " 09:30:00"
        current_time = datetime.strptime( current_time, date_format)                                             
        time_interval = 900
        
        while ( cont )  :
            #print("\t\t\t\t + Current Time : " , current_time ) 
            if (current_time.hour < 9  and current_time.minute < 30 ) or ( current_time.hour >= 17 ) :                
                cont = False
                print("\t\t\t\t -> Outside of market hours ")
            elif (current_time.hour == 9  and (current_time.minute >= 30  or current_time.minute  <= 59 ) ):    # ORB CALCULATIONS
                Strategies.SetORB(configs['stock'], account, current_time)    
            elif ( current_time.hour == 15 and (current_time.minute   +  (time_interval / 60 )) >= 55)   :      # Sell whatever is InPlay
                print("\t\t\t > Market closing ; shifting InPlay -> Trades" )
                if  account.InPlay != {} :
                    symbols = [ configs['stock'] ] if isinstance( configs['stock'], str) else configs['stock']
                    for symbol in symbols:
                        print(f"\t\t + {symbol}  @ { current_time } " ) 
                        ticker_row = account.QuoteByInterval ( symbols= symbol,  frequency= time_interval , endDate = current_time) 
                        if ticker_row != [] :
                            account.Sell( stock=symbol, new_price=float(ticker_row[3])  if ticker_row != None else account.InPlay[symbol]['price'] ,
                                              ask_volume=ticker_row[5], indicators=Strategies.Stocks[symbol]['Indicators'] )
                        else:
                            print(f"\t\t\t Ticker Empty " ) 
                cont = False
            else:
                symbols = [ configs['stock'] ] if isinstance( configs['stock'], str) else configs['stock']
                for symbol in symbols:
                    print(f"\t\t + {symbol}  @ { current_time } " )
                    if isFirst :
                        ticker_row = account.Quote ( symbols= symbol)[symbol]
                        isFirst = False 
                    else:
                        ticker_row = account.QuoteByInterval ( symbols= symbol,  frequency= time_interval , endDate = current_time)
                    print(f"\t\t\t->DATA : {ticker_row} " ) 
                    if ( ticker_row != None and ticker_row != [] ): 
                       # print(f"\t\t\t->DATA : {ticker_row} " ) 
                        success , msg , time_interval = Strategies.Run(  ticker_row,  account , configs)                   
                        data[symbol].append( {'stock':symbol,'datetime':f"{current_time}",'low': float(ticker_row[2]),'quote':float(ticker_row[4]),
                                            'high':float(ticker_row[6]),'close':float(ticker_row[3]),
                                              'volume':float(ticker_row[5]), 'interval': time_interval/60 , 'msg':msg } )
                        if msg.upper() == "BOUGHT" :
                            print(f"\t\t\t   -> In Play - should shift from 15 -> {time_interval/60} min  : " )                        
                        elif msg.upper() == "CLOSED" :
                            print(f"\t\t\t   -> OUT Play - should shift from {time_interval/60} -> 15 min  : " )
                        
                        
                """    
                if account.TargetGoal == 0 :
                    account.SetFunds(4500 , .40)  #5000.00, 0.50 )
                    account.SetTargetGoal( target = 0.5  ) # Target making 50% of our funds ( SetFunds) before auto quitting 
                    current_time   , sleep_interval   = calculate_new_poll_time( current_time , 1800) #30 min break
                else:
                """
            current_time , sleep_interval   = calculate_new_poll_time( current_time , time_interval)                    
                        
                #else:
                #    cont = False
                #    print( 'Just received  empty ticker info ')

        #RECONCILE WHAT WE LOGGED WITH HOW THE BROKERAGE EXECUTED OUR TRADES
        account.Reconcile()
        
        # SEND TRANSACTIONS TO SQL
        #send_transactions_to_sql( configs, account.Trades  )

        # SEND DATA TO FILE
        #send_data_to_file( configs, data )

        
        # SEND EMAIL OF PERFORMANCE
        summary_report( configs, data, account )
    except:
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )







def  back_test( configs: dict  ) -> None :
    """
        Run the selected data through the day_trade_strategy to see outcome
        Provide  charts for confirmation
        1. load data
        2. 
        PARAMETERS :                    
                    configs     :  dictionary of configuration info
                    
        RETURNS    :
                    Nothing 
    """
    msg         = "" 
    data        = None
    new_data    = {}
    success     = False 
    account     = TradeAccount(funds=5000, limit=0.10, app_type=configs['trading_platform'], userName = configs['username'], email=configs['email'],
                                        app_key = configs['app_key'], app_secret = configs['app_secret'] )# ,
                                    #sqlServer =configs['sql_server'], sqlUserName =configs['sql_user'], sqlPassword =configs['sql_password'] )
    interval    = 900
    thorHammer  = { }
    account.SetFunds( funds=5000.00, limit=0.10 )

    
    try:
        # LOAD TEST DATA
        if configs['input_data'] == '' or  configs['input_data'] is None :
            print( '\t\t * No input data supplied, cannot back test')
            return
        
        data = read_csv( configs['input_data'] )        
        data = data.sort_values( by=['DATETIME'], ascending=True)        
        print( '\t* About to back_test: ', account )
        Strategies.Set( configs['strategy'] , account)
        account.SetMode( "TEST")
        for index, row in data.iterrows() :
            for symbol in configs['stock']:
                if not ( symbol in new_data ):
                    new_data[  symbol ]       = []
                    thorHammer [  symbol ]    = { 'high' : -1,'low':-1, 'close': -1,'volume': -1 }

                
                ticker_row = [f"{row['SYMBOL']}",f"{row['DATETIME']}",float(row['LOW']),float(row['CLOSE']),
                                  float(row['QUOTE']),float(row['VOLUME']),float(row['HIGH']), row['MSG'] if 'MSG' in row else '']
                print(f"\t\t\t->DATA : {ticker_row} " ) 
                """  figure if this is useful at all
                if ( row['open'] == row['low']) :
                    print(f"\t\t\t******* Thor's Hammer : {  configs['stock'] } -> { row }")
                    thorHammer [  configs['stock'] ]    = {'high' : float(row['high']),'low':float(row['low']), 'close': float(row['close']),'volume': float(row['volume']) }
                if ( row['low']  <   thorHammer [  configs['stock'] ].get( 'low', -1)):
                     print(f"\t\t\t****** TRIGGERED -Less THan  {row['low']}  -> { thorHammer [  configs['stock'] ].get( 'low', -1)}" )
                """          
            
                #print( f"\t\t Data :  {ticker_row} ")
                success , msg , interval = Strategies.Run(  ticker_row,  account, configs )
                
                new_data[symbol].append( {'stock':symbol,'datetime':f"{ticker_row[1]}",'low': float(ticker_row[2]),'quote':float(ticker_row[4]),
                                            'high':float(ticker_row[6]),'close':float(ticker_row[3]),
                                          'volume':float(ticker_row[5]), 'interval': interval/60 , 'msg': msg } )
                if msg.upper() == "BOUGHT" :
                    print("\t\t\t In Play - should shift from 15 -> 5 min  : " )
                elif msg.upper() == "CLOSED" :
                    print("\t\t\t OUT Play - should shift from 5 -> 15 min  : " )

        #RECONCILE WHAT WE LOGGED WITH HOW THE BROKERAGE EXECUTED OUR TRADES
        account.Reconcile()
                
        # SEND TRANSACTIONS TO SQL
        #send_transactions_to_sql( configs, account.Trades  )
        
        # SEND EMAIL OF PERFORMANCE
        summary_report( configs, new_data, account )
    except:
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )




def  sync_broker_transactions( configs: dict  ) -> None :
    """
        Sync the local database with the transactions from the selected brokerage account
        ARGS   :
                configs  ( dict ) - dictionary of configuratios
        RETURNS:
                nothing 
    """
    account         = None
    traderDB        = None
    
    try:        
        account     = TradeAccount(funds=5000, limit=0.10, app_type=configs['trading_platform'], app_key = configs['app_key'], app_secret = configs['app_secret'])
        traderDB    = TraderDB( server =configs['sql_server'], userName =configs['sql_user'], password =configs['sql_password'] )
        print( f'\t* Syncing transactions from  {configs["sync_interval"] } days prior for :', account )

        if not account :
            print("\t\t\t Could not connect to provided user's trading account ")
            return

        if not traderDB : 
            print(f"\t\t\t Could not connect to provided SQL instance {configs['sql_server']} ")
            return
                  
        #GET TRANSACTIONS FROM BROKERAGE 
        orders = account.Orders( time_interval=int(configs.get('sync_interval',10)))
        #print( orders ) 

        #Send the brokerages transactions to TraderDB for processing 
        traderDB.SyncEntries(orders=orders, time_interval=int(configs.get('sync_interval',10)), username=configs['username'], email=configs['email'] )
        
    except:
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )






def summary_report ( configs : dict , data : dict , account : object ) -> None :
    """
        Prep and send report of trading
        ARGS   :
                    configs  ( dict )         - configuration info
                    data     ( dict )         - quote entries to store in csv file
                    account  ( TradeAccount ) - Trading Account that abstracts Schwab 
        RETURNS:
                    nothing 
    """
    try:
        print( '\t* Summary Report: ')
        #CONFIRM THE REPORT FOLDER EXISTS
        username = configs['username'] if configs['username'] != '' else configs['email']
        if not os.path.exists(f"../reports/{configs['action']}/"):
            os.mkdir(f"../reports/{configs['action']}/")

        if isinstance( configs['stock'] ,str ) :
            if configs['stock'] in data:
                report = PDFReport( f"../reports/{configs['action']}/{str(datetime.now())[:19]}_{username}_{configs['strategy']}_{ configs['stock']  }.pdf")
                summary_report_engine(  configs['stock']  , data  , account  , report  ) 
        elif isinstance( configs['stock'] , list ) :
            for symbol in configs['stock'] :
                if symbol in data:
                    report = PDFReport( f"../reports/{configs['action']}/{str(datetime.now())[:19]}_{username}_{configs['strategy']}_{symbol}.pdf")
                    summary_report_engine( symbol  , data  , account  , report  ) 

    except: 
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )


def Bollinger_Bands(data : pd.DataFrame , look_back_interval : int ):
    """
        Plot the Bollinger Bands from the data provides
        ARGS   :
                  data                ( Pandas.DataFrame )  timeseries data for symbol
                  look_back_interval  ( int )               context to use for data
        RETURNS:
                    dataframe with  Bollinger Bands high/low 
    """    
    # Calculating the moving average
    MA = data['close'].rolling(window=look_back_interval).mean()
    
    # Calculating the standard deviation
    SD = data['close'].rolling(window=look_back_interval).std()

    data['Lower_BB'] = MA - (2 * SD)  # Lower Bollinger Band
    data['Upper_BB'] = MA + (2 * SD)  # Upper Bollinger Band

    return data




def plotting( ax  : object , plot_lines : list , x_label : str , y_label : str , has_grid : bool , title : str  ) -> object :
    """
        Basic lines to get a line graph draw ( can have multiple lines )
        ARGS  :
                plot_lines  ( list of list ) the data and color for each plot line series  ( like Bollinger bands )
                x_label     ( str )           label on the x axis
                y_label     ( str )           label on the y axis
                has_grid    ( bool )          True/False to show grid lines on chart
                title       ( str )           Title of the chart
        RETURNS:
                matplotlib chart object 
    """
    try:
        for line in plot_lines :            
            ax.plot(line[0]   , color=line[1])   # replace dt1 with df_bollinger
            
        
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.grid( has_grid ) 
        ax.set_title(title)
    except: 
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )
    finally:
        return ax

    
def summary_report_engine(symbol : str, data : dict , account : object , report : object ) -> None :
    """
        The contents ofthe summary report process that allows it to be repeatable if necessary
        ARGS   :
                    symbol   ( str )          - stock symbol 
                    data     ( dict )         - quote entries to store in csv file
                    account  ( TradeAccount ) - Trading Account that abstracts Schwab
                    report   ( PDFReport )    - PDF Report class for the symbol 
        RETURNS:
                    nothing 
    """
    try:
        dt1     = []
        dt1_2   = []
        dt2     = []
        dt3     = []
        off_on  = True

        if not ( symbol in data )  or not (symbol in account.Trades) :
            print(f"\t\t\t {symbol} No data for Symbol  ")
            return

        if len(account.Trades[symbol]) == 0 :
            print(f"\t\t\t {symbol} No TRADING data for Symbol  ")
            return 
        
        for entry in data[symbol] :
            #print("\t\t ADDING DT1 : " , entry )
            dt1.append(  entry.get('close',0)  )
            
        for entry in account.Trades[symbol]:    
            #print("\t\t ADDING DT2 / DT3: " , entry )        
            dt2.append( entry.get("p_l", 0) )
            dt3.append( entry.get("actualPL", 0) )

        
        df_bollinger =  Bollinger_Bands( pd.DataFrame( {'close' : dt1} ), look_back_interval=6)
                 
        pixplt =plt
        fig, (ax1, ax2,ax3) = pixplt.subplots(3, 1)
        
        # GRAPH 1
        plot_lines =  [[df_bollinger['close']   , 'orange'], [df_bollinger['Lower_BB'], 'blue'],[df_bollinger['Upper_BB'], 'green' ]]        
        ax1 = plotting( ax = ax1 , plot_lines = plot_lines , x_label="time" , y_label="dollars", has_grid=True , title=f"{symbol} Activity "  )
        
        # GRAPH 2
        ax2 = plotting( ax=ax2 , plot_lines=[[dt2,"green"]], x_label="time" , y_label="dollars", has_grid=True , title=f"{symbol} P & L"  )
        
        # GRAPH 3
        ax2 = plotting( ax=ax3 , plot_lines=[[dt3,"green"]], x_label="time" , y_label="dollars", has_grid=True , title=f"{symbol} Actual P & L" )
        
        
        chart_graph = "../pix/graph1.png"
        pixplt.tight_layout()
        #pixplt.show()
        fig.savefig( chart_graph )
        report.AddImage( chart_graph )
        
        #report.AddLineChart2( symbol ,  dt  , ['A','B','C'])
        
      
            
        # Pie chart
        report.AddText( "Wins vs Losses ", "h1", 1)    
        stats = ''
        opts = ['WIN','LOSS' ]
        for opt in opts :
            stats = [account.Performance[symbol].count( opt ) for opt in opts ]            
            plt.pie( stats, labels=opts, autopct='%1.1f%%', startangle=90)
        plt.title( symbol  )
        plt.axis ('equal')
        #plt.show ()        
        report.AddPieChart( stats, opts)

        
        # LIST OF COMPLETED ORDERS
        report.AddText( "OrderBook ", "h1", 1)    
        contents        = ""
        total_profit    = 0
        print(f"\t {symbol} ORDERBOOK")
        print(f"\t    == OPENED ==\t=== BID=== \t== CLOSED == \t==== ASK ====\t== QUANTITY ==\t=== P & L ====\t\t= ACTUAL P&L =" )            
        for entry in account.Trades[symbol]:
            print(f"\t   {entry['bidTime'][:19] }\t${entry['bid'] :.4f}\t\t" +
                  f"{entry['askTime'][11:19]}\t${entry['ask']:.4f}\t\t\t{entry['qty']}\t"+
                  f"${entry['p_l']:.4f}\t\t${ entry.get('actualPL',0):.4f}" )            
            total_profit += entry.get("p_l")

        # LIST OF INPLAY
        print(f"\n\t {symbol}  InPLAY")
        for inplay in account.InPlay:
            print( "\t -  " , inplay ) 

        print( "* Account : " , account  , " : " , account.Funds , " : " ,
                   total_profit  , " : " , round((total_profit/(account.Funds - total_profit))* 100,5) ,"%")

        header = ['STOCK','TIME','PRICE','QTY','CLOSED','ASK','P&L']
        row     = [] 
        table  = []

        table.append( header ) 
        for rec in account.Trades[symbol] :
            row = [] 
            for key in ['symbol', 'bidTime','bid', 'qty','askTime','ask','p_l'] :
                row.append ( rec.get(key, 0) )
            table.append( row ) 
        
        report.AddTable( table , "h3", 1 )        
        contents = f"* FUNDS : ${account.Funds}           TOTAL PROFIT: ${total_profit}"
        report.AddText( contents , "h3", 2)
        report.Save()

        # DISPLAY AT THE END OF THINGS
        pixplt.show()
    except:
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )



def business_logic_test(current_time :str = "2025-08-16 15:27:35",  time_interval : int = 900 ) -> datetime:
    """
        TODO :: Scaffolding for testing
        ARGS    :
                    current_time  ( str ) the time to be altered
                    time_interval ( int ) the interval of time to increase by in seconds 
        RETURNS :
                    datetime 
    """
    date_format         = "%Y-%m-%d %H:%M:%S"
    current_time        = datetime.strptime( current_time, date_format)
    new_poll_time, _    = calculate_new_poll_time( current_time = current_time, time_interval  = 900) 
    print(f"\t\t * Business Logic Test: New Poll Time  {current_time} @ { time_interval}  == > {new_poll_time }")
    return  new_poll_time




def server_interface(   ) -> None :
    """
        Function that allows client to connect with this server 
    """    
    HOST = '127.0.0.1'  # Standard loopback interface address (localhost)
    PORT = 65432        # Port to listen on (non-privileged ports are > 1023)
    global  Configs
    try:
        print( "Inside the interface ", type(Configs) , " : " , Configs)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((HOST, PORT))
            s.listen()
            while True:
                conn, addr = s.accept()
                with conn:
                    print(f"[INTERFACE] Connected by {addr}")
                    with DataLock :
                        while True:
                            data = conn.recv(1024)
                            print(f"[INTERFACE] Received : {data}")
                            if not data:
                                print("[INTERFACE] Empty Data ")
                                #break
                            else: #if  data == b'username':
                                data = f"{Configs[data.decode() ]}".encode("utf-8")                                
                                print( f"[INTERFACE] Trying to send : { data } " )
                            
                            conn.sendall(data)
    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )
    finally:
        print('[INTERFACE] finished')



    




        

            
def main() -> None :
    """
        main logic of application 
    """       
    #required_fields = ['url','doi','project-title_01','award-number']
    
    try:
        # GET THE CONFIGURATION - EITHER DEFAULTS OR COMMAND LINE GIVEN        
        Configs = parse_arguments()       


        #IF CSV_CONFIG  USE THIS FIRST, THEN COMMAND LINE ARGS
        print( '\t * Checking csv_config ' )
        if Configs['csv_config'] != ''  :
            Configs = apply_csv_config ( Configs)
        
            
        # IF THE USER NEEDS TO KNOW WHICH FIELDS TO INCLUDE
        if Configs['csv_input_fields'] :
            print( '\t * Display csv input fields ' )
            display_csv_input_fields()

            
        # DISPLAY THE AVAILABLE STRATEGIES 
        # IN THE CLASS NEEDS TO HAVE AN EXPLANATION ABOUT EACH STRATEGY 
        if Configs['list_strategies'] :
            print( '\t * List strategies' )
            display_strategies() 

        # DISPLAY THE CONFIG IF SELECTED
        if Configs['display_config'] :
            print( '\t * Display config ' )
            display_config(  Configs)      


        #launch the interface
        #th_interface = threading.Thread( target=server_interface , args=() )

        #th_interface.start()
        #th_interface.join()

        

        # ACTION == DOWNLOAD / BACK_TEST / TRADE
        hub = {
                'options'       : options_trading,
                'download'      : download_stock_data,
                'back_test'     : back_test,
                'test'          : system_test,
                'live_test'     : live_test,
                'live_trade'    : live_trade,
                'replay_test'   : replay_test,
                'sync'          : sync_broker_transactions
            }

        hub[ Configs ['action'] ] ( Configs  ) 
        
              
        return 

        
    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )


if __name__ == "__main__":
    # execute only if run as a script        
    main()  
