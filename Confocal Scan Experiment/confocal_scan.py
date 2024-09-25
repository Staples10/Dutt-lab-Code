import numpy as np
from src.Controller import MCLNanoDrive, ADwinGold
from src.core import Parameter, Experiment
import os

class ConfocalScan(Experiment):
    '''
    This class runs a confocal microscope scan using the MCL NanoDrive and the ADwin Gold.

    NOTE THIS IS UNFINISHED AND UNTESTED
    '''

    _DEFAULT_SETTINGS = [
        Parameter('point_a',    #start corner of scanning grid
                  [Parameter('x',0,float,'x-coordinate start in microns'),
                         Parameter('y',0,float,'y-coordinate start in microns')
                  ]),
        Parameter('point_a',
                  [Parameter('x',10,float,'x-coordinate end in microns'),
                         Parameter('y', 10, float, 'y-coordinate end in microns')
                  ]),
        Parameter('resolution', .1, float, 'Resolution of each pixel in microns'),

        Parameter('time_per_pt', 2.0, [0.267,0.5,1.0,2.0], 'Time in ms at each point to get counts'),
        Parameter('control_clock', 'Pixel', ['Pixel','Line','Frame','Aux'], 'Nanodrive clocked used for correlating specific point with counts')
    ]

    #For actual experiment use LP100 [MCL_NanoDrive({'serial':2849})]. For testing using HS3 ['serial':2850]
    _DEVICES = {'nanodrive': MCLNanoDrive(settings={'serial':2849}), 'adwin':ADwinGold()}
    _EXPERIMENTS = {}

    def __init__(self, devices, experiments=None, name=None, settings=None, log_function=None, data_path=None):
        """
        Example of a experiment that emits a QT signal for the gui
        Args:
            name (optional): name of experiment, if empty same as class name
            settings (optional): settings for this experiment, if empty same as default settings
        """
        super().__init__(name, settings=settings, sub_experiments=experiments, devices=devices, log_function=log_function, data_path=data_path)
        #get instances of devices
        self.nd = self.devices['nanodrive']['instance']
        self.adw = self.devices['adwin']['instance']



    def setup_scan(self):
        counter_script = os.path.join(os.path.dirname(os.path.dirname(__file__)),'src','Controller','binary_files','ADbasic','Trial_Counter.TB1')
        self.nd.update({'load_rate':self.settings['time_per_pt']})
        self.adw.update({'process_1':{'load':counter_script,'delay':self.settings['time_per_pt]']/2}})
        #Need to understand how time_per_pt is actually calculated. Load time in nanodrive

        #array form point_a x,y to point_b x,y with step of resolution
        step = self.settings['resolution']
        self.x_array = np.arange(self.settings['point_a']['x'], self.settings['point_b']['x']+step, step)
        self.y_array = np.arange(self.settings['point_a']['y'], self.settings['point_b']['y']+step, step)

        #arrays for position and counts at each position might need to add indeies i,j to correlate
        self.x_data = []
        self.y_data = []
        self.count_data = []


    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        i,j = 0     #index to have position matrix and count matrix line up
        self.adw.update({'process_1':{'start':True}})

        for x in self.x_array:
            self.nd.update({'x_pos':x})
            x_pos = self.nd.read_probes('x_pos')
            self.x_data[i] = x_pos

            for y in self.y_array:
                self.nd.update({'y_pos':y})
                y_pos = self.nd.read_probes('y_pos')
                self.y_data[j] = y_pos

                counts = self.adw.read_probes('int_var',id=1)
                self.count_data[i][j] = counts

        print('Position Data: ','\n',self.x_data,'\n',self.y_data)
        print('Counts: ','\n',self.count_data)



