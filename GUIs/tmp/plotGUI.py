# -*- coding: utf-8 -*-
"""
Created on Fri Jul 31 11:30:08 2015

@author: mvillalon
"""
# -*- coding: utf-8 -*-


from PyQt4 import QtCore, QtGui, uic
from guiqwt.builder import make
import numpy as np
import sys
#import plot

class myGui(QtGui.QDialog):#, plot.Ui_Form):
    """
    myGui is inherited from both QtGui.QDialog and test.Ui_Dialog
    """    
    def __init__(self, parent=None):
        QtGui.QDialog.__init__(self)
        #super(myGui,self).__init__(parent)
        uic.loadUi("plot.ui",self)
        
        self.pushButtonPlot.clicked.connect(self.texto)
        self.pushButtonPlot.clicked.connect(self.plot)
        #self.setupUi(self)
        #self.connectActions()
    def main(self):
        self.show()
    def texto(self):
        self.labelTextoPrueba.setText('apretaste el boton')
    def plot(self):
        
        self.t = np.linspace(0, 80, 400)        
        self.y = np.sin(2 * np.pi * self.t / 10.)
        self.curvewidget.get_plot().add_item(make.curve(self.t,self.y))        
        
    def connectActions(self):
        pass
    
    
if __name__=="__main__":
    app=QtGui.QApplication(sys.argv)
    myGuiObj=myGui()
    myGuiObj.main()
    app.exec_()
    #sys.exit(app.exec_())
        
