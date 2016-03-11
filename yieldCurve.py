# -*- coding: utf-8 -*-
"""
Created on Thu Jan 14 10:27:18 2016

@author: mvillalon
"""

from scipy.optimize import leastsq
# from statsmodels.tsa.ar_model import AR
from statsmodels.tsa.vector_ar.var_model import VAR
#from statsmodels.tsa.stattools import acf
#from statsmodels.tsa.stattools import OLS
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import sqlite3
from datetime import datetime as dtime

class rates(object):
    
    def __init__(self, parameters = pd.DataFrame()):
        
#        self._nsCurve = nelsonSiegel(parameters)
        self._dlCurve = dieboldLi()
        
    def calibrateCurveParametersNS(self, tenors, yields, tau = 1):
        
        self._dlCurve.calibrateParameters(tenors, yields, tau)
    
    def calibrateCurveParametersDL(self, currency = 'USD', tau = 1, lag = 1):
        
        self._dlCurve.calibrateDieboldLi(currency = currency, tau = tau, lag = lag)

    
    def yieldCurve(self, tenors):
        
        return self._dlCurve.nelsonSiegelCurve(tenors)
        
    def shiftYieldCurve(self, parallel = 0, slope = 0, curvature = 0, tau = 0):
"""        Función que genera una nueva yieldCurve en base a los shifts ingresados """
      
        shiftedRates = rates()
        shiftedRates._dlCurve = self._dlCurve.factorShift(parallel = parallel, slope = slope, curvature = curvature, tau = tau)
        
        return shiftedRates
        
        
class spread(object):
    def __init__(self):
        self.spreadParameters = []
        

class nelsonSiegel(object):
    #Clase especializada en calcular una curva basado en los parámetros de N&S, o calibrar sus parámetros en base a los datos
    
    def __init__(self, parameters = None):
        """
        inputs: array
        """
        self._parameters = parameters
        #Los siguientes son los yields y tenores usados para estimar los parámetros de Nelson y Siegel
        self._tenors = None
        self._yields = None

    def nelsonSiegelCurve(self, tenors, parameters = None):
        #A partir de los tenores ingresados entrega los puntos de la curva de tasas para los parámetros ingresados o lo guardados
        """
        inputs: array, list or array
        output: array
        """
        if parameters is None:
            parameters = self._parameters

        if parameters is None:
            print("""There are no parameters calibrated for the curve. Run calibrateParameters first.""")
            return False
              
        b0, b1, b2 = parameters[1:4]
        tau = float(parameters[0])
        
        yc = b0 + b1*(1 - np.exp(-tenors/tau))/(tenors/tau) + b2*((1 - np.exp(-tenors/tau))/(tenors/tau) - np.exp(-tenors/tau))
        
        return yc
        
    def parameters(self):
        """
        output : DataFrame
        """
        return pd.DataFrame([self._parameters], columns = ['tau','b0','b1','b2'])
        
    def nelsonSiegelForwardCurve(self, tenors, parameters = None):
        
        """
        inputs: array, array
        output: DataFrame
        """
        
        if not parameters:
            parameters = self._parameters
        if not parameters:
           return False
        
        b0, b1, b2 = parameters[1:4]
        tau = float(parameters[0])
        
        yc = b0 + b1*np.exp(-tenors/tau) + b2*(-tenors/tau)*np.exp(-tenors/tau)  
        
        return pd.DataFrame(yc)
    
    def slope(self, tenors, parameters = None):
        """
        inputs: array, array
        output: DataFrame
        """
        
        if not parameters:
            parameters = self._parameters
        if not parameters:
           return False
           
        b1 = parameters[2]
        tau = float(parameters[0])
        yc = b1*np.exp(-tenors/tau)
        
        return pd.DataFrame(yc)
        
    def curvature(self, tenors, parameters = None):
        """
        inputs: array, array
        output: DataFrame
        """
        if not parameters:
            parameters = self._parameters
        if not parameters:
           return False
           
        b2 = parameters[3]
        tau = float(parameters[0])
        yc = b2*(-tenors/tau)*np.exp(-tenors/tau)
        
        return pd.DataFrame(yc)
           
    def calibrateParameters(self, tenors, yields, tau = 1):
        
        """
        inputs: array, array, int
        output: array
        """
        x0 = np.array([0.1, 0.1, 0.1])
        param = leastsq(self.nelsonSiegelCurveResiduals, x0, args = (tenors, yields, tau))
        self._tenors = tenors
        self._yields = yields
        self._parameters = [tau] + param[0].tolist()
        
        return np.array(self._parameters)
    
    def nelsonSiegelCurveResiduals(self, p, tenors, yields, tau):
        """
        inputs: array, array, array, int
        output: array
        """
        
        b0, b1, b2 = p
        err = yields - self.nelsonSiegelCurve(tenors, [tau, b0, b1, b2])
        
        return err
        
    def plot(self, tenor = np.array([]), style = 'dark_background'):
        
        with plt.style.context((style)):
            plt.plot(tenor,self.nelsonSiegelCurve(tenor, self._parameters))
            plt.scatter(self._tenors, self._yields)
            plt.title('N&S Calibrated Curve')
        plt.show()
    
    def factorShift(self, parallel = 0, slope = 0, curvature = 0, tau = 0):
        #Función que desplaza la curva para cada factor especificado
        shift = [tau, parallel, slope, curvature]
        parameters = [a + b for a,b in zip(self._parameters, shift)]

        return nelsonSiegel(parameters = parameters)
        
        
