import numpy as np
from src.Controller import MCLNanoDrive, ADwinGold
from src.core import Parameter, Experiment
import os
from time import sleep

#need to empliment ploting and propably change x_data, y_data, etc. arrays with standard self.data and add dictionaries to it
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
        Parameter('point_b',
                  [Parameter('x',10,float,'x-coordinate end in microns'),
                   Parameter('y', 10, float, 'y-coordinate end in microns')
                  ]),
        Parameter('resolution', .1, float, 'Resolution of each pixel in microns'),
        Parameter('time_per_pt', 2.0, [0.267,0.5,1.0,2.0], 'Time in ms at each point to get counts'),
        Parameter('control_clock', 'Pixel', ['Pixel','Line','Frame','Aux'], 'Nanodrive clocked used for correlating specific point with counts')
    ]

    #For actual experiment use LP100 [MCL_NanoDrive({'serial':2849})]. For testing using HS3 ['serial':2850]
    _DEVICES = {'nanodrive': MCLNanoDrive(settings={'serial':2850}), 'adwin':ADwinGold()}
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

        self.setup_scan()



    def setup_scan(self):
        #gets an 'overlaping' path to trial counter in binary_files folder
        trial_counter_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..','..','Controller','binary_files','ADbasic','Trial_Counter.TB1')
        counter_script = os.path.normpath(trial_counter_path)

        #print(trial_counter_path,'\n',counter_script)
        self.nd.update({'load_rate':self.settings['time_per_pt']})
        self.adw.update({'process_1':{'load':counter_script}})
        #Need to understand how time_per_pt is actually calculated. Load time in nanodrive

        print('scan setup')


    def _function(self):
        """
        This is the actual function that will be executed. It uses only information that is provided in the settings property
        will be overwritten in the __init__
        """
        print('started')
        #array form point_a x,y to point_b x,y with step of resolution
        step = self.settings['resolution']
        x_array = np.arange(self.settings['point_a']['x'], self.settings['point_b']['x']+step, step)
        y_array = np.arange(self.settings['point_a']['y'], self.settings['point_b']['y']+step, step)

        #arrays for position and counts at each position might need to add indeies i,j to correlate
        self.x_data = np.zeros(len(x_array))
        self.y_data = np.zeros(len(y_array))
        self.count_data = np.zeros((len(x_array),len(y_array)))
        #self.data['description'] should be used instead of seting new data names


        i = 0    #index to have position matrix and count matrix line up
        j = 0

        #want time_per_pt = full adwin counting and clear cycle (2 lines)
        #time_per_pt = 2 * (delay * 3.3ns)
        adwin_delay = self.settings['time_per_pt'] / (2*3.3e-9)
        self.adw.update({'process_1':{'delay':1212,'start':True}})
        print('process: ', self.adw.read_probes('process_status', id=1))
        print('nd connectd: ',self.nd.is_connected)

        #set inital x and y and set nanodrive stage to that position
        x = self.settings['point_a']['x']
        y = self.settings['point_a']['y']
        self.nd.update({'x_pos':x,'y_pos':y})
        sleep(0.1)  #time for stage to move and adwin process to initilize

        #crashes after sending first x cord to nd maybe cause window trys to plot but plotting isnt set up
        while x <= self.settings['point_b']['x']:
            self.nd.update({'x_pos':x})
            sleep(0.01)
            x_pos = self.nd.read_probes('x_pos')
            self.x_data[i] = x_pos

            while y <= self.settings['point_b']['y']:
                self.nd.update({'y_pos':y})
                sleep(0.01)
                y_pos = self.nd.read_probes('y_pos')
                self.y_data[j] = y_pos
                sleep(self.settings['time_per_pt']*10e-6)   #sleep time for counts at each point. Need to find a reliable way to time
                counts = self.adw.read_probes('int_var',id=1)
                self.count_data[i][j] = counts
                y = y + step
                j = j + 1

            #increment x and set y back to starting point and index
            x = x + step
            y = self.settings['point_a']['y']
            i = i + 1
            j = 0

        print('Position Data: ','\n',self.x_data,'\n',self.y_data)
        print('Counts: ','\n',self.count_data)

        '''
         for x in x_array:
            print('updating nd')
            self.nd.update({'x_pos':x})
            sleep(0.1)
            print('reading probes')
            x_pos = self.nd.read_probes('x_pos')
            self.x_data[i] = x_pos
            print('added to data')

            for y in y_array:
                self.nd.update({'y_pos':y})
                sleep(0.1)
                y_pos = self.nd.read_probes('y_pos')
                self.y_data[j] = y_pos
                print('updated nd y')

                counts = self.adw.read_probes('int_var',id=1)
                self.count_data[i][j] = counts
                print('read counts')
                j = j + 1

            i = i + 1
            j = 0
        '''






