# -*- coding: utf-8 -*-
"""
Created on Tue 4 June 2019

@author: Sandor Zoletnik

This is the flap module for the Wendelstein 7-X MDSPlus archive 
"""
import numpy as np
import copy
import configparser
import copy
import fnmatch
import io
import pickle
import os
import math
import matplotlib.pyplot as plt

import flap
import flap_mdsplus
flap_mdsplus.register()


def w7x_mdsplus_get_data(exp_id=None, data_name=None, no_data=False, options=None, coordinates=None, data_source=None):
    """ Data read function for the W7-X MDSPlus database
    exp_id: Experiment ID, YYYYMMDD.xxx
    data_name: Channel names [\]tree::node
               or virtual names:
                   CR-x: Correlation reflectometry, x is antenna A,B,C,D
    coordinates: List of flap.Coordinate() or a single flap.Coordinate
                 Defines read ranges. The following coordinates are interpreted:
                     'Sample': The read samples
                     'Time': The read times
                     Only a single equidistant range is interpreted in c_range.
    options: Dictionary. Defaults will be read from W7X_MDSPlus section in configuration file.
            'Protocol': For ssh connection use 'ssh://'
            'Server': Server name (default: mds-trm-1.ipp-hgw.mpg.de)
            'User': User name for access. Password-free access should be set up for this user.
            'Virtual name file': A file name to translate virtual names to MDS+ entries. For 
                                 format see w7x_mds_virtual_names()
            'Verbose': (bool) Write progress information during data read.
            'Cache data': (bool) Cache data to options['Cache directory'] and read it from there
            'Cache directory': (str) Name of the cache directory
    """
    if (data_source is None):
        data_source = 'W7X_MDSPlus'
    if (exp_id is None):
        raise ValueError('exp_id should be set for W7X MDSPlus.')

    default_options = {'Protocol': None,
                       'Server': 'mds-trm-1.ipp-hgw.mpg.de',
                       'User': None,
                       'Virtual name file': None,
                       'Verbose': True,
                       'Cache data': False,
                       'Cache directory': None
                       }
    _options = flap.config.merge_options(default_options,options,data_source=data_source)

    if (exp_id is None):
        raise ValueError("exp_id must be set for reading data from MDSPlus.")
    if (type(exp_id) is not str):
        raise TypeError("exp_is must be a string with format YYYYMMDD.nnn")
    exp_id_split = exp_id.split('.')
    if ((len(exp_id_split) is not 2) or (len(exp_id_split[0]) != 8) or (len(exp_id_split[1]) != 3)):
        raise ValueError("exp_is format error: must be a string YYYYMMDD.nnn")
    exp_id_mds = int(exp_id_split[0][2:] + exp_id_split[1])
    
    try:
        d = flap.get_data('MDSPlus',exp_id=exp_id_mds,name=data_name,no_data=no_data,options=_options,coordinates=coordinates)
        d.data_title = 'W7X_MDSPlus data'
    except Exception as e:
        raise e
    return d

def add_coordinate(data_object, new_coordinates, options=None):
    raise NotImplementedError("Coordinate conversions not implemented yet.")

def register(data_source=None):
    if (data_source is None):
        data_source = 'W7X_MDSPlus'
    flap.register_data_source(data_source, get_data_func=w7x_mdsplus_get_data, add_coord_func=add_coordinate)
