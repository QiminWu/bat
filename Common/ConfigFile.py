#
#             Semantic of config file entries
#
import os
import platform

WINDOWS = (platform.system() == 'Windows')

from ConfigParser import SafeConfigParser

#      Imports from Common

import Globals                     # Own global data
import Basic                       # Own module with basic functions
import Logfile                     # Implements logfile

# -------------------------------------------------------------------------------------------------

class ConfigObj (object):

    def __init__ (self, fileName=None, dict=None) :
        self._fileName = fileName
        self._dict     = dict
        self._debug    = False

    def __getitem__ (self, key) :
        return self._dict.__getitem__ (key)


    def getDict (self) :      return self._dict
    def setDict (self,d) :    self._dict = d

    def getFileName (self) :  return self._fileName
    
    # --------------------------------------------------------------------------------------------

    def Str (self, key, default=None) :
        return self.String (key, default)                # zur Verkuerzung von Ausdruecken

    def String (self, key, default=None) :

        if key in self._dict : s = self._dict [key]
        elif default != None : s = default
        else :                 self._keyMissing (key)

        if self._debug : print 'cfg [' + key + '] = ' + s

        return s

    def Int (self, key, default=None) :

        if default != None : val = self._checkIntNumber (key, default)
        else :               val = None

        s = self.String (key, val)
        return self._checkIntNumber (key, s)

    def UInt (self, key, maxVal=None, default=None) :

        assert default == None or default >= 0
        val = self.Int (key, default)

        if val < 0 :                         self._error (key, str(val) + ' < 0')
        if maxVal != None and val > maxVal : self._error (key, str(val) + ' > ' + str(maxVal))

        return val

    def Float (self, key, default=None) :

        if default != None : val = self._checkFloatNumber (key, default)
        else :               val = None

        s = self.String (key, val)
        return self._checkFloatNumber (key, s)


    def UFloat (self, key, maxVal=None, default=None) :

        assert default == None or default >= 0.0
        val = self.Float (key, default)

        if val < 0.0 :                       self._error (key, str(val) + ' < 0.0')
        if maxVal != None and val > maxVal : self._error (key, str(val) + ' > ' + str(maxVal))
        
        return val


    def Bool (self, key, default=None) :

        val = self.Int (key, default)

        if val == 0 : return False
        if val == 1 : return True

        self.rangeError (key, '0','1')

    def IntRange (self, key1, key2) :

        a = self.Int (key1)
        b = self.Int (key2)

        if a > b : self.rangeError2 (key1,key2)

        return a,b


    def FloatRange (self, key1, key2) :

        a = self.Float (key1)
        b = self.Float (key2)

        if a > b : self.rangeError2 (key1,key2)

        return a,b

    # ---------------------------------------------------------------------------------------------

    def Distance (self, key, maxVal = 40 * 1000) : return self.UFloat (key, maxVal)
    def Freq     (self, key, maxVal = 1000) :      return self.UFloat (key, maxVal)
    def Duration (self, key='duration') :          return self.UFloat (key)
    def Time     (self, key='time') :              return self.String (key)

    def lat    (self) :       return self.Float ('lat')        # ??? range einbauen
    def lon    (self) :       return self.Float ('lon')        # ???
    def depth  (self) :       return self.Float ('depth')      # ???

    def dimX   (self) :       return self.UInt ('dimx')
    def dimY   (self) :       return self.UInt ('dimy')
    def winlen (self) :       return self.UInt ('winlen')
    def step   (self) :       return self.UInt ('step')

    def newFrequency (self)  : return self.Freq ('new_frequence')

    # ---------------------------------------------------------------------------------------------

    def _error0 (self,msg) :

        Logfile.error (msg)
        Logfile.abort ()    

    def _error (self, key,msg) : self._error0 (self.getFileName() + ',' + key + ' : ' + msg)

    def _checkFloatNumber (self, key, s) :

        if not Basic.isNumber (s) : self._error (key, 'Key is not a number')
        return float (s)

    def _checkIntNumber (self, key, s) :

        if not Basic.isNumber (s) : self._error (key, 'Key is not a number')
        if not Basic.isInt (s) :    self._error (key, 'Key is not integer number')

        return int (s)

    def _keyMissing (self, key) :      self._error  (key, 'Key missing')  
    def rangeError  (self, key, a,b) : self._error  (key, 'Value outside [' + a + ',' + b + ']')
    def rangeError2 (self, key1,key2): self._error0 ('Range error : ' + key1 + ' > ' + key2) 

#endclass ConfigObj

# -------------------------------------------------------------------------------------------------

