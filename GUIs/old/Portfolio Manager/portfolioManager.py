# -*- coding: utf-8 -*-
"""
Created on Wed Sep 09 16:53:11 2015

@author: mvillalon
"""

import sys
from PyQt4 import QtCore, QtGui, uic
sys.path.append("G:\DAT\GII\MES_INT\INVINTER\Matlab Programas\packagePY")
import numpy as np
import portfolioAnalytics as pA
#import time
import pylab
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT
#import csv, StringIO

class portfolioManaging(QtGui.QWidget):
    
    def __init__(self):
        super(portfolioManaging,self).__init__()
        #Insertamos un splash screen para que se vea más bonito...
        splash_pix = QtGui.QPixmap('splash.png')
        splash=QtGui.QSplashScreen(splash_pix,QtCore.Qt.WindowStaysOnTopHint)
        splash.setMask(splash_pix.mask())
        splash.show()
        
        uic.loadUi('portfolioManager.ui',self)
        
        self.initUI()
        #time.sleep(1)
        self.show()
        splash.finish(self)
        
    def initUI(self):
        self.setWidgetsPropertiesAndActions()
        
    def setWidgetsPropertiesAndActions(self):
        
        self.fxDialogCon=[]
        self.tradesDialog=[]
        self.addIsinCon=[]
        
        #formColor=self.palette().color(QtGui.QPalette.Background)
        
        #self.tableWidgetPositions.cornerWidget().setStyleSheet("QHeaderView::section { background-color:rgb(48, 48, 48) }")
        self.tableWidgetPositions.horizontalHeader().setStyleSheet("QHeaderView::section { background-color:rgb(48, 48, 48) }")
        self.tableWidgetPositions.verticalHeader().hide()#setStyleSheet("QHeaderView::section { background-color:rgb(48, 48, 48) }")
        
        self.tableWidgetPortfolioSummary.horizontalHeader().setStyleSheet("QHeaderView::section { background-color:rgb(48, 48, 48) }")
        self.tableWidgetPortfolioSummary.verticalHeader().hide()#.setStyleSheet("QHeaderView::section { background-color:rgb(48, 48, 48) }")
        
        self.dateEdit.setDate(pA.dt.today())
        #self.dateEdit.dateChanged.connect(self.loadButtonClicked)
        
        self.updateAvailablePortfolios()       
        self.pushButtonLoad.setToolTip('Load portfolio for specific date')
        self.pushButtonLoad.clicked.connect(self.loadButtonClicked)
        self.comboBoxCurrencies.activated[str].connect(self.populateTableCrncy)
        self.comboBoxIssuers.activated[str].connect(self.populateTable)
        #Descomentar el siguiente código cuando averigüe como eliminar el "edit" del toolbar
        self.navi_toolbar=NavigationToolbar(self.mplwidgetExposures, self)
        self.navi_toolbar.removeEdit()
        self.LayoutPlot.addWidget(self.navi_toolbar)
       
        self.checkBoxDuration.stateChanged.connect(self.plotExposures)
        self.checkBoxFX.stateChanged.connect(self.plotExposures)
        self.checkBoxSpread.stateChanged.connect(self.plotExposures)
        self.checkBoxKRD.stateChanged.connect(self.plotExposures)
        
        self.pushButtonBuy.clicked.connect(self.pushButtonTrade)
        self.pushButtonSell.clicked.connect(self.pushButtonTrade)
        
        self.pushButtonResetTrades.clicked.connect(self.resetTrades)
        self.tableWidgetPositions.clicked.connect(self.updateIsinPriceEdit)
        
        self.pushButtonFX.clicked.connect(self.openFXDialog)
        self.pushBuyFromBMK.clicked.connect(self.openbuyFromBMKDialog)
        
        self.pushButtonOpenToday.clicked.connect(self.openPositionsForToday)
        self.pushButtonShowTrades.clicked.connect(self.openShowTradesDialog)
        
        self.pushButtonAutoRebalance.setEnabled(False)
        
        self.pushButtonImport.clicked.connect(self.showImportDialog)
        self.pushButtonPriceSecurities.clicked.connect(self.showSecuritiesDialog)
        self.pushButtonDepo.clicked.connect(self.openDeposDialog)
        self.plotExposures()
     
    #Redefinimos algunos event handlers 
    def closeEvent(self, event):
        reply=QtGui.QMessageBox.question(self,'Message',
                                         "Sure you want to quit?...Quitter",QtGui.QMessageBox.Yes |
                                         QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
            
    def keyPressEvent(self, e):     
        if e.key() == QtCore.Qt.Key_Escape: 
            self.close()
            
    def showImportDialog(self):
        self.importDialog = importDialog()
        self.importDialog.exec_()
        self.updateAvailablePortfolios()
        
    def showSecuritiesDialog(self):
        self.securitiesDialog = securitiesDialog()
        self.securitiesDialog.show()
        
    def updateAvailablePortfolios(self):
        activePortTmp=pA.activePortfolio()
        availablePorts=activePortTmp.availablePortfolioInDB()
        self.comboBoxPortfolio.clear() 
        self.comboBoxPortfolio.addItems(availablePorts) 
        
    def openShowTradesDialog(self):
        self.tradesDialog=simulatedTradesDialog(self.activePort)
        self.pushButtonBuy.clicked.connect(self.tradesDialog.populateTable)
        self.pushButtonSell.clicked.connect(self.tradesDialog.populateTable)
        
        self.tradesDialog.show()
        
    def openPositionsForToday(self):
        self.activePort.openPositionsForToday()
        self.dateEdit.setDate(pA.dt.today())
        self.loadButtonClicked()
        self.pushButtonOpenToday.setEnabled(False)
        
    def updateIsinPriceEdit(self):
        rowIndex=self.tableWidgetPositions.currentRow()
        isin=str(self.tableWidgetPositions.item(rowIndex,0).text())
        price=str(self.tableWidgetPositions.item(rowIndex,2).text())
        if str(self.tableWidgetPositions.item(rowIndex,6).text())!='CASH':
            self.lineEditIsin.setText(isin)
            self.lineEditPrice.setText(price)
            
    def openFXDialog(self):
        
        self.fxDialogCon=FXDialog(self.activePort)
        self.fxDialogCon.pushButtonApply.clicked.connect(self.updateTradeFX)
        self.fxDialogCon.show()
        
#        fxDialogCon=FXDialogController(self)
#        fxDialogCon.ui.show()
#        fxDialogCon.show()
    def openDeposDialog(self):
        self.deposDialog = deposDialog(self.activePort)
        self.deposDialog.lineEditIsin.textChanged.connect(self.updateDepoIsin)
        self.deposDialog.lineEditPrice.textChanged.connect(self.updateDepoPrice)
        self.deposDialog.show()
        
    def updateDepoIsin(self):
        depoIsin = self.deposDialog.lineEditIsin.text()
        self.lineEditIsin.setText(depoIsin)
        
    def updateDepoPrice(self):
        priceIsin = self.deposDialog.lineEditPrice.text()
        self.lineEditPrice.setText(priceIsin)    
        
    def openbuyFromBMKDialog(self):
        
        self.addIsinCon=buyFromBMKDialog(self.activePort)
        self.addIsinCon.tableWidgetPositions.clicked.connect(self.updateIsinPriceEditBMK)
        #self.addIsinCon.pushButtonBuy.clicked.connect(self.buyFromBMK)
        self.addIsinCon.show()
        
    def updateIsinPriceEditBMK(self):
        rowIndex=self.addIsinCon.tableWidgetPositions.currentRow()
        isin=str(self.addIsinCon.tableWidgetPositions.item(rowIndex,0).text())
        price=str(self.addIsinCon.tableWidgetPositions.item(rowIndex,2).text())
        if str(self.addIsinCon.tableWidgetPositions.item(rowIndex,6).text())!='CASH':
            self.lineEditIsin.setText(isin)
            self.lineEditPrice.setText(price)
            
    def updateTradeFX(self):
        fxTrade=self.fxDialogCon.dataFXTrade()
        
        for trade in fxTrade:
            if trade['nominal']:
                self.activePort.trade([trade])
                self.updateComboBoxCurrencyIssuer()
                self.populateTableCrncy()
        #print(self.activePort.portfolio.trades) 
        
    def pushButtonTrade(self):
        
        isin=str(self.lineEditIsin.text())
        if str(self.sender().objectName())=='pushButtonBuy':
            amount=self.spinBoxTradeAmount.value()
        elif str(self.sender().objectName())=='pushButtonSell':
            amount=-self.spinBoxTradeAmount.value()
            
        price=float(self.lineEditPrice.text())
        
        tradeTmp=[{'id':isin,'price':price,'nominal':amount}]
        
        if amount:
            self.activePort.trade(tradeTmp)
            self.updateComboBoxCurrencyIssuer()
            self.populateTableCrncy()
            
    def resetTrades(self):
        
        self.activePort.deleteTrades()
        self.updateComboBoxCurrencyIssuer()
        self.populateTableCrncy()
        
    def loadButtonClicked(self):
        
        portName=str(self.comboBoxPortfolio.currentText()) #Por el momento no necesito el resultado en unicode
        portDate=self.dateEdit.date()
        self.activePort=pA.activePortfolio(portfolioName=portName,date=portDate.toPyDate())
        self.activePort.loadPositionsFromDB()
        self.updateComboBoxCurrencyIssuer()
#        totalCurrencies=['Currency']
#        totalIssuers=['Issuer']
#        totalCurrencies.extend(self.activePort.totalProperties('currency'))
#        totalIssuers.extend(self.activePort.totalProperties('issuer'))
#        #sender=self.sender() #Esta función detecta de quien viene la señal.
#        #Este message box lo tengo para ir probando y mostrando cosas
#        self.comboBoxCurrencies.clear()
#        self.comboBoxCurrencies.addItems(list(totalCurrencies))
#        self.comboBoxIssuers.clear()
#        self.comboBoxIssuers.addItems(list(totalIssuers))
        self.checkDateEnableOpenPositions()
        self.dateEdit.setDate(self.activePort.date)
        self.populateTable()
        self.labelLastPriced.setText(self.activePort.portfolio.securities.date.strftime('%m/%d/%Y'))
        
    def updateComboBoxCurrencyIssuer(self):
        totalCurrencies=['Currency']
        totalIssuers=['Issuer']
        totalCurrencies.extend(self.activePort.totalProperties('currency'))
        totalIssuers.extend(self.activePort.totalProperties('issuer'))
        currentCurrency = self.comboBoxCurrencies.currentText()
        currentIssuer = self.comboBoxIssuers.currentText()
        self.comboBoxCurrencies.clear()
        self.comboBoxCurrencies.addItems(list(totalCurrencies))
        self.comboBoxIssuers.clear()
        self.comboBoxIssuers.addItems(list(totalIssuers))
        self.comboBoxCurrencies.setCurrentIndex(self.comboBoxCurrencies.findText(currentCurrency))
        self.comboBoxIssuers.setCurrentIndex(self.comboBoxIssuers.findText(currentIssuer))
        
    def checkDateEnableOpenPositions(self):
        portDate = self.dateEdit.date()
        if portDate.toPyDate() == pA.dt.today():
            if self.activePort.date < pA.dt.today():
                self.pushButtonOpenToday.setEnabled(True)
            
    def populateTableCrncy(self):
        #Esta función es llamada cuando cambio el combobox de currencies. Actualiza adicionalmente el gráfico de exposición.
        self.populateTable()        
        self.plotExposures()
        
    def populateTable(self):
        #funcion encargada de rellenar la tabla que muestra las posiciones del portafolio
        
        conditions=self.updateConditionsAndFilters()    
        positions=self.activePort.portfolio.filterPortfolio(conditions)
        
        filas=max([len(data) for data in positions.values()])
        
        #Estas serán las columnas que se mostrarán en la tabla
        columnsIdentifier=['id','nominal','price','yield','duration','spread','quality','maturity','inflation','KRD']
        self.tableWidgetPositions.setColumnCount(len(columnsIdentifier))
        self.tableWidgetPositions.setRowCount(filas)
        
        columnName=[]
        
        for n, key in enumerate(columnsIdentifier):
            columnName.append(key)
            for m, item in enumerate(positions[key]):                
                newItem= QtGui.QTableWidgetItem(str(item))
                self.tableWidgetPositions.setItem(m,n,newItem)
        self.tableWidgetPositions.setHorizontalHeaderLabels(columnName)
        
        self.tableWidgetPositions.resizeColumnsToContents()
        self.tableWidgetPositions.resizeRowsToContents()
        
        self.populateTableSummary(conditions)
        
    def populateTableSummary(self,conditions=None):
        #Funcion que actualiza tabla resumen del portafolio
        portfolioExposure,BMKExposure=self.activePort.riskExposurePortfolio(conditions)
        
        #Propiedades totales, no por contribución al portafolio
        for riskFactorName in portfolioExposure:
            if riskFactorName != 'FX':
                portfolioExposure[riskFactorName]/=portfolioExposure['FX']
                BMKExposure[riskFactorName]/=BMKExposure['FX']
                
        portfolioExposure['FX']*=100
        BMKExposure['FX']*=100
        columnsIdentifier=['marketValue','FX','duration','DTS','KRD 0.5','KRD 1.0','KRD 2.0','KRD 3.0','KRD 5.0','KRD 7.0','KRD 10.0','KRD 20.0','KRD 30.0']
        columnName=['','marketValue','Weight','Duration','DTS','KRD 0.5','KRD 1.0','KRD 2.0','KRD 3.0','KRD 5.0','KRD 7.0','KRD 10.0','KRD 20.0','KRD 30.0']
        
        nfilas=3
        ncolumnas=len(columnName)
        
        self.tableWidgetPortfolioSummary.setColumnCount(ncolumnas)
        self.tableWidgetPortfolioSummary.setRowCount(nfilas)
        
        newItem= QtGui.QTableWidgetItem('Portfolio')
        self.tableWidgetPortfolioSummary.setItem(0,0,newItem)
        newItem= QtGui.QTableWidgetItem('BMK')
        self.tableWidgetPortfolioSummary.setItem(1,0,newItem)
        newItem= QtGui.QTableWidgetItem('Active')
        self.tableWidgetPortfolioSummary.setItem(2,0,newItem)
        
        for n, key in enumerate(columnsIdentifier):
            item=portfolioExposure[key]            
            newItem= QtGui.QTableWidgetItem(str(round(item,1)))
            self.tableWidgetPortfolioSummary.setItem(0,n+1,newItem)
            
            itemBMK=BMKExposure[key]            
            newItemBMK= QtGui.QTableWidgetItem(str(round(itemBMK,1)))
            self.tableWidgetPortfolioSummary.setItem(1,n+1,newItemBMK)
            
            itemBMK=portfolioExposure[key]-BMKExposure[key]            
            newItemBMK= QtGui.QTableWidgetItem(str(round(itemBMK,1)))
            self.tableWidgetPortfolioSummary.setItem(2,n+1,newItemBMK)
            
        self.tableWidgetPortfolioSummary.setHorizontalHeaderLabels(columnName)
        #self.tableWidgetPortfolioSummary.setVerticalHeaderLabels(['Portfolio','BMK','Active'])
        
        self.tableWidgetPortfolioSummary.resizeColumnsToContents()
        self.tableWidgetPortfolioSummary.resizeRowsToContents()
        
  
    def plotExposures(self):
        #Función que se encarga de graficar las posiciones activas
        factor=0.19
        mainColor=(factor,factor,factor)
        fig=self.mplwidgetExposures.figure
        fig.set_facecolor(mainColor)
        ax=fig.add_subplot(111, axisbg=mainColor)
        ax.hold(False)
        self.mplwidgetExposures.draw()
        ax.tick_params(axis='x',colors='white')
        ax.tick_params(axis='y',colors='white')
        
        #Reseteamos los axes disponibles            
        for axes in fig.get_axes():
            axes.get_xaxis().set_ticks([])
            axes.get_yaxis().set_ticks([])
        
        if self.comboBoxCurrencies.currentIndex()>0:
            currency=str(self.comboBoxCurrencies.currentText())
            riskExposure=self.activePort.riskExposureActive(currency)
            width=0.7 #Ancho de las barras
            riskFactorsNamesAvbl=sorted(riskExposure.keys())
            riskFactorsNames=[]
            if self.checkBoxFX.isChecked():
                riskFactorsNames.extend(list(set(['FX']).intersection(riskFactorsNamesAvbl)))
            if self.checkBoxDuration.isChecked():
                riskFactorsNames.extend(list(set(['duration']).intersection(riskFactorsNamesAvbl)))
            if self.checkBoxSpread.isChecked():
                riskFactorsNames.extend(list(set(['DTS']).intersection(riskFactorsNamesAvbl)))
            if self.checkBoxKRD.isChecked():
                order=['KRD 0.5','KRD 1.0','KRD 2.0','KRD 3.0','KRD 5.0','KRD 7.0','KRD 10.0','KRD 20.0','KRD 30.0']
                namesAux = list(set(\
                ['KRD 0.5','KRD 1.0','KRD 2.0','KRD 3.0','KRD 5.0','KRD 7.0','KRD 10.0','KRD 20.0','KRD 30.0']).\
                intersection(riskFactorsNamesAvbl))
                riskFactorsNames.extend(sorted(namesAux, key=lambda s:order.index(s)))
                
            if riskFactorsNames:
                riskFactorsValues=[riskExposure[key] for key in riskFactorsNames]
                #Datos a graficar en las barras horizontales
                x=np.arange(len(riskFactorsNames)) #índice de cada posición activa
                y=riskFactorsValues #Valor de las exposiciones activas                
                
                #Generamos la figura
                #self.mplwidgetExposures.palette().setColor(QtGui.QPalette.Background, QtCore.Qt.black)
                
                
                #print(len(fig.get_axes()))
                
                #Fijamos los márgenes del gráfico
                
                #fig.subplots_adjust(left=0.4,right=0.95,top=0.97, bottom=0.03)
                
                #ax=fig.get_axes()
                
               
                rects=ax.barh(x,y,height=width, color=(0,0.5,0.7), edgecolor=(0,0.5,0.7))
                            
                ax.set_yticks(x + width/2)
                pylab.setp(ax, yticklabels=riskFactorsNames)
                
                ax.set_xticks([min(y),max(y)])
                pylab.setp(ax, xticklabels=[round(min(y),0),round(max(y),1)])
                
                self.autolabel(ax,rects,riskFactorsValues)
                #self.zoom_factory(ax)
                fig.tight_layout()                
                
                #ax.set_title(currency)                
                self.mplwidgetExposures.draw()
                self.labelPlotTitle.setText(self.activePort.name + " " + currency)
        
            
    def autolabel(self,ax,rects,labels):
        #Función usada en plotExposures para agregar labels a las barras
        for num,rect in enumerate(rects):
            width=rect.get_width()
            label=round(labels[num],1)
           
            if (label < 0):        # The bars aren't wide enough to print the ranking inside
                xloc = 0.1*width  # Shift the text to the left side of the right edge
                clr = (1,1,1)      # White on magenta
                align = 'right'
            else:
                xloc = 0.1*width  # Shift the text to the left side of the right edge
                clr = (1,1,1)      # White on magenta
                align = 'left'
                
            # Center the text vertically in the bar
            yloc = rect.get_y()+rect.get_height()/2.0
            
            ax.text(xloc,yloc,label,horizontalalignment=align,
            verticalalignment='center', color=clr, weight='bold')
     
#==============================================================================
#     def updateComboBoxPlotExposure(self):
#         if self.comboBoxCurrencies.currentIndex()>0:
#             currency=str(self.comboBoxCurrencies.currentText())
#             riskExposure=self.activePort.riskExposureActive(currency)
#             riskFactorsNames=sorted(riskExposure.keys())
#             self.comboBoxRiskPlot.clear()
#             self.comboBoxRiskPlot.addItems(riskFactorsNames)
#==============================================================================
#==============================================================================
#     def zoom_factory(self,ax,base_scale = 1.5):
#         def zoom_fun(event):
#             # get the current x and y limits
#             cur_xlim = ax.get_xlim()
#             cur_ylim = ax.get_ylim()
#             cur_xrange = (cur_xlim[1] - cur_xlim[0])*.5
#             cur_yrange = (cur_ylim[1] - cur_ylim[0])*.5
#             xdata = event.xdata # get event x location
#             ydata = event.ydata # get event y location
#             if event.button == 'up':
#                 # deal with zoom in
#                 scale_factor = 1/base_scale
#             elif event.button == 'down':
#                 # deal with zoom out
#                 scale_factor = base_scale
#             else:
#                 # deal with something that should never happen
#                 scale_factor = 1
#                 print event.button
#             # set new limits
#             ax.set_xlim([xdata - cur_xrange*scale_factor,
#                          xdata + cur_xrange*scale_factor])
#             ax.set_ylim([ydata - cur_yrange*scale_factor,
#                          ydata + cur_yrange*scale_factor])
#                          
#             self.mplwidgetExposures.draw() # force re-draw
#     
#         fig = ax.get_figure() # get the figure of interest
#         # attach the call back
#         fig.canvas.mpl_connect('scroll_event',zoom_fun)
# 
#         #return the function
#         return zoom_fun    
#==============================================================================
        
        
    def updateConditionsAndFilters(self):
        #Función que devuelve el diccionario de condiciones filtradas
        #Adicional actualiza los filtros dada la selección ingresada por el usuario
    
        #Revisamos si se seleccionó filtro de currency
        currencyFilter=str(self.sender().objectName())=='comboBoxCurrencies'
        conditions={}
        if self.comboBoxCurrencies.currentIndex()>0:
            currency=str(self.comboBoxCurrencies.currentText())
            conditions.update({'currency':[currency]})
            if currencyFilter:
                totalIssuers = ['Issuer']
                totalIssuers.extend(self.activePort.totalProperties('issuer',{'currency':[currency]}))
                self.comboBoxIssuers.clear()
                self.comboBoxIssuers.addItems(list(totalIssuers))
        elif currencyFilter:
            totalIssuers=['Issuer']
            totalIssuers.extend(self.activePort.totalProperties('issuer'))
            self.comboBoxIssuers.clear()
            self.comboBoxIssuers.addItems(list(totalIssuers))
        
        if self.comboBoxIssuers.currentIndex()>0:    
            issuer=str(self.comboBoxIssuers.currentText())
            conditions.update({'issuer':[issuer]})
        if not conditions:
            conditions=None
        #print(conditions)
        return conditions
        
class FXDialog(QtGui.QDialog):
    #La siguiente clase genera el diálogo de FX basado en FxDialog previamente creado en Qt Designer
    def __init__(self, activePort):
        
        super(FXDialog,self).__init__()
        self.ui=uic.loadUi('FxDialog.ui',self)
        self.activePort = activePort
        self.FX = activePort.portfolio.securities.usdFXData.keys()
        #self.FX = list(activePort.totalProperties('currency'))
        #self.FX = activePort.portfolio.filterPortfolio({'issuer':'CASH'})
        self.initUI()
        #self.show()
        
    def initUI(self):        
        self.setWidgetsPropertiesAndActions()
        
    def setWidgetsPropertiesAndActions(self):
        
        #ids=self.FX['id']
        ids = self.FX
        self.comboBoxBUY.addItems(ids)
        self.comboBoxSELL.addItems(ids)
        
        #self.buttonBoxFX.rejected.connect(self.reject)
        
        self.comboBoxBUY.activated[str].connect(self.updateRate)
        self.comboBoxSELL.activated[str].connect(self.updateRate)
        self.checkBoxInvert.stateChanged.connect(self.updateRate)
        
        self.dateEdit.setDate(self.activePort.date)
        self.editAmount.setText('0')
        
    def updateRate(self):
        buyCurrency=""
        sellCurrency=""        
        
        if self.comboBoxBUY.currentIndex()>-1:
            buyCurrency=str(self.comboBoxBUY.currentText())            
            buyRateUSD = self.activePort.portfolio.securities.usdFXData[buyCurrency]
        if self.comboBoxSELL.currentIndex()>-1:
            sellCurrency=str(self.comboBoxSELL.currentText())
            sellRateUSD = self.activePort.portfolio.securities.usdFXData[sellCurrency]
        
        
        if self.checkBoxInvert.isChecked():
            rateStr=sellCurrency+"/"+buyCurrency 
            rate=str(sellRateUSD/buyRateUSD)
        else:
            rateStr=buyCurrency+"/"+sellCurrency        
            rate=str(buyRateUSD/sellRateUSD)
            
        self.labelRate.setText(rateStr)
        self.lineEditRate.setText(rate)       
        
    
#    def updateTradeFX(self):
#        pass
    
    def dataFXTrade(self):
        
        buyCurrency=str(self.comboBoxBUY.currentText())
        sellCurrency=str(self.comboBoxSELL.currentText())
        
        if self.ui.checkBoxInvert.isChecked():
            rate=1/float(self.lineEditRate.text())
        else:
            rate=float(self.lineEditRate.text())
        
        baseIndex = self.comboBoxBase.currentIndex()
        amount = float(self.editAmount.text())
        
        if baseIndex==0:
            nominal=amount
        if baseIndex==1:
            nominal=amount
        if baseIndex==2:
            nominal=amount
         
        trade=[{'id':buyCurrency, 'nominal':nominal,'currencyPay':sellCurrency,'price':rate}]
        return trade
    
#    @staticmethod    
#    def getFXtrade(parent = None):
#        dialog = FXDialog(parent)
#        result = dialog.exec_()
#        fx = 'hola'#dialog.data()
#        return fx
        
#class FXDialogController(QtGui.QWidget):
#      #La siguiente clase conecta el FXDialog con la ventana principal para que se puedan aplicar cambios en forma paralela.
#    def __init__(self,portfolioManager):
#        
#        super(FXDialogController, self).__init__()
#        self.portfolioManager=portfolioManager
#        self.ui=FXDialog(portfolioManager.activePort)
#        #self.ui.buttonBoxFX.button(QtGui.QDialogButtonBox.Apply).clicked.connect(self.updateTradeFX)
#        self.ui.pushButtonApply.clicked.connect(self.updateTradeFX)
#        
#    def updateTradeFX(self):
#        self.fxTrade=self.ui.dataFXTrade()
#        
#        for trade in self.fxTrade:
#            if trade['nominal']:
#                self.portfolioManager.activePort.trade(self.fxTrade)  
#                self.portfolioManager.populateTableCrncy()
        
class deposDialog(QtGui.QDialog):
    def __init__(self, activePort):
        
        super(deposDialog,self).__init__()
        self.ui=uic.loadUi('deposDialog.ui',self)
        self.activePort = activePort
        self.initUI()

        #self.show()
        
    def initUI(self):        
        self.setWidgetsPropertiesAndActions()
        
    def setWidgetsPropertiesAndActions(self):
        
        self.availableIssuers = self.activePort.getPortAvailableIssuers()
        self.FX = self.activePort.portfolio.securities.usdFXData.keys()
        self.depoType = [{'name':'Time Deposit', 'identifier':'DEPO'},{'name':'Commercial Papers', 'identifier':'COMP'}]
        self.accrualType = [{'name':'Act/365', 'identifier':'A1'}]
        issuerName = [issuer['name'] for issuer in self.availableIssuers]
        depoName = [depo['name'] for depo in self.depoType]
        accrualName = [depo['name'] for depo in self.accrualType]
        
        self.comboBoxType.addItems(depoName)
        self.comboBoxIssuer.addItems(issuerName)
        self.comboBoxCurrency.addItems(self.FX)
        self.comboBoxAccrual.addItems(accrualName)
        self.dateEdit.setDate(pA.dt.today())
        
        self.comboBoxType.activated[str].connect(self.updateIsinStr)
        self.comboBoxIssuer.activated[str].connect(self.updateIsinStr)
        self.comboBoxCurrency.activated[str].connect(self.updateIsinStr)
        self.comboBoxAccrual.activated[str].connect(self.updateIsinStr)
        self.dateEdit.dateChanged.connect(self.updateIsinStr)
        self.lineEditRate.editingFinished.connect(self.updateIsinStr)
        
        self.updateIsinStr()
        
    def updateIsinStr(self):
        depoType = self.depoType[self.comboBoxType.currentIndex()]['identifier']
        issuer=self.availableIssuers[self.comboBoxIssuer.currentIndex()]['identifier']
        currency=self.comboBoxCurrency.currentText()
        accrual=self.accrualType[self.comboBoxAccrual.currentIndex()]['identifier']
        rate=self.lineEditRate.text()
        date = self.dateEdit.date().toPyDate().strftime('%Y%m%d')
        
        isinStr = str(depoType) + str(currency) + date + str(accrual) + str(issuer) + '_' + str(rate)
        self.lineEditIsin.setText(isinStr)
        self.updateDepoPrice()
        
    def updateDepoPrice(self):
        secTmp = pA.port.securityClas()
        depoIsin = self.lineEditIsin.text()
        [infoU,tasa] = depoIsin.split('_')
        info = str(infoU)
        rate = float(tasa)
        
        maturity = pA.dtime.strptime(info[7:15],"%Y%m%d").date()
        baseAccrual = info[15:17]
        price = secTmp.depoPrice(rate, maturity, baseAccrual)
        self.lineEditPrice.setText('')
        self.lineEditPrice.setText(str(price))
        
        
class buyFromBMKDialog(QtGui.QDialog):
    def __init__(self, activePort):
        
        super(buyFromBMKDialog,self).__init__()
        self.ui=uic.loadUi('buyFromBMKDialog.ui',self)
        self.activePort = activePort
        self.initUI()

        #self.show()
        
    def initUI(self):        
        self.setWidgetsPropertiesAndActions()
        
    def setWidgetsPropertiesAndActions(self):
        
        totalCurrencies=['Currency']
        totalIssuers=['Issuer']
        totalCurrencies.extend(self.activePort.totalProperties('currency'))
        totalIssuers.extend(self.activePort.totalProperties('issuer'))
        
        self.comboBoxCurrencies.activated[str].connect(self.populateTable)
        self.comboBoxIssuers.activated[str].connect(self.populateTable)
        
        self.comboBoxCurrencies.clear()
        self.comboBoxCurrencies.addItems(list(totalCurrencies))
        self.comboBoxIssuers.clear()
        self.comboBoxIssuers.addItems(list(totalIssuers))        
        
        self.populateTable()
        
            
    def populateTable(self):
        
        conditions=self.updateConditionsAndFilters()    
        positions=self.activePort.BMK.filterPortfolio(conditions)
        
        filas=max([len(data) for data in positions.values()])
        
        #Estas serán las columnas que se mostrarán en la tabla
        columnsIdentifier=['id','nominal','price','yield','duration','spread','quality','maturity','inflation','KRD']
        self.tableWidgetPositions.setColumnCount(len(columnsIdentifier))
        self.tableWidgetPositions.setRowCount(filas)
        
        columnName=[]
        
        for n, key in enumerate(columnsIdentifier):
            columnName.append(key)
            for m, item in enumerate(positions[key]):                
                newItem= QtGui.QTableWidgetItem(str(item))
                self.tableWidgetPositions.setItem(m,n,newItem)
                
        self.tableWidgetPositions.setHorizontalHeaderLabels(columnName)
        
        self.tableWidgetPositions.resizeColumnsToContents()
        self.tableWidgetPositions.resizeRowsToContents()
       
        
    def updateConditionsAndFilters(self):      
        
        currencyFilter=str(self.sender().objectName())=='comboBoxCurrencies'
        conditions={}
        if self.comboBoxCurrencies.currentIndex()>0:
            currency=str(self.comboBoxCurrencies.currentText())
            conditions.update({'currency':[currency]})
            if currencyFilter:
                totalIssuers = ['Issuer']
                totalIssuers.extend(self.activePort.totalProperties('issuer',{'currency':[currency]}))
                self.comboBoxIssuers.clear()
                self.comboBoxIssuers.addItems(list(totalIssuers))
                
        elif currencyFilter:
            totalIssuers=['Issuer']
            totalIssuers.extend(self.activePort.totalProperties('issuer'))
            self.comboBoxIssuers.clear()
            self.comboBoxIssuers.addItems(list(totalIssuers))
        
        if self.comboBoxIssuers.currentIndex()>0:    
            issuer=str(self.comboBoxIssuers.currentText())
            conditions.update({'issuer':[issuer]})
        if not conditions:
            conditions=None
        #print(conditions)
        return conditions
        
class simulatedTradesDialog(QtGui.QDialog):
    
    def __init__(self, activePort):
        
        super(simulatedTradesDialog,self).__init__()
        self.ui=uic.loadUi('simulatedTradesDialog.ui',self)
        self.activePort = activePort
        self.initUI()
        
    def initUI(self):        
        self.setWidgetsPropertiesAndActions()
        
    def setWidgetsPropertiesAndActions(self):
        
        self.labelPortfolioTitle.setText('Trades from ' + self.activePort.name)
        self.populateTable()
            
    def populateTable(self):
         
        tradesSimulated=self.activePort.portfolio.trades['tradesSimulated']
        filas=len(tradesSimulated)
        
        #Estas serán las columnas que se mostrarán en la tabla
        columnsIdentifier=['id','nominal','price','currencyPay','cashPending']
        
        self.tableWidgetPositions.setColumnCount(len(columnsIdentifier))
        self.tableWidgetPositions.setRowCount(filas)
        columnName=columnsIdentifier
        
        for m, trade in enumerate(tradesSimulated):
            for n, key in enumerate(columnsIdentifier):
                item=trade[key]
                newItem= QtGui.QTableWidgetItem(str(item))
                self.tableWidgetPositions.setItem(m,n,newItem)
                
        self.tableWidgetPositions.setHorizontalHeaderLabels(columnName)
        
        self.tableWidgetPositions.resizeColumnsToContents()
        self.tableWidgetPositions.resizeRowsToContents()
        
class importDialog(QtGui.QDialog):
    def __init__(self):
        super(importDialog,self).__init__()      
        self.ui = uic.loadUi('importDialog.ui',self)
        self.initUI()
        self.activePortfolio = []
        
    def initUI(self):
        self.setWidgetsPropertiesAndActions()
        
    def setWidgetsPropertiesAndActions(self):
        self.pushButtonImportCSV.clicked.connect(self.showFileDialog)
        self.pushButtonDone.clicked.connect(self.close)
        self.pushButtonLoadPositions.clicked.connect(self.loadPositionsFromText)
        self.pushButtonReset.clicked.connect(self.reset)
        self.pushButtonCommitToDB.clicked.connect(self.commitToDB)
        self.dateEdit.setDate(pA.dt.today())
        
    def showFileDialog(self):
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Open file', 
                '/home')        
        f = open(fname, 'r')
        with f:        
            self.data = f.read()
            
    def updateLabels(self):
        if self.activePortfolio:
            date = self.activePortfolio.date.strftime('%m/%d/%Y')
            self.labelPortfolioName.setText(self.activePortfolio.name + ", " + date)
            self.labelPortfolioType.setText(', '.join(self.activePortfolio.getPortTypeLabels()))
        else:
            self.labelPortfolioName.setText('')
            self.labelPortfolioType.setText('')
        
    def reset(self):
        self.activePortfolio = []
        self.updateLabels()
        
    def readPositions(self):
        rowSeparator ='\n'        
        textPositions = str(self.textEditPositions.toPlainText())
        positionsTmp = textPositions.split(rowSeparator)
        positions = {}
        for row in positionsTmp:
            if row:
                [identifier, nominal] = row.split('\t')
                positions.update({identifier: float(nominal)})
        
