"""Unit tests for orbitpy.orbitpropcov.OrbitPropCovGrid class covering checks on format of produced output files and
   propagation states.

   :code:`/temp/` folder contains temporary files produced during the run of the tests below. SOme of the parameters are chosen
   randomly for the tests (and compared with corresponding outputs), hence each test is run with different inputs, and expected 
   outputs. 

"""

import unittest
import json
import numpy
import sys, os, shutil
import subprocess
import copy
import numpy as np
import pandas as pd
import random

from orbitpy.orbitpropcov import OrbitPropCovGrid
from orbitpy.util import PropagationCoverageParameters, CoverageCalculationsApproach

RE = 6378.137 # [km] radius of Earth

class TestOrbitPropCovGrid(unittest.TestCase):

    def __init__(self, *args, **kwargs):
        # Create new directory to store output of all the class functions. 
        dir_path = os.path.dirname(os.path.realpath(__file__))
        out_dir = os.path.join(dir_path, 'temp')
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(out_dir)

        # create a default set of propagation and coverage parameters specs
        self.default_pcp = PropagationCoverageParameters(
                        sat_id="1", 
                        epoch="2018,5,26,12,0,0", # JD: 2458265.00000
                        sma=RE+random.uniform(350,850), 
                        ecc=0.001, 
                        inc=random.uniform(0,180), 
                        raan=random.uniform(0,360), 
                        aop=random.uniform(0,360), 
                        ta=random.uniform(0,360), 
                        duration=random.random(), 
                        cov_grid_fl=dir_path+"/temp/covGrid", 
                        sen_fov_geom="CONICAL", 
                        sen_orien="1,2,3,0,0,0",
                        sen_clock="0", 
                        sen_cone=str(random.uniform(5,60)), 
                        purely_sidelook = 0, 
                        yaw180_flag = 0, 
                        step_size = 0.1+random.random(), 
                        sat_state_fl = dir_path+"/temp/state", 
                        sat_acc_fl = dir_path+"/temp/acc", 
                        cov_calcs_app= CoverageCalculationsApproach.GRIDPNTS)


        super(TestOrbitPropCovGrid, self).__init__(*args, **kwargs)

    def produce_cov_grid(self, sat_id, latUpper, latLower, lonUpper, lonLower, grid_res):
        """ Write a coverage grid file. """
        dir_path = os.path.dirname(os.path.realpath(__file__))
        prc_args = [os.path.join(dir_path, '..', '..', 'oci', 'bin', 'genCovGrid')] 

        cov_grid_fl = dir_path + "/temp/covGrid" # coverage grid file path        
        prc_args.append(cov_grid_fl)

        prc_args.append(str(sat_id)+','+str(latUpper)+','+str(latLower)+
                            ','+str(lonUpper)+','+str(lonLower)+','+str(grid_res) # same grid resolution for all regions
                            )
        result = subprocess.run(prc_args, check= True)

    def test_run_1(self):
        """ Test the output format of state and access files.""" 
        
        TestOrbitPropCovGrid.produce_cov_grid(self, 1, 0, -10, 10, 0, 1)

        prop_cov_param = copy.deepcopy(self.default_pcp)
        opc_grid = OrbitPropCovGrid(prop_cov_param)
        opc_grid.run()

        ##### state file test ##### 
        sat_state_fl = prop_cov_param.sat_state_fl

        epoch_JDUT1 = pd.read_csv(sat_state_fl, skiprows = [0], nrows=1, header=None).astype(str) # 2nd row contains the epoch
        epoch_JDUT1 = float(epoch_JDUT1[0][0].split()[2])
        self.assertEqual(epoch_JDUT1, 2458265.00000)

        step_size = pd.read_csv(sat_state_fl, skiprows = [0,1], nrows=1, header=None).astype(str) # 3rd row contains the stepsize
        step_size = float(step_size[0][0].split()[4])
        self.assertAlmostEqual(step_size, prop_cov_param.step_size)

        duration = pd.read_csv(sat_state_fl, skiprows = [0,1,2], nrows=1, header=None).astype(str) # 4th row contains the mission duration
        duration = float(duration[0][0].split()[4])
        self.assertAlmostEqual(duration, prop_cov_param.duration)

        column_headers = pd.read_csv(sat_state_fl, skiprows = [0,1,2,3], nrows=1, header=None).astype(str) # 5th row contains the columns headers
        self.assertEqual(column_headers.iloc[0][0],"TimeIndex")
        self.assertEqual(column_headers.iloc[0][1],"X[km]")
        self.assertEqual(column_headers.iloc[0][2],"Y[km]")
        self.assertEqual(column_headers.iloc[0][3],"Z[km]")
        self.assertEqual(column_headers.iloc[0][4],"VX[km/s]")
        self.assertEqual(column_headers.iloc[0][5],"VY[km/s]")
        self.assertEqual(column_headers.iloc[0][6],"VZ[km/s]")
        
        data = pd.read_csv(sat_state_fl, skiprows = [0,1,2,3]) # 5th row header, 6th row onwards contains the data
        self.assertEqual(data["TimeIndex"].iloc[0],0)
        self.assertEqual(data["TimeIndex"].iloc[1],1)
        self.assertAlmostEqual((data["TimeIndex"].iloc[-1] + 1)*step_size, duration*86400, delta = 60) # almost equal, probably due to errors introduced by floating-point arithmetic

        ##### access_ file test ##### 
        inter_access_fl = prop_cov_param.sat_acc_fl + '_'

        epoch_JDUT1 = pd.read_csv(inter_access_fl, skiprows = [0], nrows=1, header=None).astype(str) # 2nd row contains the epoch
        epoch_JDUT1 = float(epoch_JDUT1[0][0].split()[2])
        self.assertEqual(epoch_JDUT1, 2458265.00000)

        step_size = pd.read_csv(inter_access_fl, skiprows = [0,1], nrows=1, header=None).astype(str) # 3rd row contains the stepsize
        step_size = float(step_size[0][0].split()[4])
        self.assertAlmostEqual(step_size, prop_cov_param.step_size)

        duration = pd.read_csv(inter_access_fl, skiprows = [0,1,2], nrows=1, header=None).astype(str) # 4th row contains the mission duration
        duration = float(duration[0][0].split()[4][:-1])
        self.assertAlmostEqual(duration, prop_cov_param.duration)

        column_headers = pd.read_csv(inter_access_fl, skiprows = [0,1,2,3], nrows=1, header=None).astype(str) # 5th row contains the columns headers
        self.assertEqual(column_headers.iloc[0][0],"TimeIndex")

        covData = pd.read_csv(prop_cov_param.cov_grid_fl)
        num_of_gps = len(covData["gpi"])
        for i in range(0,num_of_gps):
            self.assertEqual(column_headers.iloc[0][i+1],"GP"+str(i))


        ##### access file test ##### 
        access_fl = prop_cov_param.sat_acc_fl

        epoch_JDUT1 = pd.read_csv(access_fl, skiprows = [0], nrows=1, header=None).astype(str) # 2nd row contains the epoch
        epoch_JDUT1 = float(epoch_JDUT1[0][0].split()[2])
        self.assertEqual(epoch_JDUT1, 2458265.00000)

        step_size = pd.read_csv(access_fl, skiprows = [0,1], nrows=1, header=None).astype(str) # 3rd row contains the stepsize
        step_size = float(step_size[0][0].split()[4])
        self.assertAlmostEqual(step_size, prop_cov_param.step_size)

        duration = pd.read_csv(access_fl, skiprows = [0,1,2], nrows=1, header=None).astype(str) # 4th row contains the mission duration
        duration = float(duration[0][0].split()[4][:-1])
        self.assertAlmostEqual(duration, prop_cov_param.duration)

        column_headers = pd.read_csv(access_fl, skiprows = [0,1,2,3], nrows=1, header=None).astype(str) # 5th row contains the columns headers
        self.assertEqual(column_headers.iloc[0][0],"accessTimeIndex")
        self.assertEqual(column_headers.iloc[0][1],"regi")
        self.assertEqual(column_headers.iloc[0][2],"gpi")
        self.assertEqual(column_headers.iloc[0][3],"lat[deg]")
        self.assertEqual(column_headers.iloc[0][4],"lon[deg]")

    def test_run_2(self):
        """ Test the satellite altitude, orbital time-period, speed.""" 
        TestOrbitPropCovGrid.produce_cov_grid(self, 1, 0, -10, 10, 0, 1)

        prop_cov_param = copy.deepcopy(self.default_pcp)
        prop_cov_param.duration = 0.1 # for faster computation
        prop_cov_param.ecc = 0.0 # circular orbit
        prop_cov_param.sma = RE+random.uniform(350,850) # randomly chosen SMA, hence altitude

        # run the propagator
        opc_grid = OrbitPropCovGrid(prop_cov_param)
        opc_grid.run()
        sat_state_fl = prop_cov_param.sat_state_fl
        data = pd.read_csv(sat_state_fl, skiprows = [0,1,2,3]) # 5th row header, 6th row onwards contains the data
        
        ##### altitude test ##### 
        alt_in =  prop_cov_param.sma - RE
        ds = data.sample().reset_index() # randomly select a row (time) altitude should be same since circular orbit
        alt_out = np.linalg.norm([ds["X[km]"], ds["Y[km]"], ds["Z[km]"]]) - RE 
        self.assertAlmostEqual(alt_in, alt_out, delta=20) # 20km difference possible?

        ##### orbital speed test ##### 
        sma = prop_cov_param.sma
        orb_sp_in = np.sqrt(3.9860044188e14/(sma*1e3)) 
        ds = data.sample().reset_index() # randomly select a row (time) orbital speed should be same since circular orbit
        orb_sp_out = np.linalg.norm([ds["VX[km/s]"], ds["VY[km/s]"], ds["VZ[km/s]"]])
        self.assertAlmostEqual(orb_sp_in*1e-3, orb_sp_out, delta=0.2) # 0.2km/s difference possible?

    def test_run_3(self):
        """ Check prograde and retrograd -icity of the orbits."""
        pass