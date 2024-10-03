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
        Parameter('resolution', 0.1, float, 'Resolution of each pixel in microns'),
        Parameter('time_per_pt', 0.5, float, 'Time in ms at each point to get counts'),
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

        #x_array = np.arange(self.settings['point_a']['x'], self.settings['point_b']['x']+step, step)
        #y_array = np.arange(self.settings['point_a']['y'], self.settings['point_b']['y']+step, step)

        #arrays for position and counts at each position might need to add indeies i,j to correlate
        #self.x_data = np.zeros(len(x_array))
        #self.y_data = np.zeros((len(x_array),len(y_array)))
        #self.count_data = np.zeros((len(x_array),len(y_array)))
        #self.data['description'] should be used instead of seting new data names

        #added to make sure data is getting recorded. If still equal none data is not being stored or measured
        self.data['x_pos'] = None
        self.data['y_pos'] = None
        self.data['counts'] = None
        self.data['count_rate'] = None
        self.data['count_img'] = None
        x_data = []
        y_data = []
        count_data = []
        count_rate_data = []

        x_min = self.settings['point_a']['x']
        x_max = self.settings['point_b']['x']
        y_min = self.settings['point_a']['y']
        y_max = self.settings['point_b']['y']
        step = self.settings['resolution']

        i = 0    #index to have position matrix and count matrix line up
        j = 0
        interation_num = 0 #number to track progress

        #plus 1 because in total_iterations because range is inclusive ie. [0,10]
        total_interations = ((x_max - x_min)/step + 1)*((y_max - y_min)/step + 1)
        print('total_interations=',total_interations)

        #want time_per_pt = full adwin counting and clear cycle (2 lines)
        #time_per_pt = 2 * (delay * 3.3ns)
        adwin_delay = int((self.settings['time_per_pt']/1000) / (2*3.3e-9))    #delay value needs to be an integer. Could use round instead. This may make it better to use
        # another
        # form of count/ position coorilation
        self.adw.update({'process_1':{'delay':adwin_delay,'start':True}})
        #print('process: ', self.adw.read_probes('process_status', id=1))
        #print('nd connectd: ',self.nd.is_connected)

        #set inital x and y and set nanodrive stage to that position
        x = x_min
        y = y_min
        self.nd.update({'x_pos':x_min,'y_pos':y_min})
        sleep(0.1)  #time for stage to move to starting posiition and adwin process to initilize


        while x <= x_max:
            self.nd.update({'x_pos':x})
            sleep(0.001)
            x_pos = self.nd.read_probes('x_pos')
            #self.x_data[i] = x_pos
            x_data.append(x_pos)
            self.data['x_pos'] = x_data

            while y <= y_max:
                self.nd.update({'y_pos':y})
                sleep(0.001)
                y_pos = self.nd.read_probes('y_pos')
                #self.y_data[i][j] = y_pos
                y_data.append(y_pos)
                self.data['y_pos'] = y_data


                sleep(self.settings['time_per_pt']/1000)   #sleep time for counts at each point. Need to find a reliable way to time
                counts = self.adw.read_probes('int_var',id=1)
                count_data.append(counts)
                self.data['counts'] = count_data

                #divide time by 1000 to get seconds and divide count by 1000 to get kcounts
                count_rate = (counts/1000)/(self.settings['time_per_pt']/1000)
                count_rate_data.append(count_rate)
                self.data['count_rate'] = count_rate_data

                interation_num = interation_num + 1
                y = y + step
                j = j + 1

            #increment x and set y back to starting point and index
            x = x + step
            y = self.settings['point_a']['y']
            i = i + 1
            j = 0

            #progress updates once then crashes gui!
            self.progress = 100. * interation_num / total_interations
            print('self.progress=',self.progress,'it num: ',interation_num)
            #self.updateProgress.emit(self.progress)
            #print('progress updated')

        print('Data collected')

        self.data['x_pos'] = x_data
        self.data['y_pos'] = y_data
        self.data['counts'] = count_data
        self.data['count_rate'] = count_rate_data
        #print('Position Data: ','\n',self.x_data,'\n',self.y_data)
        #print('Counts: ','\n',self.count_data)

        #convert list to square matrix of count/sec data
        Nx = int(np.sqrt(len(self.data['count_rate'])))
        count_img = np.array(self.data['count_rate'][0:Nx**2])      #converts to numpy array
        count_img = count_img.reshape((Nx, Nx))                 #reshapes array to square matrix

        # line to call update function in experiment parent class and triggers _plot in this class
        self.data.update({'count_img':count_img})
        print('All data: ',self.data)



    def _plot(self, axes_list, data=None):
        if data is None:
            data = self.data

        if data is not None and data is not{}:
            #use axes_list[1] which is bottom graphing section
            fig = axes_list[0].get_figure()
            extent = [self.settings['point_a']['x'],self.settings['point_b']['x'],self.settings['point_a']['y'],self.settings['point_b']['y']]
            implot = axes_list[0].imshow(data['count_img'],cmap='cividis', interpolation='nearest', extent=extent)
            fig.colorbar(implot, label='kcounts/sec')


    def _update(self,axes_list):
        print('Running _update')
        implot = axes_list[0].get_images()[0]
        implot.set_data(self.data['count_img'])

        colorbar = implot.colorbar







