#! /usr/bin/python3
## ###################################################################################################################
##  Program :   Day Trade 
##  Author  :
##  Install :   pip3 install requests  inspect platform argparse selenium webdriver-manager reportlab 
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
#import getpass
import inspect
import platform
import argparse
import functools
import requests

#import http.client
#import urllib.request
#from urllib.parse import urlparse

import pandas               as pd
#import numpy  as np 
import  matplotlib.pyplot   as plt


from datetime           import datetime, timedelta
from PDFReport          import PDFReport
from TraderDB           import TraderDB
from TradeAccount       import TradeAccount
from DayTradeStrategy   import DayTradeStrategy


Strategies = DayTradeStrategy()

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
                df = pd.read_csv( fileName, encoding = "ISO-8859-1" )
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
                    'email'             : '',
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


def apply_csv_config ( configs : dict) -> dict:
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
              
            
                
        return config_new
    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )        
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) ) 

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
			'action'            : { 'help': 'Options: download/back_test/trade/test/live_test' ,  'action' : None}, 
			'start_date'        : { 'help': 'Start date', 	                            'action' : None}, 
			'end_date'          : { 'help': 'End date' ,  			            'action' : None}, 
			'interval'          : { 'help': 'Time interval [ 5min / ]',           	    'action' : None }, 
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

def system_test( configs : dict  ) -> None :
    account     = TradeAccount(funds=5000, limit=0.10, app_type='Schwab', app_key = configs['app_key'], app_secret = configs['app_secret'])
    print('Preferences: ', account.Conn.Preference )

    account.Conn.Quote('AMD')

"""
/trader/v1/userPreference 
{
    "requests":[
        {
            "requestid" :'1",
            "service" : "ADMIN",
            "command" :"LOGIN",
            "SchwabClientCustomerId":"XXX",
            "SchwabClientCorrelId" : "XXX",
            "parameters":{
                "Authorization" :"access-token ",
                "SchwabClientChannel":"N9",
                'SchwabClientFundtionId" :"APIAPP"
                },
            }
        ]
    }
{
    "requests":[
        {            
            "service" : "LEVELONE_EQUITIES",
            "requestid" : 1, << incremented for each request
            "command" :"ADD",  << unsub / view
            "SchwabClientCustomerId":"XXX",
            "SchwabClientCorrelId" : "XXX",
            "parameters":{
                "keys" :"AMD,INTC",
                "fields" : '0,1,2,3,4,5,8"
                },
            }
        ]
    }
"""

"""
def system_test1( configs : dict  ) -> None :

    #account     = TradeAccount(funds=5000, limit=0.10, app_type='Schwab', app_key = configs['app_key'], app_secret = configs['app_secret'])
   
    client = easy_client(
        api_key      = configs['app_key'],
        app_secret   = configs['app_secret'],
        callback_url ='https://127.0.0.1:8114',
        token_path   ='/files/account_tokens.json',
        interactive=False)
    
    stream_client = StreamClient(client, account_id=88867477, show_linked=False)

    print ( stream_client.quote("AMD").json() )
    
    asyncio.run(read_stream( stream_client))
"""


