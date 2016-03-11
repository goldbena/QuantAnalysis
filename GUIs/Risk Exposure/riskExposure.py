# -*- coding: utf-8 -*-
"""
Created on Wed Sep 09 17:00:30 2015

@author: mvillalon
"""

import sys
from PyQt4 import QtCore, QtGui, uic
sys.path.append("G:\DAT\GII\MES_INT\INVINTER\Matlab Programas\packagePY")
import numpy as np
import pylab
#from matplotlib.backends.backend_qt4agg import NavigationToolbar2QT
import riskFactors as rf


class riskExposure(QtGui.QWidget):
    def __init__(self):
        super(riskExposure,self).__init__()
        uic.loadUi('riskExposure.ui',self)
        self.initUI()
        self.show()
        
    def initUI(self):
        self.setWidgetsPropertiesAndActions()
        
    def setWidgetsPropertiesAndActions(self):
        #Inicializamos variables que serán usadas por el GUI
        self.portRisk = None
        self.portActiveRiskByRF = None
        self.portActiveRiskByCurrency = None
        self.portActiveRiskDict = {}
        self.orderByCurrency = True
        self.currencyNamesSorted = None
        self.riskFactorsNamesSorted = None
        
        
        self.updateAvailablePortfolios()
        self.treeViewPositions.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.treeViewPositions.customContextMenuRequested.connect(self.openMenu)
        
#        self.treeWidgetPositions.setHeaderHidden(True)
#        self.treeWidgetPositions.setColumnCount(2)
#        
#        
        self.dateEdit.setDate(rf.pA.dt.today())
        self.updateTreeModel()
        
        self.comboBoxPortfolio.activated[str].connect(self.loadPortfolio)
        self.dateEdit.dateChanged.connect(self.loadPortfolio)
        
        self.radioButtonCurrency.toggled.connect(self.invertRfLvls)
        
        self.plotExposuresFX()
        self.plotPerCurrency()
#        self.plotExposuresPerCurrencyTE()
        
        self.comboBoxCurrencies.activated[str].connect(self.plotPerCurrency)
        self.checkBoxInflation.stateChanged.connect(self.plotPerCurrency)
        self.checkBoxFX.stateChanged.connect(self.plotPerCurrency)
        self.checkBoxSpread.stateChanged.connect(self.plotPerCurrency)
        self.checkBoxKRD.stateChanged.connect(self.plotPerCurrency)
        #self.radioButtonRiskFactor.toggled.connect(self.invertRfLvls)        
        
    def updateAvailablePortfolios(self):
        
        activePortTmp=rf.pA.activePortfolio()
        availablePorts=activePortTmp.availablePortfolioInDB()
        self.comboBoxPortfolio.clear()
        self.comboBoxPortfolio.addItems(availablePorts)
        
    def openMenu(self, position):
        
        indexes = self.treeViewPositions.selectedIndexes()
        
        if len(indexes) > 0:
            level = 0
            index = indexes[0]
            
            while index.parent().isValid():
                index = index.parent()
                level += 1
                
        menu = QtGui.QMenu()
        if level == 0:
            menu.addAction(self.tr("Edit person"))
        elif level == 1:
            menu.addAction(self.tr("Edit object/container"))
        elif level == 2:
            menu.addAction(self.tr("Edit object"))
        menu.exec_(self.treeViewPositions.viewport().mapToGlobal(position))
    
    def invertRfLvls(self):
        
        if self.portActiveRiskDict:
            if self.radioButtonCurrency.isChecked():
                self.orderByCurrency = True
                self.portActiveRiskDict = self.portActiveRiskByCurrency
                self.marginalTEDict = self.marginalTEByCurrency
                self.contributionTEDict = self.contributionTEByCurrency
            else:
                self.orderByCurrency = False
                self.portActiveRiskDict = self.portActiveRiskByRF
                self.marginalTEDict = self.marginalTEByRF
                self.contributionTEDict = self.contributionTEByRF
                
            self.updateTreeModel()   
        
            
    def loadPortfolio(self):
        
        portName=str(self.comboBoxPortfolio.currentText()) #Por el momento no necesito el resultado en unicode
        portDate=self.dateEdit.date()
        
        self.portRisk = rf.portfolioRisks()
        
        availableDate = self.portRisk.checkPortfolioDates(portfolioName = portName, date = portDate.toPyDate())
        
        if not availableDate: 
            msg = QtGui.QMessageBox.information(self, 'Message', """No hay datos cargados en BD portfolioRiskExposure para el portafolio %s en la fecha %s.\nDatos serán cargados (si es que están disponibles)""" %(portName, str(portDate.toPyDate())))
            updatedDates = self.portRisk.uploadPortfolioRiskToDB(portfolioName = portName, start = portDate.toPyDate())
            self.portRisk = rf.portfolioRisks()
            
            if not updatedDates:
                msg = QtGui.QMessageBox.information(self, 'Message', """No hay datos cargados en BD portfolios para el portafolio %s en la fecha %s.\nDebe estar cargado anteriormente por un administrador de portafolio. No se puede cargar información""" %(portName, str(portDate.toPyDate())))
                return False
            msg = QtGui.QMessageBox.information(self, 'Message', """Datos cargados en BD portfolioRiskExposure para portafolio %s y fecha %s.""" %(portName, str(portDate.toPyDate())))
        
        self.portActiveRiskByCurrency = self.portRisk.loadPortfolioActiveRiskFromDB(portfolioName = portName, date = portDate.toPyDate(), prettyRiskLabel = True)
        self.portActiveRiskByRF = self.portRisk.invertPortActiveRiskDict(self.portActiveRiskByCurrency)
        
        (self.TE, self.marginalTEByCurrency, self.contributionTEByCurrency) = self.portRisk.getTE(portfolioName = portName, date = portDate.toPyDate(), prettyRiskLabel = True)
        (self.marginalTEByRF, self.contributionTEByRF) = (self.portRisk.invertPortActiveRiskDict(self.marginalTEByCurrency), self.portRisk.invertPortActiveRiskDict(self.contributionTEByCurrency))
        
        
        if self.radioButtonCurrency.isChecked():
            self.orderByCurrency = True
            self.portActiveRiskDict = self.portActiveRiskByCurrency
            self.marginalTEDict = self.marginalTEByCurrency
            self.contributionTEDict = self.contributionTEByCurrency
        else:
            self.orderByCurrency = False
            self.portActiveRiskDict = self.portActiveRiskByRF
            self.marginalTEDict = self.marginalTEByRF
            self.contributionTEDict = self.contributionTEByRF            
        
        if self.portActiveRiskDict:
            #Ordenamos los factores de riesgo
            totalCurrencies, riskFactorsNames = self.portRisk.getTotalCurrenciesAndRiskFactors(portfolioName = portName, date = portDate.toPyDate()) 
            riskFactorsNames = []
            [riskFactorsNames.extend(value.keys()) for key, value in self.portActiveRiskDict.iteritems()]
            
