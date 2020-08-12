# -*- coding: utf-8 -*-
"""
Created on Fri Aug 30 14:48:44 2019

@author: cs17809
"""
import os
import numpy as np
import matplotlib.pyplot as plt
import csv
from scipy.optimize import curve_fit
from collections import OrderedDict

from cpex.nvec import nvec_extract
from cpex.transformation import trans_matrix, strain_transformation

class Load():
    
    def __init__(self, fpath, calc=True, lattice_list = ['111', '200', '220', '311']):
        data = np.load(fpath)
        self.e = data['e'].astype(np.float)
        self.s = data['s'].astype(np.float)
        self.elastic = data['lat'].astype(np.float)
        #self.dims = data['dims']
        self.rot = data['rot'].astype(np.float)
        #self.v = data['v']
        #self.N = data['N']
        self.num_grains = data['num_grains']
        self.num_frames = data['num_frames']
        self.backstress = data['backstress'].astype(np.float)
        self.backstress2 = data['backstress2'].astype(np.float)
        self.ghardening = data['ghardening'].astype(np.float)
        self.shearstrain = data['shearstrain'].astype(np.float)
        #self.slip_e = data['slip_e']
        try:
            self.t = data['time'].astype(np.float)
        except KeyError:
            print('time not saved in file, creating zero array')
            self.t = np.zeros((self.num_frames, ))
            
        try:
            self.b_stress = data['b_stress']
        except KeyError:
            print('back stress not saved in file, creating zero array')
        #    d_shape = (self.num_grains, self.num_frames)
        #    self.b_stress = np.zeros((12,) + d_shape)
            
        self.rot[:, :,0] = self.rot[:, :,1]
        self.lattice_list = lattice_list
        self.lattice_nvecs = [nvec_extract(*[int(i) for i in hkl]) for hkl in self.lattice_list]
        
        if calc:
            print('Calculating lattice rotations and strains...')
            self.calc_lattice_rot()
            self.calc_lattice_strain()
            self.calc_lattice_tensor()
        
        
    def extract_grains(self, data='elastic', idx=1, grain_idx=None):
        """
        Routine to extract information about some or all grains.
        This is independent of lattice family.
        """
        if idx == None and grain_idx != None:
            idx = np.s_[:, grain_idx]
        elif idx == None and grain_idx == None:
            idx = np.s_[:, :]
        elif idx != None and grain_idx == None:
            idx = np.s_[idx, :]
        else:
            idx = np.s_[idx, grain_idx]
        
        d = {'strain':self.e,
             'stress':self.s,
             'elastic':self.elastic,
             #'back stress':self.b_stress,
             #'slip strain':self.slip_e,
             'rot':self.rot - self.rot[:,:, 0][:, :, None],
             'time':self.t,
             'frame':np.arange(self.num_frames),
             'backstress':self.backstress,
             'backstress2':self.backstress2,
             'ghardening':self.ghardening,
             'shearstrain':self.shearstrain}
        
        if data not in ['time', 'frame', 'rot']:
            ex = d[data][idx]