class FilterCfg (ConfigObj) :

    def __init__  (self, dict) :   ConfigObj.__init__ (self, None, dict) 
    
    
    def newFrequency (self) : return self.Freq ('new_frequence')
    def filterswitch (self) : return self.UInt ('filterswitch', 3)        # filter

    def flo (self) :          return self.Freq ('flo')                    #    bandpass
    def fhi (self) :          return self.Freq ('fhi')
    def ns  (self) :          return self.Freq ('ns')

    def l_fc (self) :         return self.Freq ('l_fc')                   #    lowpass
    def l_ns (self) :         return self.Freq ('l_ns')

    def h_fc (self) :         return self.Freq ('h_fc')                   #    highpass
    def h_ns (self) :         return self.Freq ('h_ns')

    def filterName (self) :

        i = self.filterswitch()

        if   i == 0 : return None
        if   i == 1 : strings = [str (self.flo()),  str (self.fhi()),  str (self.ns()), self.Str('zph')]
        elif i == 2 : strings = [str (self.l_fc()), str (self.l_ns()), self.Str('l_zph')]
        elif i == 3 : strings = [str (self.h_fc()), str (self.h_ns()), self.Str('h_zph')]

        name    = '_'.join (strings)
        return name

#endclass

def filterName (dict) :

    cfg = FilterCfg (dict)
    return cfg.filterName ()

# -------------------------------------------------------------------------------------------------

class OriginCfg (ConfigObj) :

    def __init__  (self, dict) :   ConfigObj.__init__ (self, None, dict) 

    def strike (self, def1) : return self.Float  ('strike', def1)
    def dip    (self, def1) : return self.Float  ('dip',    def1)
    def rake   (self, def1) : return self.Float  ('rake',   def1)
    def time   (self)       : return self.String ('time')

#endclass

# -------------------------------------------------------------------------------------------------

DEFAULT_CONFIG_FILE = 'global.conf'
    
#
#       Keys for global.conf
#
blacklist     = 'blacklist'   
duration      = 'duration'
keyfilefolder = 'keyfilefolder'

mail          = 'mail'
mindist       = 'mindist'
maxdist       = 'maxdist'

metaCatalog   = 'metacatalog'
pwd           = 'pwd'


class GlobalConfigObj (ConfigObj):

    def __init__(self, fileName) :

        if fileName == None : name = DEFAULT_CONFIG_FILE
        else :                name = fileName

        ConfigObj.__init__ (self, name, readConf (os.path.join ('..', name)))

#endclass

_globConfigObj = None

def GlobCfg () :  return _globConfigObj

def readGlobalConf (fileName) :
    global  _globConfigObj

    _globConfigObj = GlobalConfigObj (fileName)
    return _globConfigObj.getDict()

# -------------------------------------------------------------------------------------------------

def readConf (fileName):

    if not Basic.checkFileExists (fileName) : return None

    cDict  = {}
    parser = SafeConfigParser()
    parser.read (fileName)
    
    isClient = Globals.isClient

    if not isClient :
       Logfile.setVisible (False)
       Logfile.add (' ',fileName, ' : ')

    Logfile.setErrorLog (True)

    for section_name in parser.sections() :
        for name, value in parser.items (section_name) :
            cDict [name]=value

            if not isClient :
               if name != 'mail' and name != 'pwd' :
                  Logfile.add (name + ' = ' + value)
            #endif
    #endfor

    if not isClient :
       Logfile.add (' ')
       Logfile.setVisible (True)

    Logfile.setErrorLog (False)
    return cDict

# -------------------------------------------------------------------------------------------------

def checkKeys (conf, keyList, optional=False) :

    if type (keyList) is str : list1 = list (keyList)
    else :                     list1 = keyList


    #Logfile.add (' ', 'Check config file :', ' ')

    if not optional :
       Basic.checkExistsKeys (conf, list1, isAbort=True)

    eventDir = Globals.EventDir()
    #print 'eventdir = ', eventDir
    isOk     = True

    for key in list1 :
        val = conf [key]
        msg = None

        if   key == duration :                     msg = Basic.checkGreaterZero (val)
        elif key in [mindist, maxdist] :           msg = Basic.checkNotNegative (val)
        elif key in [keyfilefolder, metaCatalog] : Basic.checkExistsDir (os.path.join (eventDir, val), isAbort=True)
        elif key in [blacklist, mail, pwd] :       continue

        if msg != None : 
           isOk = Logfile.error ('Key <' + key +'> in config file : ' + msg)

    #endfor

    if not isOk : Logfile.abort ()
    return True

