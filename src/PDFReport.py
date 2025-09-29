## ###################################################################################################################
##  Program :   Day Trade Strategies 
##  Author  :   Sean Burner
##  Detail  :   Class that holds multiple strategies as methods 
##  Install :   pip3 install reportlab
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


import  matplotlib.pyplot   as plt

from datetime                               import datetime


import smtplib
from email                                  import encoders
from email.mime.text                        import MIMEText
from email.mime.base                        import MIMEBase
from email.mime.multipart                   import MIMEMultipart




from reportlab.lib                          import colors
from reportlab.pdfgen                       import canvas
from reportlab.platypus                     import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,Image
from reportlab.lib.units                    import inch
from reportlab.lib.styles                   import getSampleStyleSheet
from reportlab.lib.pagesizes                import letter


# Import for charts
from reportlab.graphics.shapes              import Drawing
from reportlab.graphics.charts.piecharts    import Pie
from reportlab.graphics.charts.linecharts   import LineChart
from reportlab.graphics.charts.barcharts    import VerticalBarChart
from reportlab.lib.colors                   import black, blue, red
from reportlab.graphics.charts.axes         import XCategoryAxis, YValueAxis

class PDFReport: 
    def __init__(self, fileName  : str  ) -> None :
        """
            Initialize the variables for the Trading Account class 
        """        
        self.Doc        = SimpleDocTemplate(fileName, pagesize=letter)
        self.Styles     = getSampleStyleSheet()
        self.Story      = []
        self.FileName   = fileName 



    def AddText( self, text : str ,  style : str,  alignment : int ) -> None :
        """
            Add text to the document  which allows styling

            PARAMETER  :
                            text      :  contents text
                            style     :  html style tags ( h1 / h2 )
                            alignment : numer represents alignment [ 1 = center ] 
            RETURNS    :
                            Nothing 
        """
        text_style              =  self.Styles[ style ]
        text_style.alignment    =  alignment
        self.Story.append( Paragraph( text , text_style)  )
        self.Story.append(  Spacer(1,12) )



    def AddTable( self, data : object,  style : str,  alignment : int  ) -> None:
        """
            Add table to report 

            PARAMETER  :
                            data      :  list of list of data 
                            style     :  html style tags ( h1 / h2 )
                            alignment :  number represents alignment [ 1 = center ] 
            RETURNS    :
                            Nothing 
        """
        table_style = TableStyle( [
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ])
        table = Table( data)
        table.setStyle(table_style)
        self.Story.append( table )




    def AddBarChart ( self, data : list, labels : list , chartType : str = 'bar', width : int = 200, height : int = 200 ) -> None :
        """
            Add a chart to the report
            ARGS    :
                        data      :  list of int 
                        labels    :  list of string
                        chartType :  type of chart to add [ bar / line ] 
                        width     :  int
                        height    :  int
            RETURNS :
                        nothing
        """
        chartTypes = {'bar': VerticalBarChart,  'line' : LineChart }
        drawing = Drawing(width, height)
        
        chart = chartTypes.get( chartType.lower(), VerticalBarChart )() 
        chart.x = 50   # x-coordinate of the chart on the drawing
        chart.y = 30   # y-coordinate of the chart on the drawing
        chart.height    = height * .66
        chart.width     = width  * .66
        if chartType.lower() =='line':
            chart.data      = data
        else:
            chart.data      = data
        # 5. Configure the X-axis (category axis)
        chart.categoryAxis                  = XCategoryAxis()
        chart.categoryAxis.categoryNames    = labels
        chart.categoryAxis.labels.boxAnchor = 'n' # Anchor labels at the top

        # 6. Configure the Y-axis (value axis)
        chart.valueAxis = YValueAxis()
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = 60
        chart.valueAxis.valueStep = 10
        chart.valueAxis.labels.fontName = 'Helvetica'

        # Add the chart to the drawing
        drawing.add(chart)

        self.Story.append ( chart )



    def AddLineChart2 ( self, symbol : str , data : list, labels : list ,  width : int = 500, height : int = 200 ) -> None :
        """
            Add a chart to the report
            ARGS    :
                        symbol    :  str - name of stock symbol 
                        data      :  list of int 
                        labels    :  list of string
                        width     :  int
                        height    :  int
            RETURNS :
                        nothing
        """
        try:
            print( 'Doing this ') 
            
            fig, ax = plt.subplots()
            ax.plot(data, color='blue')

            # Add labels and title to the axes
            ax.set_xlabel('time')
            ax.set_ylabel('dollars')
            ax.set_title(symbol)
            chart_graph = "../pix/graph1.png"
            fig.savefig(chart_graph)
            fig.show()
            self.Story.append(  Image(chart_graph , width=6*inch, height=5*inch)    )
        except:
            print("\t\t|EXCEPTION: PDFReport::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )




    def AddImage( self, imgFile : str = "../pix/graph1.png", width : int = 500, height : int = 300  ) -> None :
        """
            Add an image( file ) to the pdf document
            ARGS    :
                        imgFile : str - filename of the image file ( png ) 
            RETURNS :
                        Nothing 
        """        
        self.Story.append(  Image(  imgFile , width=7*inch, height=5*inch)    )
            


        

    def AddLineChart ( self, data : list, labels : list ,  width : int = 200, height : int = 200 ) -> None :
        """
            Add a chart to the report
            ARGS    :
                        data      :  list of int 
                        labels    :  list of string
                        width     :  int
                        height    :  int
            RETURNS :
                        nothing
        """        
        drawing = Drawing(width, height)
        
        chart = LineChart()
        chart.x = 50   # x-coordinate of the chart on the drawing
        chart.y = 30   # y-coordinate of the chart on the drawing
        chart.height    = height * .66
        chart.width     = width  * .66
        for i, series in enumerate(data):
            chart.add(line_colors[i], series)
        
        # 5. Configure the X-axis (category axis)
        chart.categoryAxis                  = XCategoryAxis()
        chart.categoryAxis.categoryNames    = labels
        chart.categoryAxis.labels.boxAnchor = 'n' # Anchor labels at the top

        # 6. Configure the Y-axis (value axis)
        chart.valueAxis = YValueAxis()
        chart.valueAxis.valueMin = 0
        chart.valueAxis.valueMax = 60
        chart.valueAxis.valueStep = 10
        chart.valueAxis.labels.fontName = 'Helvetica'

        # Add the chart to the drawing
        drawing.add(chart)

        self.Story.append ( chart )








        
    def AddPieChart( self, data : list, labels : list , pieColors : list = [colors.blue, colors.green, colors.red] ,
                                                     width : int = 200, height : int = 200,   style : str = 'h4',  alignment : int = 1  ) -> None:
        """
            Add Pie Chart table to report  - use a dictionary for the chart info  to allow for multiple as well as 

            PARAMETER  :
                            data      :  list of int 
                            labels    :  list of string
                            colors    :  list of colors
                            width     :  int
                            height    :  int
                            style     :  html style tags ( h1 / h2 )
                            alignment :  number represents alignment [ 1 = center ] 
            RETURNS    :
                            Nothing 
        """
        if len( data) == 0  or data is None :
            return

        
        drawing = Drawing ( width, height )
        pie = Pie()
        pie.y = 100
        pie.y = 50
        pie.width = 150
        pie.height = 150
        pie.data = data
        pie.labels = labels
        pie.slices.strokeWidth = 0.5
        pie.slices.fontName = 'Helvetica'
        for pos  in  range( 0, len( labels ) ):
            pie.slices[ pos ].fillColor     = pieColors[pos]
          #  pie.slices[ pos ].label.text    = labels[pos]
        pie.slices[0].popout = 10  # visually popout the slice 
        drawing.add( pie )
        
        # Testing on making a second image / pie chart layout     
        #drawing2 = Drawing ( width, height )
        #drawing2.add( pie )

        # --- Create the Table to hold the charts ---
    
        chart_table_data = [
            [Paragraph("<b>Revenue Distribution</b>", self.Styles['Normal']) ], #, Paragraph("<b>Expense Distribution</b>", self.Styles['Normal'])],
            [drawing]#, drawing2]
        ]

        chart_table_style = TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('BOX', (0,0), (-1,-1), 0.5, colors.black),
            ('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey),
        ])

        chart_table = Table(chart_table_data, colWidths=[width ]) #,width/2])
        chart_table.setStyle(chart_table_style)

        
        self.Story.append ( chart_table ) #  drawing )
        


        
    def Save ( self ) -> None :
        """
            Save the in-memory built pdf to the actual file 
        """
        self.Doc.build( self.Story )
        print( f"\t\t {self.FileName} was created ")


        

    def Send( self, email : str ) -> bool :
        """
            Send the currently built report in memory to the given email

            PARAMENTER :
            REETURNS   : 
        """
        try:
            pass 
        except:
            print("\t\t|EXCEPTION: MAIN::" + str(inspect.currentframe().f_code.co_name) + " - Ran into an exception:" )
            for entry in sys.exc_info():
                print("\t\t >>   " + str(entry) )






















        