#            riskFactorsNamesAvbl = set(riskFactorsNames)
#            
#            order=['FX','Low Spread','Medium Spread','High Spread','Inflation','KRD 0.5','KRD 1.0','KRD 2.0','KRD 3.0','KRD 5.0','KRD 7.0','KRD 10.0','KRD 20.0','KRD 30.0']
#            namesAux = list(set(order).intersection(riskFactorsNamesAvbl))
            self.riskFactorsNamesSorted = self.sortRiskFactorsNames(riskFactorsNames)#sorted(namesAux, key=lambda s:order.index(s))
            self.currencyNamesSorted = sorted(totalCurrencies)
            
            
            self.updateTreeModel()
            
            self.comboBoxCurrencies.clear()
            self.comboBoxCurrencies.addItems(['Currency'] + self.currencyNamesSorted)
            
            self.plotExposuresFX()
            self.plotPerCurrency() #Reseteamos el gráfico
        else:
            msg = QtGui.QMessageBox.information(self, 'Message', "No information available on riskFactor DB for %s on date %d" %(portName, str(portDate.toPyDate())))
        
    def updateTreeModel(self):
                    
#        self.model = QtGui.QStandardItemModel()
#        self.model.setColumnCount(2)
#        self.addItems(self.model,  self.portActiveRiskDict)
        if self.portActiveRiskDict:
            rfNode = self.dictToRiskFactorNode(self.portActiveRiskDict)
            TENode = self.dictToTENode(self.marginalTEDict, self.contributionTEDict)
            if rfNode:
                self.rfModel =  riskFactorTreeModel(rfNode)
                self.treeViewPositions.setModel(self.rfModel)                
                self.treeViewPositions.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
                self.treeViewPositions.header().setStretchLastSection(False)
                
                self.TEModel = TETreeModel(TENode)
                self.treeViewTE.setModel(self.TEModel)                
                self.treeViewTE.header().setResizeMode(QtGui.QHeaderView.ResizeToContents)
                self.treeViewTE.header().setStretchLastSection(False)
    #        self.rfModel.setHorizontalHeaderLabels([self.tr('Risk Factor'),self.tr('Exposure')])
    #        self.treeViewPositions.resizeColumnToContents(0)
            
    def dictToRiskFactorNode(self, rfDict):
        #Función que convierte un diccionario a un RiskFactorNode
            
        if self.portRisk:
            parentRf = riskFactorNode('Exposiciones Activas')
            
            if self.orderByCurrency:
                lvl1 = self.currencyNamesSorted
                lvl2 = self.riskFactorsNamesSorted
            else:
                lvl2 = self.currencyNamesSorted
                lvl1 = self.riskFactorsNamesSorted
            
            
            for rflvl1 in lvl1:
                rfNode = riskFactorNode(rflvl1, parentRf)
                
                for rflvl2 in lvl2:
                    
                    rfNode2 = riskFactorNode(rflvl2, rfNode)
                    rfNode2.setExposure([rfDict[rflvl1][rflvl2]])
                    
            return parentRf
        return False
        
    def dictToTENode(self, marginalDict, contributionDict):
        #Función que convierte un diccionario a un RiskFactorNode
           
        if self.portRisk:
                
            parentRf = riskFactorNode('TE')
            
            if self.orderByCurrency:
                lvl1 = self.currencyNamesSorted
                lvl2 = self.riskFactorsNamesSorted
            else:
                lvl2 = self.currencyNamesSorted
                lvl1 = self.riskFactorsNamesSorted
