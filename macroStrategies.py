# -*- coding: utf-8 -*-
"""
Created on Tue Jan 12 15:49:57 2016

@author: mvillalon
"""
from datetime import date as dt, timedelta as td
import yieldCurve as yc
#import FXClas as fx





class scenario(object):
    #scenario corresponde a nodo que pueden ser conectados en cadena, y que adicionalmente pueden ser padres de otros subnodos
    def __init__(self, parent = None, name = None):
        
        self._parent = parent
        self._name = name
        self._previous = None
        self._next = None
        self._children = []
        
        if parent is not None:
            parent.addChild(self)
            
    def iter(self):
        #Función usada cuando se requiere iterar sobre los scenarios linkeados
        a = self
        yield a
        while a._next:
            a = a._next
            yield a
            
    def disconnect(self):
        #Función que desconecta nodo de la cadena
        if self._previous:
            self._previous._next = self._next
            
        if self._next:
            self._next._previous = self._previous
        
        self._previous = None
        self._next = None
            
        return self
                        
    def set_previous(self, scenario):
        #Si hay un escenario anterior, tengo que linkear el nuevo escenario entremedio      
        if self._previous:
            scenario._previous = self._previous
            self._previous._next = scenario
            
        self._previous = scenario
        scenario._next = self
       
    def set_next(self, scenario):
        #Si hay un escenario posterior, tengo que linkear el nuevo escenario entremedio      
        if self._next:
            scenario._next = self._next
            self._next._previous = scenario
            
        self._next = scenario 
        scenario._previous = self
        
    def get_next(self):
        return self._next
        
    def get_previous(self):
        return self._previous
        
    def addChild(self, child):
        
        self._children.append(child)        

    def child(self, row):
        return self._children[row]
        
    def removeChild(self, position):
        
        if position < 0 or position > len(self._children): 
            return False
        
        child = self._children.pop(position)
        child._parent = None
        
    def log(self, tabLevel = -1):
        
        output = ""
        tabLevel +=1
        
        for i in range(tabLevel):
            output += "\t"
            
        output += "|------" + self.name() + "\n"        
        
        for child in self._children:
            output += child.log(tabLevel)
        
        return output
        
    def __repr__(self):
        return self.log()    
        
    def name(self):
        return str(self._name)
        
    def childCount(self):
        return len(self._children)
    
    def to_list(self):
        
        scenarioList = []
        [scenarioList.append(s) for s in self.iter()]
        return scenarioList
    
        
class yieldCurve_scenario(scenario):
    #Scenario especializado para curvas de tasas
    def __init__(self, parent = None, name = None, date = dt.today()):
        
        super(yieldCurve_scenario, self).__init__(parent = parent, name = name)    
        self._date = date
        self._rates = yc.rates()
#        self._fx = fx.fx()
#        self._spread = yc.spread()
    
    def name(self):
        return str(self._name) + ' ' + str(self._date)
        
    def setYieldCurveFromYields(self, tenors, yields, tau = 1):
        
        self._rates.calibrateCurveParametersNS(tenors, yields, tau = tau)

    def shiftFactorsScenario(self, parallel = 0, slope = 0, curvature = 0, tau = 0, fx = 0, spread = 0, date = None):
        #Genera un nuevo escenario con factores modificados
        
        if not date:
            date = self._date
        newScenario = yieldCurve_scenario()
        
        
        newRates = self._rates.shiftYieldCurve(parallel = parallel, slope = slope, curvature = curvature, tau = tau)
        newScenario._rates = newRates
        ################################################################
        ####INSERT ADITIONAL CODE HERE FOR UPDATING THE OTHER MACRO FACTORS (FX, SPREAD, ETC)###
        
        ################################################################        
        
        newScenario._date = date
        newScenario._name = self._name
        
        return newScenario
        
    def createAndAppendScenario(self, where = 'next', parallel = 0, slope = 0, curvature = 0, tau = 0, fx = 0, spread = 0, date = None, days = None):
        #Genera nuevo scenario a partir del actual, y lo agrega antes o despues.
        assert where.upper() in ('NEXT', 'PREVIOUS'), """Input 'where' should be either 'next' or 'previous'"""
        
        if not date:
            if days:
                date = self._date + td(days=days)
           
        newScenario = self.shiftFactorsScenario(parallel = parallel, slope = slope, curvature = curvature, tau = tau, fx = fx, spread = spread, date = date)
        
        if where.upper() == 'NEXT':
            self.set_next(newScenario)
        elif where.upper() == 'PREVIOUS':
            self.set_previous(newScenario)
            
        return newScenario
        
    def plot(self):
        
        tenors = yc.np.array([1,3,5,7,10,20,30])
        self._rates._dlCurve.plot(tenors)
        
    
    def rates(self):
        
        return self._rates

















        
class scenarioModel(object):
    #Modelo sobre el que se linkea y trabaja con scenarios

    def __init__(self, root):
       self._root = root
       
    def __str__(self):
       return(str(self._root.to_list()))
       
    def getScenario(self, position):
        """
        input: int
        output: scenario
        """         
        scenarioList = self._root.to_list()    
        return scenarioList[position]
        
    def insertScenario(self, position, scenario):
        
        self.getScenario(position).set_previous(scenario)
    
    def appendScenario(self, scenario):
        
        lastScenario = self._root.to_list()[-1]
        lastScenario.set_next(scenario)
        
class yieldCurveScenarioModel(scenarioModel):
    
    def __init__(self, root):
        """
        input: macro_scenario
        """
        #Este será el nodo raíz de cualquier modelo
        assert isinstance(root, yieldCurve_scenario), 'Root must be a macro_scenario object'
        super(yieldCurveScenarioModel, self).__init__(root)
    
    def yieldCurveHistorical(self, tenors):
        
        yc = {}
        for scenario in self._root.iter():       
            yc[scenario._date] = scenario.rates().yieldCurve(tenors)
            
        return yc
   

        
if __name__ == '__main__':
    
#    s1 = scenario()
#    s1next = scenario()
#    s1.set_next(s1next)
#    s2 = scenario(s1)
#    s3 = scenario(s1)
#    s4 = scenario(s3)
#    s5 = scenario(s1next)
#    
#    for i in s1.iter():
#        print(i)
    
    #Definimos un escenario macro con el nombre 'USD'    
    ms1 = yieldCurve_scenario(name = 'US')
    
    #Agregamos una curva de tasas de interés a partir de los datos para hoy    
    tenors = yc.np.array([1, 2, 3, 5, 10, 30])
    yields= yc.np.array([0.482, 0.836, 1.070, 1.426, 2.018, 2.9])
    ms1.setYieldCurveFromYields(tenors, yields, tau = 10)
    
    #Podemos graficar el estado actual de los factores
#    ms1.plot()
    
    #Agregamos un nuevo escenario linkeado proyectando una subida paralela de 1% en las tasas a un año:
    ms1.createAndAppendScenario(parallel = 1, days = 365)
    
    msFinal = ms1._next
    
    #Insertamos un escenario antes del final
    msFinal.createAndAppendScenario(where = 'previous', parallel = -0.5, days = -180)
    
#    msMitad = msFinal._previous
#    newMs1 = ms1.shiftFactorsScenario(parallel = 1)    
#    newMs1.plot()
    
    model = yieldCurveScenarioModel(ms1)
    
    
    