#        f = StringIO.StringIO(textPositions)
#        reader = csv.reader(f)
        return positions
            
    def loadPositionsFromText(self):
        
        positions = self.readPositions()
        importType = self.comboBoxImportType.currentIndex()
        date = self.dateEdit.date().toPyDate()
        
        if not self.activePortfolio:
            name=str(self.lineEditPortfolioName.text())
            self.activePortfolio = pA.activePortfolio(portfolioName = name)
            
        if importType == 0:
            self.activePortfolio.createPortfolio(date = date, portfolioInitialPositions = positions)
        elif importType == 1:
            self.activePortfolio.createPortfolio(date = date, BMKInitialPositions = positions)
        elif importType == 2:
            pass
        
        self.dateEdit.setDate(self.activePortfolio.date)
        self.updateLabels()
    
    def commitToDB(self):
        
        #Agregar un warning acá que la base de datos será modificada
        
        if self.activePortfolio:
            reply=QtGui.QMessageBox.question(self,'Message',
                                         "Portfolio " + self.activePortfolio.name + " is going to be uploaded to DB on date "+ str(self.activePortfolio.date) + ". Proceed?" ,QtGui.QMessageBox.Yes |
                                         QtGui.QMessageBox.No, QtGui.QMessageBox.No)
            if reply == QtGui.QMessageBox.Yes:
                self.activePortfolio.savePositionsToDB()
                msg = QtGui.QMessageBox.information(self, 'Message', "Portfolio should be now loaded on DB")
            