#            
            parentRf.setTypeInfo('branch')
            for rflvl1 in lvl1:
                
                if rflvl1 in marginalDict:
                    
                    rfNode = riskFactorNode(rflvl1, parentRf)
                    rfNode.setTypeInfo('branch')
                    
                    for rflvl2 in lvl2:
                        
                        if rflvl2 in marginalDict[rflvl1]:
                          
                            rfNode2 = riskFactorNode(rflvl2, rfNode)
                            rfNode2.setTypeInfo('leaf')
                            rfNode2.setExposure([marginalDict[rflvl1][rflvl2], contributionDict[rflvl1][rflvl2]])
                    
            return parentRf
        return False
    
    def sortRiskFactorsNames(self, riskFactorList):
        #Función que genera una lista ordenada para ser usada y presentada en las tablas de factores de riesgo
        riskFactorsNamesAvbl = set(riskFactorList)
        order=['FX','Low Spread','Medium Spread','High Spread','Inflation','KRD 0.5','KRD 1.0','KRD 2.0','KRD 3.0','KRD 5.0','KRD 7.0','KRD 10.0','KRD 20.0','KRD 30.0']
        namesAux = list(set(order).intersection(riskFactorsNamesAvbl))
        
        return sorted(namesAux, key=lambda s:order.index(s))
        
    def closeEvent(self, event):
        reply=QtGui.QMessageBox.question(self,'Message',
                                         "Quitters will always eventually quit.",QtGui.QMessageBox.Yes |
                                         QtGui.QMessageBox.No, QtGui.QMessageBox.No)
        if reply == QtGui.QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()
            
    def keyPressEvent(self, e):     
        if e.key() == QtCore.Qt.Key_Escape: 
            self.close()
            
    def plotExposuresFX(self):
        #Función que se encarga de graficar las posiciones activas
        
        
        factor=0.19
        mainColor=(factor,factor,factor)
        fig=self.mplwidgetExposuresFX.figure
        fig.set_facecolor(mainColor)
        ax=fig.add_subplot(111, axisbg=mainColor)
        ax.hold(False)
        self.mplwidgetExposuresFX.draw()
        ax.tick_params(axis='x',colors='white')
        ax.tick_params(axis='y',colors='white')
        
        #Reseteamos los axes disponibles            
        for axes in fig.get_axes():
            axes.get_xaxis().set_ticks([])
            axes.get_yaxis().set_ticks([])
        
    
        currencies = self.currencyNamesSorted
        width=0.7 #Ancho de las barras
            
        if currencies:
            riskFactorsValues = [self.portActiveRiskByRF['FX'][key] for key in currencies]
            
            #Datos a graficar en las barras verticales
            x=np.arange(len(currencies)) #índice de cada posición activa
            y=riskFactorsValues #Valor de las exposiciones activas  
           
            rects=ax.bar(x,y,width=width, color=(0,0.5,0.7), edgecolor=(0,0.5,0.7))
                        
            ax.set_xticks(x + width/2)
            pylab.setp(ax, xticklabels=currencies)
            
            ax.set_yticks([min(y),max(y)])
            pylab.setp(ax, yticklabels=[round(min(y),0),round(max(y),1)])
            
            self.autolabelVertical(ax,rects,riskFactorsValues)
            #self.zoom_factory(ax)
            fig.tight_layout()                
            
            #ax.set_title(currency)                
            self.mplwidgetExposuresFX.draw()
            portName=str(self.comboBoxPortfolio.currentText())
            self.labelPlotTitleFX.setText(portName + " FX active exposure")
            
