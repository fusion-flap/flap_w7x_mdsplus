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

import MDSplus

import flap


def w7x_mds_virtual_names(data_name, exp_id, channel_config_file):
    """
    Translates virtual data names to MDSPlus entries. 
    Returns a list of virtual names and translated full names.
    The list is read from the configuration file. The file is a standard configuration file
    with one section [Virtual names]. Each entry looks like one of the following templates.
        Simple translation:
            <name> = <mdsname>
        Translation in an expID range, including ends:
            <name>(startID-endID) = <mdsname>
          One of startID or endID may be omitted.
        <mdsname> can be either a single MDS name or complex(mds1, mds2) which will construct a complex signal
        from the two MDS+ entries.
    Wildcards are allowed in data names. Data names can be a single string or list of strings.
    Return value:
        virt_names, mds_names
        virt names is a list of the interpreted names.
        mds_names is a list of the same length as virt_names. Elements can be the following:
            string: a single MDS+ name
            list: [<type>, <mds1>, <mds2>, ...]
                type can be 
                  'complex': two MDS entries are expected (real, imag), compelx signal will be created from them.
        
    """
    if (type(exp_id) is not str):
        raise TypeError("exp_id should be string.")
    try:
        exp_id_num = int(exp_id[:8]+exp_id[9:])
    except Exception as e:
        raise ValueError("Invalid exp_id value: '{:s}".format(exp_id))
        
    config = configparser.ConfigParser()
    config.optionxform = str
    read_ok = config.read(channel_config_file)
    if (read_ok == []):
        raise OSError("Error reading MDSPlus virtual name file "+channel_config_file)
    try:
        entries = config.items('Virtual names')
    except Exception as e:
        raise ValueError("Invalid MDSPlus virtual name file "+channel_config_file) 
    entry_descr = [e[0] for e in entries]
    entry_values = [e[1] for e in entries]
    mds_names = []
    entry_names = []
    # Finding etries with matching exp_id
    for e,ev in zip(entry_descr,entry_values):
        start_brace = e.find('(')
        stop_brace = e.find(')')
        if (start_brace * stop_brace < 0):
            raise ValueError("Invalid entry '{:s}' in virtual name file: {:s}".format(e, channel_config_file))
        if (start_brace > 0):
            # ExpID range given
            exp_id_range = e[start_brace+1:stop_brace].split('-')
            if (len(exp_id_range) != 2):
                raise ValueError("Invalid expID range in entry '{:s}' in virtual name file: {:s}".format(e, channel_config_file))
            if (exp_id_range[0].strip() == ''):
                exp_id_start = None
            else:
                try:
                    exp_id_start = int(exp_id_range[0][:8]+exp_id_range[0][9:])
                except ValueError:
                    raise ValueError("Invalid expID start in entry '{:s}' in virtual name file: {:s}".format(e, channel_config_file))
            if (exp_id_range[1].strip() == ''):
                exp_id_stop = None
            else:
                try:
                    exp_id_stop = int(exp_id_range[1][:8]+exp_id_range[1][9:])
                except ValueError:
                    raise ValueError("Invalid expID stop in entry '{:s}' in virtual name file: {:s}".format(e, channel_config_file))
            if ((exp_id_start is not None) and (exp_id_num < exp_id_start) or \
                (exp_id_stop is not None) and (exp_id_num > exp_id_stop)) :
                continue
            entry_names.append(e[:start_brace])
        else:
            entry_names.append(e)
        mds_names.append(ev)
    if (type(data_name ) is not list):
        _data_name = [data_name]
    else:
        _data_name = data_name
    select_list = []
    select_mds_list = []
    for i,dn in enumerate(_data_name):    
        try:
            sl, si = flap.select_signals(entry_names, dn)
            select_list += sl
            select_mds_list += [mds_names[i] for i in si]
        except ValueError as e:
            select_list.append(None)
            select_mds_list.append(dn)
            
    mds_descr = []
    for descr in select_mds_list:
        start_brace = descr.find('(')
        stop_brace = descr.find(')')
        if (start_brace * stop_brace < 0):
            raise ValueError("Invalid value '{:s}' in virtual name file: {:s}".format(descr, channel_config_file))
        if (start_brace > 0):
            mds_list = descr[start_brace+1:stop_brace].split(',')
            mds_type = descr[:start_brace]
            mds_descr.append([mds_type] + mds_list)
        else:
            mds_descr.append(descr)    
    return select_list, mds_descr        

