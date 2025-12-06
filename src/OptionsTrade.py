#! /usr/bin/python3
## ###################################################################################################################
##  Program :   OptionsTrade
##  Author  :
##  Install :   pip3 install  pygobject requests  inspect platform argparse selenium webdriver-manager reportlab pandas schwab-py matplotlib pymssql mysql-connector loguru
##              sudo dnf install gcc gobject-introspection-devel cairo-gobject-devel pkg-config python3-devel gtk4 gtk4-devel
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


import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk


class OptionsTrade:
    def __init__( self ):
        """
            Initialize the class variables
        """
        self.AppId      = 'org.aegesware.trading.options'
        self.Window     = None
        self.ClassName  = "OptionTrade"
        

    def MainWindow( self , width : int = 700, height : int = 400 ) -> None :
        """
            Builds the main window of the dialog 
        """
        self.Window = Gtk.ApplicationWindow(title="Options Dialog")
        self.Window.present()
        self.Window.show_all()
                                

    def Run( self, width : int = 700, height : int = 400 ) -> None :
        """
            Assembles the GUI elements
        """
        app = None 
        try:
            self.MainWindow( width = width, height = height )
            app = Gtk.Application(application_id=self.AppId)            
            app.connect('activate', self.on_activate)
            app.run(None)

        except:
            print("\t\t[EXCEPTION]" + self.ClassName + " : " + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t  |   " + str(entry) )


    
    def on_activate(self, app) -> None :
        ##<summary> 
        ##      BUILD THE GUI ELEMENTS 
        ##</summary>
        
        sessions        = []
        session_index   = 4
        recentSub       = ()
        """
        menuInfo        = { "Options" : [ ("Dashboard", self.DashboardTab ),
                                        ("Calculated Fields" , self.CalculatedFieldsDialog ) ,
                                          ("Regions" , self.RegionsDialog ) ,
                                            ("Applicants" , self.ApplicantsDialog ) ,
                                                ("Sessions" , [ ("Create" , self.CreateSessionDialog ) ] ) 
                                       ],
                        "Info" : [  ("About" , self.AboutDialog ) ,
                                    ("Help" , self.HelpDialog ) 
                                ]
                        }
        """
        container   = None 
        button      = None
        
        try:
            pass
            """
            self.MainWin     = MainWindow(app, self.AppName)
            self.MainWin.present()        
            
            # CONNECTION 
            self.SQLConn  = ODBCConn()
            self.SQLConn.Connect(credentials.Database["Server"], credentials.Database["DBName"],False,
                                         credentials.Database["Username"],credentials.Database["Password"])            
            self.Queries  = QueryFactory(credentials.Database["DBName"])


            #BUILD SUBMENU OF SESSIONS            
            self.SQLConn.Send( self.Queries.GetSessions() )
            self.Recents = {} 
            for row in self.SQLConn.Results:
                sessions.append( ( row[1], self.SessionLoadCallback ) )
                self.Recents[row[1] ] = row[0]
            recentSub = ( "Recents", sessions ) 
            menuInfo["Options"][session_index][1].append( recentSub  )
            menuInfo["Options"].append( ( "Quit" , self.CallBack) )

            #BUILD MIN WINDOW 
            self.MainWin.Build(self.Width, self.Height,menuInfo )
            self.MainWin.connect("destroy", Gtk.main_quit)
            self.MainWin.Show(True)

            
            #ADD THE DASHBOARD TAB
           # self.DashboardTab()
            """
            Gtk.main()
                        
        except:
            print("\t\t[EXCEPTION]" + self.ClassName + " : " + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t  |   " + str(entry) )