#        if data in ['slip strain']: 
#            ex = d[:][data][idx]
        else:
            ex = d[data]
            
        return ex
    
    
    def extract_lattice(self, data='lattice', family='311', 
                        grain_idx=None, plane_idx=None):
        """
        Routine to extract information about some or all grains for a 
        specified lattice plane.
        """
        if plane_idx == None and grain_idx != None:
            idx = np.s_[:, grain_idx]
        elif plane_idx == None and grain_idx == None:
            idx = np.s_[:, :]
        elif plane_idx != None and grain_idx == None:
            idx = np.s_[plane_idx, :]
        else:
            idx = np.s_[plane_idx, grain_idx]
        
        lattice = self.lattice_strain[family][idx]
        phi = self.lattice_phi[family]
        
        d = {'phi':phi,'lattice':lattice}
        
        return d[data]
    
    def extract_phi_idx(self, family='311', phi=0, window=10, frame=0):
        """
        Allows for selection of the index of lattice planes wityh a defined 
        orientation with resepect to the y axis (nominally the loading axis).
        A 2D array of indices with be returned if a frame is specified, the
        elemtns in the array will be structured:
            
            [[grain_idx, plane_idx],
            [grain_idx, plane_idx],
            ...]
        
        If None is passed as the frame variable then the rotation of
        the grain during loading/dwell etc. is being considered - a 2D array 
        is returned with each element being structured as follows:
            
            [[grain_idx, frame_idx, plane_idx],
            [grain_idx, frame_idx, plane_idx],
            ...]
            
        In addition to the list of indices an equivalent boolean array is 
        returned in each case.
            
        """
        if frame == None:
            frame = np.s_[:]
            
        phi_ = 180 * self.lattice_phi[family][:, frame] / np.pi
        
        phi_ -= 90
        phi -= 90
        w = window / 2
        p0, p1 = phi - w, phi + w
        
        s0 = np.logical_and(phi_ > np.min(p0), phi_ < np.max(p1))
        s1 = np.logical_and(-phi_ > np.min(p0), -phi_ < np.max(p1))
        select = np.logical_or(s0, s1)
        
        va = np.argwhere(select)
        return va, select

    
    def plot_phi(self, y='lattice', family='200', frame=-1, idx=0, 
                         alpha=0.1, restrict_z=False, restrict_range = [70, 110]):
        
        lattice = self.lattice_strain
        
        y_ = {'lattice': lattice[family],
              'back stress': self.b_stress[idx]}[y]
        try:
            y_tensor = self.lattice_tensor[family]
            tens = True
        except KeyError:
            print('Tensor not available')
            tens=False
        
        if y == 'back stress':
            x = self.rot[1]
        else:
            x = self.lattice_phi[family]
            
        rot = self.lattice_rot[family]

        
        if restrict_z == True and y == 'lattice':
            r0, r1 = restrict_range
            t_z = rot[:, :, 2]* 180 / np.pi
            va = np.logical_and(t_z > r0, t_z < r1)
            vaf = np.zeros_like(rot[:, :, 2], dtype='bool')
            vaf[:, frame, :] += True
            va = np.logical_and(va, vaf)
        else:
            va = np.s_[:, frame]

        plt.plot(x[va].flatten(), y_[va].flatten(), '.', alpha=alpha)
        if y == 'lattice' and tens:
            plt.plot(np.linspace(0, np.pi, 1001), strain_transformation(np.linspace(0, np.pi, 1001), *y_tensor[:, frame]), 'r')
        x = 'lattice rot (phi)' if y == 'lattice' else 'grain rot (phi)'
        plt.xlabel(x)
        plt.ylabel(y)
    
    
    def plot_grains(self, y='elastic', x='stress', x_mean=True, 
             y_mean=False, x_idx=1, y_idx=1, grain_idx=None, alpha=0.2,
             color='k', mcolor='r'):
        """
        Plot grain specific information
        """
        # If necessary put grain_idx into list for fancy indexing
        if isinstance(grain_idx, int):
            grain_idx = [grain_idx,]
            
        # Time and frame can't be averaged
       # if x in ['time', 'frame']:
           # x_mean = False
        if y in ['time', 'frame']:
            y_mean = False
        
        # Data extraction
        x_ = self.extract_grains(data=x, idx=x_idx, grain_idx=grain_idx)
        y_ = self.extract_grains(data=y, idx=y_idx, grain_idx=grain_idx)
        csvfile=open('strain_grain.csv','w', newline='')
        obj=csv.writer(csvfile)
        for val in np.transpose(x_):
            obj.writerow(val)
        csvfile.close()
        
        csvfile=open('stress_grain.csv','w', newline='')
        obj=csv.writer(csvfile)
        for val in np.transpose(y_):
            obj.writerow(val)
        csvfile.close()
        # Calculate mean of arrays
        xm = np.nanmean(x_, axis=0) #if x not in ['time', 'frame'] else x_
        ym = np.nanmean(y_, axis=0) if y not in ['time', 'frame'] else y_

        x__ = xm if x_mean else x_.T
        y__ = ym if y_mean else y_.T
        
        # Tinkering with axis labels
        x = '{} (idx={})'.format(x, x_idx) if x not in ['time', 'frame'] else x
        y = '{} (idx={})'.format(y, y_idx) if y not in ['time', 'frame'] else y
        x = 'mean {}'.format(x) if x_mean else x
        y = 'mean {}'.format(y) if y_mean else y
        
        #extracting data
        csvfile=open('stress-strain4.csv','w', newline='')
        #total=np.concatenate((np.squeeze(x__),np.squeeze(y__)))
        total=np.transpose([np.squeeze(x__),np.squeeze(y__)])
        obj=csv.writer(csvfile)
        for val in total:
            obj.writerow(val)
        # Plotting
        plt.plot(np.squeeze(x__), np.squeeze(y__), color=color, alpha=alpha)
        if (not y_mean or not x_mean) and (grain_idx == None or len(grain_idx) != 1):
            plt.plot(xm, ym, color=mcolor, label='Mean response')
            plt.legend()


        plt.ylabel(y)
        plt.xlabel(x)
        csvfile.close()
        
    
    def plot_lattice_strain(self, lat_ax='x', ax2='stress', ax2_idx=1, ax2_mean=True, family='200', phi=0, 
                     window=10, frame=0, alpha=0.2, color='k', mcolor='r',
                     plot_select=True):
        
        """
        Plot data for a specified family of lattice planes at a defined
        azimuthal angle (angle wrt y axis)
        """
        
        ax2_mean = False if ax2 in ['time', 'frame'] else ax2_mean

        d = self.extract_grains(data=ax2, idx=ax2_idx, grain_idx=None)

        valid, select = self.extract_phi_idx(family=family, phi=phi,window=window, frame=frame)
        if ax2 in ['time', 'frame']:
            d, dm = d, d
            
        else:
            
            d = np.nanmean(d, axis=0) if ax2_mean else d[valid[:,0]].T
            dm = d if ax2_mean else np.nanmean(d, axis=1)
            
        lattice = self.extract_lattice(family=family)
        
        lattice = lattice[valid[:,0], :, valid[:,1]].T
        
        x_ = lattice if lat_ax == 'x' else d
        y_ = lattice if lat_ax != 'x' else d
        
        #plt.figure(1)
        #ax=plt.plot(x_,y_)
        #plt.legend(ax, slplabel,loc='center left',bbox_to_anchor=(1, 0.5))
        #plt.xlim([0,0.0025])
        #plt.ylim([0, 0.5])
       
        
        #plt.xlabel('Macro Strain')
        #plt.ylabel('Relative Slip Activity')
        #plt.tight_layout()
        #plt.savefig('lattice_311.png', dpi = 300)
        #plt.show()
        
       
       
        
        
        assert np.sum(select) > 0, 'Phi window too small for {} - no grains/planes selected'.format(family)
        if plot_select:
            plt.plot(x_, y_, 'k', alpha=alpha)
            
        x_ = np.nanmean(lattice, axis=1) if lat_ax == 'x' else dm
        y_ = np.nanmean(lattice, axis=1) if lat_ax != 'x' else dm

        plt.plot(x_, y_, label=family, color=mcolor)
        
        csvfile=open('lattice_220.csv','w', newline='')
        total=np.transpose([np.squeeze(x_),np.squeeze(y_)])
        obj=csv.writer(csvfile)
        for val in total:
            obj.writerow(val)
        
        
        ax2 = '{} (idx={})'.format(ax2, ax2_idx) if ax2 not in ['time', 'frame'] else ax2
        ax2 = ax2 if not ax2_mean else 'mean {}'.format(ax2)
        xlabel = ax2 if lat_ax != 'x' else 'lattice'
        ylabel = ax2 if lat_ax == 'x' else 'lattice'   
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        
    def extract_lattice_strain_map(self, family='200', az_bins=19):
        """
        Effectively cake/average the data into the number of specified bins, 
        return 2D array for family.
        """
        phi_steps = az_bins + 1
        arr1 = np.moveaxis(self.lattice_strain[family], 1, 2)
        arr1 = arr1.reshape((-1, arr1.shape[-1]))
        
        arr2 = np.moveaxis(self.lattice_phi[family], 1, 2)
        arr2 = arr2.reshape((-1, arr2.shape[-1]))
        arr2[arr2 > np.pi/2] -= np.pi # -90 to 90
        
        bins = np.linspace(-90, 90, phi_steps)
        e_phi = np.nan * np.ones((phi_steps - 1, self.num_frames))
        
        for idx, i in enumerate(bins[:-1]):
            va = np.logical_and(arr2 < bins[idx + 1] * np.pi / 180, arr2 > bins[idx] * np.pi / 180)
            try:
                e_phi[idx] = np.sum(arr1 * va, axis=0) / np.nansum(va, axis=0)
            except ZeroDivisionError:
                pass
            
        return (bins[:-1]+bins[1:])/2, e_phi
        
    def plot_lattice_strain_map(self, family='200', az_bins=19, ax2='time',
                                ax2_idx=1):
