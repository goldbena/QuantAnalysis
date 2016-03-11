# -*- coding: utf-8 -*-
"""
Created on Fri Feb 12 10:23:58 2016

Class for managing portfolios under Central Bank of Chile administration

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
        
def log(msg, file = 'G:\DAT\GII\MES_INT\INVINTER\Quantitative Analysis\packagePY/log/log_file_portfolios.txt'):
    with open(file, 'a') as f:
        f.write('*' * 25 + '\n')
        f.write(msg + '\n')
        f.write('*' * 25 + '\n')        
        
class portfolio():
    
    def __init__(self, path = 'G:/DAT/GII/MES_INT/INVINTER/Quantitative Analysis/packagePY/DB/portfolioDB.db', date = None):
        
        if date is None:
            date = dt.today()
            
        self._date= date
        self._securities = sec.security()
        self._initialPositions = pd.DataFrame()
        self._trades = pd.DataFrame()
        self._dbPath = path

### Get Risk Exposure information and properties
#==============================================================================
# Functions for getting portfolio risk exposure information, such as Duration, DTS, Yield, etc, and positioning such as Nominal and Market Value USD and Market Value Local
# Additionally gives instrument values and properties for grouping, sush as Currency, Inflation, Quality.
#============================================================================== 

    def getPortfolioRiskContribution(self, portfolio_name, date = None, DBtype = 'portfolios', groupby = None):
        #Get risk properties from portfolio or BMK
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name        
        
        if date is None:
            date = self._date
        
        riskColumns = ['YIELD', 'CONVEXITY', 'DURATION', 'SPREAD', 'KRD', 'DTS']
        groupColumns = ['INFLATION', 'CURRENCY', 'QUALITY']
        
        portfolio = self.DBgetPortfolioProperties(portfolio_name, date = date, DBtype = DBtype)
        
        portfolio['DTS'] = portfolio['DURATION']*portfolio['SPREAD']
        riskContribution = portfolio[riskColumns].mul(portfolio['WEIGHT'], axis = 0)
        
        portfolioRisk = pd.concat([portfolio[['NOMINAL','MARKET_VALUE_USD','MARKET_VALUE_LOCAL','WEIGHT'] + groupColumns], riskContribution], axis = 1)
        
        if groupby is not None:
            portfolioRisk = portfolioRisk.groupby(groupby).agg(lambda x: x.sum())
        
        return portfolioRisk
        
    def getActiveRiskContribution(self, portfolio_name, date = None, groupby = None):
        
        portfolioRisk = self.getPortfolioRiskContribution(portfolio_name, date = date, DBtype = 'portfolios', groupby = groupby)
        BMKRisk = self.getPortfolioRiskContribution(portfolio_name, date = date, DBtype = 'BMK', groupby = groupby)
        
        activeRisk = pd.DataFrame()        
        for column in portfolioRisk:
            try:
                activeColumn = portfolioRisk[column].subtract(BMKRisk[column], fill_value = 0)
            except:
                activeColumn = pd.merge(portfolioRisk[[column]], BMKRisk[[column]], on = column, how = 'outer', right_index = True, left_index = True)
                
                
            activeRisk = pd.concat([activeRisk, activeColumn], axis = 1)
        return activeRisk
        
    def DBgetPortfolioProperties(self, portfolio_name, date = None, DBtype = 'portfolios'):
        #Get portfolio along securities description and pricing
    
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolios %s not created in database. Use createPortolio first.'%(DBtype, portfolio_name)
        assert DBtype.upper() in ('PORTFOLIOS','BMK')
        
        if date is None:
            date = self._date
       
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""SELECT IDENTIFIER, NOMINAL, PORTFOLIO_NAME, MARKET_VALUE_LOCAL, MARKET_VALUE_USD FROM %s
            WHERE PORTFOLIO_NAME = ? AND DATE = ?"""%DBtype, (portfolio_name, date))
            portfolioRetrieved = cur.fetchall()
            
            if not portfolioRetrieved:
                banner("There is no information available for %s %s on date %s"%(DBtype, portfolio_name, date))
                return pd.DataFrame()
                
        portfolioFrame = pd.DataFrame(portfolioRetrieved, columns = ['IDENTIFIER', 'NOMINAL', 'PORTFOLIO_NAME', 'MARKET_VALUE_LOCAL', 'MARKET_VALUE_USD']).set_index(['IDENTIFIER'])        
        securitiesFrame = self.DBgetSecurities(portfolio_name = portfolio_name, date = date, DBtype = DBtype)
        
        if securitiesFrame.empty:
            return securitiesFrame
        
        dataPortfolioAsFrame = pd.concat([portfolioFrame, securitiesFrame], axis = 1)
        
        dataPortfolioAsFrame['WEIGHT'] = dataPortfolioAsFrame['MARKET_VALUE_USD']/dataPortfolioAsFrame['MARKET_VALUE_USD'].sum()
        
        return dataPortfolioAsFrame
        
