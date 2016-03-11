# -*- coding: utf-8 -*-
"""
Created on Fri Jan 29 09:59:35 2016

Class for managing securities used in portfolios under Central Bank of Chile administration

@author: mvillalon
"""

import sys
import sqlite3
import json
import pandas as pd
from tia.bbg import v3api
from datetime import date as dt, datetime as dtime

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
    
class security(object):

    def __init__(self,path = 'G:/DAT/GII/MES_INT/INVINTER/Quantitative Analysis/packagePY/DB/securityDB.db'):
        
        self._date = dt.today()
        self._dbPath=path
        self._securities = None   
        
### Main retrieve securities
#==============================================================================
# Main Functions for retrieving securities information. Always prefer using this.
#==============================================================================

    @property
    def securities(self):
        return self._securities
        
    def DBgetSecurities(self, identifiers = None, date = None):
        #Función que busca datos de securities en base datos para identificadores y fecha indicada.
    
        dynamicColumns = ['IDENTIFIER', 'PRICE', 'YIELD', 'CONVEXITY','DURATION','SPREAD','KRD','DATE']
        descriptionColumns = ['TICKER', 'MATURITY','ISSUER','INFLATION','CURRENCY','QUALITY','DESCRIPTION','CASHFLOWS']
        fxColumns = ['PRICE']
        
        dynColStr = ','.join(['b.' + col for col in dynamicColumns])
        desColStr = ','.join(['a.' + col for col in descriptionColumns])
        fxColStr = ','.join(['c.' + col for col in fxColumns])
        
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            if identifiers is None:
                query = """SELECT DISTINCT %s, %s, %s
                FROM securitiesDescription a,
                securitiesPricing b,
                USDfx c
                WHERE a.IDENTIFIER = b.IDENTIFIER AND a.CURRENCY = c.IDENTIFIER AND b.DATE in
                (SELECT MAX(DATE) FROM securitiesPricing WHERE DATE >= ?)
                AND c.DATE = b.DATE"""%(dynColStr, desColStr, fxColStr)
            else:
                identifierStr = '\'' + "\',\'".join(identifiers) + '\''
                query = """SELECT DISTINCT %s, %s, %s
                FROM securitiesDescription a,
                securitiesPricing b,
                USDfx c
                WHERE a.IDENTIFIER = b.IDENTIFIER AND a.CURRENCY = c.IDENTIFIER AND b.DATE in
                (SELECT MAX(DATE) FROM securitiesPricing WHERE DATE >= ?)
                AND a.IDENTIFIER IN (%s)
                AND c.DATE = b.DATE"""%(dynColStr, desColStr, fxColStr, identifierStr)
                
            cur.execute(query, (date,))
            dataRetrieved = cur.fetchall()
            
            if not dataRetrieved:
                return pd.DataFrame()
        
        dataDecoded = []
        for data in dataRetrieved:
            dataDecoded.append(self.decodeData(data))
        
        dataAsFrame = pd.DataFrame.from_records(dataDecoded, columns = dynamicColumns + descriptionColumns + ['USDFX'])
        dataAsFrame.set_index('IDENTIFIER', inplace = True)
        
        self._securities = dataAsFrame
        
        return dataAsFrame
    
    def DBgetCashFlows(self, identifiers = None, date = None):
        #Función que busca datos de cashflows en base datos para identificadores y a partir de la fecha indicada.
        #Si no se especifica fecha se entregará a partir de la fecha actual del objeto
        
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            if identifiers is None:
                query  = """SELECT IDENTIFIER, DATE, COUPON, PRINCIPAL FROM cashflows
                WHERE DATE >= ?"""
                
            else:
#                identifierStr = ','.join(identifiers)
                identifierStr = '\'' + "\',\'".join(identifiers) + '\''
                query  = """SELECT IDENTIFIER, DATE, COUPON, PRINCIPAL FROM cashflows
                WHERE DATE >=? AND IDENTIFIER IN (%s)"""%identifierStr
                
            cur.execute(query,(date,))
            dataRetrieved = cur.fetchall()
            
            if not dataRetrieved:
                return False
        
        dataAsFrame = pd.DataFrame.from_records(dataRetrieved, columns = ['IDENTIFIER', 'DATE', 'COUPON', 'PRINCIPAL'])
            
        return dataAsFrame    
    
    def as_list(self):
        
        if self._securities is None: 
            return False
        
        return self._securities.values.tolist()
        
    def as_frame(self):
        #Función que entrega información de los securities del objeto como un dataFrame
        if self._securities is None: 
            return False
            
        return self._securities
        
    def as_dict(self):
        #Función que entrega información de los securities del objeto como un diccionario
        if self._securities is None: 
            return False
            
        return self._securities.to_dict()

