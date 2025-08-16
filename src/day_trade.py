#! /usr/bin/python3
## ###################################################################################################################
##  Program :   Day Trade 
##  Author  :
##  Install :   pip3 install requests  inspect platform argparse selenium webdriver-manager reportlab 
##  Example :
##              python3 day_trade.py --csv_config=files/config.csv --display_config 
##              python3 day_trade.py --api_key=7LZZ6KE0XBTNIPBI --action=download  --stock=QQQ --csv_output=../data --interval=15min --display_config
##              python3 day_trade.py --api_key=7LZZ6KE0XBTNIPBI --action=back_test --stock=QQQ --input_data=../data/QQQ_15min_.csv --interval=15min --display_config --account_api=xxxxxxx --strategy=basic  --list_strategies
##              python3 day_trade.py --api_key=7LZZ6KE0XBTNIPBI --action=back_test --interval=15min --display_config --account_api=xxxxxxx --strategy=basic  --list_strategies --input_data=../data/intraday_15min_QQQ.csv --stock=QQQ
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

from MySQLConn          import MySQLConn
from datetime           import datetime, timedelta
from PDFReport          import PDFReport
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
                        'strategy'          : { 'help': 'Strategy to use ',                         'action' : None },
                        'app_key'           : { 'help': 'Schwab application key ',                  'action' : None },
                        'app_secret'        : { 'help': 'Schwab application Secret ',               'action' : None },
                        'trading_platform'  : { 'help': 'Platform of your trading account [ Schwab]','action' : None},
                        'app_secret'        : { 'help': 'Schwab application Secret ',               'action' : None },
                        'replay_date'       : { 'help': 'Date to pull quotes to do a replay_test',  'action' : None },
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


        return configs

    except:
        print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )






def system_test( configs : dict ) -> None :
    """
        Transiant - tests the integration of different code 
    """
    account = TradeAccount(funds=5000, limit=0.10, app_type='Schwab', app_key = configs['app_key'], app_secret = configs['app_secret'])







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





    
def send_transactions_to_sql( configs : dict , trades: list  )   -> None :
    """
        SEND THE COMPLETED TRANSACTIONS TO SQL FOR REPORTING AND ANALYSIS LATER
        ARGS   :
                configs : configuration dictionary
                trades  : list of entries 
        RETURNS:
                Nothing

        create table orderbook ( id int auto_increment primary  key, yrmo  varchar(10), fulldate varchar(10) ,symbol varchar(10), initiatedAt varchar(20),bought decimal(10,2),qty int, closedAt varchar(20), sold  decimal(10,2), p_l decimal(10,2), time_interval int  );

    """    
    conn        = MySQLConn( )
    indx        = 0
    line        = ""
    query       = ""

    
    try:
        if len( trades ) == 0 :
            return

        if configs['sql_server'] == "" or  configs['sql_user'] == ""  or configs['sql_password'] == "" :
            return 
        
        conn.Connect(server =configs['sql_server'], database='trading', username =configs['sql_user'], passwd =configs['sql_password'] )
        query = "INSERT INTO trading.orderbook ( yrmo,fulldate,symbol, initiatedAt, bought, qty, closedAt, sold, p_l) values "
        
        for entry in trades :
            line = f"'{entry[1][:7]}','{entry[1][:10]}'"          
            for field in entry :
                if len( line) > 1  :
                    line += ','
                line +=  "'" + (str(field)[:19] if len(str(field)) > 19 else str(field) ) +"'"
            query += ( ',' if indx > 0 else '') + '(' + line + ')'
            indx += 1
            
        print(f" QUERY : { query } " )
        conn.Write( query ) 
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
    
    account.SetFunds( 5000.00, 0.10 )
    try:        
        print( '\t* About to live test: ', account )
        Strategies.Set( configs['strategy'] , account)        
        account.SetMode( "TEST")
        for stock in configs['stock'].split(",") :
            data[stock] = []

        current_time = configs['replay_date'][:10] + " 09:30:00"
        current_time = datetime.strptime( current_time, date_format)                                             
        time_interval = 900
        
        while ( cont )  :
            #print("\t\t\t\t + Current Time : " , current_time ) 
            if (current_time.hour < 9  and current_time.minute < 30 ) or ( current_time.hour >= 17 ) :                
                cont = False
                print("\t\t\t\t -> Outside of market hours ")
                ## Sell whatever is InPlay
            else:
               # print(f"\t\t -> Quote @ { current_time }" )
                td = account.Quote ( symbols= configs['stock'],  frequency= time_interval , endDate = current_time)
                if td != None:
                    ticker_row = [ stock,f"{datetime.now()}",f"{td['low']}",f"{td['close']}",f"{td['open']}",f"{td['volume']}"]
                    data[stock].append( {'stock':stock,'datetime':f"{datetime.now()}",'low': float(td['low']),'quote':float(td['open']),
                                                             'high':float(td['high']),'close':float(td['close']),'volume':float(td['volume']), 'interval': time_interval/60 })
                  #  print(f"\t\t\t->DATA : {ticker_row} " ) 
                    success , msg , time_interval = Strategies.Run(  ticker_row,  account )
                    if msg.upper() == "BOUGHT" :
                        print(f"\t\t\t In Play - should shift from 15 -> {time_interval} min  : " )                    
                    elif msg.upper() == "CLOSED" :
                        print(f"\t\t\t OUT Play - should shift from {time_interval} -> 15 min  : " )                    
                    
                #    print(f"\t\t -> time interval { time_interval }" )
                    current_time = current_time + timedelta( seconds=time_interval)
                        
                else:
                    cont = False
                    print( 'Just received  empty ticker info ')
        
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


            

