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
import pandas as pd
import numpy  as np 
import getpass
import inspect
import platform
import argparse
import functools
import requests

from datetime           import datetime 
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
        self.User       = getpass.getuser()     # CURRENT PERSON LOGGED INT 
        self.Conn       = MySQLConn( )
        self.Conn.Connect(server =self.Server, database='trading', username =self.UserName, passwd =self.Password )

    def Tables( self ) -> None :
        """
            Staging Area to design schema 
        """
        users   = ("DELIMITER // "+
                    " CREATE PROCEDURE createTableUsers( INOUT dbName  varchar(20)  )  " +
                    " BEGIN  " +
                    " create table if not exists  users ( userId int auto_increment not null, " +
                       " firstName varchar(20) , lastName  varchar(20),username varchar(20) PRIMARY KEY NOT NULL, passwd varchar(20) not null, pwd_hash varchar(256) , email varchar(30) , " +
                       "active  tinyint , createdBy varchar(20), createdDate date, modBy varchar(20), modDate date ); "+                   
                    " INSERT IGNORE INTO users ( username , passwd, pwd_hash, active,createdBy,createdDate,modBy, modDate ) values ('trader','verified', SHA2('verified', 256),1,'trader',now(),'trader',now() ) ; " +
                    "end // " +
                    "DELIMITER; " )
        verifyUser = (" DELIMITER // " +
                   "CREATE PROCEDURE verifyUser( IN user_name varchar (20), IN pass_word varchar(30), OUT userId  int  ) " +  
                    " BEGIN  " +
                    "    select userId FROM  users  where username=user_name and pwd_hash = SHA2(pass_word, 256) ; " +                    
                    " end // " +
                    " DELIMITER;  ")
        dates   = (" DELIMITER // " +
                   "CREATE PROCEDURE createTableDates( INOUT dbName  varchar(20) ) " +  
                    " BEGIN  " +
                    "    create table if not exists  dates  ( dateId int auto_increment PRIMARY KEY not null, " +
                    "       date date not null, yearmo varchar(6) not null, year int not null ,month int not null, " +
                    "       day int not null ,active  tinyint , createdBy varchar(20), createdDate date, modBy varchar(20), modDate date );  " +
                    " end // " +
                    " DELIMITER;  ")
                    
        stocks  = ("DELIMITER //  " +
                   " CREATE PROCEDURE createTableStocks( INOUT dbName  varchar(20)  )  " +
                    " BEGIN  " +
                    " create table if not exists  stocks ( stockId int auto_increment PRIMARY KEY not null, " +
                    "       stock varchar(10) , symbol varchar(10) not null, description varchar(50),  " +
                    "       sector varchar(15) ,active  tinyint , createdBy varchar(20), createdDate date, modBy varchar(20), modDate date ); " +
                    " end // "+ 
                    "DELIMITER; ")


        orderbook = ("DELIMITER // "+
                        " CREATE PROCEDURE createTableOrderBook(  INOUT dbName  varchar(20)  )   " +
                        " BEGIN  "+
                             "create table orderbook( id int auto_increment PRIMARY KEY not null, userId int not null, initiated  int  not null, stockId int not null, " +
                                "bid decimal(10,4) not null , qty  int not null , volume_in int , closed  int not null,  ask  decimal(10,4), volume_out int, p_l decimal(10,4) , " +                    
                                " active  tinyint , createdBy varchar(20), createdDate date, modBy varchar(20), modDate date,  " +
                                "FOREIGN KEY ( userId )   REFERENCES users(userId)  ," +
                                "FOREIGN KEY ( stockId  ) REFERENCES stocks(stockId) , " +
                                "FOREIGN KEY ( initiated) REFERENCES dates(dateId)   , " +
                                "FOREIGN KEY ( closed)    REFERENCES dates(dateId)     ); " +
                        "     END //  "+
                        "     DELIMITER ;  ")

        v_orderbook = ("DELIMITER // "+
                        " CREATE PROCEDURE createTable_vOrderBook(   )   " +
                        " BEGIN  "+
                        "     create view v_orderbook  as" +
                        "         select o.id, u.email, d.date as initiated , s.symbol,o.bid, o.volume_in,o.qty,d2.date as closed ,o.ask , " +
                        "          o.volume_out, o.p_l, o.active, o.createdBy, o.createdDate, o.modBy,o.modDate "+
                        "     from orderbook o " +
                        "     inner join dates d on o.initiated =d.dateid "+
                        "     inner join dates d2 on o.closed = d2.dateid  "+
                        "     inner join stocks s on o.stockid =s.stockid  "+
                        "     inner join users u on o.userid=u.userid; "+
                        "     END //  "+
                        "     DELIMITER ;  ")
        p_createTables = ("DELIMITER // "+
                            " CREATE PROCEDURE createAllTables( )  " +
                            " BEGIN " +
                            " call createTableDates(@something); " +
                            " call createTableUsers(@something); " +
                            " call createTableStocks(@something); " +
                            " call createTableOrderbook(@something); " +
                            " END // " +
                            " DELIMITER ;")

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
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
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
                query =f"INSERT INTO users( username, firstName, lastName, passwd,pwd_hash,email {self.InsertMetaFields( 0) } ) values  ("            
            
                query += f"'{self.Sanitize(userName)}','{self.Sanitize(firstName)}','{self.Sanitize(lastName)}','{self.Sanitize(passwd)}',sha2({passwd},256),'{self.Sanitize(email)}'"
                query += f" {InsertMetaFields(1) } ); "
            
                userId  = self.Conn.Write( query)
            else:
                userId = self.Conn.Results[0][0]
        except :      
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )     
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
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )
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
        query       = f"select stockId from stocks where stock = '{self.Sanitize(stock)}'  or symbol ='{self.Sanitize(stock)}' or symbol ='{self.Sanitize(symbol)}';"
        stockId     = None

        try:
            self.Conn.Send( query )
        
            if self.Conn.Results == [] :
                query =f"INSERT INTO stocks( stock, symbol, description,sector {self.InsertMetaFields( 0) }  ) values  ("                        
                query += f"'{self.Sanitize(stock)}','{self.Sanitize(symbol)}','{self.Sanitize(description)}','{self.Sanitize(sector)}' {self.InsertMetaFields( 1) } ); "
            
                stockId  = self.Conn.Write( query)            
            else:
                stockId = self.Conn.Results[0][0]
                
        except:      
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )
        finally:
            return stockId




    
    def InsertOrderbook( self, orderbook : list , email : str , username : str = '') -> bool:
        """
            Insert the transactions from the order book in to the database properly normalized
            ARGS   :
                        orderbook  ( list )  - entries to be added to orderbook table
                        email      ( str )   - email of user to associate with orderbook entries
                        username   ( str )   - user name to associate with session entries
            RETURNS:
                        nothing 
        """
        header          = (f"INSERT INTO orderbook( userId, initiated, stockId, bid, qty , closed,ask,p_l {self.InsertMetaFields(0) } ) values " +
                            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)" )
        numRec          = 0
        dupeNum         = 0
        contents        = []
        success         = False
        userId          = None 
        stockId         = None 
        initDateId      = None
        closeDateId     = None

        try:
            print("\t\t * Inserting Order book ")
            print("\t\t   -> user : ", email , " : " ,username)
            for order in orderbook :
                userId      = self.InsertUser(  email  = email, userName =username )
                stockId     = self.InsertStock( symbol = order[0] )
                initDateId  = self.InsertDate(  date   = order[1] )
                closeDateId = self.InsertDate(  date   = order[4] )
                self.Conn.Send( f"select id from orderbook where userId ={userId} and initiated ={initDateId} and stockId={stockId} ;")
                if self.Conn.Results != [] :
                    print("\t\t\t   | Found PreExisting OrderBook Entry : ", order )
                    dupeNum += 1
                else:
                    contents.append( [userId, initDateId,stockId,order[2],order[3],closeDateId,order[5],order[6], *self.InsertMetaFields(2)  ] )
                    numRec += 1

            if contents != []:
                self.Conn.WriteMany( header = header, contents = contents )
                success = True 
        
            print (f"\t\t\t -> Inserted {numRec} entries, while ignoring {dupeNum} duplicates in orderbook" )
            
        except:      
            print("\t\t|EXCEPTION: TradeAccount::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t |   " + str(entry) )     

        finally:
                return success
  
