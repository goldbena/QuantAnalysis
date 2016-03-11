# -*- coding: utf-8 -*-
"""
Created on Fri Mar 11 15:11:24 2016

Class for managing estimating risks from portfolios managed under Central Bank of Chile administration

@author: mvillalon
"""


import securities as sec
import sqlite3
import pandas as pd
from datetime import date as dt, datetime as dtime
import json

#Para mostrar informacion en un widget. Solo referencial, deberá ser usado cuando se construya el GUI
#from pandasqt.models import DataFrameModel as dfm
#from PyQt4 import QtGui, QtCore
#import sys

def banner(msg):
        print '*' * 25
        print msg
        print '*' * 25
        log(msg)
        
def log(msg, file = 'G:\DAT\GII\MES_INT\INVINTER\Quantitative Analysis\packagePY/log/log_file_riskFactors.txt'):
    with open(file, 'a') as f:
        f.write('*' * 25 + '\n')
        f.write(msg + '\n')
        f.write('*' * 25 + '\n')
        
class portfolio():
    
    def __init__(self, path = 'G:/DAT/GII/MES_INT/INVINTER/Quantitative Analysis/packagePY/DB/portfolioDB.db', date = None):
        
        if date is None:
            date = dt.today()
        
        self._date = date
        
### DB connections and create DB
#==============================================================================
# Open DB connections and creating necessary data bases for working with the object
#==============================================================================

    def openConnection(self):
        #Función que abre una conexión con el default path de la clase
        con = sqlite3.connect(self._dbPath, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        con.text_factory = str
        return con                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               

    def DBcreate(self):
        #Función que crea base de datos y tablas necesarias para trabajar con el objeto.
        #SOLO ejecutarla si es que no existen tablas anteriores, ya que borra las tablas.
        #A futuro se insertará un comando de seguridad acá (un password)
        con=self.openConnection()
        cursor = con.cursor()
        #con=sqlite3.connect(':memory:')
        cursor.execute('DROP TABLE IF EXISTS identifiers')
       
        
        cursor.execute("CREATE TABLE portfoliosDescription \
                (ID INTEGER PRIMARY KEY NOT NULL,\
                CURRENCY TEXT NOT NULL,\
                RISK_TYPE TEXT NOT NULL,\
                RISK_NAME TEXT NOT NULL,\
                UNIQUE(PORTFOLIO_NAME))")
                
       
        #De la tabla trades TRADE_DESCRIPTION corresponde a la descripción del trade (FX, bono, deposito, contribution, etc).
        #TRADE_TYPE corresponde al tipo de trade ingresado, ya sea SIMULATED, COMMITTED
        #FLAG corresponde a un identificador para poder agrupar trades en estrategias y hacer seguimiento
        cursor.execute("CREATE TABLE trades \
                (ID INTEGER PRIMARY KEY NOT NULL,\
                DATE TIMESTAMP NOT NULL,\
                PORTFOLIO_NAME TEXT NOT NULL,\
                IDENTIFIER TEXT NOT NULL,\
                PRICE REAL NOT NULL,\
                SETTLEMENT_DATE DATE,\
                NOMINAL REAL NOT NULL,\
                CASH_PENDING REAL NOT NULL,\
                CURRENCY_PAY TEXT NOT NULL,\
                TRADE_DESCRIPTION TEXT,\
                TRADE_TYPE TEXT NOT NULL,\
                FLAG TEXT)")                
                
        con.close() 