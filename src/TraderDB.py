## ###################################################################################################################
##  Program :   TraderDB 
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
import getpass
import inspect
import platform
import argparse
import functools
import requests

import pandas           as pd
import numpy            as np

from datetime           import datetime,timedelta
from MySQLConn          import MySQLConn


class TraderDB:
    def __init__( self, server : str, userName : str, password : str  ) -> None :
        """
            Initialize variables and connection to database
            ARGS    :
                    server    ( str ) representation of the mysql server location
                    userName  ( str ) low level user account for logging in
                    password  ( str ) password for user account
                    encKey    ( str ) encryption key for low level account 
            RETURNS :
                    Nothing 
        """
        self.Server     = server
        self.UserName   = userName
        self.Password   = password
        self.EncKey     = ""
        self.User       = getpass.getuser()     # CURRENT PERSON LOGGED IN 
        self.Conn       = MySQLConn( )
        self.Conn.Connect(server =self.Server, database='trading', username =self.UserName, passwd =self.Password )

        self.CheckDB()  #Confirm the tables were set up in the database
        # Probably not necessary anymore 
        self.BlankOrderBook = {'symbol':'', 'type': 0,
                               'bidTime': "2025-10-01 09:30:00",    'bid': 1.00,        'bidVolume':1000, 'bidFilled' : 1.01 , 'bidRecipt' : '111111' ,
                               'askTime':"2025-10-01 09:32:00",     'ask':1.25,         'askVolume':1000, 'askFilled' : 1.19 , 'askReceipt' :'222222',
                               'qty' :250,                          'p_l': ((1.25 - 1.00) * 250),         'actualPL'  : ((1.19-1.01)*250),                      
                               'indicators_in': {},                 'indicators_out': {}
                               }
                   

    def Sanitize ( self, field : object  ) -> object :
        """
            Takes any input and if its an instance of a str then sanitizes it
            ARGS    :
                        field (???) - any field value of any type that might need to be sanitized 
            RETURNS :
                        field (???) - sanitized if str, original if not str 
        """
        newField  = None
        
        if isinstance( field, str ) :
            newField = field.lower()
            
            return  newField.replace(' or ','').replace(' and ','').replace(' _ ','').replace('*','').replace(';','').replace('\\','').replace('/','').replace("'",'')
        else:
            return newField



    def GetUserId( self, userName : str ) -> int | None  :
        """
            Get the userid  by the userName or email address; if not exists return None 
        """
        userId = None
        query  = f"select userId from users where username ='{self.Sanitize(userName)}' or email ='{self.Sanitize(userName)}' ;"

        try:
            self.Conn.Send( query )
            if self.Conn.Results != [] :
                userId = self.Conn.Results[0][0]
                
        except:      
            print("\t\t|EXCEPTION: TraderDB::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )     
        finally:
            return userId 




    def InsertMetaFields ( self, aspect : int = 0  ) -> str | tuple:
        """
            Inserts the Active, Created and Mod fields for each  table in the insert clause
            ARGS    :
                        aspect   ( int )  -  0 = field name   1 = field values   2 = tuple 
            RETURNS :
                        Active, Created and Mod fields
        """
        if aspect == 0 :
            return ",active,createdBy,createdDate,modBy,modDate "
        elif aspect ==1 :
            return f",1,'{self.User}','{datetime.now()}','{self.User}','{datetime.now()}' "
        else: 
            return 1,self.User,datetime.now(),self.User,datetime.now()



    def InsertUser( self, userName :  str , firstName : str = '' , lastName : str = '', passwd : str = '', email : str = ''  ) -> int | None  :
        """
            Checks/Inserts a userName/email into the users tables
            ARGS    :
                        userName  ( str ) - name to assign to user
                        firstName ( str ) - first Name of individual
                        lastName  ( str ) - last Name of individual
                        password  ( str ) - password
                        eamil     ( str ) - email to assign to user 
                        
            RETURNS :
                        userId (int ) - user entry id from the users table 
        """
        query   = f"select userId from users where username  = '{self.Sanitize(userName)}'  or email ='{self.Sanitize(email)}' or email = '{self.Sanitize(userName)}';"
        userId  = None
        try:
            self.Conn.Send( query )
            if self.Conn.Results == [] :
                query =f"INSERT INTO users( username, firstName, lastName,"
                if passwd != '' :
                    query +=  "passwd,pwd_hash,"
                    
                query += f"email {self.InsertMetaFields( 0) } ) values  ("            

                
                query += f"'{self.Sanitize(userName)}','{self.Sanitize(firstName)}','{self.Sanitize(lastName)}'," 
                if passwd != '':
                    query +=  f"'{self.Sanitize(passwd)}',sha2({passwd},256),'"
                query += f"'{self.Sanitize(email)}'  {self.InsertMetaFields(1) } ); "
            
                userId  = self.Conn.Write( query)
            else:
                userId = self.Conn.Results[0][0]
        except :      
            print("\t\t|EXCEPTION: TraderDB::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )
            print(f"\t\tQUERY: {query}")
        finally:
            return userId

        
    def InsertDate( self, date : datetime | str ) -> int | None  :
        """
            Checks/Inserts a datetime element into the dates tables
            ARGS    :
                        date  ( datetime / str ) - date entry 
                        
            RETURNS :
                        dateId (int ) - date entry id from the dates table 
        """
        query           = ""
        dateId          = None
        date_format     = "%Y-%m-%d %H:%M:%S"

        try:            
            if isinstance( date, str ) :            
                date = datetime.strptime( date[:19],  date_format)
            
            query           = f"select dateId from dates where date = '{date}' ;"
            self.Conn.Send( query )
            
            if self.Conn.Results == [] :
                query =f"INSERT INTO dates( date, yearmo, year, month,day {self.InsertMetaFields( 0) }  ) values  ("       
                query += f"'{date}','{date.year}{date.month:02d}','{date.year}','{date.month:02d}','{date.day:02d}'"
                #else:
                #    query += f"'{date}','{datetime(date).year}{datetime(date).month}','{datetime(date).year}','{datetime(date).month}','{datetime(date).day}' "
                query += f" {self.InsertMetaFields( 1) } ); "
           
                dateId  = self.Conn.Write( query)
            else:
                dateId = self.Conn.Results[0][0]
        except:      
            print("\t\t|EXCEPTION: TraderDB::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )

            print( f"\t\tQUERY:{query}")
        finally:
            return dateId


    def InsertStock( self, stock : str = ""  , symbol : str = "", description : str = ''  , sector : str = '') -> int | None :
        """
            Checks/Insert a stock into the stocks table
            ARGS   :
                        stock    (str)  - stock symbol to add to table
                        symbol   (str)  - 
            RETURNS:
                        stockId ( int ) - stockId from table 
        """
        query       = (f"select stockId from stocks where " +
                         ( f"stock = '{self.Sanitize(stock)}'  or symbol ='{self.Sanitize(stock)}' or  " if stock != '' and stock != None else '' ) +
                        f"  symbol ='{self.Sanitize(symbol).upper()}';" )
        stockId     = None

        try:            
            self.Conn.Send( query )
        
            if self.Conn.Results == [] :
                query =  f"INSERT INTO stocks( stock, symbol, description,sector {self.InsertMetaFields( 0) }  ) values  ("                        
                query += f"'{self.Sanitize(stock)}','{self.Sanitize(symbol).upper()}','{self.Sanitize(description)}','{self.Sanitize(sector)}' {self.InsertMetaFields( 1) } ); "
            
                stockId  = self.Conn.Write( query)            
            else:
                stockId = self.Conn.Results[0][0]
                
        except:      
            print("\t\t|EXCEPTION: TraderDB::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )
            print( f"\t\tQUERY:{query}")
        finally:
            return stockId



    def GetIndicators( self, indicators : dict  ) -> dict :
        """
            Get the current entries in Indicators tables then update as  necessary
            ARGS   :
                    indicators  ( dict ) - indicators present in one of the records in the order book
            RETURNS:
                    dictionary of  indicator names and id
        """
        query           = "select indicator, indId from indicators;"
        header          = f"INSERT INTO indicators ( indicator {self.InsertMetaFields(0) } ) values ( %s,%s,%s,%s,%s,%s );"
        contents        = [] 
        indicatorTbl    = {}
        
        try:
            self.Conn.Send( query )            
            if self.Conn.Results != []:
                for indName in indicators.keys():
                    if not( indName.upper()  in str(self.Conn.Results).upper() ) :  
                        contents.append ( [indName ,*self.InsertMetaFields(2) ] ) 
                        
            
                    
            # Add The missing entries 
            if contents != []:
                self.Conn.WriteMany( header = header, contents = contents )

            # PULL ALL THE ENTRIES AGAIN
            query       = "select indicator, indId from indicators;"
            self.Conn.Send( query )
            if self.Conn.Results != [] :
                for entry in self.Conn.Results:
                    indicatorTbl.update( { entry[0] : entry[1] } )
            else:
                print("\t\t\t WARNING - Although tried to update - did not get the indicators ")
        except: 
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )
            print( f"\t\tQUERY:{query}")
        finally:
            return indicatorTbl 


    def InsertOrderIndicators( self, indicatorsId : dict , orderId : int , indicators_in : dict ,indicators_out : dict  ) -> None :
        """
            Add the associated indicators for the order to the orderIndicates table
            ARGS   :
                        orderId       ( int )  ID for the overall order
                        indicatorsId  ( dict ) ID for the inidcators in the sql table 
                        inidcators_in ( dict ) indicators for the bid
                        inidcators_out( dict ) indicators for the ask
            RETURNS:
                        nothing
        """
        header      = f"INSERT INTO orderIndicates( orderId,indicateId,bidValue,askValue {self.InsertMetaFields(0) } ) values (%s,%s,%s,%s,%s,%s,%s,%s,%s);"
        contents    = []
        
        try:
            for ind in indicatorsId.keys() :
                if ind in indicators_in and ind in indicators_out:
                    contents.append( [orderId, indicatorsId[ind],round(float(indicators_in[ind]),5) ,
                                      round( float(indicators_out[ind]),5)  ,*self.InsertMetaFields(2) ] )
            if contents != [] :
                self.Conn.WriteMany( header=header, contents =contents)
            
        except:
            print("\t\t|EXCEPTION: TraderDB::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )
            print( f"\t\tQUERY:{header } -> {contents}")
            
    
    def InsertOrderbook( self, orderbook : dict , email : str , username : str = '') -> bool:
        """
            Insert the transactions from the order book in to the database properly normalized
            ARGS   :
                        orderbook  ( dict )  - entries to be added to orderbook table
                        email      ( str )   - email of user to associate with orderbook entries
                        username   ( str )   - user name to associate with session entries
            RETURNS:
                        nothing 
        """
        header          = (f"INSERT INTO orderbook( userId, initiated, stockId, bid, qty , closed,ask,p_l,type,bidVolume,askVolume," +
                            f"bidReceipt,bidFilled,askReceipt,askFilled,actualPL {self.InsertMetaFields(0) } ) values " )
                            #"(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)" )
        query           = ""
        numRec          = 0
        dupeNum         = 0
        contents        = []
        success         = False
        userId          = None
        orderId         = None 
        stockId         = None 
        initDateId      = None
        closeDateId     = None
        indicatorsId    = {}
        
        try:
            print("\t\t * Inserting Order book ")
            print(f"\t\t   -> user : {username} [ {email} ] " )

            if len( orderbook) == 0 :
                print ("\t\t   -> No orders to save to database, skipping ")
                return  success
            
                      
            indicatorsId = self.GetIndicators( indicators = orderbook[ list(orderbook.keys())[0]][0]['indicators_in'] )
            
            for symbol in orderbook.keys():
                dupeNum = 0
                if len( orderbook[symbol]) > 0 :
                    for order in  orderbook[symbol]  : 
                        userId      = self.InsertUser(  email  = email, userName =username )
                        stockId     = self.InsertStock( symbol = symbol )
                        initDateId  = self.InsertDate(  date   = order['bidTime'] )
                        closeDateId = self.InsertDate(  date   = order['askTime'] )
                        self.Conn.Send( f"select id from orderbook where userId ={userId} and initiated ={initDateId} and stockId={stockId} ;")
                        if self.Conn.Results != [] :
                            print("\t\t\t   | Found PreExisting OrderBook Entry : ", self.Conn.Results)#order )
                            dupeNum += 1
                        else:
                            query = (header + f"('{userId}','{initDateId }','{stockId}','{order['bid']}','{order['qty']}','{closeDateId}','{order['ask']}'," +
                                    f"'{order['p_l']}','{order['type'] }','{order['bidVolume'] }','{order['askVolume']}','{order['bidReceipt']}'," +
                                     f"'{order['bidFilled']}','{order['askReceipt']}','{order['askFilled'] }'," +
                                     f"'{order['actualPL']}' {self.InsertMetaFields(1)} );"  )                        
                        
                            orderId  =  self.Conn.Write( query )
                            if orderId != None :
                                self.InsertOrderIndicators( indicatorsId=indicatorsId, orderId=orderId, 
                                                        indicators_in=order['indicators_in'],indicators_out=order['indicators_out'] )
                                numRec += 1
                                success = True 
  
        
            print (f"\t\t\t -> Inserted {numRec} entries, while ignoring {dupeNum} duplicates in orderbook" )
            
        except:      
            print("\t\t|EXCEPTION: TraderDB::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )
            print( f"\t\tQUERY:{query}")
        finally:
                return success


  
    def CheckDB( self ) -> None :
        """
            Confirm the database can be connected to 
        """
        query = "show databases;"
        try :
            self.Conn.Send( query )
            if not ( 'trading' in str(self.Conn.Results) ) :
                print("\t\t Database ( trading ) has not be initiated")
                return 
            query  = "show tables in trading;"
            self.Conn.Send( query )
            if len(self.Conn.Results) < 6   :
                print("\t\t Building Tables and procedures")
                self.CreateTables()
            
        except:      
            print("\t\t|EXCEPTION: TraderDB::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )     



    def Orders ( self, time_interval : int = 0 ) -> list :
        """
            Retreives the symbol, bidTime, bidReceipt,qty  from the orderbook
            ARGS  :
                    time_interval  ( int ) - days interval for entry retreival
            RETURNS:
                    list of list  of entries 
        """        
        query           = ""
        orders          = None
        date_format     = "%Y-%m-%d %H:%M:%S"
        from_date       = str( datetime.now() - timedelta( days=time_interval) )[:10]
        
        try:
            query = (f"select s.symbol, d.date,o.bidReceipt,o.askReceipt from orderbook o " +
                         " inner join stocks s on s.stockid =o.stockid  " +
                         " inner join dates d on d.dateid = o.initiated " +
                          " where d.date >='{from_date}'; " )
            #print("QUERY : " , query )
            self.Conn.Send( query )
            orders = self.Conn.Results
            
            
                     
        except:      
            print("\t\t|EXCEPTION: TraderDB::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )
        return orders


    def SyncEntryRecord( self, symbol : str , order : dict , orderLeg : dict , order_type : int   )-> dict :
        """
            Build the SyncEntry record - this might need to be in the SchwabAccount 
            ARGS    :
                        symbol     ( str )  stock symbol
                        order      ( dict ) the full order structure ( including orderLeg) for time/price  ( overkill )
                        orderLeg   ( dict ) order leg info from platform
                        order_type ( int )  0 = EQUITY  1 =OPTIONS_CALL  2=OPTIONS_PUT
            RETURNS :
                        dictionary of values
        """
        return { 'symbol'   : symbol, #orderLeg['instrument']['underlyingSymbol'].upper(),   # orderLeg['instrument']['symbol'].upper()
                                     'legType'  : orderLeg['orderLegType'], #  'EQUITY' or OPTION
                                     'qty'      : orderLeg['quantity'] ,
                                     'type'     : order_type , # 0 = regular , 1 = options call 2 = options puts 
                                     'action'   : orderLeg['instruction'].upper() ,                            
                                    'bidTime'           if orderLeg['instruction'].upper().find("BUY") > -1  else 'askTime'           : str(order['enteredTime'])[:19].replace('T',' '),
                                    'bidReceipt'        if orderLeg['instruction'].upper().find("BUY") > -1  else 'askReceipt'        : order['orderId'],
                                    'bidFilled'         if orderLeg['instruction'].upper().find("BUY") > -1  else 'askFilled'         : order['orderActivityCollection'][0]['executionLegs'][0]['price'],
                                    'bidFilledAt'       if orderLeg['instruction'].upper().find("BUY") > -1  else 'askFilledAt'       : order['orderActivityCollection'][0]['executionLegs'][0]['time'],
                                    'indicators_in'     if orderLeg['instruction'].upper().find("BUY") > -1  else 'indicators_out'    : {}
                                } 
        

    def SyncEntries ( self, orders : list , time_interval : int , username : str , email : str ) -> list :
        """
            Accepts a list of dictionary representing orders from the brokerage
            ARGS   :
                    orders        ( list of dictionary ) - orders from brokerage with keys ( symbol, openedAt, bidReceipt, bid, qty ,   askReceipt, ask, pl )
                    time_interval ( int )  number of days we need to look bakc 
            RETURNS:
                    nothing 
        """
        pos         = 0
        recs        = []
        found       = False 
        types       = { 'OPTION': {
                                    'CALL' : 1 ,
                                    'PUT'  : 2
                                },
                          'EQUITY': 0
                      }        
        orderbook  = {}
        order_type  = 0
        
        try:            
            #Get entries from SQL 
            entries = self.Orders( time_interval=time_interval)

            #Build entries in orderbook format ( ask and bid ) to then send to self.InsertOrderbook( self, orderbook : list , email : str , username : str = '') -> bool:
            for order in orders :
                #print(f"\n** FULL ORDER : { order }")
                for orderLeg in order['orderLegCollection']:                    
                    receipt     = order['orderId']
                    order_date  = order['enteredTime'][:10]
                    if str(entries).find( str(receipt) ) == -1   :     #this order is not in the SQL so need to start building buy/sell                        
                        symbol = orderLeg['instrument']['underlyingSymbol'] if 'underlyingSymbol' in orderLeg['instrument'] else orderLeg['instrument']['symbol']
                        if not(symbol in orderbook):
                            orderbook.update( { symbol : [] })
                            
                        if orderLeg['orderLegType'] == 'EQUITY':
                            order_type = types[orderLeg['orderLegType']]
                        else:
                            order_type = types[orderLeg['orderLegType']][ orderLeg['instrument']['putCall']]
                        
                        if len(recs) == 0 :
                            recs.append( self.SyncEntryRecord( symbol=symbol , order=order, orderLeg=orderLeg , order_type=order_type   )  )                            
                        else:
                            pos     = 0
                            found   = False 
                            for indx in range(len(recs) ):                                
                                if ( symbol.upper() == recs[indx]['symbol'] and
                                           orderLeg['quantity'] == recs[indx]['qty']  and
                                           orderLeg['instruction'].upper() != recs[indx]['action']  and
                                           order_date == (recs[indx]['bidTime'][:10] if 'bidTime' in recs[indx] else recs[indx]['askTime'][:10] )
                                     ) :
                                    found = True
                                    pos = indx                                   
                                    recs[indx] |=  self.SyncEntryRecord( symbol=symbol , order=order, orderLeg=orderLeg , order_type=order_type   )  
                            
                            if not found :                                
                                pos = len( recs )
                                recs.append( self.SyncEntryRecord( symbol=symbol , order=order, orderLeg=orderLeg , order_type=order_type   )   )
                                
                        if 'bidReceipt' in recs[pos] and 'askReceipt' in recs[pos] :
                            recs[pos].update ({'bid'        : recs[pos]['bidFilled'], 'ask' : recs[pos]['askFilled'], 'price' : recs[pos]['bidFilled']} )
                            recs[pos].update ({  'p_l'      : ( (recs[pos]['askFilled'] - recs[pos]['bidFilled']) * recs[pos]['qty'] ) * (100 if order_type > 0 else 1 ) } )
                            recs[pos].update ({'actualPL'   : recs[pos]['p_l'] * (100 if order_type > 0 else 1 ), 'bidVolume' : 0, 'askVolume' : 0} )                                                       
                            orderbook[symbol].append( recs[pos] )
                            recs.pop( pos )
            print( f"\n\t\t Orders to sync ")
            print( f"\t\t\tSTOCK\tDATE/TIME\t\tCLOSED\t\tSYMBOL\tQTY\tPRICE\t\t\tBIDRECEIPT\tASKRECEIPT ")
            for symbol in orderbook.keys():
                print( f"\t\t\t{symbol}")
                for order in orderbook[symbol]:                        
                    print( f"\t\t\t\t{ order['bidTime']}\t{order['askTime'][11:16]}\t\t{ order['symbol']}"+
                           f"\t{ int( order['qty'] )}\t${ order['bidFilled']:.2f} -> ${ order['askFilled']:.2f}"+
                           f"\t\t{ order['bidReceipt']}\t{ order['askReceipt']}" ) 
               
            print("\nLEFT OVER : " , recs )

            self.InsertOrderbook(  orderbook = orderbook, email=email  , username=username)
        except:  
            print("\t\t|EXCEPTION: TraderDB::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )








    
    def CreateTables( self ) -> None :
        """
            Staging Area to design schema 
        """
        
        verifyUser = (#" DELIMITER // " +
                   "CREATE PROCEDURE verifyUser( IN user_name varchar (20), IN pass_word varchar(30), OUT userId  int  ) " +  
                    " BEGIN  " +
                    "    select userId FROM  users  where username=user_name and pwd_hash = SHA2(pass_word, 256) ; " +                    
                    " end // " +
                    " DELIMITER;  ")
        
        indicators = (#"DELIMITER // "+
                    " CREATE PROCEDURE createTableIndicators( )  " +
                    " BEGIN  " +
                    " create table if not exists  indicators ( indId int auto_increment PRIMARY KEY not null, " +
                       " indicator varchar(20) , details  varchar(200), " +
                       "active  tinyint , createdBy varchar(20), createdDate datetime, modBy varchar(20), modDate datetime ); "+                   
                    " INSERT INTO indicators ( indicator,details, active,createdBy,createdDate,modBy, modDate ) values  " +
                      "('SMA9','Simple Moving Average: 9 day',1,'trader',now(),'trader',now() ), ('SMA14','Simple Moving Average:14 day',1,'trader',now(),'trader',now() ) , " +
                      "('SMA21','Simple Moving Average: 21 day',1,'trader',now(),'trader',now() ), ('SMA50','Simple Moving Average:50 day',1,'trader',now(),'trader',now() ) , " +
                      "('SMA200','Simple Moving Average:200 day',1,'trader',now(),'trader',now() ), ('VWAP','Volume Weighted Price',1,'trader',now(),'trader',now() ) , " +
                      #"('SMA','Simple Moving Average:for the day',1,'trader',now(),'trader',now() ), ('FIB','Fibonacci Retracement: All Time',1,'trader',now(),'trader',now() ) , " +
                      "('ATH','All Time High: 200 days',1,'trader',now(),'trader',now() ), ('ATL','All Time Low: 200 days',1,'trader',now(),'trader',now() ) , " +
                      "('HIGH','Daily High',1,'trader',now(),'trader',now() ), ('LOW','Daily Low',1,'trader',now(),'trader',now() ) , " + #('dFib','Fibonacci Retracement: daily data',1,'trader',now(),'trader',now() ) , " +
                      "('RSI','Relative Strength Index',1,'trader',now(),'trader',now() ), ('VolIndex','Volatility Index',1,'trader',now(),'trader',now() ) ; " +
                    "end // " +
                    "DELIMITER; " )
        users   = (#"DELIMITER // "+
                    " CREATE PROCEDURE createTableUsers(   )  " +
                    " BEGIN  " +
                    " create table if not exists  users ( userId int auto_increment PRIMARY KEY not null, " +
                       " firstName varchar(20) , lastName  varchar(20),username varchar(20)  NOT NULL, passwd varchar(20) , pwd_hash varchar(256) , email varchar(30) , " +
                       "active  tinyint , createdBy varchar(20), createdDate datetime, modBy varchar(20), modDate datetime ); "+                   
                    " INSERT IGNORE INTO users ( username , passwd, pwd_hash, active,createdBy,createdDate,modBy, modDate ) values ('trader','verified', SHA2('verified', 256),1,'trader',now(),'trader',now() ) ; " +
                    "end // " +
                    "DELIMITER; " )
        dates   = (#" DELIMITER // " +
                   "CREATE PROCEDURE createTableDates(  ) " +  
                    " BEGIN  " +
                    "    create table if not exists  dates  ( dateId int auto_increment PRIMARY KEY not null, " +
                    "       date datetime not null, yearmo varchar(6) not null, year int not null ,month int not null, " +
                    "       day int not null ,active  tinyint , createdBy varchar(20), createdDate datetime, modBy varchar(20), modDate datetime );  " +
                    " end // " +
                    " DELIMITER;  ")
                    
        stocks  = (#"DELIMITER //  " +
                   " CREATE PROCEDURE createTableStocks( )  " +
                    " BEGIN  " +
                    " create table if not exists  stocks ( stockId int auto_increment PRIMARY KEY not null, " +
                    "       stock varchar(10) , symbol varchar(10) not null, description varchar(50),  " +
                    "       sector varchar(15) ,active  tinyint , createdBy varchar(20), createdDate datetime, modBy varchar(20), modDate datetime ); " +
                    " end // "+ 
                    "DELIMITER; ")


        orderbook = (#"DELIMITER // "+
                        " CREATE PROCEDURE createTableOrderBook(    )   " +
                        " BEGIN  "+
                             "create table if not exists orderbook( id int auto_increment PRIMARY KEY not null, userId int not null, initiated  int  not null,  stockId int not null, " +
                                "type int not null,bid decimal(10,4) not null , qty  int not null , bidVolume int ,  closed  int not null,ask  decimal(10,4), askVolume int, p_l decimal(10,4) , " +
                                 "bidReceipt bigint(25) , bidFilled decimal(10,4),  askReceipt bigint(20) , askFilled decimal(10,4), actualPL decimal(10,4), " +                    
                                " active  tinyint , createdBy varchar(20), createdDate datetime, modBy varchar(20), modDate datetime,  " +
                                "FOREIGN KEY ( userId )   REFERENCES users(userId)  ," +
                                "FOREIGN KEY ( stockId  ) REFERENCES stocks(stockId) , " +
                                "FOREIGN KEY ( initiated) REFERENCES dates(dateId)   , " +
                                "FOREIGN KEY ( closed)    REFERENCES dates(dateId)     ); " +
                        "     END //  "+
                        "     DELIMITER ;  ")
        orderIndicates = (#"DELIMITER // "+
                        " CREATE PROCEDURE createTableOrderIndicates(    )   " +
                        " BEGIN  "+
                             "create table if not exists orderIndicates( id int auto_increment PRIMARY KEY not null, orderId int not null, " +
                                "indicateId  int  not null, bidValue decimal(10,4), askValue decimal(10,4)  ,  " +                    
                                " active  tinyint , createdBy varchar(20), createdDate datetime, modBy varchar(20), modDate datetime,  " +
                                "FOREIGN KEY ( orderId  )     REFERENCES orderbook(id) , " +
                                "FOREIGN KEY ( indicateId )   REFERENCES indicators(indId) ); " +
                        "     END //  "+
                        "     DELIMITER ;  ")
        # NOT SURE A SEPARATE TABLE IS NEEDED FOR THIS 
        orderOptions = (#"DELIMITER // "+
                        " CREATE PROCEDURE createTableOrderOptions(    )   " +
                        " BEGIN  "+
                             "create table if not exists orderOptions( orderOptionid int auto_increment PRIMARY KEY not null, orderId int not null, strike  decimal(10,4),  " +
                                "askValue decimal(10,4) not null ,  " +                    
                                " active  tinyint , createdBy varchar(20), createdDate datetime, modBy varchar(20), modDate datetime,  " +
                                "FOREIGN KEY ( orderId  )     REFERENCES orderBook(id) , " +
                                "FOREIGN KEY ( indicateId )   REFERENCES indicators(indId) ); " +
                        "     END //  "+
                        "     DELIMITER ;  ")
        v_orderbook = (#"DELIMITER // "+
                        " CREATE PROCEDURE if not exists createTable_vOrderBook(   )   " +
                        " BEGIN  "+
                        "     create view v_orderbook  as" +
                        "         select o.id, u.email, d.date as initiated , s.symbol,o.bid, o.bidVolume,o.qty,d2.date as closed ,o.ask , " +
                        "          o.askVolume, o.p_l, o.bidFilled, o.askFilled,o.actualPL " + #, o.active, o.createdBy, o.createdDate, o.modBy,o.modDate "+
                        "     from orderbook o " +
                        "     inner join dates d on o.initiated =d.dateid "+
                        "     inner join dates d2 on o.closed = d2.dateid  "+
                        "     inner join stocks s on o.stockid =s.stockid  "+
                        "     inner join users u on o.userid=u.userid "+
                        "     where o.active = 1; " +
                        "     END //  "+
                        "     DELIMITER ;  ")        
        p_createTables = (#"DELIMITER // "+
                            " CREATE PROCEDURE createAllTables( )  " +
                            " BEGIN " +
                            " call createTableIndicators(); " +
                            " call createTableDates(); " +
                            " call createTableUsers(); " +
                            " call createTableStocks(); " +
                            " call createTableOrderbook(); " +
                            " call createTableOrderIndicates(); " +
                            " call createTable_vOrderbook(); " +
                            " END // " +
                            " DELIMITER ;")
        try:
            tables = [verifyUser,indicators,users, dates,stocks,orderbook, orderIndicates ,v_orderbook, p_createTables ] #     
            for table in tables :
                print( f"Table : {table}")
                self.Conn.Write( table)
                             
            self.Conn.Write( "call createAllTables(); " )
            
        except:      
            print("\t\t|EXCEPTION: TraderDB::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )


        """
            SELECT 
    ROUTINE_NAME, 
    ROUTINE_SCHEMA, 
    ROUTINE_TYPE, 
    CREATED, 
    DEFINER 
FROM 
    INFORMATION_SCHEMA.ROUTINES 
WHERE 
    ROUTINE_TYPE = 'PROCEDURE' 
    AND ROUTINE_SCHEMA = 'your_database_name';
            SHOW CREATE PROCEDURE your_procedure_name;
            SELECT * FROM mysql.proc WHERE name = 'your_procedure_name' \G


                        CREATE PROCEDURE createTableOrderIndicates(    )   
                         BEGIN  
                             create table orderIndicates( id int auto_increment PRIMARY KEY not null, orderId int not null, indicateId  int  not null, bidValue decimal(10,4), 
                                askValue decimal(10,4) not null , 
                                 active  tinyint , createdBy varchar(20), createdDate datetime, modBy varchar(20), modDate datetime,  
                                FOREIGN KEY ( orderId  )     REFERENCES orderbook(id) , 
                                FOREIGN KEY ( indicateId )   REFERENCES indicators(indId) ); 
                             END // 


             CREATE PROCEDURE if not exists createTable_vOrderBook(   )   
                         BEGIN  
                             create view v_orderbook  as
                                 select o.id, u.email, d.date as initiated , s.symbol,o.bid, o.bidVolume,o.qty,d2.date as closed ,o.ask , 
                                  o.askVolume, o.p_l, o.active, o.createdBy, o.createdDate, o.modBy,o.modDate 
                             from orderbook o 
                             inner join dates d on o.initiated =d.dateid 
                             inner join dates d2 on o.closed = d2.dateid  
                             inner join stocks s on o.stockid =s.stockid  
                             inner join users u on o.userid=u.userid; 
                             END //  
                             DELIMITER
            Indicators
            * Smart Money Concepts
            * C& B Scout  ( RedK Chop and Breakout Scout )
            * Average True Range ( ATR ) 
        """