### Main update and price       
#==============================================================================
# ### Main Functions for updating and pricing securities. Always prefer using this.
#==============================================================================
        
    def insertNewSecurity(self, query_with_identifiers):
        #Función que inserta cualquier tipo de security ingresado, distribuyéndolo a la función que le corresponda. Son reconocidos a partir del identificador.
        #Se recomienda usar esta función para insertar bonos, depositos y commercial papers, y cash
        id_classified = self.classifySecurities(query_with_identifiers)
        
        if id_classified['bonds']:
            self.DBinsertNewSecurityFromBloomberg(id_classified['bonds'], description = 'BOND')
        if id_classified['cash']:
            self.DBinsertNewCurrency(id_classified['cash'])
        if id_classified['deposits_and_cp']:
            self.DBinsertNewDepositCP(id_classified['deposits_and_cp'])
            
        if not id_classified['bonds'] and not id_classified['cash'] and not id_classified['deposits_and_cp']:
            banner('Identifiers could not be classified into any type.')
            return False
        else:
            #Insertamos como instrumento cualquier nueva moneda ingresada desde un instrumento nuevo.            
            self.DBinsertMissingCurrencies()
        
        return id_classified

            
    def priceSecurities(self, identifiers = None, Overwrite = False):
        #Función que valoriza los instrumentos y tipos de cambios cargados en base de datos (securitiesDescription).
        #Se recomienda usar esta función para actualizar precios, ya que ejecuta los distintos pricing para los distintos tipos de instrumentos.
        banner('\n(%s) - START PRICING ALL:'%(dtime.now()))
        if identifiers is None:
            self.DBpriceSecurityFromBloomberg(Overwrite = Overwrite)
            self.DBpriceCash(Overwrite = Overwrite)
            self.DBpriceDepositCP(Overwrite = Overwrite)
            self.DBpriceUSDFX(Overwrite = Overwrite)
        
        else:            
            query_with_identifiers = [(None, i) for i in identifiers]
            id_classified = self.classifySecurities(query_with_identifiers)
            identifiersBonds = [i[1] for i in id_classified['bonds']]
            identifiersCash = [i[1] for i in id_classified['cash']]
            identifiersDepoCP  = [i[1] for i in id_classified['deposits_and_cp']]
            
            if identifiersBonds:
                self.DBpriceSecurityFromBloomberg(identifiers = identifiersBonds, Overwrite = Overwrite)
            if identifiersCash:
                self.DBpriceCash(identifiers = identifiersCash, Overwrite = Overwrite)
            if identifiersDepoCP:
                self.DBpriceDepositCP(identifiers = identifiersDepoCP, Overwrite = Overwrite)
            if identifiersCash:
                self.DBpriceUSDFX(identifiers = identifiersCash, Overwrite = Overwrite)
                
        banner('(%s) - END PRICING ALL.\n'%(dtime.now()))
        
    def priceSecuritiesHistorical(self, identifiers = None, Overwrite = False, date = None):
        #Por el momento solo se puede actualizar históricamente depos y cash.
        #A futuro se introducirá FX. Para el resto de los instrumentos aún no existe un método pensado.
        if date is None:
            date = self._date
            
        if identifiers is None:            
            self.DBpriceCash(Overwrite = Overwrite, pricing_date = date)
            self.DBpriceDepositCP(Overwrite = Overwrite, pricing_date = date)
            
        else:
            query_with_identifiers = [(None, i) for i in identifiers]
            id_classified = self.classifySecurities(query_with_identifiers)
            identifiersBonds = [i[1] for i in id_classified['bonds']]
            identifiersCash = [i[1] for i in id_classified['cash']]
            identifiersDepoCP  = [i[1] for i in id_classified['deposits_and_cp']]
            
            if identifiersBonds:
                banner('(%s) bonds cannot be priced for a past date.'%len(identifiersBonds))
            if identifiersCash:
                self.DBpriceCash(identifiers = identifiersCash, Overwrite = Overwrite, pricing_date = date)
            if identifiersDepoCP:
                self.DBpriceDepositCP(identifiers = identifiersDepoCP, Overwrite = Overwrite, pricing_date = date)
            if identifiersCash:
                banner('(%s) FX cannot be priced for a past date.'%len(identifiersCash))
            
