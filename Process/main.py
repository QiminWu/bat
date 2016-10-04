
import os
import sys
import platform

WINDOWS = (platform.system() == 'Windows')
                
import logging
import shutil
import time
import multiprocessing
from   optparse import OptionParser    
import cPickle  as pickle

# add local directories to import path

sys.path.append ('../tools/')                     
sys.path.append ('../Common/')

#       Import from common

import  Basic
import  Globals
import  Logfile
import  Debug
from    Program    import MainObj
import  ConfigFile
from    ConfigFile import ConfigObj, FilterCfg, OriginCfg 

#       Import from Tools

import config
from   config import Event,Trigger

#       Import from Process

from    Version  import  VERSION_STRING

import  deserializer
import  filterStation
import  ttt
import  sembCalc
import  waveform
import  times

#from   xcorrfilter import Xcorr
from    array_crosscorrelation_v4  import Xcorr, cmpFilterMetavsXCORR, getArrayShiftValue

import semp

# -------------------------------------------------------------------------------------------------

logger = logging.getLogger(sys.argv[0])
logger.setLevel(logging.DEBUG)

#formatter = logging.Formatter ("%(asctime)s - %(name)s - %(levelname)s - %(message)s")  #hs
formatter  = logging.Formatter ("%(message)s")

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)

logger.addHandler(ch)

# --------------------------------------------------------------------------------------------------

evpath  = None

def initModule () :

    global  evpath

    parser = OptionParser(usage="%prog -f Eventpath ")
    parser.add_option ("-f", "--evpath", type="string", dest="evpath", help="evpath")

    (options, args) = parser.parse_args()

    if options.evpath == None:
       parser.error ("non existing eventpath")
       return False

    evpath = options.evpath
    Globals.setEventDir (evpath)
    return True

# --------------------------------------------------------------------------------------------------

def processLoop () :
    
    #==================================get meta info==========================================
    C      = config.Config (evpath)
    Origin = C.parseConfig ('origin')
    Config = C.parseConfig ('config')
    Meta   = C.readMetaInfoFile()
    #==================================get meta info==========================================
    
    #==================================do prerequiries========================================
    Folder = C.createFolder()

    C.cpSkeleton  (Folder,Config)
    C.writeConfig (Config,Origin,Folder)
    
    cfg    = ConfigObj (dict=Config) 
    filter = FilterCfg (Config)
    origin = OriginCfg (Origin)

    ntimes  = int ((cfg.UInt ('forerun') + cfg.UInt ('duration') ) / cfg.UInt ('step') )

    default = 0
    strike  = origin.strike (default)        # Origin.get ('strike', default)
    dip     = origin.dip    (default)        # Origin.get ('dip',    default)
    rake    = origin.rake   (default)        # Origin.get ('rake',   default)
    