class dieboldLi(nelsonSiegel):

    def __init__(self, parameters = None):
        super(dieboldLi, self).__init__(parameters = parameters)
        self._parametersHistorical = None
        self._tenorsHistorical = None
        self._yieldsHistorical = None
        
    def parametersHistorical(self):
        return pd.DataFrame(self._parametersHistorical, columns = ('tau','b0','b1','b2'), index = pd.to_datetime(self._dates))
        
    def calibrateParametersHistorical(self, tenors, yields, tau = 1):
        """
        inputs: array, array, float
        output: DataFrame
        """
        
        yieldCurve = zip(tenors, yields)
        param= []
        x0 = np.array([0.1, 0.1, 0.1])
        
        for t,y in yieldCurve:
            
            x0 = leastsq(self.nelsonSiegelCurveResiduals, x0, args = (t, y, tau))
            x0 = x0[0]
            param.append([tau] + x0.tolist())
            
        self._tenorsHistorical = tenors
        self._yieldsHistorical = yields
        self._parametersHistorical = param
        
        return param
    
    def getHistoricalYields(self, currency):
        """
        inputs: str
        output: DataFrame
        """
        path = 'G:/DAT/GII/MES_INT/INVINTER/Matlab Programas/packagePY/DB/riskFactors.db'
        
        with sqlite3.connect(path) as con:
            cur = con.cursor()
            
            cur.execute("""CREATE TEMP TABLE TEMPDATA AS 
            SELECT DATE, IDENTIFIER, DATA FROM rfData
            WHERE IDENTIFIER IN 
            (SELECT IDENTIFIER FROM rfClasification WHERE CURRENCY = ? AND NAME IN
            (SELECT NAME FROM rfNameExposures WHERE TYPE = 'Curve')
            )""", (currency,))
            
            cur.execute("""SELECT a.DATE, c.TENOR, a.DATA FROM
            TEMPDATA a,
            rfClasification b,
            rfNameExposures c
            WHERE a.IDENTIFIER = b.IDENTIFIER AND b.NAME = c.NAME
            ORDER BY a.DATE, c.TENOR""")
            
            dataTmp = cur.fetchall()
        
        yieldCurveRaw = pd.DataFrame(dataTmp, columns = ['date', 'tenor', 'yield'])
        yieldCurve = yieldCurveRaw.pivot(index = 'date', columns = 'tenor', values = 'yield')

        return yieldCurve
        
    def parametersAR(self, lag = 1):