#    def plotPerCurrency(self):
#
#        self.plotExposuresPerCurrency()
#        self.plotExposuresPerCurrencyTEMarginal()
#        self.plotExposuresPerCurrencyTEContribution()
        
    def plotPerCurrency(self):
        #Función que se encarga de graficar las posiciones activas
        factor=0.19
        mainColor=(factor,factor,factor)
        
        fig=self.mplwidgetExposures.figure
        fig.set_facecolor(mainColor)
        fig.clf() #Borramos cualquier axe anterior
        
        figMarg=self.mplwidgetExposuresTEMarginal.figure
        figMarg.set_facecolor(mainColor)
        figMarg.clf() #Borramos cualquier axe anterior
        
        figCont=self.mplwidgetExposuresTEContribution.figure
        figCont.set_facecolor(mainColor)
        figCont.clf() #Borramos cualquier axe anterior
        
        ax=fig.add_subplot(111, axisbg=mainColor)
        ax.hold(False)
        ax.tick_params(axis='x',colors='white')
        ax.tick_params(axis='y',colors='white')
        
        axMarg=figMarg.add_subplot(111, axisbg=mainColor)
        axMarg.hold(False)
        axMarg.tick_params(axis='x',colors='white')
        axMarg.tick_params(axis='y',colors='white')
        
        axCont=figCont.add_subplot(111, axisbg=mainColor)
        axCont.hold(False)
        axCont.tick_params(axis='x',colors='white')
        axCont.tick_params(axis='y',colors='white')
        
        self.mplwidgetExposures.draw()
        self.mplwidgetExposuresTEMarginal.draw()
        self.mplwidgetExposuresTEContribution.draw()
        
        #Reseteamos los axes disponibles            
        for axes in fig.get_axes():
            axes.get_xaxis().set_ticks([])
            axes.get_yaxis().set_ticks([])
            
        for axes in figMarg.get_axes():
            axes.get_xaxis().set_ticks([])
            axes.get_yaxis().set_ticks([])
            
        for axes in figCont.get_axes():
            axes.get_xaxis().set_ticks([])
            axes.get_yaxis().set_ticks([])
        
        if self.comboBoxCurrencies.currentIndex()>0:
            currency=str(self.comboBoxCurrencies.currentText())
            
            riskExposure=self.portActiveRiskByCurrency[currency]
            marginalExposure = self.marginalTEByCurrency[currency]
            contributionExposure = self.contributionTEByCurrency[currency]
            
            width=0.7 #Ancho de las barras
            
            
            riskFactorsNamesTotal=[]
            
            riskFactorsNamesAvbl = riskExposure.keys()
            riskFactorsNamesAvblTE = marginalExposure.keys()#self.riskFactorsNamesSorted
            
            if self.checkBoxFX.isChecked():
                riskFactorsNamesTotal.extend(['FX'])
            if self.checkBoxInflation.isChecked():
                riskFactorsNamesTotal.extend(['Inflation'])
            if self.checkBoxSpread.isChecked():
                riskFactorsNamesTotal.extend(['Low Spread', 'Medium Spread', 'High Spread'])
            if self.checkBoxKRD.isChecked():
                riskFactorsNamesTotal.extend(['KRD 0.5','KRD 1.0','KRD 2.0','KRD 3.0','KRD 5.0','KRD 7.0','KRD 10.0','KRD 20.0','KRD 30.0'])
            
            riskFactorsNames = self.sortRiskFactorsNames(list(set(riskFactorsNamesTotal).intersection(riskFactorsNamesAvbl)))
            riskFactorsNamesTE = self.sortRiskFactorsNames(list(set(riskFactorsNamesTotal).intersection(riskFactorsNamesAvblTE)))

            if riskFactorsNames:
                
                riskFactorsValues = [riskExposure[key] for key in riskFactorsNames]
                riskFactorsValuesMarg = [marginalExposure[key] for key in riskFactorsNamesTE]
                riskFactorsValuesCont = [contributionExposure[key] for key in riskFactorsNamesTE]
                
                
                #Datos a graficar en las barras horizontales
                x=np.arange(len(riskFactorsNames)) #índice de cada posición activa
                xMarg=np.arange(len(riskFactorsValuesMarg)) #índice de cada posición activa
                xCont=np.arange(len(riskFactorsValuesCont)) #índice de cada posición activa
                
                y=riskFactorsValues #Valor de las exposiciones activas
                yMarg=riskFactorsValuesMarg #Valor de las exposiciones activas
                yCont=riskFactorsValuesCont #Valor de las exposiciones activas  
               
                rects=ax.barh(x,y,height=width, color=(0,0.5,0.7), edgecolor=(0,0.5,0.7))
                rectsMarg=axMarg.barh(xMarg,yMarg,height=width, color=(0,0.5,0.7), edgecolor=(0,0.5,0.7))
                rectsCont=axCont.barh(xCont,yCont,height=width, color=(0,0.5,0.7), edgecolor=(0,0.5,0.7))
                            
                ax.set_yticks(x + width/2)
                axMarg.set_yticks(xMarg + width/2)
                axCont.set_yticks(xCont + width/2)
                
                pylab.setp(ax, yticklabels=riskFactorsNames)
                pylab.setp(axMarg, yticklabels=riskFactorsNamesTE)
                pylab.setp(axCont, yticklabels=riskFactorsNamesTE)
                
                ax.set_xticks([min(y),max(y)])
                axMarg.set_xticks([min(yMarg),max(yMarg)])
                axCont.set_xticks([min(yCont),max(yCont)])
                
                pylab.setp(ax, xticklabels=[round(min(y),0),round(max(y),1)])
                pylab.setp(axMarg, xticklabels=[round(min(y),0),round(max(y),1)])
                pylab.setp(axCont, xticklabels=[round(min(y),0),round(max(y),1)])
                
                self.autolabel(ax,rects,riskFactorsValues)
                self.autolabel(axMarg,rectsMarg,riskFactorsValuesMarg)
                self.autolabel(axCont,rectsCont,riskFactorsValuesCont)
                #self.zoom_factory(ax)
                fig.tight_layout()
                figMarg.tight_layout() 
                figCont.tight_layout() 
                
                #ax.set_title(currency)                
                self.mplwidgetExposures.draw()
                self.mplwidgetExposuresTEMarginal.draw()
                self.mplwidgetExposuresTEContribution.draw()
                
                portName=str(self.comboBoxPortfolio.currentText())
                self.labelPlotTitle.setText(portName + " exposures for " + currency)
                