class securitiesDialog(QtGui.QDialog):
    def __init__(self):
        super(securitiesDialog,self).__init__()      
        self.ui = uic.loadUi('securitiesDialog.ui',self)
        self.initUI()
        self.securities = []
        
    def initUI(self):
        self.setWidgetsPropertiesAndActions()
        
    def setWidgetsPropertiesAndActions(self):
        self.pushButtonImportCSV.clicked.connect(self.showFileDialog)
        self.pushButtonCashflows.clicked.connect(self.updateCashFlows)
        self.pushButtonLoadDB.clicked.connect(self.loadPositionsFromDB)
        self.pushButtonLoadText.clicked.connect(self.loadPositionsFromText)
        self.pushButtonPrice.clicked.connect(self.priceSecurities)
        self.pushButtonCommitToDB.clicked.connect(self.commitToDB)
        self.dateEdit.setDate(pA.dt.today())
        
    def updateCashFlows(self):
        if self.securities:
            totalSecurities = sum([len(isin) for isin in self.securities.isin.values()])
            if totalSecurities > 0:
                self.securities.updateCashFlows()
                QtGui.QMessageBox.information(self, 'Message', "Cash flows should be now loaded on DB")
                
    def showFileDialog(self):
        fname = QtGui.QFileDialog.getOpenFileName(self, 'Open file', 
                '/home')        
        f = open(fname, 'r')
        with f:        
            self.data = f.read()
            
    def updateLabels(self):
        if self.securities:
            date = self.securities.date.strftime('%m/%d/%Y')
            self.labelSecurities.setText(str(len(self.securities.isin['security'])) + " securities, " + date)
            self.labelDepos.setText(str(len(self.securities.isin['deposit'])) + " deposits or CP, " + date)
            self.labelCurrencies.setText(str(len(self.securities.isin['currency'])) + " currencies, " + date)
        else:
            self.labelSecurities.setText('')
            self.labelDepos.setText('')
            self.labelCurrencies.setText('')
            
    def updateText(self):
        if self.securities:
            totalIds = []
            [totalIds.extend(isin) for isin in self.securities.isin.values()]
            self.textEditPositions.setPlainText('\n'.join(totalIds))
            
    def reset(self):
        self.securities = []
        self.updateLabels()
        
    def readPositions(self):
        rowSeparator ='\n'
        textPositions = str(self.textEditPositions.toPlainText())
        positionsTmp = textPositions.split(rowSeparator)
        return positionsTmp
        
    def priceSecurities(self):
        if self.securities:
            totalSecurities = sum([len(isin) for isin in self.securities.isin.values()])
            if totalSecurities > 0:
                self.securities.updateLoadedSecurities()
                self.dateEdit.setDate(self.securities.date)
                self.updateText()
                self.updateLabels()
                newTotalSecurities = sum([len(isin) for isin in self.securities.isin.values()])
                msg = QtGui.QMessageBox.information(self, 'Message', str(newTotalSecurities) + " securities priced")
            else:
                msg = QtGui.QMessageBox.information(self, 'Message', "There aren't securities loaded")
                
    def loadPositionsFromDB(self):
        date = self.dateEdit.date().toPyDate()
        if not self.securities:
            self.securities = pA.port.securityClas()
            
        self.securities.DBToSecurity(date = date)
        self.dateEdit.setDate(self.securities.date)
        self.updateLabels()
        self.updateText()
    
    def loadPositionsFromText(self):
        
        positions = self.readPositions()
        if not self.securities:
            self.securities = pA.port.securityClas()
            
        self.securities.addSecuritiesAndCash(securities = positions)
        self.dateEdit.setDate(self.securities.date)
        self.updateLabels()
    
    def commitToDB(self):
        #Agregar un warning acá que la base de datos será modificada
        if self.securities:
            if self.securities.securityData:
                totalSecurities = sum([len(isin) for isin in self.securities.isin.values()])
                
                reply=QtGui.QMessageBox.question(self,'Message',
                                         str(totalSecurities) + " securities are going to be uploaded to DB on date "+ str(self.securities.date) + ". Proceed?" ,QtGui.QMessageBox.Yes |
                                         QtGui.QMessageBox.No, QtGui.QMessageBox.No)
                if reply == QtGui.QMessageBox.Yes:
                    self.securities.securityDataToDB()
                    msg = QtGui.QMessageBox.information(self, 'Message', "Securities should be now loaded on DB for date: " + str(self.securities.date))
            else:
                msg = QtGui.QMessageBox.information(self, 'Message', "Securities are not priced")
        else:
            msg = QtGui.QMessageBox.information(self, 'Message', "There aren't securities loaded")
            
class NavigationToolbar(NavigationToolbar2QT):
    #Clase que modifica el navigation Toolbar usado en el gráfico
    # only display the buttons we need
    toolitems = [t for t in NavigationToolbar2QT.toolitems if
                 t[0] in ('Home','Pan', 'Zoom', 'Save')] #Subplots
    
    #Eliminamos el boton de "edit" 
    def removeEdit(self):
        actions = self.findChildren(QtGui.QAction)
        for a in actions:
            if a.text() == 'Customize':
                self.removeAction(a)
                break
#            
#class myTableModel(QtCore.QAbstractTableModel):
#    #Será usado para generar el modelo con los datos a mostrar en tabla o table tree.
#    def __init__(self):    
#        pass
#    def rowCount(): #función requerida para implementar la clase QAbstractTableModel
#        pass
#    def columnCount(): #función requerida para implementar la clase QAbstractTableModel
#        pass
#    def data(): #función requerida para implementar la clase QAbstractTableModel
#        pass
#    def headerData(): #función recomendada para implementar la clase QAbstractTableModel
#        pass
    
def main():
    app = QtGui.QApplication(sys.argv)
    QtGui.QApplication.setStyle('plastique')
    portManager=portfolioManaging()
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()