### Portfolio Managing
#==============================================================================
# Functions for managing portfolio, such as trades, 
#==============================================================================   
        
    def TradeAndUpdatePortfolio(self, portfolio_name, trades, date = None):
        #Function for uploading trades for one specific portfolio and updating portfolio.
        #Any portfolio asign to each specific trade will be overwritten by the portfolio_name
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date= self._date
        
        for trade in trades:

            trade['portfolio_name'] = portfolio_name

            if 'date_time' in trade:
                if trade['date_time'] is None:
                    trade['date_time'] = dtime.combine(date, dtime.min.time())
            else:
                trade['date_time'] = dtime.combine(date, dtime.min.time())
            
        self.DBuploadTrades(trades)
        self.DBupdateNominalAndPricePortfolio(portfolio_name)
        
    def DeleteSimulatedAndUpdatePortfolio(self, portfolio_name, identifiers = None, date = None):
        
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date= self._date
            
        self.DBdeleteSimulatedTrades(portfolio_name, identifiers = identifiers, date = date)
        self.DBupdateNominalAndPricePortfolio(portfolio_name)        
        
    def DBuploadTrades(self, trades):
        #Function for uploading trades into trades database
        dataDB = []        
        for trade in trades:
            try:
                tradeDataFrame = self.getTradeProperties(**trade)
                dataEncoded = self.encodeTradeData(tradeDataFrame.values.tolist()[0])
                dataDB.append(tuple(dataEncoded))
            except Exception, e:
                print(e)
        
        columns = tradeDataFrame.columns.tolist()
        columnStr = ','.join(columns)
        
        questionMarksStr = ','.join(['?']*len(columns))
        
        with self.openConnection() as con:
            cur = con.cursor()
            query = """INSERT INTO trades (%s)
            VALUES (%s)""" %(columnStr, questionMarksStr)
            cur.executemany(query, dataDB)
        
        return dataDB
    
    def DBcommitTrades(self, portfolio_name, identifiers = None, date = None):
        
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            
            if identifiers is None:
                query = """UPDATE trades
                SET TRADE_TYPE = 'COMMITTED'
                WHERE TRADE_TYPE = 'SIMULATED' AND DATE(DATE) = ? AND PORTFOLIO_NAME = ?"""
            else:
                identifierStr = '\'' + "\',\'".join(identifiers) + '\''
                query = """UPDATE trades
                SET TRADE_TYPE = 'COMMITTED'
                WHERE TRADE_TYPE = 'SIMULATED' AND DATE(DATE) = ? AND PORTFOLIO_NAME = ?
                AND IDENTIFIER IN (%s)"""%identifierStr
            cur.execute(query,(date, portfolio_name))
            
        banner('Simulated trades are now committed on portfolio %s for date %s' %(portfolio_name, date))
        return None
                
    def DBdeleteSimulatedTrades(self, portfolio_name, identifiers = None, date = None):
        
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
        
        with self.openConnection() as con:
            cur = con.cursor()
            
            if identifiers is None:
                query = """DELETE FROM trades
                WHERE TRADE_TYPE = 'SIMULATED' AND DATE(DATE) = ? AND PORTFOLIO_NAME = ?"""
            else:
                identifierStr = '\'' + "\',\'".join(identifiers) + '\''
                query = """DELETE FROM trades
                WHERE TRADE_TYPE = 'SIMULATED'
                AND DATE(DATE) = ? AND PORTFOLIO_NAME = ?
                AND IDENTIFIER IN (%s)"""%identifierStr
            cur.execute(query,(date, portfolio_name))
            
        banner('Simulated trades deleted from portfolio %s for date %s' %(portfolio_name, date))
        return None



