# -*- coding: utf-8 -*-
"""
Created on Thu May 28 09:36:52 2020

@author: mi19356
"""

import numpy as np
import pandas as pd 
import sys
from numpy import loadtxt
import matplotlib.pyplot as plt
from collections import OrderedDict
import time   
import re

from cpex.nvec import nvec_extract
from cpex.transformation import trans_matrix, strain_transformation



class load_amitexinfo:
   
    def __init__(self,fname, lattice_list = ['111', '200', '220', '311']):
        "read in data from file"
        content_array=file_read(fname)
        
        "create new array from data"
        newarray=[[]]*len(content_array)
        for line in range(0,len(content_array)):
            newarray[line]=content_array[line].split()
            
            #newarray[line]=list(map(float,content_array[line]))
        newarray=np.array(newarray)
        self.newarray=newarray

        "determine total number of grains"

        check=np.where(newarray[:-1,0] != newarray[1:,0])[0]
        grainnum=check[1]-check[0]
        num_grains=grainnum
        
       
        
        grainarray=[[]]*grainnum
        
        "combining to form arrays specific to each grain"
        for grain in range(0,grainnum):
            grainarray[grain]=newarray[grain:len(newarray):grainnum]
        
        " convert to numpy array for saving in dataframe"
        grainarray=np.array(grainarray)
        
        "saving number of frames"
        num_frames=np.size(grainarray,1)
        
        "transposing array to be ordered correctly for scrape"
        grainarray=np.transpose(grainarray, (2,0,1))
        
        "placing data into dataframe"
        data= {'euler': grainarray[16:19,:,:],
               'elastic': grainarray[19:25,:,:],
               'time': grainarray[0,:,:],
               's': grainarray[1:6,:,:],
               'e': grainarray[7:13,:,:],
               'num_frames': num_frames,
               'num_grains': num_grains,
               'back stress2': grainarray[99:123:2,:,:],
               'back stress': grainarray[75:98:2,:,:],
               'shearstrain': grainarray[49:73:2,:,:],
               'g hardening': grainarray[25:48:2,:,:]}
        
        
        "saving the values to self"
        self.e = data['e']
        self.s = data['s']
        self.elastic = data['elastic']
        self.rot = data['euler']
        self.t = data['time']
        self.num_grains=data['num_grains']
        self.num_frames=data['num_frames']
        self.backstress=data['back stress']
        self.backstress2=data['back stress2']
        self.ghardening=data['g hardening']
        self.shearstrain=data['shearstrain']
        
        
   
    def save_cpex(self, fpath):
        np.savez(fpath, s=self.s, e=self.e, lat=self.elastic, 
                 rot=self.rot, time=self.t, num_grains=self.num_grains,
                 num_frames=self.num_frames,backstress=self.backstress,
                 ghardening=self.ghardening,shearstrain=self.shearstrain,
                 backstress2=self.backstress2)         

def file_read(fname):
    content_array = []
    with open(fname) as f:
                #Content_list is the list that contains the read lines.     
        for line in f:
            content_array.append(line)
               
    return (content_array)

loadinfo=load_amitexinfo('reprime_originalbackcorrect_130.zstd')
t1 = time.time()
loadinfo.save_cpex("cpex_{}.npz".format(time.strftime("%Y%m%d_%H%M%S")))