#   ev = Event (Origin['lat'],Origin['lon'],Origin['depth'],Origin['time'],
#               strike = strike,dip=dip,rake=rake)
    ev = Event (origin.lat(), origin.lon(), origin.depth(), origin.time(),  
                strike = strike,dip=dip,rake=rake)

    filtername = filter.filterName()  
    Logfile.add ('filtername = ' + filtername)

    #todo crosscorrelation for all arrays before processing

    XDict   = {}
    RefDict = {}
    SL      = {}

    if cfg.Int ('xcorr') == 1:
        
        newFreq                = str (filter.newFrequency())
        fobjreferenceshiftname = newFreq + '_' + filtername + '.refpkl'
        rp                     = os.path.join (Folder['semb'], fobjreferenceshiftname)
        fobjpickleshiftname    = newFreq + '_' + filtername + '.xcorrpkl'
        ps                     = os.path.join (Folder['semb'], fobjpickleshiftname)

        if (os.path.isfile(rp) and os.path.getsize(rp) != 0 and os.path.isfile(ps) and os.path.getsize(ps) != 0):
            Logfile.add ('file exits : ' + rp)
            Logfile.add ('load refshifts')

            f             = open(rp)
            RefDict       = pickle.load(f)
            x             = open(ps)
            XDict         = pickle.load(x)
           #xcorrnetworks = Config['networks'].split(',')
            xcorrnetworks = cfg.String ('networks').split(',')

            for i in xcorrnetworks:
                SL[i] = len (Config[i].split('|'))
        else:
            SL = {}
            xcorrnetworks = cfg.String ('networks').split(',')

            for i in xcorrnetworks:
            
                W = {}
                refshift    = 0
                network     = cfg.String(i).split('|')
                FilterMeta  = ttt.filterStations (Meta,Config,Origin,network)
                arrayfolder = os.path.join (Folder['semb'],i)

                if os.access (arrayfolder,os.F_OK) == False:
                   os.makedirs(arrayfolder)
            
                A = Xcorr (ev,FilterMeta,evpath,Config,arrayfolder)
                W,triggerobject = A.runXcorr()
                
                XDict[i]   = W
                RefDict[i] = triggerobject.tdiff
                SL[i]      = len(network)
            #endfor

            fobjrefshift = open (rp,'w')
            pickle.dump (RefDict,fobjrefshift)
            fobjrefshift.close()
        
            output = open (ps, 'w')
            pickle.dump (XDict, output)
            output.close()
        #endif
        
        for i in sorted (XDict.iterkeys()) :
            Logfile.red ('Array %s has %3d of %3d Stations left' % (i,len(XDict[i]),SL[i]))

        logger.info ('\033[31mFor proceeding without changes press enter or give new comma seperatet network list or quit for exit\033[0m')

        while True :
           nnl = raw_input ("please enter your choice: ")
           #Logfile.add ('Choise = ' + nnl)

           if len(nnl) == 0:
              if not Basic.question ('Process all networks ?') : continue

              Logfile.red ('This networks will be used for processing: %s' % (Config['networks']))
              break

           elif str(nnl) == 'quit':
               sys.exit()

           elif str(nnl) == 'rerun':
               event = os.path.join (*evpath.split('/')[-1:])

               try:
                   os.remove(rp)
                   os.remove(ps)

               except : pass

               mainfolder = os.path.join (os.path.sep,*evpath.split('/')[:-2])
               os.chdir (mainfolder)

               cmd = ('%s arraytool.py process %s') % (sys.executable,event)
               Logfile.add ('cmd = ' + cmd)
               os.system   (cmd)
               sys.exit()

           else:
               # Check if selected array(s) exists

               names = nnl.split (',')
               isOk  = True

               for array in names :
                   arrayfolder = os.path.join (Folder['semb'], array)
               
                   if not os.path.isdir (arrayfolder) :
                      Logfile.error ('Illegal network name ' + str(array))
                      isOk = False
                      break
               #endfor

               if not isOk :  continue   # Illegal network : input again
 
               # use these networks

               Logfile.add ('This networks will be used for processing: %s' % (nnl))
               Config ['networks'] = nnl
               break
           #endif
        #endwhile True

        for i in range(3,0,-1):
            time.sleep(1)
            Logfile.red ('Start processing in %d seconds ' % (i))
        #endfor
 
    #print XDict
    #print RefDict
    
    #TriggerOnset.append(triggerobject)
    #print 'MAINTDIFF ',triggerobject.tdiff
    
    #sys.exit()
    
    wd = Origin['depth']    
    start,stop,step = cfg.String ('depths').split(',')

    start = int(start)
    stop  = int(stop)+1
    step  = int(step)

    Logfile.add ('working on ' + Config['networks'])

    #==================================loop over depth=======================================
    for depthindex in xrange(start,stop):

        workdepth = float(wd) + depthindex * step
        Origin['depth'] = workdepth
        
        ev = Event (Origin['lat'],Origin['lon'],Origin['depth'],Origin['time'],
                    strike = strike,dip=dip,rake=rake)
        Logfile.add ('WORKDEPTH: ' + str (Origin['depth']))

        #==================================do prerequiries========================================

        #==================================loop over arrays=======================================
        ASL          = []
        networks     = Config['networks'].split(',')
        counter      = 1
        TriggerOnset = []
        
        for i in networks:
        
            arrayname = i
            arrayfolder = os.path.join (Folder['semb'],arrayname)
            
            network = Config[i].split('|')
            Logfile.add ('network: ' + str (network))
            
            FilterMeta = ttt.filterStations (Meta,Config,Origin,network)
            
            #if len(FilterMeta) < 3: continue              #hs : wieder rein
            if len(FilterMeta)  < 3: continue

            W = XDict[i]
            refshift = RefDict[i]
            
            FilterMeta = cmpFilterMetavsXCORR (W, FilterMeta)       
            #print 'W: ',W,len(W); print refshift; print 'FM ',FilterMeta,len(FilterMeta)
            
            Logfile.add ('BOUNDING BOX DIMX: %s  DIMY: %s  GRIDSPACING: %s \n'
                         % (Config['dimx'],Config['dimy'],Config['gridspacing']))

            ##############=======================PARALLEL===========================================

            Logfile.red ('Calculating Traveltime Grid')
            t1 = time.time()

            if WINDOWS : isParallel = False                            #hs : parallel 
           #else :       isParallel = True                             #10.12.2015
            else :       isParallel = False                            #10.12.2015

            if isParallel :                                            #hs
               maxp = int (Config['ncore'])
              #maxp = 20                                               #hs
               po   = multiprocessing.Pool(maxp)
            
               for i in xrange(len(FilterMeta)):
                   po.apply_async (ttt.calcTTTAdv,(Config,FilterMeta[i],Origin,i,arrayname,W,refshift))

               po.close()
               po.join()

            else :                                                                           #hs+
               for i in xrange(len(FilterMeta)):
                  t1 = time.time()
                  ttt.calcTTTAdv (Config,FilterMeta[i],Origin,i,arrayname,W,refshift)
                  Logfile.add ('ttt.calcTTTAdv : ' + str(time.time() - t1) + ' sec.')
            #endif                                                                           #hs-

            assert len(FilterMeta) > 0 

            TTTGridMap = deserializer.deserializeTTT (len(FilterMeta))
            mint,maxt  = deserializer.deserializeMinTMaxT (len(FilterMeta))
            
            t2 = time.time()
            Logfile.red ('%s took %0.3f s' % ('TTT', (t2-t1)))

            #sys.exit()
            ##############=======================SERIELL===========================================
            
            tw  = times.calculateTimeWindows (mint,maxt,Config,ev)        
            Wd  = waveform.readWaveforms     (FilterMeta, tw, evpath, ev)
            Wdf = waveform.processWaveforms  (Wd, Config, Folder, arrayname, FilterMeta, ev, W)    
            #sys.exit()
 
            C.writeStationFile(FilterMeta,Folder,counter)
            Logfile.red ('%d Streams added for Processing' % (len(Wd)))

            ##############=========================================================================

            ##############=======================PARALLEL==========================================
            t1        = time.time()
            arraySemb = sembCalc.doCalc (counter,Config,Wdf,FilterMeta,mint,maxt,TTTGridMap,
                                         Folder,Origin,ntimes)
            t2        = time.time()
            Logfile.add ('CALC took %0.3f sec' % (t2-t1))
            
            ASL.append(arraySemb)
            counter +=1
            
            sembCalc.writeSembMatricesSingleArray (arraySemb,Config,Origin,arrayfolder,ntimes)

            fileName = os.path.join (arrayfolder,'stations.txt')
            Logfile.add ('Write to file ' + fileName)

            fobjarraynetwork = open (fileName,'w')

            for i in FilterMeta:
                fobjarraynetwork.write (('%s %s %s\n') % (i.getName(),i.lat,i.lon))

            fobjarraynetwork.close()
        
        if ASL:
            Logfile.red ('collect semblance matrices from all arrays')
            
            sembCalc.collectSemb (ASL,Config,Origin,Folder,ntimes,len(networks))
    
            #fobjtrigger = open (os.path.join(Folder['semb'],'Trigger.txt'),'w')
            #for i in TriggerOnset:
            #    print i.aname,i.sname,i.ttime
            #    fobjtrigger.write(('%s %s %s\n')%(i.aname,i.sname,i.ttime))
            #fobjtrigger.close()
            
        else:
            Logfile.red ('Nothing to do  -> Finish')

# --------------------------------------------------------------------------------------------------

class ProcessMain (MainObj) :
    
    def __init__ (self) :
        initModule ()

        MainObj.__init__ (self, self, VERSION_STRING, 'process_run.log', 'process.log')

    # ---------------------------------------------------------------------------------------------

    def init (self) :  
        
        if not Globals.init () : return False

        #  Copy model file to working directory

        file = 'ak135.model'

        if not os.path.isfile (file) :
           source = os.path.join   ('..','tools', file)
           Basic.checkFileExists (source, isAbort = True)
           shutil.copy (source, file)                  

        return True

    # --------------------------------------------------------------------------------------------

    def process (self) : 
        processLoop ()
        return True

    def finish (self) :    pass

#endclass ProcessMain
# -------------------------------------------------------------------------------------------------

def MainProc () :

    mainObj = ProcessMain ()
    mainObj.run()

# -------------------------------------------------------------------------------------------------

isClient = False

if __name__ == "__main__":
   
   if not isClient :    
      MainProc()