### Create and upload positions for portfolios
#==============================================================================
# Create new portfolios on DB, upload positions.
#==============================================================================

    def DBcreatePortfolio(self, portfolio_name):
        #Creates a new portfolio on portfoliosDescription        
        actualTime = dtime.now()
        checkPortfolio = self.DBcheckPortfolio(portfolio_name)
        
        assert not checkPortfolio, 'Portfolio %s already created in database on %s.'%(checkPortfolio[1], checkPortfolio[0])
            
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""INSERT INTO portfoliosDescription (DATE_CREATED, PORTFOLIO_NAME)
            VALUES (?,?)""", (actualTime, portfolio_name))
            
            banner("New portfolio %s created at %s"%(portfolio_name, actualTime))
        
        return (actualTime, portfolio_name)
        
    def DBdeletePortfolio(self, portfolio_name):
        #Deletes portfolio from DB, including portfoliosDescription, portfolios and BMK
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""DELETE FROM portfolios WHERE PORTOFOLIO_NAME = ?""", (portfolio_name,))
            cur.execute("""DELETE FROM BMK WHERE PORTOFOLIO_NAME = ?""", (portfolio_name,))
            cur.execute("""DELETE FROM portfoliosDescription WHERE PORTOFOLIO_NAME = ?""", (portfolio_name,))
            
            
    def DBuploadPositionsPortfolio(self, positions, portfolio_name, date = None):
        #Carga posiciones de un portafolio a BD
        if not self.DBcheckPortfolio(portfolio_name):
            banner('Portfolio %s not created in database. Use createPortolio first.'%portfolio_name)
            return False
        if date is None:
            date = self._date
        
        dataDB = [(date, portfolio_name, identifier, position) for identifier, position in positions]
        
        with self.openConnection() as con:
            cur = con.cursor()
            cur.executemany("""INSERT OR REPLACE INTO portfolios (DATE, PORTFOLIO_NAME, IDENTIFIER, NOMINAL_INITIAL)
            VALUES (?,?,?,?)""", dataDB)
        
        return dataDB
        
    def DBuploadPositionsBMK(self, positions, portfolio_name, date = None):
        #Carga posiciones de un BMK a BD
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
        
        dataDB = [(date, portfolio_name, identifier, position) for identifier, position in positions]
        
        with self.openConnection() as con:
            cur = con.cursor()
            cur.executemany("""INSERT OR REPLACE INTO BMK (DATE, PORTFOLIO_NAME, IDENTIFIER, NOMINAL)
            VALUES (?,?,?,?)""", dataDB)
        
        return dataDB
        
    def DBHoldPositionsAndPrice(self, portfolio_name, date = None, Overwrite = False):
        #Open portfolio and BMK for specified date from last positions
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
        
        checkIdentifiersPortfolio = self.DBgetIdentifiersFromPortfolio(portfolio_name = portfolio_name, date = date)
        checkIdentifiersBMK = self.DBgetIdentifiersFromBMK(portfolio_name = portfolio_name, date = date)
        
        if not Overwrite and checkIdentifiersPortfolio:
            banner("There are %s positions for portfolio %s on date %s. Set Overwrite parameter to True if you want to overwrite them."%(len(checkIdentifiersPortfolio), portfolio_name, date))
        else:
            self.DBHoldPositionsPortfolio(portfolio_name, date = date)
            self.pricePortolio(portfolio_name, date = date)
            
        if not Overwrite and checkIdentifiersBMK:
            banner("There are %s positions for BMK %s on date %s. Set Overwrite parameter to True if you want to overwrite them."%(len(checkIdentifiersPortfolio), portfolio_name, date))
        else:
            self.DBHoldPositionsBMK(portfolio_name, date = date)
            self.priceBMK(portfolio_name, date = date)
            
        
        
    def DBHoldPositionsPortfolio(self, portfolio_name, date = None):
        #Open portfoliofor specified date from last positions available.
        #Warning: any previous positions for that date will be overwrited.
        if not self.DBcheckPortfolio(portfolio_name):
            banner('Portfolio %s not created in database. Use createPortolio first.'%portfolio_name)
            return False
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""SELECT MAX(DATE) FROM portfolios WHERE PORTFOLIO_NAME = ? and DATE < ?""", (portfolio_name, date))
            lastAvailableDate = cur.fetchall()[0][0]
            if not lastAvailableDate:
                banner('There are no identifiers available for portfolio %s previous to date %s .'%(date, portfolio_name))
                return False
                        
            cur.execute("""DELETE FROM portfolios
                WHERE PORTFOLIO_NAME = ? AND DATE = ?""",(portfolio_name, date))
            
            cur.execute("""INSERT INTO portfolios (DATE, PORTFOLIO_NAME, IDENTIFIER, NOMINAL_INITIAL)
            SELECT ?, PORTFOLIO_NAME, IDENTIFIER, NOMINAL FROM portfolios
            WHERE DATE = ? and PORTFOLIO_NAME = ? AND NOMINAL <> 0""",(date, lastAvailableDate, portfolio_name))
            
        banner('Portfolio %s opened for date %s using positions from %s.'%(portfolio_name, date, lastAvailableDate))
        
        self.DBupdateNominal(portfolio_name, date = date)
        
        return True
            
    def DBHoldPositionsBMK(self, portfolio_name, date = None):
        #Open portfoliofor specified date from last positions available.
        #Warning: any previous positions for that date will be overwrited.
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""SELECT MAX(DATE) FROM BMK WHERE PORTFOLIO_NAME = ? and DATE < ?""", (portfolio_name, date))
            lastAvailableDate = cur.fetchall()[0][0]
            if not lastAvailableDate:
                banner('There are no identifiers available for BMK %s previous to date %s .'%(date, portfolio_name))
                return False
                        
            cur.execute("""DELETE FROM BMK
                WHERE PORTFOLIO_NAME = ? AND DATE = ?""",(portfolio_name, date))
            
            cur.execute("""INSERT INTO BMK (DATE, PORTFOLIO_NAME, IDENTIFIER, NOMINAL)
            SELECT ?, PORTFOLIO_NAME, IDENTIFIER, NOMINAL FROM BMK
            WHERE DATE = ? and PORTFOLIO_NAME = ? AND NOMINAL <> 0""",(date, lastAvailableDate, portfolio_name))
        
        
        banner('BMK %s opened for date %s using positions from %s.'%(portfolio_name, date, lastAvailableDate))
        return True    
            
            