def w7x_mdsplus_get_data(exp_id=None, data_name=None, no_data=False, options=None, coordinates=None):
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
            'Server': Server name (default: mds-trm-1.ipp-hgw.mpg.de)
            'User': User name for access. Password-free access should be set up for this user.
            'Virtual name file': A file name to translate virtual names to MDS+ entries. For 
                                 format see w7x_mds_virtual_names()
            'Verbose': (bool) Write progress information during data read.
            'Cache data': (bool) Cache data to options['Cache directory'] and read it from there
            'Cache directory': (str) Name of the cache directory
    """
    if (exp_id is None):
        raise ValueError('exp_id should be set for W7X MDSPlus.')

    default_options = {'Server': 'mds-trm-1.ipp-hgw.mpg.de',
                       'User': None,
                       'Virtual name file': None,
                       'Verbose': True,
                       'Cache data': False,
                       'Cache directory': None
                       }
    _options = flap.config.merge_options(default_options,options,data_source='W7X_MDSPlus')

    if (exp_id is None):
        raise ValueError("exp_id must be set for reading data from MDSPlus.")
    if (type(exp_id) is not str):
        raise TypeError("exp_is must be a string with format YYYYMMDD.nnn")
    exp_id_split = exp_id.split('.')
    if ((len(exp_id_split) is not 2) or (len(exp_id_split[0]) != 8) or (len(exp_id_split[1]) != 3)):
        raise ValueError("exp_is format error: must be a string YYYYMMDD.nnn")
    exp_id_mds = int(exp_id_split[0][2:] + exp_id_split[1])
    
    if (_options['Server'] is None):
        raise ValueError("Option 'Server' should be set for using MDSPlus.")
    if (_options['User'] is None):
        raise ValueError("Option 'User' must be set for using MDSPlus.")
    if ((type(data_name) is not str) and (type(data_name) is not list)):
        raise ValueError("data_name should be a string or list of strings.")
    if (_options['Virtual name file'] is not None):
        try:
            virt_names, virt_mds = w7x_mds_virtual_names(data_name, exp_id, _options['Virtual name file'])
        except Exception as e:
            raise e
    
    connection_name = 'ssh://' + _options['User'] + '@' + _options['Server']
    
    signal_list = []
    data_list = []
    time_start = None
    time_step = None
    time_end = None
    
    for name, mds_descr in zip(virt_names,virt_mds):
        # Assembling a list of MDS nodes needed for this data
        mds_request_list = []
        if (name is None):
            # This was not recognized as virtual name
            mds_request_list = [mds_descr]
            signal_list.append(mds_descr)
            readtype = 0
        else:
            # This was recongnized as a virtual signal
            signal_list.append(name)
            if (type(mds_descr) is not list):
                # This was recognized as a single MDS node
                mds_request_list = [mds_descr]
                readtype = 0
            else:
                # This is a composite virtual signal
                mds_request_list = mds_descr[1:]
                readtype = 1 
        # Reading the required nodes
        this_data_list = []
        for mds_name in mds_request_list:
            mds_name_split = mds_name.split('::')
            if (len(mds_name_split) is not 2):
                raise ValueError("Invalid mds name '{:s}', missing tree name? Data name is tree::node".format(mds_name))
            tree_name = mds_name_split[0].strip()
            if (tree_name[0] == '\\'):
                tree_name = tree_name[1:]
            node_name = mds_name_split[1]
            if ((_options['Cache data']) and (_options['Cache directory'] is not None)):
                filename = str(exp_id_mds)+'_'+mds_name
                for c in ['\\',':']:
                   filename = filename.replace(c,'_')
                filename = os.path.join(_options['Cache directory'],filename)
                try:
                    f = io.open(filename,'rb')
                    mdsdata_pickle = pickle.load(f)
                    f.close()
                    try:
                        if (mdsdata_pickle['MDSdata cache']):
                            mdsdata = mdsdata_pickle['Data']
                            mdsdata_start = mdsdata_pickle['Start']
                            mdsdata_end = mdsdata_pickle['End']
                            mdsdata_step = mdsdata_pickle['Step']
                            del mdsdata_pickle
                            data_cached = True
                    except:
                        data_cached = False
                except:
                    data_cached = False
            else:
                data_cached = False
            if (not data_cached):
                try:
                    conn
                except NameError:
                    try:
                        if (_options['Verbose']):
                            print("Connecting to "+connection_name)
                        conn = MDSplus.Connection(connection_name)
                    except Exception as e:
                        raise e
                    try:
                        conn.openTree(tree_name,exp_id_mds)
                    except MDSplus.MDSplusException as e:
                        raise RuntimeError("Error connecting to tree {:s}, experiment {:s}".format(tree_name,exp_id)) 
                if (_options['Verbose']):
                    print("Reading "+mds_name)
                try:
                    mdsdata = conn.get(mds_name)
                    mdsdata_start = mdsdata.dim_of()._fields['begin']
                    mdsdata_step = mdsdata.dim_of()._fields['delta']
                    mdsdata_end = mdsdata.dim_of()._fields['ending']
                    mdsdata = mdsdata.data()               
                except MDSplus.MDSplusException as e:
                    raise RuntimeError("Cannot read MDS node:{:s}".format(mds_name))
            if (not data_cached and (_options['Cache data']) and (_options['Cache directory'] is not None)):
                while True:
                    try:
                        f = io.open(filename,"wb")
                    except:
                        print("Warning: Cannot open cache file: "+filename)
                        break
                    mdsdata_pickle = {}
                    mdsdata_pickle['MDSdata cache'] = True
                    mdsdata_pickle['Data'] = copy.deepcopy(mdsdata)
                    mdsdata_pickle['Start'] = mdsdata_start
                    mdsdata_pickle['End'] = mdsdata_end
                    mdsdata_pickle['Step'] = mdsdata_step
                    try:
                        pickle.dump(mdsdata_pickle,f)
                        del mdsdata_pickle
                    except Exception as e:
                        print("Warning: Cannot write cache file: "+filename)
                        break
                    try:
                        f.close()
                    except Exception as e:
                        print("Warning: Cannot write cache file: "+filename)
                    break
                                        
            if (time_start is not None):
                if ((mdsdata_start != time_start) or (mdsdata_step != time_step)
                    or (mdsdata_end != time_end)):
                    raise ValueError("Different timescales for signals. Not possible to return in one flap.DataObject.")
            else:
                time_start = mdsdata_start
                time_step = mdsdata_step
                time_end = mdsdata_end
            this_data_list.append(mdsdata) 
        if (readtype == 0):
            data_list.append(this_data_list[0])
        elif (readtype == 1):
            data_list.append(this_data_list[0] + 1j * this_data_list[1])
    # Determining data type
    dtype = int
    for i in range(len(data_list)):
        if (dtype is not complex) and (data_list[i].dtype.kind == 'f'):
                dtype = float
        if (data_list[i].dtype.kind == 'c'):
            dtype = complex
    if (len(data_list) == 1):
        data = data_list[0]
        signal_dim = []
    else:    
        data = np.empty((len(data_list[0]),len(data_list)),dtype=dtype)
        for i in range(len(data_list)):
            data[:,i] = data_list[i].astype(dtype)
        signal_dim = [1]
    coord = []
    if ((time_start is not None) and (time_step is not None)):
        coord.append(copy.deepcopy(flap.Coordinate(name='Time',
                                                   unit='Second',
                                                   mode=flap.CoordinateMode(equidistant=True),
                                                   start=time_start,
                                                   step=time_step,
                                                   dimension_list=[0])
                                    ))
    coord.append(copy.deepcopy(flap.Coordinate(name='Sample',
                                               unit='',
                                               mode=flap.CoordinateMode(equidistant=True),
                                               start=0,
                                               step=1,
                                               dimension_list=[0])
                               ))
    coord.append(copy.deepcopy(flap.Coordinate(name='Signal name',
                                               unit='',
                                               mode=flap.CoordinateMode(equidistant=False),
                                               values=signal_list,
                                               dimension_list=signal_dim)
                                 ))

    data_title = "W7-X MDSPlus data"
    d = flap.DataObject(data_array=data,
                        data_unit=flap.Unit(),
                        coordinates=coord,
                        exp_id=exp_id,
                        data_title=data_title,
                        data_source="W7X_MDSPlus")
    return d


def add_coordinate(data_object, new_coordinates, options=None):
    raise NotImplementedError("Coordinate conversions not implemented yet.")

def register():
    flap.register_data_source('W7X_MDSPlus', get_data_func=w7x_mdsplus_get_data, add_coord_func=add_coordinate)