#    def plotExposuresPerCurrencyTEMarginal(self):
#        #Función que se encarga de graficar las posiciones activas
#        factor=0.19
#        mainColor=(factor,factor,factor)
#        fig=self.mplwidgetExposuresTEMarginal.figure
#        fig.set_facecolor(mainColor)
#        fig.clf() #Borramos cualquier axe anterior
#        ax=fig.add_subplot(111, axisbg=mainColor)
#        ax.hold(False)
#        ax.tick_params(axis='x',colors='white')
#        ax.tick_params(axis='y',colors='white')
#        self.mplwidgetExposuresTEMarginal.draw()
#        
#        #Reseteamos los axes disponibles            
#        for axes in fig.get_axes():
#            axes.get_xaxis().set_ticks([])
#            axes.get_yaxis().set_ticks([])
#        
#        if self.comboBoxCurrencies.currentIndex()>0:
#            currency=str(self.comboBoxCurrencies.currentText())
#            
#            marginalExposure = self.marginalTEByCurrency[currency]
#            
#            riskExposure = marginalExposure
#            width=0.7 #Ancho de las barras
#            riskFactorsNamesAvbl = riskExposure.keys()#self.riskFactorsNamesSorted
#            riskFactorsNames=[]
#            if self.checkBoxFX.isChecked():
#                riskFactorsNames.extend(list(set(['FX']).intersection(riskFactorsNamesAvbl)))
#            if self.checkBoxInflation.isChecked():
#                riskFactorsNames.extend(list(set(['Inflation']).intersection(riskFactorsNamesAvbl)))
#            if self.checkBoxSpread.isChecked():
#                riskFactorsNames.extend(list(set(['Low Spread', 'Medium Spread', 'High Spread']).intersection(riskFactorsNamesAvbl)))
#            if self.checkBoxKRD.isChecked():
#                order=['KRD 0.5','KRD 1.0','KRD 2.0','KRD 3.0','KRD 5.0','KRD 7.0','KRD 10.0','KRD 20.0','KRD 30.0']
#                namesAux = list(set(\
#                ['KRD 0.5','KRD 1.0','KRD 2.0','KRD 3.0','KRD 5.0','KRD 7.0','KRD 10.0','KRD 20.0','KRD 30.0']).\
#                intersection(riskFactorsNamesAvbl))
#                riskFactorsNames.extend(sorted(namesAux, key=lambda s:order.index(s)))
#                
#            if riskFactorsNames:
#                riskFactorsValues=[riskExposure[key] for key in riskFactorsNames if key in riskFactorsNames]
#                #Datos a graficar en las barras horizontales
#                x=np.arange(len(riskFactorsNames)) #índice de cada posición activa
#                y=riskFactorsValues #Valor de las exposiciones activas                     
#               
#                rects=ax.barh(x,y,height=width, color=(0,0.5,0.7), edgecolor=(0,0.5,0.7))
#                            
#                ax.set_yticks(x + width/2)
#                pylab.setp(ax, yticklabels=riskFactorsNames)
#                
#                ax.set_xticks([min(y),max(y)])
#                pylab.setp(ax, xticklabels=[round(min(y),0),round(max(y),1)])
#                
#                self.autolabel(ax,rects,riskFactorsValues)
#                #self.zoom_factory(ax)
#                fig.tight_layout()                
#                
#                #ax.set_title(currency)                
#                self.mplwidgetExposuresTEMarginal.draw()
##                portName=str(self.comboBoxPortfolio.currentText())
##                self.labelPlotTitle.setText(portName + " exposures for " + currency)
#                
#    def plotExposuresPerCurrencyTEContribution(self):
#        #Función que se encarga de graficar las posiciones activas
#        factor=0.19
#        mainColor=(factor,factor,factor)
#        fig=self.mplwidgetExposuresTEContribution.figure
#        fig.set_facecolor(mainColor)
#        fig.clf() #Borramos cualquier axe anterior
#        ax=fig.add_subplot(111, axisbg=mainColor)
#        ax.hold(False)
#        ax.tick_params(axis='x',colors='white')
#        ax.tick_params(axis='y',colors='white')
#        self.mplwidgetExposuresTEContribution.draw()
#        
#        #Reseteamos los axes disponibles            
#        for axes in fig.get_axes():
#            axes.get_xaxis().set_ticks([])
#            axes.get_yaxis().set_ticks([])
#        
#        if self.comboBoxCurrencies.currentIndex()>0:
#            currency=str(self.comboBoxCurrencies.currentText())
#           
#            contributionExposure = self.contributionTEByCurrency[currency]
#            
#            riskExposure = contributionExposure
#            width=0.7 #Ancho de las barras
#            riskFactorsNamesAvbl = riskExposure.keys()#self.riskFactorsNamesSorted
#            riskFactorsNames=[]
#            if self.checkBoxFX.isChecked():
#                riskFactorsNames.extend(list(set(['FX']).intersection(riskFactorsNamesAvbl)))
#            if self.checkBoxInflation.isChecked():
#                riskFactorsNames.extend(list(set(['Inflation']).intersection(riskFactorsNamesAvbl)))
#            if self.checkBoxSpread.isChecked():
#                riskFactorsNames.extend(list(set(['Low Spread', 'Medium Spread', 'High Spread']).intersection(riskFactorsNamesAvbl)))
#            if self.checkBoxKRD.isChecked():
#                order=['KRD 0.5','KRD 1.0','KRD 2.0','KRD 3.0','KRD 5.0','KRD 7.0','KRD 10.0','KRD 20.0','KRD 30.0']
#                namesAux = list(set(\
#                ['KRD 0.5','KRD 1.0','KRD 2.0','KRD 3.0','KRD 5.0','KRD 7.0','KRD 10.0','KRD 20.0','KRD 30.0']).\
#                intersection(riskFactorsNamesAvbl))
#                riskFactorsNames.extend(sorted(namesAux, key=lambda s:order.index(s)))
#                
#            if riskFactorsNames:
#                riskFactorsValues=[riskExposure[key] for key in riskFactorsNames if key in riskFactorsNames]
#                #Datos a graficar en las barras horizontales
#                x=np.arange(len(riskFactorsNames)) #índice de cada posición activa
#                y=riskFactorsValues #Valor de las exposiciones activas                     
#               
#                rects=ax.barh(x,y,height=width, color=(0,0.5,0.7), edgecolor=(0,0.5,0.7))
#                            
#                ax.set_yticks(x + width/2)
#                pylab.setp(ax, yticklabels=riskFactorsNames)
#                
#                ax.set_xticks([min(y),max(y)])
#                pylab.setp(ax, xticklabels=[round(min(y),0),round(max(y),1)])
#                
#                self.autolabel(ax,rects,riskFactorsValues)
#                #self.zoom_factory(ax)
#                fig.tight_layout()                
#                
#                #ax.set_title(currency)                
#                self.mplwidgetExposuresTEContribution.draw()
                
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
            
    def autolabelVertical(self,ax,rects,labels):
        #Función usada en plotExposures para agregar labels a las barras
        for num,rect in enumerate(rects):
            height=-rect.get_height()
            label=round(labels[num],1)
           
            if (label < 0):        # The bars aren't wide enough to print the ranking inside
                yloc = 0.1*height  # Shift the text to the left side of the right edge
                clr = (1,1,1)      # White on magenta
                align = 'bottom'
            else:
                yloc = 0.1*height  # Shift the text to the left side of the right edge
                clr = (1,1,1)      # White on magenta
                align = 'top'
                
            # Center the text vertically in the bar
            xloc = rect.get_x()+rect.get_width()/2.0
            
            ax.text(xloc,yloc,label,verticalalignment=align,
            horizontalalignment='center', color=clr, weight='bold')
            