#    ax2='stress', ax2_idx=1, 
#                                nstep=10, ax2_mean=True):
#        
        """
        Plot 2D map of strain distribution wrt. phi and frame/time. 
        """
        
        bin_c, e_phi = self.extract_lattice_strain_map(family=family, az_bins=az_bins)
        
        d = self.extract_grains(data=ax2, idx=ax2_idx, grain_idx=None)
        ax2_mean = False if ax2 in ['time', 'frame'] else True
        if ax2_mean:
            d = np.nanmean(d, axis=0)
        
        time, phi = np.meshgrid(d, bin_c)
        plt.contourf(time, phi, e_phi)
        plt.colorbar()

        ax2 = 'mean {} (idx={})'.format(ax2, ax2_idx) if ax2 not in ['time', 'frame'] else ax2

        plt.xlabel(ax2)
        plt.ylabel('phi (reflected at 0$^o$)')
            
    
    def plot_lattice_strain_all(self, lat_ax='x', ax2='stress', ax2_mean=True, 
                                phi=0, window=10, frame=0, ax2_idx=1):
        """
        Repeat plotting for all lattice plane families
        """
        for family in self.lattice_list:
            try:
                self.plot_lattice_strain(family=family, lat_ax=lat_ax, ax2=ax2, ax2_idx=ax2_idx, phi=phi, 
                         window=window, frame=frame, plot_select=False, mcolor=None, ax2_mean=ax2_mean)
            except AssertionError:
                print('Phi window too small for {} - no grains/planes selected'.format(family))
        plt.legend(self.lattice_list)
            

    def plot_back_lattice(self, back_ax='y', b_idx=1, 
                          ax2='stress', ax2_idx=1, 
                          family='200', phi=0, window=10, frame=0, 
                          alpha=0.2, color='k', mcolor='r',
                          plot_select=True):
        
        """
        Plot back stress for a specified family of lattice planes at a defined
        azimuthal angle (angle wrt y axis)
        """
        
        back = self.extract_grains(data='back stress', idx=b_idx, grain_idx=None)
        total_strain = self.extract_grains(data= 'strain', idx=b_idx, grain_idx=None)
        
        d = self.extract_grains(data=ax2, idx=ax2_idx, grain_idx=None)
        #d = d if ax2 in ['time', 'frame'] else np.nanmean(d, axis=0)

        d_ = self.extract_grains(data=ax2, idx=ax2_idx, grain_idx=None)
        valid, select = self.extract_phi_idx(family=family, phi=phi,window=window, frame=frame)
        
       # back = back[valid[:,0], :, valid[:,1]].T
        v = np.unique(valid[:,0])
        #back = back[v, :].T
        back = back[:,v, :].T
        total_strain=total_strain[1,v,:].T
        
        x_valid=np.mean(back[:,:,:],axis=1)
        totals_valid=np.mean(total_strain[:,:],axis=1)
        
        x_=1
        #x_ = back if back_ax == 'x' else d
        #y_ = back if back_ax != 'x' else d
        
        #csvfile=open('back_grain.csv','w', newline='')
        #obj=csv.writer(csvfile)
        #for val in (y_):
        #    obj.writerow(val)
        #csvfile.close()
        

     #   assert np.sum(select) > 0, 'Phi window too small for {} - no grains/planes selected'.format(family)
       # if plot_select:
     #       plt.plot(x_, y_, 'k', alpha=alpha)
            
     #   ax2 = 'mean {} (idx={})'.format(ax2, ax2_idx) if ax2 not in ['time', 'frame'] else ax2
        
     #   xlabel = ax2 if back_ax != 'x' else 'back stress'
     #   ylabel = ax2 if back_ax == 'x' else 'back stress'   
     #   plt.xlabel(xlabel)
     #   plt.ylabel(ylabel)
        
    def plot_eslip_lattice(self, back_ax='y', b_idx=1, 
                          ax2='stress', ax2_idx=1, 
                          family='200', phi=0, window=10, frame=0, 
                          alpha=0.2, color='k', mcolor='r',
                          plot_select=True):
        
        """
        Plot back stress for a specified family of lattice planes at a defined
        azimuthal angle (angle wrt y axis)
        """
        
        back = self.extract_grains(data='ghardening', idx=b_idx, grain_idx=None)
        
        d_ = self.extract_grains(data=ax2, idx=ax2_idx, grain_idx=None)
        #d = d if ax2 in ['time', 'frame'] else np.nanmean(d, axis=0)

        
        valid, select = self.extract_phi_idx(family=family, phi=phi,window=window, frame=frame)
        
        # back = back[valid[:,0], :, valid[:,1]].T
        v = np.unique(valid[:,0])
        back = back[:,v, :].T
        x_valid=np.mean(d_[v,:].T,axis=1)
        
        #x_ = back if back_ax == 'x' else d
        #y_ = back if back_ax != 'x' else d
        
        slipsystem=np.mean(back[:,:,:],axis=1)
        totalslip=np.sum(slipsystem,axis=1)
        ra=slipsystem/totalslip[:,None]
        
        slplabel = ('(1 1 1)[0 -1 1]','(1 1 1)[1 0 -1]','(1 1 1)[-1 1 0]','(-1 1 1)[1 0 1]','(-1 1 1)[1 1 0]','(-1 1 1)[0 -1 1]',
                     '(1 -1 1)[0 1 1]','(1 -1 1)[1 1 0]','(1 -1 1)[1 0 -1]','(1 1 -1)[0 1 1]','(1 1 -1)[1 0 1]','(1 1 -1)[-1 1 0]')
        
        plt.figure(1)
        ax=plt.plot(x_valid[1:,None],slipsystem[1:,:])
        plt.legend(ax, slplabel,loc='center left',bbox_to_anchor=(1, 0.5))
        #plt.xlim([0,0.0025])
        #plt.ylim([0, 0.5])
       
        
        plt.xlabel('Macro Strain')
        plt.ylabel('Relative Slip Activity')
        plt.tight_layout()
        plt.savefig('slip_activity_311.png', dpi = 300)
        plt.show()
        
    def plot_slipsystem_av(self, back_ax='y', b_idx=1, 
                          ax2='stress', ax2_idx=1, ax1='strain',axis=1):
        
        """
        Plot the average response across slip systems
        """
        
        back =np.nanmean(self.extract_grains(data=ax2, idx=b_idx, grain_idx=ax2_idx),axis=1).T
        avvalue = np.nanmean(np.nanmean(self.extract_grains(data=ax2, idx=b_idx, grain_idx=ax2_idx),axis=0),axis=0)
        
        value2=self.extract_grains(data=ax1, idx=None, grain_idx=None)
        avvalue2=np.nanmean(value2[axis,:,:],axis)
        
       
        plt.figure(1)
        ax=plt.plot(avvalue2,avvalue)
        plt.legend(ax,loc='center left',bbox_to_anchor=(1, 0.5))
       
        
        plt.xlabel('Macro Strain')
        plt.ylabel('Relative Slip Activity')
        plt.tight_layout()
        plt.savefig('slip_activity_311.png', dpi = 300)
        plt.show()

            
    def plot_active_slip(self, back_ax='y', b_active = 2,
                          ax2='stress', ax2_idx=1, 
                          family='200', phi=0, window=10, frame=0, 
                          alpha=0.2, color='k', mcolor='r',
                          plot_select=True):
        
        """
        Plot back stress for a specified family of lattice planes at a defined
        azimuthal angle (angle wrt y axis)
        """
        
        back = self.extract_grains(data='back stress', idx=None, grain_idx=None)
        back_bool = np.abs(back) > b_active
        
        d = self.extract_grains(data=ax2, idx=ax2_idx, grain_idx=None)
        d = d if ax2 in ['time', 'frame'] else np.nanmean(d, axis=0)

        
        valid, select = self.extract_phi_idx(family=family, phi=phi,window=window, frame=frame)
        
        # back = back[valid[:,0], :, valid[:,1]].T
        v = np.unique(valid[:,0])
        back_active = np.sum(back_bool, axis=0)[v, :].T
        
        x_ = back_active if back_ax == 'x' else d
        y_ = back_active if back_ax != 'x' else d
        
        assert np.sum(select) > 0, 'Phi window too small for {} - no grains/planes selected'.format(family)
        if plot_select:
            plt.plot(x_, y_, 'k', alpha=alpha)
            
        x_ = np.nanmean(back_active, axis=1) if back_ax == 'x' else d
        y_ = np.nanmean(back_active, axis=1) if back_ax != 'x' else d

        plt.plot(x_, y_, label=family, color=mcolor)
        
        ax2 = 'mean {} (idx={})'.format(ax2, ax2_idx) if ax2 not in ['time', 'frame'] else ax2
        xlabel = ax2 if back_ax != 'x' else 'Active slip systems'
        ylabel = ax2 if back_ax == 'x' else 'Active slip systems'   
        plt.xlabel(xlabel)
        plt.ylabel(ylabel)
        
    def plot_active_slip_all(self, back_ax='y', b_active = 2,
                          ax2='stress', ax2_idx=1, 
                          phi=0, window=10, frame=0):
        """
        Repeat plotting for all active slip systems
        """
        for family in self.lattice_list:
            try:
                self.plot_active_slip(family=family, back_ax=back_ax, ax2=ax2, ax2_idx=ax2_idx, phi=phi, 
                         window=window, frame=frame, plot_select=False, mcolor=None)
            except AssertionError:
                print('Phi window too small for {} - no grains/planes selected'.format(family))
        plt.legend(self.lattice_list)

    def calc_lattice_rot(self):
        """
        Extracts all angles for FCC grain families. 
         Needs to be generalised to all structures.
        """
        r0, r1, r2 = self.rot[0].astype(np.float), self.rot[1].astype(np.float), self.rot[2].astype(np.float)
        total_rot = trans_matrix(r0, r1, r2)
        total_rot = np.transpose(total_rot, (0, 1, 3, 2))
   
    
        angles = []
        for nvec in self.lattice_nvecs:
    
            rot_v1 = np.matmul(total_rot, nvec.T) # total rot matrix
            yax=np.array([[0,1,0]]).T
            angle = np.arccos(rot_v1/(np.linalg.norm(yax)*np.linalg.norm(rot_v1, axis=-2))[:, :, np.newaxis,:] )
            angles.append(angle)
        
        self.lattice_rot = OrderedDict(zip(self.lattice_list, angles))
        self.lattice_phi = OrderedDict(zip(self.lattice_list, [i[..., 1, :] for i in angles]))


    def calc_lattice_strain(self):
    
        ens = []
        for nvec in self.lattice_nvecs:
            exx, eyy, ezz, exy, exz, eyz =self.elastic.astype(np.float)
            eT = np.array([[exx, exy, exz],
                              [-exy, eyy, eyz],
                              [-exz, -eyz, ezz]])
    
            eT = np.moveaxis(np.moveaxis(eT, 0, -1), 0, -1) #[:, :, np.newaxis, :, :]
            r0, r1, r2 = self.rot[0], self.rot[1], self.rot[2]
            
            
            r = trans_matrix(r0, r1, r2)
            
            eTrot = np.matmul(np.matmul(r, eT), np.transpose(r, (0,1,3,2)))
            eTrot = eTrot[..., np.newaxis, :, :]
            nvec = nvec[:, np.newaxis, :]
            
            en = nvec@eTrot@np.transpose(nvec, (0, 2, 1))
            en = en[:, :, :, 0, 0]
            
            ens.append(en)
        
        self.lattice_strain = dict(zip(self.lattice_list, ens))
             
        
        
    def calc_lattice_tensor(self):
        
        tensors, tensors_err = [], []

        for e_lat, phi, rot in zip(self.lattice_strain.values(),
                                   self.lattice_phi.values(),
                                   self.lattice_rot.values()):
        
            e_tensor, e_tensor_err = np.zeros((3, self.num_frames)), np.zeros((3, self.num_frames))
            for idx in range(self.num_frames):
                popt, pcov = curve_fit(strain_transformation, phi[:,idx].flatten(), e_lat[:,idx].flatten(), p0=[0, 0, 0])
                e_tensor[:, idx] = popt
                e_tensor_err[:, idx] = np.sqrt(np.diag(pcov))
            
            tensors.append(e_tensor)
            tensors_err.append(e_tensor_err)
            
        self.lattice_tensor = OrderedDict(zip(self.lattice_list, tensors))
        self.lattice_tensor_err = OrderedDict(zip(self.lattice_list, tensors_err))
        