def  live_test( configs: dict  ) -> None :
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
    msg         = ""
    cont        = True
    data        = {}
    success     = False    
    account     = TradeAccount(funds=5000, limit=0.10, app_type=configs['trading_platform'], app_key = configs['app_key'], app_secret = configs['app_secret'])  
    
    
    account.SetFunds( 5000.00, 0.10 )

    
    try:        
        print( '\t* About to live test: ', account )
        Strategies.Set( configs['strategy'] , account)        
        account.SetMode( "TEST")
        for stock in configs['stock'].split(",") :
            data[stock] = []

         
        time_interval = 900 
        while ( cont )  :
            current_time = datetime.now()
            if (current_time.hour < 9  and current_time.minute < 30 ) or ( current_time.hour >= 17 ) :                
                cont = False
                print("\t\t\t\t -> Outside of market hours ")
                ## Sell whatever is InPlay
            else:
                td = account.Quote ( symbols=configs['stock'],  frequency=time_interval, endDate = current_time)
                if td != None:
                    ticker_row = [ stock,f"{datetime.now()}",f"{td['low']}",f"{td['close']}",f"{td['open']}",f"{td['volume']}"]
                    data[stock].append( {'stock':stock,'datetime':f"{datetime.now()}",'low': float(td['low']),'quote':float(td['open']),
                                                             'high':float(td['high']),'close':float(td['close']),'volume':float(td['volume']), 'interval': time_interval/60 })
                
                    success , msg , time_interval = Strategies.Run(  ticker_row,  account )
                    if msg.upper() == "BOUGHT" :
                        print(f"\t\t\t In Play - should shift from 15 -> {time_interval} min  : " )                    
                    elif msg.upper() == "CLOSED" :
                        print(f"\t\t\t OUT Play - should shift from {time_interval} -> 15 min  : " )                    
                    print(f"\t\t Sleeping from : {time_interval} - { datetime.now() }",  )
                    time.sleep( time_interval )
                    print(f"\t\t  AWAKE  : {time_interval} - { datetime.now() } -> {time_interval}",  )                
                else:
                    cont = False
                    print( 'Just received  empty ticker info ')
        
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
            
            ticker_row = [f"{configs['stock']}",f"{row['timestamp']}",float(row['high']),float(row['low']),float(row['close']),float(row['volume'])]
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
    """
    stock = configs['stock']
    report = PDFReport( f"../reports/{stock}_{str(datetime.now())[:19]}.pdf")
    try:
        dt1 = []
        dt2 = []
        for entry in data[configs['stock']] :
            dt1.append( entry.get('high',0) )
        for entry in account.Trades:
            if entry[0] == configs['stock'] :
                dt2.append( entry[6] )
            
        fig, (ax1, ax2) = plt.subplots(2, 1)
        # GRAPH 1
        ax1.plot(dt1, color='blue')
        ax1.set_xlabel('time')
        ax1.set_ylabel('dollars')
        ax1.set_title(f"{configs['stock']} Activity ")
        # GRAPH 2
        ax2.plot(dt2, color='blue')
        ax2.set_xlabel('index')
        ax2.set_ylabel('dollars')
        ax2.set_title(f"{configs['stock']} P & L")
        
        chart_graph = "../pix/graph1.png"
        plt.tight_layout()
        plt.show()
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
        for entry in account.Trades:
            print("\t -  ", entry )            
            total_profit += entry[6]
        print( "* Account : " , account  , " : " , account.Funds , " : " , total_profit)
        
        report.AddTable( [['STOCK','TIME','PRICE','QTY','CLOSED','ASK','P&L']] +  account.Trades, "h3", 1 )        
        contents = f"* FUNDS : ${account.Funds}           TOTAL PROFIT: ${total_profit}"
        report.AddText( contents , "h3", 2)
        report.Save()
    except:
        print("\t\t|EXCEPTION: day_trade::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
        for entry in sys.exc_info():
            print("\t\t >>   " + str(entry) )



def business_logic_test( val1, val2 ,val3) -> int|float:
    """
        TODO :: Scaffolding for testing
    """
    return val1 + val2 +val3




            
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
                'download'  : download_stock_data,
                'back_test' : back_test,
                'test'      : system_test,
                'live_test' : live_test,
                'replay_test': replay_test
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