#        self.treeWidgetPositions.setHeaderLabels([self.tr('Risk Factor'),self.tr('Exposure')])
#        self.addItemsTree(self.treeWidgetPositions.invisibleRootItem(), self.portActiveRiskDict)
    
#    def addItemsTree(self, root, elements):
#        root.setExpanded(True)
#        
#        if isinstance(elements, dict):
#            for text, children in elements.iteritems():
#                child = QtGui.QTreeWidgetItem()
#                child.setText(0,text)
#                root.addChild(child)
#                self.addItemsTree(child,children)
#        else:# isinstance(children, float):
#            child = QtGui.QTreeWidgetItem()
#            child.setText(0,unicode(elements))
#            root.addChild(child)
                
#    def addItems(self,parent, elements):
#        
#        for text in elements:
#            
#            item = QtGui.QStandardItem(text)            
#            if isinstance(elements[text], dict):
#                parent.appendRow(item)                
#                self.addItems(item, elements[text])
#                
#            elif isinstance(elements[text], float):
#                exposure = QtGui.QStandardItem(str(elements[text]))
#                parent.appendRow([item, exposure])


class riskFactorNode(object):

    def __init__(self, name, parent = None):
        self._name = name
        self._children = []
        self._parent = parent
        self._exposure = []
        self._typeInfo = 'rfNode'
        
        if parent is not None:
            parent.addChild(self)
    
    def setExposure(self, exposure):
        self._exposure = exposure                
        
    def exposure(self, column):
        assert 0 <= column <= len(self._exposure)
        return self._exposure[column]
        
    def typeInfo(self):
        return self._typeInfo
        
    def setTypeInfo(self, typeInfo):
        self._typeInfo = typeInfo
        
    def addChild(self, child):
        self._children.append(child)
        
    def insertChild(self, position, child):
        #Insert child into arbitrary position
        if position < 0 or position > len(self._children):
            return False
        
        self._children.insert(position, child)
        child._parent = self
        
        return True
        
    def removeChild(self, position):
        #Insert child into arbitrary position
        if position < 0 or position > len(self._children):
            return False
        
        child = self._children.pop(position)
        child._parent = None
        
        return True   
        
    def name(self):
        return self._name
        
    def child(self, row):
        return self._children[row]
        
    def childCount(self):
        return len(self._children)
        
    def parent(self):
        return self._parent
        
    def row(self):
        if self._parent is not None:
            return self._parent._children.index(self)
            
    def log(self, tabLevel = -1):
        
        output = ""
        tabLevel +=1
        
        for i in range(tabLevel):
            output += "\t"
            
        output += "|------" + self._name + "--->" + str(self._exposure) + "\n"
        for child in self._children:
            output += child.log(tabLevel)
        
        return output
        
    def __repr__(self):
        return self.log()
 

        
