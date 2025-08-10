##	PROGRAM		:	MySQL	
##	INCEPTION 	:	2021-11-09 
##	AUTHOR 		:	Sean A. Burner 
##	PURPOSE		:
##      INSTALLATION    :       pip3 install python3-devel mysql-devel mysqlclient mysql-connector-python


import sys 
import pandas as pd
import pymssql 
import mysql.connector 
import datetime 


class MySQLConn:        
	def __init__(self):
                """
                        INITIALIZE THE CLASS 
                """
                self.Cursor = None
                self.Groups = dict()
                self.ResultSize = 0
                self.Results = None
		
		
	def Connect(self,  server : str ="127.0.0.1" , database : str = "test", username : str = "guest" ,passwd : str ="guest" ) -> None :
                """
                        CONNECTION FUNCTION TO SERVER 
                        ARGS   :
                                server   = address of server
                                database = name of database to connect to
                                username = user name to conntect to server
                                passwd   = password for username account 
                        RETURNS:
                                Nothing 
                """
                try:
                        self.Conn = mysql.connector.connect(user=username, password=passwd,
                              host=server,  database=database) 
                except:
                        e = sys.exc_info()[0]
                        f = sys.exc_info()[1]
                        print("\t\t|EXCEPTION: MySQLConn -CONNECT() Ran into an exception" + str(e) + " : "  + str(f) )
                self.Cursor = None
                self.Groups = dict()
                self.ResultSize = 0
                self.Results = None
		

	def DBName_Table( self, db : str ,tbl : str ) -> str:
                """
                	FORMAT THE DBNAME AND TABLE FOR SPECIFIC VERSION
                	ARGS   :
                                        db   : database name
                                        tbl  : table name 
                	RETURNS:
                """
                return db+'.'+tbl+' '
		
		
	
	def Send(self,query : str ) -> None:
                """
                        SEND QUERY TO SERVER AND  IF CONNECTION IS NOT NULL AND STORE RESULTS IN CURSOR
                        ARGS   :
                                query - query commands 
                        RETURNS:
                                nothing 
                """
                try:
                        if self.Conn != None :
                                self.Cursor = self.Conn.cursor()
                                self.Cursor.execute(query)

                                if self.Cursor.description != None:		#MEANS THE QUERY WAS A SELECTION
                                        self.Results = list(self.Cursor.fetchall())
                                        if self.Results != None:
                                                self.ResultSize = len(self.Results)
                                                print ('Retrieved: ', self.ResultSize, ' : ' , self.Cursor.description)
                                                self.Groups = dict()
                                        else:
                                                print ("Did not get results for this query: " + query )
                                                self.ResultSize =0
                except:
                        e = sys.exc_info()[0]
                        f = sys.exc_info()[1]
                        print("\t\t|EXCEPTION: MySQLConn -SEND() Ran into an exception" + str(e) + " : "  + str(f) ) 
			#pymssql.Error as err:
			#print(err)
			#print("ProgrammingError: " , self.Cursor.description ,'\n\t', query)
			
			
	
	def Write(self,query : str) -> None :
                """
                        SEND QUERY TO SERVER THAT MKES CHANGES TO DATABASE
                        ARGS   :
                                      query - query commands 
                        RETURNS:
                                      nothing   
                """
                try:
                        if self.Conn != None :
                                self.Cursor = self.Conn.cursor()
                                self.Cursor.execute(query)
                                self.Conn.commit()					#MIGHT HAVE TO SPIT INTO SOME THAT SELECTS AND SOMETHAT THAT INSERTS/UPDATES 
			
                        self.Results = None
                        self.ResultSize = 0 				
                except:
                        e = sys.exc_info()[0]
                        f = sys.exc_info()[1]
                        print("\t\t|EXCEPTION: MySQLConn -WRITE() Ran into an exception" + str(e) + " : "  + str(f) ) #+ "\n\t\t|> " + query) 
			# pymssql.Error as err: 
			#print('\t| DVR ERR: ',err, "\n\t| SQL ERR : " , self.Cursor.description ,'\n\t| QUERY >> ', query)
			
	def WriteMany(self,header : str  , contents : str ) -> None : 
                """
                        SEND QUERY TO SERVER THAT MKES CHANGES TO DATABASE
                        ARGS   :
                                      query - query commands 
                        RETURNS:
                                      nothing   
                """
                try:
                        if self.Conn != None :
                                self.Cursor = self.Conn.cursor()
                                self.Cursor.executemany(header, contents)	
			#	self.Conn.commit()					#MIGHT HAVE TO SPIT INTO SOME THAT SELECTS AND SOMETHAT THAT INSERTS/UPDATES 
			
                        self.Results = None
                        self.ResultSize = 0 				
                except:
                        e = sys.exc_info()[0]
                        f = sys.exc_info()[1]
                        print("\t\t|EXCEPTION: MySQLConn -WRITEMANY() Ran into an exception" + str(e) + " : "  + str(f) ) 
			# pymssql.Error as err: #pyodbc.Error as err:			
			#print('\t| DVR ERR: ',err, "\n\t| SQL ERR : " , self.Cursor.description ,'\n\t| QUERY >> ', query)


