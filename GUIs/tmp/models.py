# -*- coding: utf-8 -*-
"""
Created on Wed Sep 09 17:00:32 2015

@author: mvillalon
"""

import sys
from PyQt4 import QtGui, uic 


class modeling(QtGui.QDialog):
    def __init__(self):
        super(modeling,self).__init__()
        uic.loadUi('models.ui',self)
        self.show()
        
def main():
    app = QtGui.QApplication(sys.argv)
    modelLoaded=modeling()
    sys.exit(app.exec_())
    
if __name__ == '__main__':
    main()