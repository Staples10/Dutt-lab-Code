from src.core import Device,Parameter

from ctypes import *
import os

'''
To update for next version:
 
 -Make binding/unbinding more intuitive
 -add clocks into update method if changing parameters in GUI only triggers update
    Need to figure out what is called when paras are changed in GUI is it just calling update method?
    Current issue of when changing clock dictionary will override all and leave incomplete
        ie. {full dic} --> {clocks:{pixel:{mode:0}}}
 -Internal functions to convert mode and polarity from 0/1 to words so GUI is more intuitive
 
 
New to this version:
 -load DLL before calling super().__init__ so nanodrive interfaces properly with GUI
 -default postion to 0
 -add connect for serial in update
 -add description of class
 -add x,y,z position to parameters and read probes
    Need to figure out what is called when parameters are changed in GUI is it just calling update method?
    Having axis=None may not be implementable in context of GUI but still usable when writing experiment
 
 -Clock parameters changed so dictionary only goes 1 deep. If dic goes 2 deep updating overrides unimputed parameters
    Also changed read probes to return all clock settings in line with parameter change
'''


class MCL_NanoDrive(Device):
    """
    This class implements the Mad City Labs NanoDrive. The class loads the
    madlib.dll library to communicate with the device.
    """
    _DEFAULT_SETTINGS = Parameter([Parameter('serial',2850,int,'serial of specific Nano Drive. Dutt labs LP100:2849 & HS3:2850 (20 bit systems)'),
                                   Parameter('x_pos',0,float,'position of x axis in microns'),
                                   Parameter('y_pos', 0, float, 'position of y axis in microns'),
                                   Parameter('z_pos', 0, float, 'position of z axis in microns'),
                                   Parameter('read_rate',2.0,[0.267,0.5,1.0,2.0,10.0,17.0,20.0],'value in ms'),
                                   Parameter('load_rate',2.0,float,'ms/point load rate. Valid values 1/6-5 ms'),
                                   Parameter('num_datapoints',1,list(range(1,6667)),'number of data points used for waveforms'),
                                   Parameter('axis', 'x', ['x', 'y', 'z', 'aux'],'axis for load/read waveforms. Aux not a valid axis on lab nanodrive'),
                                   Parameter('load_waveform',[0],list, 'waveform to be loaded to nanodrive'),
                                   Parameter('read_waveform',[0],list,'waveform read from nanodrive'),
                                   Parameter('mult_ax',[
                                             Parameter('waveform',[[0],[0],[0]],list,'lists for multi axis waveform. Ex: [[x_wf],0,[z_wf]]. Input trigger("arbitrary key", mult_ax_stop=True) to stop'),
                                             Parameter('time_step',1.0,[0.267,0.5,1.0,2.0],'time step between datapoints in ms'),
                                             Parameter('iterations',1,int,'Number of iterations to run through multi axis waveform. 0 = infinite')
                                             ]),
                                   Parameter('Pixel',[
                                             Parameter('mode',0,[0,1],'low=0, high=1'),
                                             Parameter('polarity',0,[0,1],'0:low-to-high, 1:high-to-low'),
                                             Parameter('binding','read',['x','y','z','aux','read','load','none'],'axis/event to bind to')
                                       ]),
                                   Parameter('Line',[
                                             Parameter('mode',0,[0,1],'low=0, high=1'),
                                             Parameter('polarity', 0, [0, 1], '0:low-to-high, 1:high-to-low'),
                                             Parameter('binding', 'load', ['x', 'y', 'z', 'aux', 'read', 'load','none'],'axis/event to bind to')
                                       ]),
                                   Parameter('Frame',[
                                             Parameter('mode',0,[0,1],'low=0, high=1'),
                                             Parameter('polarity',0,[0,1],'0:low-to-high, 1:high-to-low'),
                                             Parameter('binding','none',['x','y','z','aux','read','load','none'],'axis/event to bind to')
                                       ]),
                                   Parameter('Aux',[
                                             Parameter('mode',0,[0,1],'low=0, high=1'),
                                             Parameter('polarity',0,[0,1],'0:low-to-high, 1:high-to-low'),
                                             Parameter('binding','none',['x','y','z','aux','read','none'],'axis/event to bind to')
                                       ])
                                   ])

    def __init__(self, name=None, settings=None):
        try:            #Loads DLL file. Should be in same folder as nanodrive.py
            self.DLL = windll.LoadLibrary(os.path.join(os.path.dirname(__file__),'madlib.dll'))
        except (OSError, WindowsError) as error:
            print('Unable to load Mad City Labs DLL')
            raise
        super(MCL_NanoDrive, self).__init__(name, settings)

        self.empty_waveform = [0]       #arbitray empty waveform to be used in 'read_waveform':MCL_NanoDrive.empty_waveform. Proper size is created in appropriate method
        self.set_read_waveform = False  #setup status to false so that a trigger doesnt occur without a setup
        self.set_load_waveform = False
        self.set_mult_ax_waveform = False

        #set an error dictionary to see what issue device runs into
        self.mcl_error_dic = {
            -1: lambda:self._raise_error('GENERAL_ERROR: These errors generally occur due to an internal sanity check failing.'),
            -2: lambda:self._raise_error('DEVICE_ERROR: A problem occurred when transferring data to the Nano Drive. It is likely that the Nano Drive will have to be power cycled to correct these errors.'),
            -3: lambda:self._raise_error('DEVICE_NOT_ATTACHED: The Nano Drive cannot complete the task because it is not attached.'),
            -4: lambda:self._raise_error('USAGE_ERROR: Using a function from the library which the Nano Drive does not support causes these errors.'),
            -5: lambda:self._raise_error('DEVICE_NOT_READY: The Nano Drive is currently completing or waiting to complete another task.'),
            -6: lambda:self._raise_error('ARGUMENT_ERROR: An argument is out of range or a required pointer is equal to NULL.'),
            -7: lambda:self._raise_error('INVALID_AXIS: Attempting an operation on an axis that does not exist in the Nano Drive.'),
            -8: lambda:self._raise_error('INVALID_HANDLE: The handle is not valid or at least not valid in this instance of DLL.')
        }
        self._initilize_handle()

    def _initilize_handle(self):
        #Grabs all handles and controls handle corresponding to serial
        numDevices = self.DLL.MCL_GrabAllHandles()
        self.handle = c_int(self.DLL.MCL_GetHandleBySerial(c_short(self.settings['serial'])))
        self.settings['x_pos'] = self.read_probes('x_pos')  #reads current position when initilizing handle to show correct value
        self.settings['y_pos'] = self.read_probes('y_pos')  #Note if you switch handles in GUI will not update number in box
        self.settings['z_pos'] = self.read_probes('z_pos')
        return numDevices, self.handle

    def __del__(self):
        #at the end of running program releases control of handle if not already closed
        self.DLL.MCL_ReleaseHandle(self.handle)

    def update(self, settings):
        '''
        Updates internal settings of NanoDrive and physical position parameter to single value or through the values of a waveform
        Args:
            settings: a dictionary in the standard settings format
                -waveforms can be made using numpy arrays but inputs should be lists ie. wf = list(np.arrange(#,#,#))
        ex:
            update(settings={'x_pos':5}) for setting position
            update(settings = {'axis':'x', 'num_datapoints':len(waveform), 'load_waveform':waveform})
        '''

        super(MCL_NanoDrive, self).update(settings) #updates settings as per entered with method

        if self._settings_initilized:
            for key, value in settings.items():     #goes through inputed settings to see what commands to send ot update parameters
                if key == 'serial':
                    self._initilize_handle()    #changes handle under control

                elif key in ['x_pos','y_pos','z_pos']:      #updates axis position
                    axis = self._axis_to_internal(key)
                    error = self._check_error(self.DLL.MCL_SingleWriteN(c_double(value), axis, self.handle))

                elif key == 'load_waveform':    #loads waveform onto specified axis
                    if self.settings['num_datapoints'] != len(settings['load_waveform']):
                        print('Error: Length of waveform input list does not match number of data points')
                        raise
                    ArrayType = c_double * self.settings['num_datapoints']  #creates empty array of proper length
                    wf = ArrayType(*settings['load_waveform'])              #fills array with waveform values
                    load_rate = self._load_rate_check(self.settings['load_rate'])
                    axis = self._axis_to_internal(self.settings['axis'])
                    error = self._check_error(self.DLL.MCL_LoadWaveFormN(axis,c_uint(self.settings['num_datapoints']),load_rate,byref(wf),self.handle))

    def setup(self, settings, axis=None):
        '''
        Updates internal settings of NanoDrive and sets up for triggering commands
        Args:
            settings: a dictionary in the standard settings format
                -waveforms can be made using numpy arrays but inputs should be lists ie. wf = list(np.arrange(x,x,x))
            axis: specific axis to move (can also specify in settings dictionary). If not specified sets up last interacted with axis
        '''
        super(MCL_NanoDrive, self).update(settings)
        if axis != None:
            self.settings['axis'] = axis
        axis = self._axis_to_internal(self.settings['axis'])

        for key, value in settings.items():
            if key == 'read_waveform':  #arbitrary value for read_wf key but value must be a list. Can input MCL_NanoDrive.empty_waveform
                read_rate = self._read_rate_to_internal(self.settings['read_rate'])
                error = self._check_error(self.DLL.MCL_Setup_ReadWaveFormN(axis,c_uint(self.settings['num_datapoints']),read_rate,self.handle))
                self.set_read_waveform = True   #lets trigger_read and waveform_acquisition run

            elif key == 'load_waveform':
                if self.settings['num_datapoints'] != len(settings['load_waveform']):
                    print('Error: Length of waveform imput list does not match number of data points')
                    raise
                ArrayType = c_double * self.settings['num_datapoints']
                wf = ArrayType(*settings['load_waveform'])
                load_rate = self._load_rate_check(self.settings['load_rate'])
                error = self._check_error(self.DLL.MCL_Setup_LoadWaveFormN(axis,c_uint(self.settings['num_datapoints']),load_rate,byref(wf),self.handle))
                self.set_load_waveform = True    #lets trigger_load and waveform_acquisition run

            elif key == 'mult_ax':
                if 'time_step' not in settings['mult_ax'] or 'iterations' not in settings['mult_ax']:   #check to make sure time_step and iterations are specified
                    print('Input both time_step and iterations parameters')
                    raise
                self.mult_ax_num_points = self.settings['num_datapoints']
                wf = self._multiaxis_waveform(settings['mult_ax']['waveform'])  #makes waveform into proper format
                if not self.mult_ax_num_points==len(wf[0])==len(wf[1])==len(wf[2]):
                    print('ERROR: Length of waveform input lists do not match number of data points. Note TOTAL number of data points is 6666.')
                    raise
                time_step = self._time_step_to_internal(settings['mult_ax']['time_step'])
                iterations = c_ushort(settings['mult_ax']['iterations'])
                error = self._check_error(self.DLL.MCL_WfmaSetup(byref(wf[0]), byref(wf[1]), byref(wf[2]), c_uint(self.settings['num_datapoints']), time_step, iterations, self.handle))
                self.set_mult_ax_waveform = True

    def trigger(self, key, axis=None, mult_ax_stop=False):
        '''
        Triggers set up commands
        Args:
            key: the key of a parameter in the settings dictionary to specify what setup to trigger ['read_waveform' or 'load_waveform' or 'mult_ax']
            axis: specific axis to move (can also specify in settings dictionary). If not specified will trigger last interacted with axis
            mult_ax_stop=True to stop multi axis waveform (input along with arbirtrary key)
        '''
        if mult_ax_stop:
            error = self._check_error(self.DLL.MCL_WfmaStop(self.handle))
            return None
        if axis != None:
            self.settings['axis'] = axis
        axis = self._axis_to_internal(self.settings['axis'])

        if key == 'read_waveform':
            if not self.set_read_waveform:      #checks to see if read waveform has been set
                print('ERROR: Read waveform has not been set!')
                raise
            else:
                ArrayType = c_double * self.settings['num_datapoints']
                empty_wf = ArrayType()
                error = self._check_error(self.DLL.MCL_Trigger_ReadWaveFormN(axis,c_uint(self.settings['num_datapoints']),byref(empty_wf),self.handle))
                return list(empty_wf)   #returns read sensor data

        elif key == 'load_waveform':
            if not self.set_load_waveform:      #checks to see if load waveform has been set
                print('ERROR: Load waveform has not been set!')
                raise
            error = self._check_error(self.DLL.MCL_Trigger_LoadWaveFormN(axis,self.handle))

        elif key == 'mult_ax':
            if not self.set_mult_ax_waveform:
                print('ERROR: Multi-axis waveform not set!')
                raise
            else:
                error = self._check_error(self.DLL.MCL_WfmaTrigger(self.handle))

    def waveform_acquisition(self, axis=None, num_datapoints=None):
        '''
        Tiggers a waveform acquisition which loads and reads a waveform on one axis
        Args:
            axis if internal settings have been changed since setting up load and read waveform
            num_datapoints if internal settings have been changed since setting up load and read waveform
        returns array of position values
        '''
        if not self.set_load_waveform:  # checks to see if load waveform has been set
            print('ERROR: Load waveform has not been set!')
            raise
        if not self.set_read_waveform:  # checks to see if read waveform has been set
            print('ERROR: Read waveform has not been set!')
            raise
        if axis != None:
            self.settings['axis'] = axis
        if num_datapoints != None:
            self.settings['num_datapoints'] = num_datapoints
        else:
            axis = self._axis_to_internal(self.settings['axis'])
            ArrayType = c_double * self.settings['num_datapoints']
            empty_wf = ArrayType()  # creates empty array for read data
            error = self._check_error(self.DLL.MCL_TriggerWaveformAcquisition(axis, c_uint(self.settings['num_datapoints']),byref(empty_wf), self.handle))
            return list(empty_wf)

    def clock_functions(self, clock, mode=None, polarity=None, binding=None, reset=False, pulse=False):
        '''
        Updates clock settings by sending relevant command to NanoDrive. See _Default_Settings for binding options
        Args:
            clock: string of clock name
            mode: 0 for low, 1 for high
            polarity: 0 = low-to-high pulses, 1 = high-to-low pulses, 2 for unbinding with binding input
                -Note: If clock is binded, axis/event polarity is independent of pulse polarity
            binding: binds to axis read or event (must specify polarity)
                -if bound to read every time a point is recorded a pulse is generated
                -if bound to load pulse is generated prior to first point and after the last point
            reset=True to reset ALL clocks to defaults (with arbitrary clock input)
            pulse=True to generate a 250ns pulse on specified clock (pulse triggers after polarity and mode update)
        '''
        if reset:
            error = self._check_error(self.DLL.MCL_IssResetDefaults(self.handle))
            reset_settings = {'Pixel':{'mode':0,'polarity':0,'binding':'read'}, 'Line':{'mode': 0,'polarity': 0,'binding':'load'}, 'Frame':{'mode':0,'polarity': 0,'binding':'none'}, 'Aux':{'mode':0,'polarity':0,'binding':'none'}}
            super(MCL_NanoDrive, self).update(reset_settings)
            return None
        clock_name = self._clocks_to_internal(clock, cap=True)  #needed for pulse command and to update settings
        clock = self._clocks_to_internal(clock_name)
        if mode != None:
            error = self._check_error(self.DLL.MCL_IssSetClock(clock, c_int(mode), self.handle))
            self.settings[clock_name]['mode'] = mode
        if polarity != None and binding == None:
            error = self._check_error(self.DLL.MCL_IssConfigurePolarity(clock, c_int(polarity+2), self.handle))
            self.settings[clock_name]['polarity'] = polarity
        if binding != None:
            if polarity == None:
                print('Polarity must be specified for binding [0:low-to-high, 1:high-to-low, 2:unbind]')
                raise
            else:
                bind_to_axis = self._bind_axis_to_internal(binding)
                bind_polarity = self._bind_polarity_fix(polarity)
                error = self._check_error(self.DLL.MCL_IssBindClockToAxis(clock, bind_polarity, bind_to_axis, self.handle))
                self.settings[clock_name]['binding'] = binding
        if pulse:
            error = self._check_error(getattr(self.DLL, f'MCL_{clock_name}Clock')(self.handle)) #getattr assembles the self.DLL+MCL_PixelClock+(self.handle) command
        return None

    def read_probes(self, key, axis=None):
        assert(self._settings_initialized)
        assert key in list(self._PROBES.keys())

        if axis != None:
            self.settings['axis'] = axis
        axis = self._axis_to_internal(self.settings['axis'])

        if key in ['x_range','y_range','z_range']:
            axis = self._axis_to_internal(key)
            self.DLL.MCL_GetCalibration.restype = c_double
            value = self._check_error(self.DLL.MCL_GetCalibration(axis, self.handle))
        elif key in ['x_pos','y_pos','z_pos']:
            axis = self._axis_to_internal(key)
            self.DLL.MCL_SingleReadN.restype = c_double
            value = self._check_error(self.DLL.MCL_SingleReadN(axis, self.handle))

        elif key == 'read_waveform':    #reads waveform for given axis and stores sensor data in read_waveform
            ArrayType = c_double * self.settings['num_datapoints']  #creates empty array with correct number of datapoints
            empty_wf = ArrayType()
            read_rate = self._read_rate_to_internal(self.settings['read_rate'])
            error = self._check_error(self.DLL.MCL_ReadWaveFormN(axis,c_uint(self.settings['num_datapoints']),read_rate,byref(empty_wf),self.handle))
            value = list(empty_wf)
            #Note to read must be triggered within ~3ms otherwise returns list with every value equal to the current position.
            #Should be good if load and read lines are consecutive. Or use wavefrom_acquisition for simultaneous load and read.

        elif key == 'mult_ax_waveform':     #reading waits for mult_ax waveform to stop triggering or stops an infinite loop
            empty_waveform = self._multiaxis_waveform([0], empty=True)
            self._check_error(self.DLL.MCL_WfmaRead(byref(empty_waveform[0]),byref(empty_waveform[1]),byref(empty_waveform[2]),self.handle))
            value = [list(empty_waveform[0]),list(empty_waveform[1]),list(empty_waveform[2])]

        elif key == 'read_rate':
            value = self.settings['read_rate']
        elif key == 'load_rate':
            value = self.settings['load_rate']
        elif key == 'num_datapoints':
            value = self.settings['num_datapoints']
        elif key == 'clock_settings':
            value = {
                'Pixel': self.settings['Pixel'],
                'Line': self.settings['Line'],
                'Frame': self.settings['Frame'],
                'Aux': self.settings['Aux']
            }

        return value

    @property
    def _PROBES(self):
        return {
            #ask device
            'x_range': 'position range of x axis',
            'y_range': 'position range of y axis',
            'z_range': 'position range of z axis',
            'x_pos': 'current position of x axis',
            'y_pos': 'current position of y axis',
            'z_pos': 'current position of z axis',
            'read_waveform': 'reads current waveform',
            'mult_ax_waveform': 'reads multi axis waveform',
            #check code parameters
            'read_rate':'rate to read waveform data',
            'load_rate':'rate to upload waveform data',
            'num_datapoints':'number of data points of waveform',
            'clock_settings':'internal parameters of all clocks'
        }

    @property
    def is_connected(self):
        #true if connected, false if not
        self.DLL.MCL_DeviceAttached.restype = c_bool
        return self.DLL.MCL_DeviceAttached(0,self.handle)

    @property
    def device_info(self):
        #prints product name, id, DLL version, firmware version, and other information
        return self.DLL.MCL_PrintDeviceInfo(self.handle)

    def close(self):
        #releases control of the handle under control in this instance
        self.DLL.MCL_ReleaseHandle(self.handle)

    #2 error functions to see if an error occured when sending a command and raise the error if it does
    def _raise_error(self, message):
        raise Exception(message)
    def _check_error(self, value):  #returns inputed value if not an error value. If error value raises error encounted
        check_error = self.mcl_error_dic.get(value, lambda:value)
        return check_error()

    def _axis_to_internal(self, axis):
        if axis == 'x' or axis == 'x_pos' or axis == 'x_range':
            return c_uint(1)
        elif axis == 'y' or axis == 'y_pos' or axis == 'y_range':
            return c_uint(2)
        elif axis == 'z' or axis == 'z_pos' or axis == 'z_range':
            return c_uint(3)
        elif axis == 'aux':
            return c_uint(4)
        else:
            raise KeyError

    def _read_rate_to_internal(self, value):
        #Value in milliseconds. See _Default_Settings for accepted values
        if value == 0.267:
            return c_double(3)
        if value == 0.5:
            return c_double(4)
        if value == 1:
            return c_double(5)
        if value == 2:
            return c_double(6)
        if value == 10:
            return c_double(7)
        if value == 17:
            return c_double(8)
        if value == 20:
            return c_double(9)
        else:
            raise KeyError

    def _load_rate_check(self, value):
        #Value in milliseconds
        if value >= 1/6 and value <= 5:
            return c_double(value)
        else:
            raise KeyError

    def _multiaxis_waveform(self, input_list, empty=False):
        '''
        Sets waveform as empty if input is 0 ie [[x_waveform], [0], [z_waveform]]
        else returns properly formated waveform array.
        All none zero waveforms should be the same number of datapoints!
        '''

        ArrayType = c_double * self.mult_ax_num_points
        #ensures that len of mult_ax waveform is the same as last loaded mult_ax instaed of last loaded single axis wavefrom
        x_waveform = y_waveform = z_waveform = ArrayType()
        if empty:
            return [x_waveform, y_waveform, z_waveform]
        else:
            if input_list[0] != [0]:
                x_waveform = ArrayType(*input_list[0])
            if input_list[1] != [0]:
                y_waveform = ArrayType(*list[1])
            if input_list[0] != [0]:
                z_waveform = ArrayType(*input_list[2])
            return [x_waveform, y_waveform, z_waveform]

    def _time_step_to_internal(self, value):
        #Value in milliseconds. See _Default_Settings for accepted values
        if value == 0.267:
            return c_double(3)
        if value == 0.5:
            return c_double(4)
        if value == 1:
            return c_double(5)
        if value == 2:
            return c_double(6)
        else:
            raise KeyError

    def _clocks_to_internal(self, name, cap=False):
        if cap:
           return name.capitalize()
        elif name == 'Pixel':
            return c_int(1)
        elif name == 'Line':
            return c_int(2)
        elif name == 'Frame':
            return c_int(3)
        elif name == 'Aux':
            return c_int(4)
        else:
            raise KeyError

    def _bind_axis_to_internal(self, axis):
        axis = axis.lower()
        if axis == 'x':
            return c_int(1)
        elif axis == 'y':
            return c_int(2)
        elif axis == 'z':
            return c_int(3)
        elif axis == 'aux':
            return c_int(4)
        elif axis == 'read':
            return c_int(5)
        elif axis == 'load':
            return c_int(6)
        else:
            raise KeyError

    def _bind_polarity_fix(self, polarity):
        '''
        Issue where polarity options for binding are the opposite of normal polarity options.
        This function serves to make the user input the same so that 0 = low-to-high and 1 = high-to-low always
        '''
        if polarity == 0:
            return c_int(3)
        elif polarity == 1:
            return c_int(2)
        elif polarity == 2:
            return c_int(4)
        else:
            raise KeyError

if __name__ == '__main__':
    nd = MCL_NanoDrive()
    print(nd.is_connected)
    nd.close()