if __name__ == '__main__':
    folder = os.path.join(os.path.dirname(__file__), r'data') # should be sub [0]
    fpath = os.path.join(folder, r'cpex_20200717_114455.npz')
    data = Load(fpath)
    data.plot_slipsystem_av(back_ax='y', b_idx=None, ax2='ghardening', ax2_idx=None, ax1='strain',axis=0)
    #data.plot_grains(x='time', x_mean=True, y='stress', y_mean=True,x_idx=1, y_idx=0, alpha=1, mcolor='r')
  
    #data.plot_lattice_strain_all(lat_ax='x', ax2='stress', ax2_mean=True, phi=0, window=15, frame=10, ax2_idx=1)

    
    #data.plot_lattice_strain(family='200', lat_ax='x', # Choose the family and axis to plot the strains on
    #                  phi=0, window=15,frame=0, # The angle to the loading axis and range around this to select grains/planes 
    #                  ax2='strain', ax2_idx=1, ax2_mean=True)
    
    #data.plot_lattice_strain_all(lat_ax='x', 
    #                 phi=90, window=15,frame=0,
    #                 ax2='stress', ax2_idx=1, ax2_mean=True)
    
    #data.plot_back_lattice(back_ax='y', b_idx=None,ax2='back stress', ax2_idx=1, family='200', phi=0, window=15, frame=0, alpha=0.2, color='k', mcolor='r',plot_select=True)

    #data.plot_eslip_lattice(back_ax='y', b_idx=None ,ax2='stress', ax2_idx=1, family='220', phi=0, window=15, frame=50, alpha=0.2, color='k', mcolor='r',plot_select=True)

   # data.plot_lattice_strain_map(family='200', az_bins=19, ax2='time',
    #                            ax2_idx=1)

    #data.plot_active_slip_all(back_ax='y', b_active = 2,
    #                      ax2='strain', ax2_idx=1, 
    #                      phi=0, window=15, frame=0)
    
    