class riskFactorTreeModel(QtCore.QAbstractItemModel):
#Clase para definir el modelo usado en el treeview (TreeView Model)
    """INPUTS: Node, QObject"""
    def __init__(self, root, parent = None):
        super(riskFactorTreeModel, self).__init__(parent)
        self._rootNode = root
        
    """INPUTS: QModelIndex"""
    """OUTPUT: int"""    
    def rowCount(self, parent):
        #Returns the amount of children
        if not parent.isValid():
            parentNode = self._rootNode
        else:
            parentNode = parent.internalPointer()
        
        return parentNode.childCount()
    
    """INPUTS: QModelIndex"""
    """OUTPUT: int"""
    def columnCount(self, parent):
        return 2
    
    """INPUTS: QModelIndex, int"""
    """OUTPUT: QVariant, strings are cast to QString which is a QVariant"""
    def data(self, index, role):
        
        if not index.isValid():
            return None
            
        node = index.internalPointer()
        
        if role == QtCore.Qt.DisplayRole:
            if index.column() == 0:
                return node.name()
            else:
                return node.exposure(index.column()-1)
    
    """INPUTS: int, Qt::Orientation, int"""
    """OUTPUT: QVariant, strings are cast to QString which is a QVariant"""
    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if section == 0:
                return "Risk Factor"
            else:
                return "Exposure"
    
    """INPUTS: QModelIndex"""
    """OUTPUTS: int (flag)"""
    def flag(self, index):
        #Returns if item is selectable or enabled
        return QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        
    
    """INPUTS: QModelIndex"""
    """OUTPUTS: QModelIndex"""
    """Should return the parent of the node with the given QModelIndex"""
    def parent(self, index):
        
        node = index.internalPointer()
#        node = index.getNode(index) #This one also checks if index is valid
        parentNode = node.parent()
        
        if parentNode == self._rootNode:
            return QtCore.QModelIndex()
        
        #We wrap it up on a QModelIndex and return it
        return self.createIndex(parentNode.row(), 0, parentNode)
    
    """INPUTS: int, int, QModelIndex"""
    """OUTPUTS: QModelIndex"""
    """Should return the QModelIndex that corresponds to the given row, column and parent node"""
    def index(self, row, column, parent):
        
