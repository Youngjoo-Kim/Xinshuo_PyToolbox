# Author: Xinshuo Weng
# email: xinshuo.weng@gmail.com

# this file contains function for generating many formats of data

from scipy.misc import imread
import numpy as np
import os, time
import h5py

import __init__paths__
from math_function import identity
from check import is_path_exists, isnparray, is_path_exists_or_creatable, isfile, isfolder, isfunction, isdict, isstring
from file_io import load_list_from_file, mkdir_if_missing, fileparts, load_list_from_folder
from preprocess import preprocess_image_caffe

def generate_hdf5(save_dir, data_src, data_name='data', batch_size=1, ext_filter='png', label_src=None, label_name='label', label_preprocess_function=identity, debug=True, vis=True):
    '''
    # this function creates data in hdf5 format from a image path 

    # input parameter
    #   data_src:       where the data is
    #   label_src:      where the label is
    #   save_dir:       where to store the hdf5 data
    #   batch_size:     how many image to store in a single hdf file
    #   ext_filder:     what format of data to use for generating hdf5 data 
    '''

    # parse input
    assert is_path_exists_or_creatable(save_dir), 'save path should be a folder to save all hdf5 files'
    mkdir_if_missing(save_dir)

    if isfolder(data_src):
        if debug:
            print 'data is loading from %s' % data_src
        datalist, num_data = load_list_from_folder(data_src)
    elif isfile(data_src):
        datalist, num_data = load_list_from_file(data_src)
    else:
        assert False, 'data source format is not correct.'
    assert isstring(data_name), 'dataset name is not correct'

    if label_src is None:
        labeldict = None
        labellist = None
    elif isfile(label_src):
        assert is_path_exists(label_src), 'file not found'
        _, _, ext = fileparts(label_src)
        assert ext == '.json', 'only json extension is supported'
        labeldict = json.load(label_src)
        num_label = len(labeldict)
        assert num_data == num_label, 'number of data and label is not equal.'
        labellist = None
    elif isdict(label_src):
        labeldict = label_src
        labellist = None
    elif isnparray(label_src):
        labeldict = None
        labellist = label_src
    else:
        assert False, 'label source format is not correct.'
    
    assert isfunction(label_preprocess_function), 'label preprocess function is not correct.'

    # warm up
    size_data = imread(datalist[0]).shape
    datalist_batch = list()
    # data = np.zeros((batch_size, ) + size_data, dtype='float32')
    if labeldict is not None:
        assert isstring(label_name), 'label name is not correct'
        labels = np.zeros((batch_size, 1), dtype='float32')
        label_value = [float(label_tmp_char) for label_tmp_char in labeldict.values()]
        label_range = np.array([min(label_value), max(label_value)])
    if labellist is not None:
        labels = np.zeros((batch_size, 1), dtype='float32')
        label_range = [np.min(labellist), np.max(labellist)]

    # start generating
    count_hdf = 1       # count number of hdf5 file
    for i in xrange(num_data):
        print('%s %d/%d' % (save_dir, i+1, num_data))
        raw_image = imread(datalist[i]).astype('float32')
        if debug:
            max_value = np.max(raw_image)
            assert max_value > 1 and max_value <= 255, 'data is not in [0, 255]'
        
        img = raw_image / 255.0   # [rows,col,channel,numbers], scale the image data to (0, 1)
        datalist_batch.append(img)
        if debug:
            min_value = np.min(img)
            max_value = np.max(img)
            assert max_value >= 0 and max_value <= 1, 'data is not in [0, 1]'
            assert min_value >= 0 and min_value <= 1, 'data is not in [0, 1]'

        if labeldict is not None:
            _, name, _ = fileparts(datalist[i])
            labels[i % batch_size, 0] = float(labeldict[name])
        if labellist is not None:
            labels[i % batch_size, 0] = float(labellist[i])

        if i % batch_size == 0:
            data = preprocess_image_caffe(datalist_batch, debug=debug, vis=vis)   # swap channel, transfer from list of HxWxC to NxCxHxW

            # write to hdf5 format
            h5f = h5py.File(os.path.join(save_dir, 'data_%010d.hdf5' % count_hdf), 'w')
            h5f.create_dataset(data_name, data=data, dtype='float32')
            if (labeldict is not None) or (labellist is not None):
                labels = label_preprocess_function(data=labels, data_range=label_range, debug=debug)
                h5f.create_dataset(label_name, data=labels, dtype='float32')
                labels = np.zeros((batch_size, 1), dtype='float32')

            h5f.close()
            count_hdf = count_hdf + 1
            del datalist_batch[:]
            if debug:
                assert len(datalist_batch) == 0, 'list has not been cleared'

    return count_hdf, num_data