#        OLS(self.parametersHistorical()['b0'], self.parametersHistorical()['b0'][])
#        self._arModel = (AR(self.parametersHistorical()['b0']).fit(lag), AR(self.parametersHistorical()['b1']).fit(lag), AR(self.parametersHistorical()['b2']).fit(lag))
        self._varModel = VAR(self.parametersHistorical()[['b0', 'b1', 'b2']]).fit(lag)
        self._varModel.summary()
        return True
    
    def calibrateDieboldLi(self, currency = 'USD', tau = 1, lag = 1):
        
        yieldCurve = self.getHistoricalYields(currency)
        tenors = [yieldCurve.columns.tolist()] * len(yieldCurve)
        yields = yieldCurve.values.tolist()
        self.calibrateParametersHistorical(np.array(tenors), np.array(yields), tau = tau)
        self._dates = [dtime.strptime(datestr,"%Y-%m-%d").date() for datestr in yieldCurve.index]
        self.parametersAR(lag = lag)
        self._currency = currency
        
        
    def setNSParameters(self, position = -1):
        
        self._parameters = self._parametersHistorical[position]
        self._tenors = self._tenorsHistorical[position]
        self._yields = self._yieldsHistorical[position]
        
    def forecastDLParameters(self, initialParameters = None, steps = 1, alpha = 0.05):
        #Función que proyecta parámetros Diebold Li a futuro
        """
        inputs : array, int
        output: array
        """
        assert not isinstance(self._varModel, VAR), "Theres no model yet. Run calibrateDieboldLi first"
        
        if initialParameters is None:
            initialParameters = self._parameters
            
        parameters = np.array([initialParameters[1:4]])
        
        return self._varModel.forecast_interval(parameters, steps, alpha = alpha), initialParameters
     
    def plotForecastedCurve(self, tenor, initialParameters = None, steps = 1, alpha = 0.05, style = 'dark_background', error = True):
        #Función que grafica forecast de curva, junto con error
        forecast, initialParameters = self.forecastDLParameters(initialParameters = initialParameters, steps = steps, alpha = alpha)
        
        baseParameter = initialParameters
        fcParameter = [baseParameter[0]] + forecast[0][-1].tolist()
        topParameter = [baseParameter[0]] + forecast[1][-1].tolist()
        bottomParameter = [baseParameter[0]] + forecast[2][-1].tolist()
        
        with plt.style.context(style, after_reset = True):
            plt.plot(tenor,self.nelsonSiegelCurve(tenor, baseParameter), linewidth = 2.0)
            plt.plot(tenor,self.nelsonSiegelCurve(tenor, fcParameter), 'w.')
            if error:
                plt.plot(tenor,self.nelsonSiegelCurve(tenor, topParameter), 'w--')
                plt.plot(tenor,self.nelsonSiegelCurve(tenor, bottomParameter), 'w--')
                plt.text(0.2, 0.7, """$\\alpha$ = %s"""%alpha, transform =  plt.gca().transAxes)   
                
            plt.ylabel('%')
            plt.title('%s Months Projection for %s calibrated curve'%(str(steps),self._currency))
                 
        plt.show()
        
if __name__ == '__main__':
    ns = nelsonSiegel(np.array([1, 0.2, -0.2, 0.2]))
#    yc = ns.nelsonSiegelCurve(np.array([1, 2, 3]))
#    plt.plot(yc)
    tau = 10
    param = ns.calibrateParameters(np.array([1,3,5,10,30]), np.array([0.5, 0.75, 1, 2.1, 2.5]), tau = tau)
    tenor = np.array(range(1,30))
#    ns.plot(tenor)
#    ns2 = ns.factorShift(parallel = 0.1)
#    ns2.plot(tenor, style = 'ggplot')
#    
#    ns3 = ns2.factorShift(slope = 0.1)
###    ns3.plot(tenor)
#    
#    dl = dieboldLi()
##    tenor, yields = dl.getHistoricalYields('USD')
#    dl.calibrateDieboldLi('EUR', tau = tau, lag = 1)
#    dl.setNSParameters()
##    dl.plot(tenor)
#    #Efecto de respuesta impulso a 2 años frente a un movimiento en los factores:
##    dl._varModel.irf(24).plot()
#    
#    forecast = dl.forecastDLParameters(steps = 1)
#    
#    dl.plotForecastedCurve(tenor, steps = 6, alpha = 0.5, error = True, style =['dark_background'] )
#    
#    