### DB connections and create DB
#==============================================================================
# ### Open DB connections and creating necessary data bases for working with the object
#==============================================================================
   
    def openConnection(self):
        #Función que abre una conexión con el default path de la clase
        con = sqlite3.connect(self._dbPath, detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
        con.text_factory = str
        return con
        
    def DBcreate(self):
        #Función que crea base de datos y tablas necesarias para trabajar con el objeto.
        #SOLO ejecutarla si es que no existen tablas anteriores, o si se quiere restablecer totalmente las tablas, ya que borra las tablas.
        #A futuro se insertará un comando de seguridad acá (un password)
        con=self.openConnection()
        cursor = con.cursor()
        #con=sqlite3.connect(':memory:')
        cursor.execute('DROP TABLE IF EXISTS securities')
        cursor.execute('DROP TABLE IF EXISTS securitiesDescription')
        cursor.execute('DROP TABLE IF EXISTS usdFX')
        cursor.execute('DROP TABLE IF EXISTS cashflows')
        cursor.execute('DROP TABLE IF EXISTS bloombergFieldID')
        cursor.execute('DROP TABLE IF EXISTS depositoryInstitution')
        
        #Tabla que guarada toda la información de los securities que cambia en el tiempo. Será el core de información para calcular
        #valores en portafolios
        cursor.execute("CREATE TABLE securitiesPricing \
                (ID INTEGER PRIMARY KEY NOT NULL,\
                DATE DATE NOT NULL,\
                IDENTIFIER TEXT NOT NULL,\
                PRICE REAL,\
                YIELD REAL,\
                CONVEXITY REAL,\
                DURATION REAL,\
                SPREAD REAL,\
                KRD TEXT,\
                UNIQUE(IDENTIFIER,DATE))")
                
        #Tabla que guarada toda la información de los securities disponibles       
        cursor.execute("CREATE TABLE securitiesDescription \
                (ID INTEGER PRIMARY KEY NOT NULL,\
                IDENTIFIER TEXT NOT NULL,\
                BBG_QUERY TEXT,\
                TICKER TEXT,\
                MATURITY DATE,\
                ISSUER TEXT,\
                INFLATION TEXT,\
                CURRENCY TEXT,\
                QUALITY TEXT,\
                CASHFLOWS TEXT,\
                NAME TEXT,\
                DESCRIPTION TEXT,\
                UNIQUE(IDENTIFIER))")
        
        #Tabla que guarda información de los tipos de cambio en el tiempo. Usada para dolarizar los portafolios
        cursor.execute("CREATE TABLE usdFX \
                (ID INTEGER PRIMARY KEY NOT NULL,\
                DATE DATE NOT NULL,\
                IDENTIFIER TEXT NOT NULL,\
                PRICE REAL,\
                UNIQUE(IDENTIFIER,DATE))")
                
        #Tabla que guarda los cashflows de cada instrumento, para ser usados en los cashflows de los portafolios
        cursor.execute("CREATE TABLE cashflows \
                (ID INTEGER PRIMARY KEY NOT NULL,\
                DATE DATE NOT NULL,\
                IDENTIFIER TEXT NOT NULL,\
                COUPON REAL,\
                PRINCIPAL REAL,\
                UNIQUE(IDENTIFIER,DATE))")
                
        #Tabla que clasifica los FIELDS usados para extraer información desde Bloomberg
        cursor.execute("""CREATE TABLE bloombergFieldID
                        (ID INTEGER PRIMARY KEY NOT NULL,
                        NAME TEXT,
                        BBG_FLDS TEXT,
                        COLUMN_IDENTIFIER TEXT,
                        GROUPTYPE TEXT,
                        UNIQUE(NAME,BBG_FLDS))""")
                        
        #Tabla que clasifica instituciones emisoras de depósitos bancarios o commercial papers           
        cursor.execute("""CREATE TABLE depositoryInstitution
                        (ID INTEGER PRIMARY KEY NOT NULL,
                        NAME TEXT,
                        IDENTIFIER TEXT,
                        QUALITY TEXT,
                        MOODY TEXT,
                        SP TEXT,        
                        FITCH TEXT,
                        TIME_DEPOSITS INT,
                        COMMERCIAL_PAPER INT,
                        UNIQUE(IDENTIFIER))""")
        con.close()
     
### Specific update and price        
#==============================================================================
# ### Functions for inserting and pricing securities in DB for specific types    
#==============================================================================
        
    def DBinsertNewSecurityFromBloomberg(self, query_with_identifier, description = None):
        #Función que incorpora nuevos securities a la BD securitiesDescription, usando información de Bloomberg. Es necesario ingresar el identificador con el que se denominará y el código
        #que se usará para hacer el query a bloomberg. Adicionalmente se puede incorporar una descripción de los instrumentos agregados.       
                
        fldsDict = self.DBgetBBGFlds(group = 'description')
        flds = fldsDict['fields']
        columnIdentifier = fldsDict['columns_identifier']
        
        identifier = dict(query_with_identifier)
        bbg_query = identifier.keys()
        
        data = self.loadBBGData(bbg_query, flds)
        
        if data is False:
            return False
            
        dataDB = []
        for row in data[flds].itertuples():
            formatRow = self.encodeData(row)
            dataDB.append(tuple([identifier[formatRow[0]], description] + formatRow))            
            #Ordenamos los datos en el orden de las columnas
        
        #Tratamos el caso particular del USD
        if 'USD' in identifier.values():
                dataDB.append(tuple(['USD', description] + [None*len(formatRow)]))   
                
        columnList = ['IDENTIFIER', 'DESCRIPTION','BBG_QUERY'] + columnIdentifier
        columnStr = ','.join(columnList)
        
        questionMarks = ['?']*len(columnList)
        questionMarksStr = ','.join(questionMarks)
        
        with self.openConnection() as con:
            cur = con.cursor()
            cur.executemany("""INSERT OR IGNORE INTO securitiesDescription (%s)
            values (%s) 
            """ %(columnStr, questionMarksStr), dataDB)
            
            
            #Actualizamos descripción de instrumentos de caja en securitiesDescription (características que no son actualizadas desde Bloomberg), en particular CASH
            cur.execute("""UPDATE securitiesDescription
            SET MATURITY = NULL, CURRENCY = IDENTIFIER
            WHERE DESCRIPTION = 'CASH' AND MATURITY IS NOT NULL""")
            
        banner('Securities inserted to securitiesDescription using Bloomberg.')
        return dataDB    
        
    def DBinsertNewCurrency(self, query_with_identifiers):
        #Actualiza descripción de instrumentos ingresados para el caso particular que sea un currency
    
        dataDB = [(identifier[1], identifier[0], identifier[1], 'CASH') for identifier in query_with_identifiers]
        
        with self.openConnection() as con:
            cur = con.cursor()
            cur.executemany("""INSERT OR IGNORE INTO securitiesDescription (IDENTIFIER, BBG_QUERY, CURRENCY, DESCRIPTION)
            VALUES (?,?,?,?)""", dataDB)
            
        banner('Currencies inserted to securitiesDescription using Bloomberg.')
        return dataDB
        
    def DBinsertNewDepositCP(self, query_with_identifiers):
        #Actualiza descripción de instrumentos de depositos y commercial papers en securitiesDescription (características que no son actualizadas desde Bloomberg)
        #Debe ser usada cuando se ingresa un deposito/CP nuevo en la base de datos
    
        depositosCP = [identifier[1] for identifier in query_with_identifiers]
        depositInfo = self.getDepositInfoFromIdentifiers(depositosCP)
        
        dataRaw = depositInfo['description']
        
        dataDB = []
        for data in dataRaw.itertuples():
            dataDB.append(self.encodeData(data))
            
        columnStr = 'IDENTIFIER,' + ','.join(dataRaw.columns)
        
        questionMarks = ['?']*(len(dataRaw.columns) + 1)
        questionMarksStr = ','.join(questionMarks)
        
        with self.openConnection() as con:
            cur = con.cursor()
            cur.executemany("""INSERT OR IGNORE INTO securitiesDescription (%s)
            VALUES (%s)""" %(columnStr, questionMarksStr), dataDB)
        
        banner('Deposits and/or Commercial Papers inserted to securitiesDescription.')
        return dataDB
            
    def DBinsertMissingCurrencies(self):
        #Agrega como instrumento nuevo la descripción de currencies no disponibles en securitiesDescription.
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""SELECT DISTINCT CURRENCY FROM securitiesDescription
            WHERE CURRENCY NOT IN 
            (SELECT DISTINCT IDENTIFIER FROM securitiesDescription WHERE DESCRIPTION = 'CASH')""")
            currencyRetrieved = cur.fetchall()
            if not currencyRetrieved:
                return False

        query_with_identifiers = [(i[0] + 'USD CURNCY', i[0]) for i in currencyRetrieved]        
        self.DBinsertNewCurrency(query_with_identifiers)
        
        for currency in currencyRetrieved:
            banner('(%s) missing currency introduced into DB'%(currency))
            
            
    def DBpriceSecurityFromBloomberg(self, identifiers = None, Overwrite = False):
        #Función que valoriza identificadores previamente ingresados en securitiesDescription usando Bloomberg. Si se ingresan identificadores, valorizará solo aquellos que están en BD.
    
        fldsDict = self.DBgetBBGFlds(group = 'dynamic')
        flds = fldsDict['fields']
        columnIdentifier = fldsDict['columns_identifier']
        
        with self.openConnection() as con:
            cur = con.cursor()
            if identifiers is None:
                query = """SELECT BBG_QUERY, IDENTIFIER FROM securitiesDescription
                WHERE DESCRIPTION IN ('BOND')"""
                
            else:
                identifierStr = '\'' + "\',\'".join(identifiers) + '\''
                query = """SELECT BBG_QUERY, IDENTIFIER FROM securitiesDescription 
                WHERE DESCRIPTION IN ('BOND') AND identifier IN (%s)"""%identifierStr
                
            cur.execute(query)
            query_with_identifier = cur.fetchall()
            if not query_with_identifier:
                banner("Securities are not loaded in securitiesDescription database. It should loaded first using DBinsertNewSecurityFromBloomberg")
                return False
                
        identifier = dict(query_with_identifier)
        bbg_query = identifier.keys()
        
        data = self.loadBBGData(bbg_query, flds)
        
        if data is False:
            return False
        
        dataDB = []
        self._date = dt.today()
        
        for row in data[flds].itertuples():
            formatRow = self.encodeData(row)
            dataDB.append(tuple([identifier[formatRow[0]], self._date] + formatRow[1:]))
            
        columnList = ['IDENTIFIER','DATE'] + columnIdentifier
        columnStr = ','.join(columnList)
        
        questionMarks = ['?']*len(columnList)
        questionMarksStr = ','.join(questionMarks)
        
        with self.openConnection() as con:
            cur = con.cursor()
            if Overwrite:
                cur.executemany("""INSERT OR REPLACE INTO securitiesPricing (%s)
                VALUES (%s) 
                """ %(columnStr, questionMarksStr), dataDB)
            else:
                cur.executemany("""INSERT OR IGNORE INTO securitiesPricing (%s)
                VALUES (%s) 
                """ %(columnStr, questionMarksStr), dataDB)
        banner('(%s) securities priced from Bloomberg for date (%s)'%(str(len(dataDB)), str(self._date)))
        
        #Actualizamos los casos especiales que no son valorizados por Bloomberg
        self.DBpriceSpecialCases(identifiers, date = self._date)
        
        return dataDB
    
    def DBpriceDepositCP(self, identifiers = None, pricing_date = None, Overwrite = False):
        #Función que valoriza identificadores de depósitos y CP previamente ingresados en securitiesDescription. Si se ingresan identificadores, valorizará solo aquellos que están en BD.
        
        if pricing_date is None:
            pricing_date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            if identifiers is None:
                query = """SELECT IDENTIFIER FROM securitiesDescription
                WHERE DESCRIPTION IN ('TIME DEPOSIT', 'COMMERCIAL PAPER')"""
            else:
#                identifierStr = ','.join(identifiers)
                identifierStr = '\'' + "\',\'".join(identifiers) + '\''
                query = """SELECT IDENTIFIER FROM securitiesDescription 
                WHERE DESCRIPTION IN ('TIME DEPOSIT', 'COMMERCIAL PAPER') AND identifier IN (%s)"""%identifierStr
                
            cur.execute(query)
            identifierDepoCP = cur.fetchall()
            if not identifierDepoCP:
                banner("Depos or Cash not found securitiesDescription database.")
                return False
                
        
        depositosCP = [i[0] for i in identifierDepoCP]
        depositInfo = self.getDepositInfoFromIdentifiers(depositosCP, pricing_date = pricing_date)
        
        dataRaw = depositInfo['pricing']
        dataDB = []
        
        for data in dataRaw.itertuples():
            dataDB.append(self.encodeData(data))
        
        columnStr = 'IDENTIFIER,' + ','.join(dataRaw.columns)
        
        questionMarks = ['?']*(len(dataRaw.columns) + 1)
        questionMarksStr = ','.join(questionMarks)
        
        with self.openConnection() as con:
            cur = con.cursor()
            if Overwrite:
                cur.executemany("""INSERT OR REPLACE INTO securitiesPricing (%s)
                VALUES (%s)""" %(columnStr, questionMarksStr), dataDB)
            else:
                cur.executemany("""INSERT OR IGNORE INTO securitiesPricing (%s)
                VALUES (%s)""" %(columnStr, questionMarksStr), dataDB)
                
        banner('(%s) deposits or CP priced for date (%s)'%(str(len(dataDB)), str(pricing_date)))    
        return dataDB
    
    def DBpriceCash(self, identifiers = None, pricing_date = None, Overwrite = False):
        #Función valoriza Cash (que no se descargan de Bloomberg) para una fecha determinada
    
        if pricing_date is None:
            pricing_date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            if identifiers is None:
                query = """SELECT IDENTIFIER FROM securitiesDescription
                WHERE DESCRIPTION = 'CASH'"""
            else:
#                identifierStr = ','.join(identifiers)
                identifierStr = '\'' + "\',\'".join(identifiers) + '\''
                query = """SELECT IDENTIFIER FROM securitiesDescription 
                WHERE DESCRIPTION = 'CASH' AND identifier IN (%s)"""%identifierStr
                
            cur.execute(query)
            identifierCash = cur.fetchall()    
            
            if not identifierCash:
                banner('Cash securities not found on securitiesDescription')
                return False
                
        krdCash = pd.DataFrame.from_records([(0.5, 0.0), \
                                          (1.0, 0.0), \
                                          (2.0, 0.0), \
                                          (3.0, 0.0), \
                                          (5.0, 0.0), \
                                          (7.0, 0.0), \
                                          (10.0, 0.0), \
                                          (20.0, 0.0), \
                                          (30.0, 0.0)],\
                                          columns = ['Maturity','Duration'])
        krdCashEncoded = self.encodeData([krdCash])[0]
        
        dataDB = []
        [dataDB.append((pricing_date, i[0], 100, 0.0, 0.0, 0.0, 0.0, krdCashEncoded)) for i in identifierCash]
        columnsStr = 'DATE,IDENTIFIER,PRICE,YIELD,CONVEXITY,DURATION,SPREAD,KRD'
        
        questionMarks = ['?']*len(dataDB[0])
        questionMarksStr = ','.join(questionMarks)
            
        with self.openConnection() as con:
            
            cur = con.cursor()
            if Overwrite:
                query = """INSERT OR REPLACE INTO securitiesPricing (%s)
                VALUES (%s)"""%(columnsStr, questionMarksStr)
                cur.executemany(query, dataDB)
            else:
                query = """INSERT OR IGNORE INTO securitiesPricing (%s)
                VALUES (%s)"""%(columnsStr, questionMarksStr)
                cur.executemany(query, dataDB)
        
        banner('(%s) currencies priced for date (%s)'%(str(len(dataDB)), str(pricing_date)))     
        return dataDB
        
        
    def DBpriceUSDFX(self, identifiers = None, pricing_date = None, Overwrite = False):
        #Función que valoriza los tipo de cambio a USD de los distintos identificadores ingresados (puede ser cash o cualquier otro instrumnento)
        
        if pricing_date is None:
            pricing_date = self._date
        
        with self.openConnection() as con:
            cur = con.cursor()
            if identifiers is None:
                query = """SELECT BBG_QUERY, IDENTIFIER FROM securitiesDescription
                WHERE IDENTIFIER IN (SELECT DISTINCT CURRENCY FROM securitiesDescription WHERE CURRENCY <> 'USD')"""
            else:
                identifierStr = '\'' + "\',\'".join(identifiers) + '\''
                query = """SELECT BBG_QUERY, IDENTIFIER FROM securitiesDescription
                WHERE IDENTIFIER IN (SELECT DISTINCT CURRENCY FROM securitiesDescription WHERE CURRENCY <> 'USD' AND IDENTIFIER IN (%s)) 
                """%identifierStr
            currenciesRaw = cur.execute(query).fetchall()
            
            if not currenciesRaw:
                return False
        
        currenciesRawDict = dict(currenciesRaw)
        
        bbg_query = currenciesRawDict.keys()
        
        data = self.loadBBGData(bbg_query, ['PX_LAST'])
        
        
        ########## Dividimos el tipo de cambio KRWUSD por 100 ############
        krwIndex = data.index.get_loc("KRWUSD CURNCY")
        
        if krwIndex:
            data["PX_LAST"][krwIndex] /= 100
        ##################################################################            
        
        
        dataDB = []
        [dataDB.append((pricing_date, currenciesRawDict[i[0]], i[1])) for i in data.to_records()]
        
        ########## Actualizamos el tipo de cambio USD de forma separada ########        
        dataDB.append((pricing_date, 'USD', 1))
        #########################################################################
        
        with self.openConnection() as con:
            
            cur = con.cursor()
            if Overwrite:
                cur.executemany("""INSERT OR REPLACE INTO usdFX (DATE, IDENTIFIER, PRICE)
                VALUES (?, ?, ?)""", dataDB)
            else:
                cur.executemany("""INSERT OR IGNORE INTO usdFX (DATE, IDENTIFIER, PRICE)
                VALUES (?, ?, ?)""", dataDB)
                
        banner('(%s) FX priced for date (%s)'%(str(len(dataDB)), str(pricing_date)))    
        return dataDB
    
    def DBupdateCashFlows(self, identifiers = None):
        #Función que actualiza tabla de cashFlows para los instrumentos en securitiesDescription
        columnDict={}
        columnDict['Coupon Amount']  = 'COUPON'
        columnDict['Payment Date'] = 'DATE'
        columnDict['Principal Amount'] = 'PRINCIPAL'
        
        with self.openConnection() as con:
            cur = con.cursor()
            if identifiers is None:
                query = """SELECT IDENTIFIER, CASHFLOWS FROM securitiesDescription
                        WHERE CASHFLOWS IS NOT NULL AND IDENTIFIER NOT IN
                        (SELECT DISTINCT IDENTIFIER FROM cashflows)"""
                        
                cur.execute(query)
                dataRetrieved = cur.fetchall()
            
            if not dataRetrieved:
                return False
            dataDecoded = []
            
            
            for data in dataRetrieved:
                formattedData = self.decodeData(data)                
#                formattedData[1].set_index('Payment Date', inplace = True)
                identifier = formattedData[0]
                cashflows = formattedData[1]
                
                dataDB = [tuple([identifier] + self.encodeData(cashflow)) for cashflow in cashflows.values.tolist()]
                
                columnsCF = [columnDict[columnName] for columnName in cashflows.columns]
                columnStr = 'IDENTIFIER,' + ','.join(columnsCF)

                questionMarks = ['?']*4
                questionMarksStr = ','.join(questionMarks)
                
                query = """INSERT INTO cashflows (%s)
                VALUES (%s)"""%(columnStr, questionMarksStr)
                
                cur.executemany(query, dataDB)
                
                dataDecoded.append(dataDB)
        
        return dataDecoded
    
    def DBpriceSpecialCases(self, identifiers = None, date = None):
        #Esta función se encargará de llamar a las funciones que valoricen todos los flds de pricing que entregados por Bloomberg
        if date is None:
            date = self._date
            
        self.DBupdateLinkersKRD(identifiers = identifiers, date = date)
        self.DBpriceBills(identifiers = identifiers, date = date)
        
        
    def DBupdateLinkersKRD(self, identifiers = None, date = None):
        #Linkers no tienen field partial_duration_as_of en Bloomberg, por lo que obtenemos su estructura KRD de otra forma
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            if identifiers is None:
                query = """SELECT IDENTIFIER FROM securitiesPricing
                WHERE DATE = ? AND KRD IS NULL AND IDENTIFIER IN
                (SELECT DISTINCT IDENTIFIER FROM securitiesDescription WHERE INFLATION = 'Y')"""
            else:
                identifierStr = '\'' + "\',\'".join(identifiers) + '\''
                query = """SELECT IDENTIFIER FROM securitiesPricing
                WHERE DATE = ? AND KRD IS NULL AND IDENTIFIER IN
                (SELECT DISTINCT IDENTIFIER FROM securitiesDescription WHERE INFLATION = 'Y' AND identifier IN (%s))"""%identifierStr
                
            cur.execute(query, (date,))
            dataRetrieved = cur.fetchall()

            if not dataRetrieved:
                banner('No linkers KRD to be updated.')
                return False
                
        identifiersList = [i[0] for i in dataRetrieved]
        bbg_query = [i + ' Govt' for i in identifiersList]
        
        query_with_identifier = zip(bbg_query, identifiersList)
        identifierDict = dict(query_with_identifier)
        
        KRDflds = ['OAS_KEY_RATE_DUR_3M',
                    'OAS_KEY_RATE_DUR_6M',
                    'OAS_KEY_RATE_DUR_1YR',
                    'OAS_KEY_RATE_DUR_2YR',
                    'OAS_KEY_RATE_DUR_3YR',
                    'OAS_KEY_RATE_DUR_5YR',
                    'OAS_KEY_RATE_DUR_7YR',
                    'OAS_KEY_RATE_DUR_10YR',
                    'OAS_KEY_RATE_DUR_20YR',
                    'OAS_KEY_RATE_DUR_30YR']
        
        dataBBG = self.loadBBGData(bbg_query, KRDflds)
        
        if dataBBG is False:
            banner('No Bloomberg data retrieved for linkers KRD.')
            return False
        
        dataDB = []
        KRDAsFrame = pd.DataFrame([], columns = ['Maturity', 'Duration'])
        KRDAsFrame['Maturity'] = [0.5, 1, 2, 3, 5, 7, 10, 20, 30]
        
        for data in dataBBG.itertuples():
            
            dataList = list(data)
            identifier = identifierDict[dataList[0]]
            duration = [dataList[1] + dataList[2]] + dataList[3:]
            dataAsFrame = KRDAsFrame
            dataAsFrame['Duration'] = duration
            formatRow = self.encodeData([dataAsFrame] + [identifier] + [date])
            dataDB.append(formatRow)
            
        with self.openConnection() as con:
            cur = con.cursor()
            cur.executemany("""UPDATE securitiesPricing
            SET KRD = ? WHERE IDENTIFIER = ? AND DATE = ?""",(dataDB))
            
        banner('KRD for linkers updated on date %s for (%s) identifiers.'%(date, len(identifiersList)))
        return dataDB
        
    def DBpriceBills(self, identifiers = None, date = None):
        #Precio dirty de los BILLS es entregado como tasa por Bloomberg.Esta función lo valoriza a partir de la tasa y fecha de madurez
        if date is None:
            date = self._date
            
        with self.openConnection() as con:
            cur = con.cursor()
            if identifiers is None:
                query = """SELECT IDENTIFIER
                FROM securitiesDescription
                WHERE TICKER IN ('B') AND IDENTIFIER IN
                (SELECT IDENTIFIER FROM securitiesPricing WHERE DATE = ?)"""
            else:
                identifierStr = '\'' + "\',\'".join(identifiers) + '\''
                query = """SELECT IDENTIFIER
                FROM securitiesDescription
                WHERE TICKER IN ('B') AND IDENTIFIER IN
                (SELECT IDENTIFIER FROM securitiesPricing WHERE DATE = ? AND identifier IN (%s))"""%identifierStr
            
            cur.execute(query, (date,))
            dataRetrieved = cur.fetchall()
            if not dataRetrieved:
                banner('No bills to price for date %s'%date)
                return False

        identifiersList = [i[0] for i in dataRetrieved]
        bbg_query = [i + ' Govt' for i in identifiersList]
        
        query_with_identifier = zip(bbg_query, identifiersList)
        identifierDict = dict(query_with_identifier)
        identifierDict = dict(query_with_identifier)
        
        
        
        bbg_fld = ['PX_DISC_MID']
        
        dataBBG = self.loadBBGData(bbg_query, bbg_fld)
        if dataBBG is False:
            banner('No Bloomberg data retrieved for bills pricing.')
            return False
        
        dataDB = [(price, identifierDict[identifier], date) for identifier, price in dataBBG.itertuples()]
        
        with self.openConnection() as con:
            cur = con.cursor()
            cur.executemany("""UPDATE securitiesPricing
            SET PRICE = ?
            WHERE IDENTIFIER = ? AND DATE = ?""", dataDB)
            
        banner('(%s) Bills price updated on date %s.'%(date, len(identifiersList)))    
        return dataDB    
### Classify and properties        
#==============================================================================
# ## Functions for classifying and getting properties for securities (not available in Bloomberg)
#==============================================================================
        
    def getDepositInfoFromIdentifiers(self, identifierIter, pricing_date = None):
        #Función que entrega información de depósitos y commercial papers a partir del identificador
        
        #A continuación se definen funciones que solo serán usadas en esta instancia. Estoy probando definir las funciones adentro
        #para ver si es más ordenado.
        
        #############################################################################################################################
        #############################################################################################################################
        def getDepoKRD(maturity, pricing_date):
            
            yearsToMaturity = (maturity - pricing_date).days/365.
            krd05 = 0.0
            krd1 = 0.0
            if yearsToMaturity <= 0.5:
                krd05 = yearsToMaturity
            elif yearsToMaturity > 0.5 and yearsToMaturity <= 1:
                krd05 = yearsToMaturity*(yearsToMaturity-0.5)/0.5
                krd1 = yearsToMaturity*(1-yearsToMaturity)/0.5
            
            krdDepo = pd.DataFrame.from_records([(0.5, krd05), \
                                                  (1.0, krd1), \
                                                  (2.0, 0.0), \
                                                  (3.0, 0.0), \
                                                  (5.0, 0.0), \
                                                  (7.0, 0.0), \
                                                  (10.0, 0.0), \
                                                  (20.0, 0.0), \
                                                  (30.0, 0.0)],\
                                                  columns = ['Maturity','Duration'])            
            return krdDepo

        def DBgetDepoRating(issuerCode):  
            
            with self.openConnection() as con:
                cur=con.cursor()
                cur.execute("""SELECT QUALITY FROM depositoryInstitution
                                WHERE IDENTIFIER = ?""" ,(issuerCode,))
            rating = cur.fetchall()
            return rating[0][0]
            
        def depoType(issuerType):
            if issuerType.upper() == 'DEPO':
                depoType = 'TIME DEPOSIT'
            elif issuerType.upper() == 'COMP':
                depoType = 'COMMERCIAL PAPER'
            else:
                depoType = 'UNKNOWN'        
            return depoType
        
        def depoPrice(rate, maturity, pricing_date, baseAccrual):
            #Función que devuelve el precio de un depósito dado la tasa, madurez y base de devengo
            if baseAccrual == 'A1': #Actual/365
                daysToMaturity = (maturity - pricing_date).days
                price = 100/(1 + rate/100*daysToMaturity/365)
            elif baseAccrual == 'A2': #Actual/360
                daysToMaturity = (maturity - pricing_date).days
                price = 100/(1 + rate/100*daysToMaturity/360)
            else:
                price = 100
            return price
        
        def cashFlows(rate, maturity):
            cashflows = pd.DataFrame([[maturity, rate*10000, 1000000]], columns = ['Payment Date','Coupon Amount','Principal Amount'])
            return cashflows
        #############################################################################################################################
        #############################################################################################################################
        
        if pricing_date is None:
            pricing_date = self._date
            
        descriptionColumns = ['MATURITY','ISSUER','INFLATION','CURRENCY','QUALITY','CASHFLOWS','DESCRIPTION']
        pricingColumns = ['DATE','PRICE','YIELD','CONVEXITY', 'DURATION','SPREAD','KRD']
        
        descriptionValues = []
        pricingValues = []
        
        for identifier in identifierIter:
            
            [info, tasa] = identifier.split('_')
            issuerType = depoType(info[0:4])
            rate = float(tasa)
            currency = info[4:7]
            dateMaturity = dtime.strptime(info[7:15],"%Y%m%d").date()
            baseAccrual = info[15:17]
            issuerCode = info[17:]
            price = depoPrice(rate, dateMaturity, pricing_date, baseAccrual)
            krdDepo = getDepoKRD(dateMaturity, pricing_date)
            rating = DBgetDepoRating(issuerCode)
            duration = (dateMaturity - pricing_date).days/365.
            inflation = 'N'
            cashflows = cashFlows(rate, dateMaturity)
            
            ## ACÁ TENGO QUE AGREGAR UNA VERIFICACIÓN QUE LA INFORMACIÓN VIENE BIEN ANTES DE AGREGARLA ##
            
            descriptionValues.append((dateMaturity, issuerCode, inflation, currency, rating, cashflows, issuerType))
            pricingValues.append((pricing_date, price, rate, 0.0, duration, 0.0, krdDepo))
        
        depositInfo = {}
        depositInfo['description'] = pd.DataFrame.from_records(descriptionValues, columns = descriptionColumns, index = identifierIter)
        depositInfo['pricing'] = pd.DataFrame.from_records(pricingValues, columns = pricingColumns, index = identifierIter)
        
        return depositInfo        
    
    def classifySecurities(self, query_with_identifier):
        #Función que busca tratar de clasificar un security a partir del identificador
        
        bonds = []
        cash= []
        deposits_and_cp = []
        
        for security in query_with_identifier:
            
            identifier = security[1]
            if len(identifier) > 3 and identifier[0:4].upper() not in ('DEPO','COMP'): bonds.append(security)
                
            if len(identifier) > 3 and identifier[0:4].upper() in ('DEPO','COMP'): deposits_and_cp.append(security)
                
            if len(identifier) == 3: cash.append(security)
        
        query_with_identifier_classified = {}
        query_with_identifier_classified['bonds'] = bonds
        query_with_identifier_classified['cash'] = cash
        query_with_identifier_classified['deposits_and_cp'] = deposits_and_cp
        
        return query_with_identifier_classified
        
    def DBgetAvailableIssuers(self):
        
        with self.openConnection() as con:
            cur = con.cursor()
            cur.execute("""SELECT NAME, IDENTIFIER, QUALITY, TIME_DEPOSITS, COMMERCIAL_PAPER FROM depositoryInstitution""")
            dataRetrieved = cur.fetchall()
            
            if not dataRetrieved:
                return False
        
        dataAsFrame = pd.DataFrame.from_records(dataRetrieved, columns = ['NAME', 'IDENTIFIER', 'QUALITY', 'TIME_DEPOSITS', 'COMMERCIAL_PAPER'])        
        return dataAsFrame
        
    def getQueryFromIdentifiers(self, identifiers):
        
        id_classified = self.classifySecurities(zip(identifiers, identifiers))
        
        query_with_identifiers = []
        
        if id_classified['bonds']:
            query_with_identifiers.extend([(identifier + ' Govt', identifier) for identifier, _ in id_classified['bonds']])
            
        if id_classified['cash']:
            query_with_identifiers.extend([(identifier + 'USD CURNCY', identifier) if identifier != 'USD' else (None, identifier) for identifier, _ in id_classified['cash']])
            
            
        if id_classified['deposits_and_cp']:            
            query_with_identifiers.extend(id_classified['deposits_and_cp'])            
            
        return query_with_identifiers
       
### Get Bloomberg Data        
#==============================================================================
# ### Function for getting Bloomberg data and fields
#==============================================================================
        
    def loadBBGData(self,identifiers, flds):
        #Función para sacar data de bloomeberg usando tia.
        
        banner('ReferenceDataRequest: Requesting data from Bloomberg for ' + ','.join(flds) + ' for ' + str(len(identifiers)) + ' securities.')
        LocalTerminal = v3api.Terminal('localhost', 8194)
        try:
            response = LocalTerminal.get_reference_data(identifiers, flds, ignore_security_error=1, ignore_field_error=1)
        except:
            print("Unexpected error:", sys.exc_info()[0])
            return False

        dataDF = response.as_frame()
        
        if dataDF.empty:
            banner("No se descargaron datos desde Bloomberg")
            return False
            
        dataDF = dataDF.where((pd.notnull(dataDF)), None)
        banner('Data Retrieved.')    
        return dataDF
    

    def DBgetBBGFlds(self, group = None):
        
        with self.openConnection() as con:
            
            cur = con.cursor()
            if group is None:
                cur.execute("""SELECT NAME, BBG_FLDS, COLUMN_IDENTIFIER FROM bloombergFieldID""")
            else:
                cur.execute("""SELECT NAME, BBG_FLDS, COLUMN_IDENTIFIER FROM bloombergFieldID
                    WHERE GROUPTYPE = '%s'
                    """ %group.upper())
                
            descriptionFlds = cur.fetchall()
            if not descriptionFlds:
                banner("No hay campos cargados en bloombergFieldID")
                return False
        
        names = [fld[0] for fld in descriptionFlds]
        fields = [fld[1] for fld in descriptionFlds]
        columns_identifier = [fld[2] for fld in descriptionFlds]
        
        fldsDict = dict(zip(['names','fields','columns_identifier'],[names, fields, columns_identifier]))
        return fldsDict

### Encode and Decode information    
#==============================================================================
# ### Functions for encoding and decoding information from python and data bases 
#==============================================================================
    
    def encodeData(self, dataIter):
        
        #Función que codifica los datos que vienen de blp de tia y los convierte en el formato establecido para ser cargado en base de datos.
        dataEncode = []
        for data in dataIter:
            try:
                if isinstance(data, pd.DataFrame):
                    dataEncode.append(data.to_json())
                elif isinstance(data,dtime):
                    dataEncode.append(data.date())
                elif not isinstance(data,(basestring,type(None))):
                    dataEncode.append(json.dumps(data))
                else: 
                    dataEncode.append(data)
            except:
                dataEncode.append(data)
                
        return dataEncode 
        
    def decodeData(self,dataIter):
        
        #Función que decodifica datos de base datos para poder ser usados en python
        #Ojo que hay que ingresar explicitamente las columnas que quieres que se conviertan en fecha para que los lea bien
        dataDecode = []
        for data in dataIter:
            try:
                dataDecoded = pd.read_json(data, convert_dates=['Payment Date','Date'])
#                if isinstance(data, int):
#                    dataDecode.append(float(data))
#                else:
#                    dataDecode.append(pd.read_json(data, convert_dates=['Payment Date','Date']))
            except:
                dataDecoded = data
                
            if isinstance(dataDecoded, int):
                dataDecode.append(float(dataDecoded))
            else:
                dataDecode.append(dataDecoded)
                
        return dataDecode
       
        
if __name__=="__main__":
    sec = security()
#    sec.DBcreate()
#    data = sec.loadBBGData(['CT10 Govt', 'CT3 Govt', 'EUR curncy'], ['px_last','maturity'])
    
    #Ejemplo de como cargar nuevas securities en BD
#    isin = ['US912828M565','US912828N639']
#    bbg_query = [currency + ' govt' for currency in isin]
#    query_with_identifier = zip(bbg_query, isin)
#    data = sec.DBinsertNewSecurityFromBloomberg(query_with_identifier)
    
    #Ejemplo de como cargar nuevas currencies en BD
#    currencies = ['USD','EUR','JPY','GBP','AUD','CAD','DKK','NZD','NOK','SEK','CHF','CNY','CNH','MXN', 'PLN', 'KRW']
#    bbg_query = [currency + 'USD CURNCY' for currency in currencies]
#    query_with_identifier = zip(bbg_query, currencies)
#    data = sec.DBinsertNewSecurityFromBloomberg(query_with_identifier, description = 'CASH')
    
#    data = sec.DBpriceSecurityFromBloomberg()
#    sec.DBupdateCashDescription()
#    sec.DBupdateCashPricing()
    
    
#    depos = ['DEPOCNH20160415A1QTB_3.2', 'COMPUSD20160415A1QTB_5.4', 'DEPOEUR20160415A1QTB_0.1']
#    bbg_query = ['DEPOCNH20160415A1QTB_3.2', 'COMPUSD20160415A1QTB_5.4', 'DEPOEUR20160415A1QTB_0.1']
#    query_with_identifier = zip(bbg_query, depos)
#    data = sec.insertNewSecurity(query_with_identifier)
    
#    queryClassified = sec.classifySecurities(query_with_identifier)    
#    data = sec.getDepositInfoFromIdentifiers(depos)
#    sec.DBinsertNewDepositCP(query_with_identifier)
#    data = sec.DBpriceDepositCP()
    
#    data = sec.priceSecurities(Overwrite = True)
    
    
#    data = sec.DBgetSecurities()
    
#    data = sec.DBpriceUSDFX()
    
#    securities = ['US912810RP57','DE0001102390','DEPOEUR20160415A1QTB_0.1','USD']
#    bbg_query = ['US912810RP57 Govt','DE0001102390 Govt','DEPOEUR20160415A1QTB_0.1', None]
#    query_with_identifier = zip(bbg_query, securities)
#    data = sec.insertNewSecurity(query_with_identifier)
    
#    securities = ['US912810RP57','DE0001102390','DEPOEUR20160415A1QTB_0.1','USD','EUR']
#    data = sec.priceSecurities(identifiers=securities)
#    
#    data = sec.DBupdateCashFlows()
#    data = sec.DBgetCashFlows()
    
    
    
#    securities = ['JP1201191A72']
#    bbg_query = ['JP1201191A72 Govt']
#    query_with_identifier = zip(bbg_query, securities)
#    data = sec.insertNewSecurity(query_with_identifier)
##    
#    data = sec.priceSecurities(identifiers = securities)
     
#    data = sec.DBupdateLinkersKRD()
     
#    securities = ['US912810RP57','DE0001102390','DEPOEUR20160415A1QTB_0.1','USD','EUR']
#    data = sec.getQueryFromIdentifiers(securities)