### Price portfolios
#==============================================================================
# Functions for pricing portfolios based on securities information
#==============================================================================
    
    def DBupdateNominalAndPriceAll(self, portfolio_name, date = None):
        #Función que actualiza tanto portafolio como BMK, actualizando además el nominal frente a modificaciones en los trades.
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
            
        self.DBupdateNominalAndPricePortfolio(portfolio_name, date = date)
        self.priceBMK(portfolio_name, date = date)
        
    def DBupdateNominalAndPricePortfolio(self, portfolio_name, date = None):
        #Función que actualiza nominal de los instrumentos del portafolio a partir de su nominal inicial y trades y luego los valoriza.
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
            
        self.DBupdateNominal(portfolio_name, date = date)
        self.pricePortolio(portfolio_name, date = date)
        
    def DBupdateNominal(self, portfolio_name, date = None):
        #Función que actualiza nominal de los instrumentos del portafolio a partir de su nominal inicial y trades.
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
        
        #Actualizamos los identificadores nuevos que están en la BD trades y que no están en el portafolio (cuando se ingresa un nuevo instrumento al portafolio)
        with self.openConnection() as con:
            cur = con.cursor()
            query = """INSERT INTO portfolios (DATE, PORTFOLIO_NAME, IDENTIFIER, NOMINAL_INITIAL)
            SELECT DATE(DATE), PORTFOLIO_NAME, IDENTIFIER, 0 FROM trades
            WHERE DATE(DATE) = ? AND PORTFOLIO_NAME = ? AND IDENTIFIER NOT IN
            (SELECT DISTINCT IDENTIFIER FROM portfolios WHERE DATE = ? AND PORTFOLIO_NAME = ?)"""
            cur.execute(query, (date, portfolio_name, date, portfolio_name))
            
            #Actualizamos monedas de cashpending que no estaban antes en el portafolio
            query = """INSERT INTO portfolios (DATE, PORTFOLIO_NAME, IDENTIFIER, NOMINAL_INITIAL)
            SELECT DATE(DATE), PORTFOLIO_NAME, CURRENCY_PAY, 0 FROM trades
            WHERE DATE(DATE) = ? AND PORTFOLIO_NAME = ? AND CURRENCY_PAY NOT IN
            (SELECT DISTINCT IDENTIFIER FROM portfolios WHERE DATE = ? AND PORTFOLIO_NAME = ?)"""
            cur.execute(query, (date, portfolio_name, date, portfolio_name))
            
        nominalInitial = self.DBgetNominalInitial(portfolio_name, date = date)
        trades = self.DBgetNominalModificationFromTrades(portfolio_name, date = date)
        
        
        nominal = pd.concat([nominalInitial, trades], axis = 1).sum(axis = 1)
        
        dataDB = [(nominalTotal, identifier, date, portfolio_name) for identifier, nominalTotal in nominal.iteritems()]
        
        
        
        with self.openConnection() as con:
            cur = con.cursor()
            
            #Actualizamos primer todos los nominales a su nominal inicial:
            cur.execute("""UPDATE portfolios
            SET NOMINAL = NOMINAL_INITIAL
            WHERE DATE = ? AND PORTFOLIO_NAME = ?""",(date, portfolio_name))
            
            #Actualizamos los nominales de los instrumentos transados
            cur.executemany("""UPDATE portfolios
            SET NOMINAL = ?
            WHERE IDENTIFIER = ? AND DATE = ? AND PORTFOLIO_NAME = ?""", dataDB)
            
        return dataDB
    
    
    def pricePortolio(self, portfolio_name, date = None):
        #Function that prices specified portfolio given securities stored information
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
     
        
        dataPriced = self.DBgetPortfolioProperties(portfolio_name, date = date, DBtype = 'portfolios')
        
        dataPriced['MARKET_VALUE_LOCAL'] = dataPriced['NOMINAL']*dataPriced['PRICE']/100
        dataPriced['MARKET_VALUE_USD'] = dataPriced['MARKET_VALUE_LOCAL']*dataPriced['USDFX']
        
        if dataPriced.empty:
            banner('No data available for pricing portfolio (%s). pricePortfolio() will exit.'%portfolio_name)            
            return False
            
        dataDBFrame = dataPriced[['MARKET_VALUE_USD','MARKET_VALUE_LOCAL','DATE','PORTFOLIO_NAME']]
        dataDBFrame['IDENTIFIER'] = dataDBFrame.index
        
        with self.openConnection() as con:
            cur = con.cursor()
            cur.executemany("""UPDATE portfolios
            SET MARKET_VALUE_USD = ?, MARKET_VALUE_LOCAL = ?
            WHERE DATE = ? AND PORTFOLIO_NAME = ? AND IDENTIFIER = ? """, dataDBFrame.values)
        
        unpricedPositions = self.DBcheckUnpricedPositions(portfolio_name, date = date, DBtype = 'portfolios')
        
        if unpricedPositions:
            'Warning, there are %s unpriced positions on portfolio %s for date %s. Verify they are priced on securitiesPricing DB.'%(len(unpricedPositions), portfolio_name, date)
        
        banner('Portfolio %s priced for date %s'%(portfolio_name, date))
        return dataDBFrame
        
    def priceBMK(self, portfolio_name, date = None):
        #Function that prices specified BMK given securities stored information
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
        
        dataPriced = self.DBgetPortfolioProperties(portfolio_name, date = date, DBtype = 'BMK')
        if dataPriced.empty:
            banner('No data available for pricing BMK (%s). priceBMK() will exit.'%portfolio_name)            
            return False
            
        dataPriced['MARKET_VALUE_LOCAL'] = dataPriced['NOMINAL']*dataPriced['PRICE']/100
        dataPriced['MARKET_VALUE_USD'] = dataPriced['MARKET_VALUE_LOCAL']*dataPriced['USDFX']
        
        dataDBFrame = dataPriced[['MARKET_VALUE_USD','MARKET_VALUE_LOCAL','DATE','PORTFOLIO_NAME']]
        dataDBFrame['IDENTIFIER'] = dataDBFrame.index
        
        with self.openConnection() as con:
            cur = con.cursor()
            cur.executemany("""UPDATE BMK
            SET MARKET_VALUE_USD = ?, MARKET_VALUE_LOCAL = ?
            WHERE DATE = ? AND PORTFOLIO_NAME = ? AND IDENTIFIER = ? """, dataDBFrame.values)
            
        unpricedPositions = self.DBcheckUnpricedPositions(portfolio_name, date = date, DBtype = 'BMK')
        if unpricedPositions:
            'Warning, there are %s unpriced positions on BMK %s for date %s. Verify they are priced on securities DB.'%(len(unpricedPositions), portfolio_name, date)
        
        banner('BMK %s priced for date %s'%(portfolio_name, date))    
        return dataDBFrame
    
    
    def requestInsertNewSecurities(self, query_with_identifiers):
        #Method for inserting new securities to DB using securities through portfolios instance
        self._securities.insertNewSecurity(query_with_identifiers)
        
    
    def requestPriceNewSecurities(self, identifiers = None, date = None):
        #Method for pricing securities through portfolios instance.
        #It supports historical pricing for deposits and cashs.
        if date is None:
            date = self._name
            
        if date == dt.today():
            self._securities.priceSecurities(identifiers = identifiers, Overwrite = False)
        else:
            self._securities.priceSecuritiesHistorical(identifiers = identifiers, date = date, Overwrite = False)
            
                