def system_test_old( configs : dict ) -> None :
    """
        Transiant - tests the integration of different code 
    """
    email       = 'seanburner@gmail.com'
    orderbook   = [
                    ['OPEN', '2025-09-05 10:45:00', 6.1501, 406, '2025-09-05 11:00:00', 6.325,  71.00940000000037],
                    ['OPEN', '2025-09-05 11:15:00', 6.442,  388, '2025-09-05 11:45:00', 6.4725, 11.833999999999833],
                    ['OPEN', '2025-09-05 12:15:00', 6.46,   386, '2025-09-05 12:45:00', 6.515,  21.230000000000018],
                    ['OPEN', '2025-09-05 13:15:00', 6.585,  379, '2025-09-05 13:30:00', 6.6254, 15.311599999999999],
                    ['OPEN', '2025-09-05 13:45:00', 6.7375, 371, '2025-09-05 14:45:00', 6.655,  -30.607499999999618],
                    ['OPEN', '2025-09-05 15:00:00', 6.69,   373, '2025-09-05 15:30:00', 6.6,    -33.57000000000062],
                    ['OPEN', '2025-09-05 15:45:00', 6.64,   376, '2025-09-05 18:39:47', 6.64,   0.0]
                ]
    account     = TradeAccount(funds=5000, limit=0.10, app_type='Schwab', app_key = configs['app_key'], app_secret = configs['app_secret'])
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
            contents    = "SYMBOL, DATETIME, LOW ,QUOTE, HIGH ,CLOSE , VOLUME , INTERVAL"
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
    traderDB = TraderDB( server =configs['sql_server'], userName =configs['sql_user'], password =configs['sql_password'] )

    traderDB.InsertOrderbook(orderbook=trades , email=configs['email']  )





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
        PARAMETERS :                    
                    configs     :  dictionary of configuration info                   
        RETURNS    :
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
    account         = TradeAccount(funds=100, limit=0.10, app_type=configs['trading_platform'], app_key = configs['app_key'], app_secret = configs['app_secret'])
    success         = False
    date_format     = "%Y-%m-%d %H:%M:%S"  
    
    
    account.SetFunds( params['account_funds'], params['funds_ratio'] )  #5000.00, 0.50 )

    
    try:  
        Strategies.Set( configs['strategy'] , account)        
        account.SetMode( params['mode'] )      
        print( f'\t* About to live {params["mode"]}: ', account )
        for stock in configs['stock'].split(",") :
            data[stock] = []
         
        time_interval   = params['time_interval']
        current_time    = datetime.now()
        
        while ( cont )  :            
            if (current_time.hour < 9  and current_time.minute < 30 ) or ( current_time.hour >= 17 ) :                
                cont = False
                print("\t\t\t\t -> Outside of market hours ")
                ## Sell whatever is InPlay
            elif ( current_time.hour == 16 and current_time.minute >= 15) and True :               
                if  account.InPlay != {} :
                    stocks = set( account.InPlay.keys() )
                    for stock in stocks:                        
                        account.Sell( stock, float(ticker_row[3]) )
                cont = False
            else:
                current_time = datetime.strptime( str(current_time)[:17] +"00", date_format)  
                ticker_row = account.Quote ( symbols=configs['stock'],  frequency=time_interval, endDate = current_time)
                if ticker_row != None:                    
                    print(f"\t\t\tDATE :{ticker_row}")
                    data[stock].append( {'stock':stock,'datetime':f"{current_time}",'low': float(ticker_row[2]),'quote':float(ticker_row[4]),
                                            'high':float(ticker_row[6]),'close':float(ticker_row[3]),'volume':float(ticker_row[5]), 'interval': time_interval/60 })
                
                    success , msg , time_interval = Strategies.Run(  ticker_row,  account, configs )
                    if msg.upper() == "BOUGHT" :
                        print(f"\t\t\t In Play - should shift from 15 -> {time_interval} min  : " )                    
                    elif msg.upper() == "CLOSED" :
                        print(f"\t\t\t OUT Play - should shift from {time_interval} -> 15 min  : " )   
                    current_time_temp   , sleep_interval   = calculate_new_poll_time( current_time , time_interval)                 
                    print(f"\t\t | Sleeping from : {sleep_interval} - { datetime.now() }",  )
                    time.sleep( sleep_interval )
                    print(f"\t\t \\--> AWAKE  : {time_interval} - { datetime.now() } -> {sleep_interval}",  )                
                else:
                    cont = False
                    print( 'Just received  empty ticker info ')
                    
            current_time    = datetime.now()
                    
        if params['mode']  == 'TRADE':
            # SEND TRANSACTIONS TO SQL
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
    success         = False
    account         = TradeAccount(funds=5000, limit=0.10, app_type=configs['trading_platform'], app_key = configs['app_key'], app_secret = configs['app_secret'])
    date_format     = "%Y-%m-%d %H:%M:%S"
    current_time    = ""
    
    account.SetFunds( 5000.00, 0.50 )
    try:        
        print( '\t* About to live test: ', account )
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
            #elif ( current_time.hour >= 12 and current_time.hour < 14)  and False   :               ## between 12  -> 2 seems to be loss filled
            #    sleep_time = ((14 - current_time.hour) * 60* 60 ) + (( 59 - current_time.minute))
            #    print( f'\t\t --> sleeping for {sleep_time} -> { current_time  } ->{ current_time + timedelta( seconds =sleep_time) } ')
            #    current_time +=  timedelta( seconds =sleep_time)            
            elif ( current_time.hour == 16 and current_time.minute >= 00)   :               ## Sell whatever is InPlay
                if  account.InPlay != {} :
                    stocks = set( account.InPlay.keys() )
                    for stock in stocks:                        
                        account.Sell( stock, float(ticker_row[3]) )
                cont = False
            else:
                symbols = [ configs['stock'] ] if isinstance( configs['stock'], str) else configs['stock']
                for symbol in symbols:
                    print(f"-> Quote @ { current_time } {stock} " )
                    ticker_row = account.Quote ( symbols= symbol,  frequency= time_interval , endDate = current_time)                
                    if ticker_row != None:                    
                        data[stock].append( {'stock':symbol,'datetime':f"{current_time}",'low': float(ticker_row[2]),'quote':float(ticker_row[4]),
                                            'high':float(ticker_row[6]),'close':float(ticker_row[3]),'volume':float(ticker_row[5]), 'interval': time_interval/60 })
                        print(f"\t\t\t->DATA : {ticker_row} " ) 
                        success , msg , time_interval = Strategies.Run(  ticker_row,  account , configs)
                        if msg.upper() == "BOUGHT" :
                            print(f"\t\t\t   -> In Play - should shift from 15 -> {time_interval} min  : " )                        
                        elif msg.upper() == "CLOSED" :
                            print(f"\t\t\t   -> OUT Play - should shift from {time_interval} -> 15 min  : " )
                        
                        
                    
                current_time , sleep_interval   = calculate_new_poll_time( current_time , time_interval)                    
                        
                #else:
                #    cont = False
                #    print( 'Just received  empty ticker info ')
        
        # SEND TRANSACTIONS TO SQL
        #send_transactions_to_sql( configs, account.Trades  )

        # SEND DATA TO FILE
        send_data_to_file( configs, data )

        
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
    account     = TradeAccount(funds=5000, limit=0.10, app_type=configs['trading_platform'], app_key = configs['app_key'], app_secret = configs['app_secret'])
    interval    = 900
    thorHammer  = { }
    account.SetFunds( funds=5000.00, limit=0.10 )

    
    try:
        # LOAD TEST DATA
        if configs['input_data'] == '' or  configs['input_data'] is None :
            print( '\t\t * No input data supplied, cannot back test')
            return
        
        data = read_csv( configs['input_data'] )        
        data = data.sort_values( by=['timestamp'], ascending=True)
        print( '\t* About to back_test: ', account )
        Strategies.Set( configs['strategy'] , account)
        account.SetMode( "TEST")
        for index, row in data.iterrows() :
            if not ( configs['stock'] in new_data ):
                new_data[  configs['stock'] ]       = []
                thorHammer [  configs['stock'] ]    = { 'high' : -1,'low':-1, 'close': -1,'volume': -1 }
            
            ticker_row = [f"{configs['stock']}",f"{row['timestamp']}",float(row['high']),float(row['low']),float(row['close']),float(row['volume']),float(row['high'])]
            """  figure if this is useful at all
            if ( row['open'] == row['low']) :
                print(f"\t\t\t******* Thor's Hammer : {  configs['stock'] } -> { row }")
                thorHammer [  configs['stock'] ]    = {'high' : float(row['high']),'low':float(row['low']), 'close': float(row['close']),'volume': float(row['volume']) }
            if ( row['low']  <   thorHammer [  configs['stock'] ].get( 'low', -1)):
                 print(f"\t\t\t****** TRIGGERED -Less THan  {row['low']}  -> { thorHammer [  configs['stock'] ].get( 'low', -1)}" )
            """          
            new_data[ticker_row[0]].append( {'stock':ticker_row[0],'datetime':ticker_row[1],'low': ticker_row[3],'quote': ticker_row[3],
                                                             'high':ticker_row[4],'close':ticker_row[4],'volume':ticker_row[5], 'interval': 15 })
            
            
            #print( f"\t\t Data :  {ticker_row} ")
            success , msg , interval = Strategies.Run(  ticker_row,  account )
            if msg.upper() == "BOUGHT" :
                print("\t\t\t In Play - should shift from 15 -> 5 min  : " )
            elif msg.upper() == "CLOSED" :
                print("\t\t\t OUT Play - should shift from 5 -> 15 min  : " )


        # SEND EMAIL OF PERFORMANCE
        summary_report( configs, new_data, account )
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
        #CONFIRM THE REPORT FOLDER EXISTS        
        if not os.path.exists(f"../reports/{configs['action']}/"):
            os.mkdir(f"../reports/{configs['action']}/")

        if isinstance( configs['stock'] ,str ) :
            report = PDFReport( f"../reports/{configs['action']}/{str(datetime.now())[:19]}_{configs['strategy']}_{ configs['stock']  }.pdf")
            summary_report_engine(  configs['stock']  , data  , account  , report  ) 
        elif isinstance( configs['stock'] , list ) :
            for symbol in configs['stock'] :
                report = PDFReport( f"../reports/{configs['action']}/{str(datetime.now())[:19]}_{configs['strategy']}_{symbol}.pdf")
                summary_report_engine( symbol  , data  , account  , report  ) 

    except: 
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )



            
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
        off_on  = True

        for entry in data[symbol] :
            dt1.append( float( entry.get('close',0))  )
            if off_on :
                dt1_2.append( entry.get('datetime',0)[11:16].replace(':','') )
            else:
                dt1_2.append( "")
            off_on = not off_on
        for entry in account.Trades:            
            if entry[0] == symbol :
                dt2.append( float(entry[6]) )
                
        pixplt =plt
        fig, (ax1, ax2) = pixplt.subplots(2, 1)
        # GRAPH 1
        ax1.plot(dt1, color='blue')
        #ax1.xticks([930,1100,1230,200,330,500,630])
        ax1.set_xlabel('time')
        ax1.set_ylabel('dollars')
        ax1.set_title(f"{symbol} Activity ")
        # GRAPH 2
        ax2.plot(dt2, color='blue')
        ax2.set_xlabel('index')
        ax2.set_ylabel('dollars')
        ax2.set_title(f"{symbol} P & L")
        
        chart_graph = "../pix/graph1.png"
        pixplt.tight_layout()
        #pixplt.show()
        fig.savefig( chart_graph )
        report.AddImage( chart_graph ) 
        #report.AddLineChart2( configs['stock'],  dt  , ['A','B','C'])
        
      
            
        # Pie chart
        report.AddText( "Wins vs Losses ", "h1", 1)    
        stats = ''
        opts = ['WIN','LOSS' ]        
        for stock in account.Performance.keys() :
            for opt in opts :
                stats = [account.Performance[stock].count( opt ) for opt in opts ]            
            plt.pie( stats, labels=opts, autopct='%1.1f%%', startangle=90)
            plt.title( stock )
            plt.axis ('equal')
            #plt.show ()        
        report.AddPieChart( stats, opts)

        #CHART THE STOCK
        stats = [] 
        for stock in data.keys():
            for entry in data[ stock ] :
                stats.append ( entry.get("quote", 0 ) )

      #  report.AddLineChart( [stats], ['A','B','C','D'],  500,250)

        
        # LIST OF COMPLETED ORDERS
        report.AddText( "OrderBook ", "h1", 1)    
        contents        = ""
        total_profit    = 0
        print("\t ORDERBOOK")
        for entry in account.Trades:
            print("\t -  ", entry )            
            total_profit += entry[6]

        # LIST OF INPLAY
        print("\t InPLAY")
        for inplay in account.InPlay:
            print( "\t -  " , inplay ) 

        print( "* Account : " , account  , " : " , account.Funds , " : " , total_profit)

        
        report.AddTable( [['STOCK','TIME','PRICE','QTY','CLOSED','ASK','P&L']] +  account.Trades, "h3", 1 )        
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




            
def main() -> None :
    """
        main logic of application 
    """   
    configs         = None
    #required_fields = ['url','doi','project-title_01','award-number']
    
    try:
        # GET THE CONFIGURATION - EITHER DEFAULTS OR COMMAND LINE GIVEN        
        configs = parse_arguments()       

        #IF CSV_CONFIG  USE THIS FIRST, THEN COMMAND LINE ARGS
        print( '\t * Checking csv_config ' )
        if configs['csv_config'] != ''  :
            configs = apply_csv_config ( configs)
        
            
        # IF THE USER NEEDS TO KNOW WHICH FIELDS TO INCLUDE
        if configs['csv_input_fields'] :
            print( '\t * Display csv input fields ' )
            display_csv_input_fields()

            
        # DISPLAY THE AVAILABLE STRATEGIES 
        # IN THE CLASS NEEDS TO HAVE AN EXPLANATION ABOUT EACH STRATEGY 
        if configs['list_strategies'] :
            print( '\t * List strategies' )
            display_strategies() 

        # DISPLAY THE CONFIG IF SELECTED
        if configs['display_config'] :
            print( '\t * Display config ' )
            display_config(  configs)      



        # ACTION == DOWNLOAD / BACK_TEST / TRADE
        hub = {
                'download'      : download_stock_data,
                'back_test'     : back_test,
                'test'          : system_test,
                'live_test'     : live_test,
                'live_trade'    : live_trade,
                'replay_test'   : replay_test
            }

        hub[ configs ['action'] ] ( configs  ) 
        
              
        return 

        
    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )


if __name__ == "__main__":
    # execute only if run as a script        
    main()  
