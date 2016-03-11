# -*- coding: utf-8 -*-
"""
Created on Wed Sep 09 10:18:18 2015

@author: mvillalon
"""
import sys
from PyQt4 import QtGui, uic
from portfolioManager import portfolioManaging
from riskExposure import riskExposure
from models import modeling


class mainPortfolioAnalytics(QtGui.QMainWindow):
    
    def __init__(self):
        super(mainPortfolioAnalytics,self).__init__()
        uic.loadUi('mainPortfolioAnalytics.ui',self)        
        self.pushButtonPM.clicked.connect(self.openPM)
        self.pushButtonRE.clicked.connect(self.openRE)
        self.pushButtonMod.clicked.connect(self.openMod)
        self.show()
            
    def openPM(self):        
        self.portfolioManager=portfolioManaging()
    def openRE(self):        
        self.riskExposre=riskExposure()       
    def openMod(self):        
        self.model=modeling()       

        
def main():
    app = QtGui.QApplication(sys.argv)
    QtGui.QApplication.setStyle('plastique')
    mainPort = mainPortfolioAnalytics()
    sys.exit(app.exec_())
    
    
if __name__ == '__main__':
    main()