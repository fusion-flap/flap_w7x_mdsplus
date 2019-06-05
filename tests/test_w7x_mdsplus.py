# -*- coding: utf-8 -*-
"""
Created on Tue Jun  4 09:37:34 2019

@author: Sandor Zoletnik  (zoletnik.sandor@wigner.mta.hu)

Test programs for W7X MDSPlus
"""
import flap
import flap_w7x_mdsplus

flap_w7x_mdsplus.register()

def test_mdsplus():
    names = ['\QMC::TOP.HARDWARE:ACQ132_168:CHANNELS:INPUT_03'
             ]
    try:
        d=flap.get_data('W7X_MDSPlus',name=names,exp_id='20181018.003')    
    except Exception as e:
        raise e
    flap.save(d,'test_mdsplus.dat')
        
test_mdsplus()
