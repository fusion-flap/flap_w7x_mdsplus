# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 09:37:34 2019

@author: Sandor Zoletnik  (zoletnik.sandor@wigner.mta.hu)

Test program for W7X MDSPlus.

Before usinig this program the following has to be set in test_w7x_mdsplus.cfg in the same directory 
where this program resides:
[Module W7X_MDSPlus]
 Server = 'mds-trm-1.ipp-hgw.mpg.de'
 User = 'zoletnik'
 Virtual name file = 'Virtual_names.cfg'
 Cache data =  True
 Cache directory = 'c:\data\w7x_cache'
 
 'Server' is the MDSPlus server name, 'User' is the user name. Password-free access should be set up for this user..
 'Virtual name file' points to a file which translated virrtual signal names to MDSPlus entries. An example 
 is included. It should be in the working directory or the path should be added to the entry.
 'Cache data' can be set to True, in this case loaded MDSplus data will be stored locally in directory 
 'Cache directory'. When the same signal read next time it will be loaded automatically from this cache.
"""

import matplotlib.pyplot as plt
import os

import flap
import flap_w7x_mdsplus

flap_w7x_mdsplus.register()

def test_mdsplus(): 
    plt.close('all')
    print("**** Reading an explicit MDS signal.")
    flap.delete_data_object('*')
    try:
        # Explicit MDSPlus reference
       d=flap.get_data('W7X_MDSPlus',
                        name='\QMC::TOP.HARDWARE:ACQ132_168:CHANNELS:INPUT_03',
                        exp_id='20181018.003',
                        object_name='TEST_MDS'
                        )    
    except Exception as e:
        raise e

    print("**** Reading a virtual signal")
    try:
        # Explicit MDSPlus reference
        d1=flap.get_data('W7X_MDSPlus',
                        name='PCI-1-16',
                        exp_id='20180904.027',
                        object_name="PCI-1-16"
                        )    
    except Exception as e:
        raise e
    d1.plot(axes='Time')
    
    print("**** Reading multiple complex virtual signals in part of the time.")
    try:
        # Explicit MDSPlus reference
        d2=flap.get_data('W7X_MDSPlus',
                        name=['CR-B','CR-C','CR-D','CR-E'],
                        exp_id='20181018.003',
                       coordinates={'Time':[4,4.1]},
                        object_name="CR"
                        )    
    except Exception as e:
        raise e
    plt.figure()
    d2.abs_value().plot(axes='Time',options={'All':True})
    flap.list_data_objects()
   
# Reading configuration file in the test directory
thisdir = os.path.dirname(os.path.realpath(__file__))
fn = os.path.join(thisdir,"test_w7x_mdsplus.cfg")
flap.config.read(file_name=fn)
        
test_mdsplus()