#        if not parent.isValid():
#            parentNode = self._rootNode
#        else:
#            parentNode = parent.internalPointer()
        
        parentNode= self.getNode(parent)
        childItem = parentNode.child(row)
        
        if childItem:
            return self.createIndex(row, column, childItem)
        else:
            return QtCore.QModelIndex()
            
    def setData(self, index, value, root, role = QtCore.Qt.EditRole):
        
        if index.isValid():
            
            if role == QtCore.Qt.EditRole:
                
                node = index.internalPointer()
                node.setName(value)
                
                return True
            return False
            
    """CUSTOM (we are not overwriting anything"""
    """INPUTS: QModelIndex"""
    def getNode(self, index):
        if index.isValid():
            node = index.internalPointer()
            if node:
                return node
        return self._rootNode
        
    """INPUTS: int, int, QModeIndex"""
    def insertRows(self, position, rows, parent = QtCore.QModelIndex()):
        #Inserts children into parent at an arbitrary positions
        parentNode = self.getNode(parent)
        self.beginInsertRows(parent, position, position + rows -1) #This handles comunication with the view
        
        for row in range(rows):
            
            childCount = parentNode.childCount()
            childNode = riskFactorNode("untitled" + str(childCount))
            success = parentNode.insertChild(position, childNode)
        
        self.endInsertRows()#This handles comunication with the view
        
        return success
    
    """INPUTS: int, int, QModeIndex"""
    def removeRows(self, position, rows, parent = QtCore.QModelIndex()):
        
        parentNode = self.getNode(parent)
        self.beginRemoveRows(parent, position, position + rows -1)#This handles comunication with the view
        
        for row in range(rows):
            success = parentNode.removeChild(position)
        
        self.endRemoveRows()#This handles comunication with the view
        
        return success

#class TENode(riskFactorNode):
#   
#    def __init__(self, root, parent = None):
#        super(TENode, self).__init__(root, parent)
#        self._marginal = ""
#        self._contribution = ""
#        
#    def setMarginal(self, marginal):
#        self._marginal = marginal
#           
#    def setContribution(self, contribution):
#        self._contribution = contribution
#        
#    def marginal(self):
#        return self._marginal
#        
#    def contribution(self):
#        return self._contribution
#        
#    def log(self, tabLevel = -1):
#        
#        output = ""
#        tabLevel +=1
#        
#        for i in range(tabLevel):
#            output += "\t"
#            
#        output += "|------" + self._name + "--->" + str(self.exposure()) + "\n"
#        for child in self._children:
#            output += child.log(tabLevel)
#        
#        return output
                    
class TETreeModel(riskFactorTreeModel):
    
    def __init__(self, root, parent = None):
        super(TETreeModel, self).__init__(root, parent)  
   
    def columnCount(self, parent):
        return 3
        
    def headerData(self, section, orientation, role):
        if role == QtCore.Qt.DisplayRole:
            if section == 0:
                return "Risk Factor"
            elif section == 1:
                return "Marginal"
            else:
                return "Contribution"
     
    def data(self, index, role):
        
        if not index.isValid():
            return None
            
        node = index.internalPointer()
        
        assert node is not None
        
        if role == QtCore.Qt.DisplayRole:
#            row = index.row()
            column = index.column()
#            try:
#                exposure = node.exposure(column-1)
#            except:
#                print("error")     
            
            if column == 0:
                data = node.name()
#            elif column == 1:
#                return 2#node.marginal()
#            elif column == 2:
#                return 3#node.contribution()#index.column()
            else:
                
                data = ''
                if node.typeInfo() == 'leaf':
                    data = str(round(node.exposure(column-1),5))
#                if exposure:
#                    data = exposure#exposure[0]
            return data
                                
                
def main():
    app = QtGui.QApplication(sys.argv)
    QtGui.QApplication.setStyle('plastique')
    try:
        re = riskExposure()
    except:
        print("Unexpected error:", sys.exc_info()[0])
        sys.exit(app.exec_())
    sys.exit(app.exec_())
    
def mainTreeViewTest():
    app = QtGui.QApplication(sys.argv)
    QtGui.QApplication.setStyle('plastique')
    
    rootNode = riskFactorNode("hips")
    childNode0 = riskFactorNode("LeftPirateLeg", rootNode)
    childNode1 = riskFactorNode("RightPirateLeg", rootNode)
    childNode2 = riskFactorNode("RightFoot", childNode1)
    
    print(rootNode)
    
    model = riskFactorTreeModel(rootNode)
    
    treeView = QtGui.QTreeView()
    treeView.show()
    
    treeView.setModel(model)
    
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()
#    mainTreeViewTest()