#        self._securities.insertNewSecurity(query_with_identifiers)
    
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
        cursor.execute('DROP TABLE IF EXISTS portfoliosDescription')
        cursor.execute('DROP TABLE IF EXISTS portfolios')
        cursor.execute('DROP TABLE IF EXISTS BMK')
        cursor.execute('DROP TABLE IF EXISTS trades')
        
        cursor.execute("CREATE TABLE portfoliosDescription \
                (ID INTEGER PRIMARY KEY NOT NULL,\
                DATE_CREATED TIMESTAMP NOT NULL,\
                PORTFOLIO_NAME TEXT NOT NULL,\
                UNIQUE(PORTFOLIO_NAME))")
                
        cursor.execute("CREATE TABLE portfolios \
                (ID INTEGER PRIMARY KEY NOT NULL,\
                DATE DATE NOT NULL,\
                PORTFOLIO_NAME TEXT NOT NULL,\
                IDENTIFIER TEXT NOT NULL,\
                NOMINAL REAL,\
                NOMINAL_INITIAL REAL,\
                MARKET_VALUE_USD REAL,\
                MARKET_VALUE_LOCAL REAL,\
                UNIQUE(PORTFOLIO_NAME,IDENTIFIER,DATE))")
                
        cursor.execute("CREATE TABLE BMK \
                (ID INTEGER PRIMARY KEY NOT NULL,\
                DATE DATE NOT NULL,\
                PORTFOLIO_NAME TEXT NOT NULL,\
                IDENTIFIER TEXT NOT NULL,\
                NOMINAL REAL,\
                MARKET_VALUE_USD REAL,\
                MARKET_VALUE_LOCAL REAL,\
                UNIQUE(PORTFOLIO_NAME,IDENTIFIER,DATE))")
        
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


    
### Get DB information and properties
#==============================================================================
# Functions that check information and properties on portfolios DB
#==============================================================================   
    
    def DBcheckUnpricedPositions(self, portfolio_name, date = None, DBtype = 'portfolios'):
        #Revisa y entrega todas las posiciones que no están actualmente valorizadas en el portafolio
        '''
        Inputs: str, date, str
        Outputs: list
        '''
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        assert DBtype.upper() in ('PORTFOLIOS', 'BMK')
        
        if date is None:
            date = self._date
        
        with self.openConnection() as con:
            cur = con.cursor()
            query = """SELECT IDENTIFIER FROM %s WHERE PORTFOLIO_NAME = ? AND DATE = ? AND MARKET_VALUE_USD IS NULL"""%DBtype
            cur.execute(query, (portfolio_name, date))
            unpricedPositions = cur.fetchall()
            if not unpricedPositions:
                return []
        
        return [i[0] for i in unpricedPositions]   
            
    def DBcheckPortfolio(self, portfolio_name):
        '''
        Inputs: str
        Outputs: str or bool
        '''
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""SELECT DATE_CREATED, PORTFOLIO_NAME FROM portfoliosDescription
            WHERE PORTFOLIO_NAME = ?""",(portfolio_name,))
            portfolio = cur.fetchall()
            
        if portfolio:
            return portfolio[0]
       
        return False
    
    def DBgetAllIdentifiers(self, portfolio_name = None, date = None):
        #Función que entrega los identificadores de un portafolio (o todos los portafolios) para una fecha determinada para el portafolio y BMK
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            if portfolio_name is None:
                query = """SELECT DISTINCT IDENTIFIER FROM portfolios WHERE DATE = ?
                UNION
                SELECT DISTINCT IDENTIFIER FROM BMK WHERE DATE = ?"""
                cur.execute(query, (date,date))       
            else:
                query = """SELECT DISTINCT IDENTIFIER FROM portfolios WHERE DATE = ? AND PORTFOLIO_NAME = ?
                UNION
                SELECT DISTINCT IDENTIFIER FROM BMK WHERE DATE = ? AND PORTFOLIO_NAME = ?"""
                
                cur.execute(query, (date,portfolio_name,date,portfolio_name))
                
            identifiersRetrieved = cur.fetchall()
        
        if not identifiersRetrieved:
            return False
            
        return [identifier[0] for identifier in identifiersRetrieved]
        
    def DBgetIdentifiersFromPortfolio(self, portfolio_name = None, date = None):
        #Función que entrega los identificadores de un portafolio (o todos los portafolios) para una fecha determinada para el portafolio y BMK
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            if portfolio_name is None:
                query = """SELECT DISTINCT IDENTIFIER FROM portfolios WHERE DATE = ?"""
                cur.execute(query, (date,))       
            else:
                query = """SELECT DISTINCT IDENTIFIER FROM portfolios WHERE DATE = ? AND PORTFOLIO_NAME = ?"""
                
                cur.execute(query, (date,portfolio_name))
                
            identifiersRetrieved = cur.fetchall()
        
        if not identifiersRetrieved:
            return False
            
        return [identifier[0] for identifier in identifiersRetrieved]
    
    def DBgetIdentifiersFromBMK(self, portfolio_name = None, date = None):
        #Función que entrega los identificadores de un portafolio (o todos los portafolios) para una fecha determinada para el portafolio y BMK
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            if portfolio_name is None:
                query = """SELECT DISTINCT IDENTIFIER FROM BMK WHERE DATE = ?"""
                cur.execute(query, (date,))       
            else:
                query = """SELECT DISTINCT IDENTIFIER FROM BMK WHERE DATE = ? AND PORTFOLIO_NAME = ?"""
                
                cur.execute(query, (date,portfolio_name))
                
            identifiersRetrieved = cur.fetchall()
        
        if not identifiersRetrieved:
            return False
            
        return [identifier[0] for identifier in identifiersRetrieved]
        
    def DBgetNominalInitial(self, portfolio_name, date = None):
        #Entrega el nominal Inicial por identificador del portafolio ingresado
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""SELECT IDENTIFIER, NOMINAL_INITIAL FROM portfolios
            WHERE DATE = ? AND PORTFOLIO_NAME = ?""",(date, portfolio_name))
            dataRetrieved = cur.fetchall()
            
            if not dataRetrieved:
                banner("No data for %s portfolio in portfolios DataBase fro date %s"%(portfolio_name,date))
        
        dataAsFrame = pd.DataFrame(dataRetrieved, columns = ['IDENTIFIER','NOMINAL_INITIAL']).set_index(['IDENTIFIER'])
        return dataAsFrame
        
    def DBgetNominalModificationFromTrades(self, portfolio_name, date = None):
        #Entrega modificaciones al nominal consecuencia de la información contenida en la tabla de trades
    
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
       
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""SELECT IDENTIFIER, SUM(NOMINAL) FROM trades
            WHERE PORTFOLIO_NAME = ? AND DATE(DATE) = ?
            GROUP BY IDENTIFIER""",(portfolio_name, date))
            
            dataNominalRetrieved = cur.fetchall()
            
            cur.execute("""SELECT CURRENCY_PAY, -SUM(CASH_PENDING) FROM trades
            WHERE PORTFOLIO_NAME = ? AND DATE(DATE) = ?
            GROUP BY CURRENCY_PAY""",(portfolio_name, date))
            
            dataPaymentRetrieved = cur.fetchall()
            
        dataAsFrame = pd.DataFrame(dataNominalRetrieved, columns = ['IDENTIFIER','NOMINAL']).set_index(['IDENTIFIER'])
        paymentAsFrame = pd.DataFrame(dataPaymentRetrieved, columns = ['IDENTIFIER','NOMINAL']).set_index(['IDENTIFIER'])
        
        return dataAsFrame.add(paymentAsFrame, fill_value = 0)
        
    def DBgetSecurities(self, portfolio_name = None, date = None, DBtype = 'portfolios'):
        #Entrega información de descripción y valorización de securities para un portafolio.
        #Price securities from portfolios
    
        assert DBtype.upper() in ('PORTFOLIOS', 'BMK', 'ALL'), '%s not recognized. Portfolio %s could not be priced for date %s'%(DBtype, portfolio_name, date)

        if date is None:
            date = self._date
        
        if DBtype.upper() == 'PORTFOLIOS':
            identifiers = self.DBgetIdentifiersFromPortfolio(portfolio_name = portfolio_name, date = date)
            
        elif DBtype.upper() == 'BMK':
            identifiers = self.DBgetIdentifiersFromBMK(portfolio_name = portfolio_name, date = date)
            
        elif DBtype.upper() == 'ALL':
            identifiers = self.DBgetAllIdentifiers(portfolio_name = portfolio_name, date = date)
            
        else:
            return pd.DataFrame()
        
        if not identifiers:
            banner('No identifiers for type %s on portfolio %s for date %s.'%(DBtype, portfolio_name, date))
            return pd.DataFrame()
            
        securities = self._securities.DBgetSecurities(identifiers = identifiers, date = date)
        
        #It's practical to index KRD for aggregation methods
        if not securities.empty:
            securities['KRD'] = securities['KRD'].apply(lambda x: x.set_index(['Maturity']))
            
        return securities
        
    def DBgetAllAvailableSecurities(self, date = None):
        #Gets all available securities on DB, priced on a given date.
        if date is None:
            date = self._date
            
        securities = self._securities.DBgetSecurities(date = date)
        
        #It's practical to index KRD for aggregation methods
        if not securities.empty:
            securities['KRD'] = securities['KRD'].apply(lambda x: x.set_index(['Maturity']))
            
        return securities
        
    def DBgetAvailableIssuers(self):
        
        availableIssuers = self._securities.DBgetAvailableIssuers()
        return availableIssuers
            
        
        
    def DBgetAvailablePortfolios(self):
        #Returns available portfolios in DB
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""SELECT DISTINCT PORTFOLIO_NAME FROM portfoliosDescription""")
            dataRetrieved = cur.fetchall()
            
        return [i[0] for i in dataRetrieved]
        
    def DBgetLastAvailableDate(self, portfolio_name):
        #Returns last available date for the given portfolio_name
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""SELECT MAX(DATE) FROM portfolios
            WHERE PORTFOLIO_NAME = ?""",(portfolio_name,))
            dataRetrieved = cur.fetchall()
        
        date = dtime.strptime(dataRetrieved[0][0], "%Y-%m-%d").date()
        
        return date
        
    def DBgetSimulatedTrades(self, portfolio_name, identifiers = None, date = None):
        #Returns simulated trades
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            
            if identifiers is None:
                query = """SELECT DATE, PORTFOLIO_NAME, IDENTIFIER, PRICE, NOMINAL, CURRENCY_PAY, TRADE_DESCRIPTION, CASH_PENDING FROM trades
                WHERE PORTFOLIO_NAME = ? AND DATE(DATE) = ? AND TRADE_TYPE = 'SIMULATED'"""
                
            else:
                identifierStr = '\'' + "\',\'".join(identifiers) + '\''
                query = """SELECT DATE, PORTFOLIO_NAME, IDENTIFIER, PRICE, NOMINAL, CURRENCY_PAY, TRADE_DESCRIPTION, CASH_PENDING FROM trades
                WHERE PORTFOLIO_NAME = ? AND DATE(DATE) = ? AND TRADE_TYPE = 'SIMULATED'
                AND IDENTIFIER IN (%s)"""%identifierStr
            cur.execute(query, (portfolio_name, date))
            dataRetrieved = cur.fetchall()
            
            if not dataRetrieved:
                return pd.DataFrame([], columns = ['DATE', 'PORTFOLIO_NAME', 'IDENTIFIER', 'PRICE', 'NOMINAL', 'CURRENCY_PAY', 'TRADE_DESCRIPTION', 'CASH_PENDING'])
                
        dataAsFrame = pd.DataFrame(dataRetrieved, columns = ['DATE', 'PORTFOLIO_NAME', 'IDENTIFIER', 'PRICE', 'NOMINAL', 'CURRENCY_PAY', 'TRADE_DESCRIPTION', 'CASH_PENDING'])
        
        return dataAsFrame

    def getBBGQueryFromTrades(self, identifiers):
        #Attempts to get BBG_queries based on trade_description from trade table and the identifier.
        with self.openConnection() as con:
            cur = con.cursor()
            identifierStr = '\'' + "\',\'".join(identifiers) + '\''
            cur.execute("""SELECT DISTINCT IDENTIFIER, TRADE_DESCRIPTION FROM trades
            WHERE IDENTIFIER IN (%s)"""%identifierStr)
            dataRetrieved = cur.fetchall()
            if not dataRetrieved:
                return False
                
        query_with_identifiers = []  
        
        for data, description in dataRetrieved:
            if description == 'BOND':
                query_with_identifiers.append((data + ' Govt', data))
            elif description in ('FX', 'CONTRIBUTION', 'WITHDRAWAL'):
                query_with_identifiers.append((data + 'USD Govt', data))
            else:
                query_with_identifiers.append((data, data))
                
        return query_with_identifiers
        
    def getBBGQueryFromIdentifiers(self, identifiers):
        
        return self._securities.getQueryFromIdentifiers(identifiers)
    
        
### Get Trade Properties
#==============================================================================
# Functions for getting properties for trades of different kind of securities 
#============================================================================== 
        
    def getTradeProperties(self, identifier, nominal, trade_description, portfolio_name, trade_type = 'SIMULATED', date_time = None, flag = None, price = None, **kwargs):
        
        #Get trade standarized properties for uploading information to DB, given the specific type of trade.
    
        trade_description = trade_description.upper()
        trade_type = trade_type.upper()
        nominal = float(nominal)
        
        assert trade_description in ('FX','CONTRIBUTION','WITHDRAWAL','TIME DEPOSIT', 'COMMERCIAL PAPER', 'BOND')
        assert self.DBcheckPortfolio(portfolio_name), 'Portfolio %s not created in database. Use createPortolio first.'%portfolio_name
        assert trade_type in ('COMMITTED', 'SIMULATED')
        
        if date_time is None:
            date_time = dtime.now()
        
        if trade_description == 'FX':
            assert 'currency_pay' in kwargs, 'For FX trades you need to input the currency_pay'            
            price, cash_pending, currency_pay, settlement_date = self.getFXTradeProperties(identifier, kwargs['currency_pay'], nominal, date = date_time.date(), )
            
        elif trade_description in ('CONTRIBUTION', 'WITHDRAWAL'):
            price, cash_pending, currency_pay, settlement_date = self.getContributionTradeProperties(identifier)
            
        elif trade_description == 'BOND':
            price, cash_pending, currency_pay, settlement_date = self.getBondTradeProperties(identifier, nominal, price = price, date = date_time.date(), **kwargs)
            
        elif trade_description in ('TIME DEPOSIT', 'COMMERCIAL PAPER'):
            price, cash_pending, currency_pay, settlement_date = self.getDepositTradeProperties(identifier, nominal, date = date_time.date(), **kwargs)
            
        else:
            return False
        
        dataTrade = (date_time, portfolio_name, identifier, price, settlement_date, nominal, cash_pending, currency_pay, trade_description, trade_type, flag)
        columnNames = ['DATE', 'PORTFOLIO_NAME', 'IDENTIFIER', 'PRICE', 'SETTLEMENT_DATE', 'NOMINAL', 'CASH_PENDING', 'CURRENCY_PAY', 'TRADE_DESCRIPTION', 'TRADE_TYPE', 'FLAG']
        
        dataAsFrame = pd.DataFrame([dataTrade], columns = columnNames)
        
        return dataAsFrame
        
    def getFXTradeProperties(self, identifier, currency_pay, nominal, price = None, date = None, settlement_date = None):
        
        if price is None:
            if date is None:
                date = self._date
                
            security = self._securities.DBgetSecurities(identifiers = [identifier, currency_pay], date = date)
            price = security['USDFX'][identifier]/security['USDFX'][currency_pay]
        
        cash_pending = nominal*price
        
        return price, cash_pending, currency_pay, settlement_date
        
    def getContributionTradeProperties(self, identifier):
        
        price = 0.
        cash_pending = 0.
        settlement_date = None
        currency_pay = identifier
        
        return price, cash_pending, currency_pay, settlement_date
        
    def getBondTradeProperties(self, identifier, nominal, price = None, date = None, settlement_date = None, currency_pay = None):
        
        if date is None:
                date = self._date
        security = self._securities.DBgetSecurities(identifiers = [identifier], date = date)
        
        #If identifier is not on DB, we should input the price and currency_pay for updating price.        
        if security.empty:
            assert isinstance(price, float) and isinstance(currency_pay, str), 'Security %s not found on database for date %s. Price and currency_pay should be inputed'%(identifier, date)
        else:    
            currency_pay = security['CURRENCY'][0]
            if price is None:
                price = security['PRICE'][0]
        
        cash_pending = nominal*price/100
            
        return price, cash_pending, currency_pay, settlement_date
        
    def getDepositTradeProperties(self, identifier, nominal, date = None, price = None, settlement_date = None):
        
        depositInfo = self._securities.getDepositInfoFromIdentifiers([identifier], pricing_date = date)

        price = depositInfo['pricing']['PRICE'][0]
        currency_pay = depositInfo['description']['CURRENCY'][0]
        cash_pending = nominal*price/100
        
        return price, cash_pending, currency_pay, settlement_date
    
        
### Encode/Decode Information
#==============================================================================
# Functions encoding and decoding information to/from DB 
#============================================================================== 
    
    def encodeTradeData(self, dataIter):
        #Función que codifica los datos que vienen de blp de tia y los convierte en el formato establecido para ser cargado en base de datos.
        dataEncode = []
        for data in dataIter:
            try:
                if isinstance(data, pd.DataFrame):
                    dataEncode.append(data.to_json())
                elif isinstance(data,pd.tslib.Timestamp):
                    dataEncode.append(data.to_pydatetime())
                elif not isinstance(data,(basestring,type(None))):
                    dataEncode.append(json.dumps(data))
                else: 
                    dataEncode.append(data)
            except:
                dataEncode.append(data)
                
        return dataEncode 
        
    def decodeTradeData(self, dataIter):
        
        dataDecode = []
        for data in dataIter:
            try:
                dataDecode.append(pd.read_json(data, convert_dates=['Payment Date','Date']))
            except:
                dataDecode.append(data)
                
        return dataDecode         
        
        
if __name__ == '__main__':
    port = portfolio()
#    port.DBcreate()
#    port.DBcreatePortfolio(portfolio_name = 'Test')
#    port.DBcheckPortfolio('Test')
    
#    positions = [('USD', 100),('EUR', 150),('JPY', 100),('CHF', 26)]
#    positionsBMK = [('USD', 100)]
#    
#    port.DBuploadPositionsPortfolio(positions, portfolio_name = 'Test')
#    port.DBuploadPositionsBMK(positionsBMK, portfolio_name = 'Test')
    
#    data = port.DBgetSecurities(DBtype = 'All')    
    
#    dataTrades = port.DBgetNominalModificationFromTrades('Test')
#    data = port.DBgetNominalInitial('Test')
    
#    data = port.DBupdateNominal(portfolio_name = 'Test')
#    data = port.pricePortolio('Test')
#    data = port.priceBMK('Test')
    
#    data = port.DBHoldPositionsPortfolio('Test', date = dt(2016,2,16))
#    data = port.DBHoldPositionsBMK('Test', date = dt(2016,2,16))
    
#    data = port.DBHoldPositionsAndPrice('Mauro_Test', Overwrite = True)
#    
    
        
    #FX
#    data = port.getTradeProperties('JPY', 1000, 'FX', 'Test', currency_pay = 'EUR')
    
#    columns = ['identifier', 'nominal', 'trade_description', 'portfolio_name', 'trade_type']
#    
#    trade1 = {'identifier':'JPY',
#              'nominal':1000,
#              'trade_description':'FX',
#              'portfolio_name': 'Test',
#              'currency_pay':'EUR'}
#              
#    trade2 = {'identifier':'EUR',
#              'nominal':100,
#              'trade_description':'contribution',
#              'portfolio_name': 'Test'}
#              
#    trade3 = {'identifier': 'US912828P535',
#              'nominal':100,
#              'trade_description':'bond',
#              'portfolio_name': 'Test'}
#              
#    trade4 = {'identifier': 'US912828P535',
#              'nominal':100,
#              'trade_description':'bond',
#              'portfolio_name': 'Test',
#              'price': 99.5549,
#              'currency_pay': 'USD'}
    
#    trade5 = {'identifier': 'US912828N712',
#              'nominal':146,
#              'trade_description':'bond',
#              'portfolio_name': 'Test'}
#              
#    trades = [trade5]
#            
#    data = port.DBuploadTrades(trades)
#    port.DBupdateNominalAndPricePortfolio('Test')
    
#    data = port.DBgetPortfolioProperties('Test')
    
#    data = port.getPortfolioRiskContribution('Test')
#    data = port.getPortfolioRiskContribution('Test', groupby=['CURRENCY'])
    
#    portfolioRisk = port.getPortfolioRiskContribution('Test', DBtype = 'portfolios')
#    BMKRisk = port.getPortfolioRiskContribution('Test', DBtype = 'BMK')
    
#    data = port.getActiveRiskContribution('Test')

#    data = port.getPortfolioRiskContribution('Test', groupby=['CURRENCY', 'INFLATION'])
    
#    date = port.DBupdateNominalAndPriceAll('Test')
    
#    trade = {'identifier': 'JP1201191A72',
#             'nominal': 10000,
#             'trade_description': 'bond',
#             'portfolio_name': 'Test',
#             'price': 123.629,
#             'currency_pay': 'JPY'}

#    trade = {'identifier': 'EUR',
#             'nominal': 100,
#             'trade_description': 'FX',
#             'portfolio_name': 'Test',
#             'currency_pay': 'AUD'}
#    
#             
#    trades = [trade]
#    
#    port.TradeAndUpdatePortfolio('Test', trades)
#    
#    port.DBuploadTrades(trades)
#    port.DBupdateNominalAndPriceAll('Test')
#    
#    port.DBdeleteSimulatedTrades('Test')
#    port.DeleteSimulatedAndUpdatePortfolio('Test')
    
#    port.DBcommitTrades('Test')
    
#    app = QtGui.QApplication(sys.argv) 
#    
#    dfmodel = dfm.DataFrameModel(data)
#    view = QtGui.QTableView()
#    view.setModel(dfmodel)
#    view.setSortingEnabled(True)
#    view.verticalHeader().setVisible(False)
#    
#    layout = QtGui.QVBoxLayout()
#    layout.addWidget(view)
#    widget = QtGui.QWidget()
#    widget.setLayout(layout)
#    widget.show()
#    sys.exit(app.exec_())
    
#    data = port.DBgetLastAvailableDate('Test')
#    data = port.DBgetAllAvailableSecurities()
    
#    data = port.requestInsertNewSecurities([('DEPOAUD20160308A1QTB_0.12','DEPOAUD20160308A1QTB_0.12')])
#    data = port.getBBGQueryFromTrades(['DEPOAUD20160308A1QTB_0.12', 'AUD', 'JP1201191A72'])