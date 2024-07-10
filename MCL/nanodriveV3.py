from src.core import Device,Parameter

from ctypes import *
import os
import sys

'''
To update for next version:
 
 -May want to consider making axis a nessesarry input so that a load, write does not happen on incorrect axis
 -!! Get Waveforms to work - See how it is updated in device settings else add option to method  [seemed to be no issues when testing pararmeter options]
 -Make binding/unbinding more intuitive
    
New to this version:
 -Error Dictionary [Implemented but might be best to have in the model. Could use same archetype as in this code in model]
 -is_connected works. Needed second argument of how many milliseconds to wait
 - _clock_to_internal works for both 'pixel' and 'Pixel' inputs
 -Added update settings in clock_functions method so that read_probes('clocks') returns current settings
 -Added read_waveform into read_probes method
 -Added way to read multi axis wave form in read_proves
'''


class MCL_NanoDrive(Device):

    _DEFAULT_SETTINGS = Parameter([Parameter('serial',2850,int,'serial of specific Nano Drive. Dutt labs LP100:2849 & HS3:2850'),
                                   Parameter('axis','x',['x','y','z','aux'],'axis of Nano Drive '),
                                   Parameter('position',5.0,float,'position of axis in microns'),
                                   Parameter('read_rate',2.0,[0.267,0.5,1,2,10,17,20],'value in ms. Allowed values and mapping: 3=0.267ms, 4=0.5ms, 5=1ms, 6=2ms, 7=10ms, 8=17ms, 9=20ms'),
                                   Parameter('load_rate',2,float,'ms/point load rate. Valid values 1/6-5'),
                                   Parameter('num_datapoints',1,list(range(1,6667)),'number of data points used for waveforms'),
                                   Parameter('load_waveform',[0],list, 'waveform to be loaded to nanodrive'),
                                   Parameter('read_waveform',[0],list,'waveform read from nanodrive'),
                                   Parameter('mult_ax',[
                                             Parameter('waveform',[[0],[0],[0]],list,'lists for multi axis waveform. Ex: [[x_wf],0,[z_wf]]. Input [[0],[0],[0]] to stop.'),
                                             Parameter('iterations',1,int,'Number of iterations to run through multi axis waveform. 0 = infinite')
                                             ]),
                                   Parameter('clock',[
                                       Parameter('Pixel',[
                                           Parameter('polarity',0,[0,1],'low=0, high=1'),
                                           Parameter('mode',0,[0,1],'0:low-to-high, 1:high-to-low'),
                                           Parameter('binding','read',['x','y','z','aux','read','load','none'],'axis/event to bind to')
                                       ]),
                                       Parameter('Line',[
                                           Parameter('polarity',0,[0,1],'low=0, high=1'),
                                           Parameter('mode', 0, [0, 1], '0:low-to-high, 1:high-to-low'),
                                           Parameter('binding', 'load', ['x', 'y', 'z', 'aux', 'read', 'load','none'],'axis/event to bind to')
                                       ]),
                                       Parameter('Frame',[
                                           Parameter('polarity',0,[0,1],'low=0, high=1'),
                                           Parameter('mode',0,[0,1],'0:low-to-high, 1:high-to-low'),
                                           Parameter('binding','none',['x','y','z','aux','read','load','none'],'axis/event to bind to')
                                       ]),
                                       Parameter('Aux',[
                                           Parameter('polarity',0,[0,1],'low=0, high=1'),
                                           Parameter('mode',0,[0,1],'0:low-to-high, 1:high-to-low'),
                                           Parameter('binding','none',['x','y','z','aux','read','none'],'axis/event to bind to')
                                       ]),
                                   ])
                                ])

    def __init__(self, name=None, settings=None, serial=None):
        #loads DLL file. madlib.dll should be in same folder as nanodrive.py
        super(MCL_NanoDrive, self).__init__(name, settings)

        if serial:
            self.settings['serial'] = serial        #change to have serial in settings once it is known how to incorporate (same issue as SG384)
        try:    #DLL file should be in same folder as nanodrive.py
            self.DLL = windll.LoadLibrary(os.path.join(os.path.dirname(__file__),'madlib.dll'))
        except (OSError, WindowsError) as error:
            print('Unable to load Mad City Labs DLL')
            raise
        self._initilize_handle()

        self.empty_waveform = [0]       #arbitray empty waveform to be used in 'read_waveform':MCL_NanoDrive.empty_waveform. Proper size is created in appropriate method
        self.load_waveform = [0]
        self.set_read_waveform = False  #setup status to false so that a trigger doesnt occur without a setup
        self.set_load_waveform = False
        self.set_mult_ax_waveform = False

        #set an error dictionary to see what issue device runs into
        self.mcl_error_dic = {
            -1: lambda: self._raise_error('GENERAL_ERROR: These errors generally occur due to an internal sanity check failing.'),
            -2: lambda: self._raise_error('DEVICE_ERROR: A problem occurred when transferring data to the Nano Drive. It is likely that the Nano Drive will have to be power cycled to correct these errors.'),
            -3: lambda: self._raise_error('DEVICE_NOT_ATTACHED: The Nano Drive cannot complete the task because it is not attached.'),
            -4: lambda: self._raise_error('USAGE_ERROR: Using a function from the library which the Nano Drive does not support causes these errors.'),
            -5: lambda: self._raise_error('DEVICE_NOT_READY: The Nano Drive is currently completing or waiting to complete another task.'),
            -6: lambda: self._raise_error('ARGUMENT_ERROR: An argument is out of range or a required pointer is equal to NULL.'),
            -7: lambda: self._raise_error('INVALID_AXIS: Attempting an operation on an axis that does not exist in the Nano Drive.'),
            -8: lambda: self._raise_error('INVALID_HANDLE: The handle is not valid or at least not valid in this instance of DLL.')
        }

    def _initilize_handle(self):
        #Grabs all handles and controls handle given when class is called or default handle if not specified
        numDevices = self.DLL.MCL_GrabAllHandles()
        self.handle = c_int(self.DLL.MCL_GetHandleBySerial(c_short(self.settings['serial'])))
        #return numDevices, self.handle

    def __del__(self):
        #releases control of handle if not already closed
        self.DLL.MCL_ReleaseHandle(self.handle)

    def update(self, settings):
        #includes commands that set and trigger nanodrive and return a response
        super(MCL_NanoDrive, self).update(settings) #updates settings as per entered with method
        '''
        ex update(settings = {'axis':'x','axis_position':5}) for write position
        or update(settings = {'axis':'x','read_wavefrom':MCL_NanoDrive.empty_waveform}) for reading a waveform
        '''

        #might need to change this ^    different place in code / maybe exclued / maybe seperate funciton

        for key, value in settings.items():     #goes through inputed settings to see what commands to send ot update parameters
            axis = self._axis_to_internal(self.settings['axis'])

            if key == 'position':      #updates axis position
                value = self._check_error(self.DLL.MCL_SingleWriteN(c_double(value), axis, self.handle))

            elif key == 'read_waveform':    #reads waveform for given axis and stores sensor data in read_waveform
                ArrayType = c_double * self.settings['num_datapoints']  # creates empty array with correct number of datapoints
                empty_waveform = ArrayType()
                read_rate = self._read_rate_to_internal(self.settings['read_rate'])
                value = self._check_error(self.DLL.MCL_ReadWaveFormN(axis,c_uint(self.settings['num_datapoints']),read_rate,byref(self.empty_waveform),self.handle))
                self.read_waveform = list(empty_waveform)
                return self.read_waveform

            elif key == 'load_waveform':    #loads waveform onto specified axis
                if self.settings['num_datapoints'] != len(settings['load_waveform']):
                    print('Error: Length of wavefrom input list does not match number of data points')
                    raise
                load_rate = self._load_rate_check(self.settings['load_rate'])
                self.load_waveform = settings['load_waveform']
                value = self._check_error(self.DLL.MCL_LoadWaveFromN(axis,c_uint(self.settings['num_datapoints']),load_rate,byref(self.load_waveform),self.handle))
                #To read loaded waveform use update(settings={'axis':'','read_waveform':MCL_NanoDrive.empty_waveform})

            elif key == 'mult_ax' and settings['mult_ax']['waveform'] == [[0],[0],[0]]:     #stops multi-axis waveform only if input value is 0 for all axis
                value = self._check_error(self.DLL.MCL_WfmaStop(self.handle))


    def setup(self, settings):
        #commands that sets up nanodrive for a trigger
        super(MCL_NanoDrive, self).update(settings)  # updates settings as per entered with method

        for key, value in settings.items():
            axis = self._axis_to_internal(self.settings['axis'])
            if key == 'read_waveform':
                read_rate = self._read_rate_to_internal(self.settings['read_rate'])
                value = self._check_error(self.DLL.MCL_Setup_ReadWaveFormN(axis,c_uint(self.settings['num_datapoints']),read_rate,self.handle))
                self.set_read_waveform = True   #lets trigger_read and trigger_acquisition run

            elif key == 'load_waveform':
                if self.settings['num_datapoints'] != len(settings['load_waveform']):
                    print('Error: Length of wavefrom imput list does not match number of data points')
                    raise
                load_rate = self._load_rate_check(self.settings['load_rate'])
                self.load_waveform = settings['load_waveform']     #for read_probes to see last loaded waveform
                value = self._check_error(self.DLL.MCL_Setup_LoadWaveFormN(axis,c_uint(self.settings['num_datapoints']),load_rate,byref(self.load_waveform),self.handle))
                self.set_load_waveform = True    #lets trigger_load and tirgger_acquisition run

            elif key == 'mult_ax':
                self.load_waveform = self._multiaxis_waveform(settings['mult_ax']['waveform'])
                if not self.settings['num_datapoints']==len(self.load_waveform[0])==len(self.load_waveform[1])==len(self.load_waveform[2]):
                    print('ERROR: Length of waveform input lists do not match number of data points. Note TOTAL number of data points is 6666.')
                    raise
                #setup command looks confusing but the lengh is just from converting python variable types to c variable types
                value = self._check_error(self.DLL.MCL_WfmaSetup(byref(self.load_waveform[0]), byref(self.load_waveform[1]), byref(self.load_waveform[2]), c_uint(self.settings['num_datapoints']), c_double(self.settings['load_rate']), c_ushort(self.settings['mult_ax']['iterations']), self.handle))
                self.set_mult_ax_waveform = True

    def trigger(self, settings):
        #commands that triggers a setup and return a response
        super(MCL_NanoDrive, self).update(settings) #Updates the self.settings so that axis, num_datapoints, etc. are as specified

        axis = self._axis_to_internal(self.settings['axis'])

        for key, value in settings.items():
            if key == 'read_waveform':
                if not self.set_read_waveform:      #checks to see if read waveform has been set
                    print('ERROR: Read wavefrom has not been set!')
                    raise
                else:
                    ArrayType = c_double * self.settings['num_datapoints']
                    empty_waveform = ArrayType()
                    value = self._check_error(self.DLL.MCL_Trigger_ReadWaveFormN(axis,c_uint(self.settings['num_datapoints']),byref(empty_waveform),self.handle))
                    self.read_waveform = list(empty_waveform)
                    return self.read_waveform

            elif key == 'load_waveform':
                if not self.set_load_waveform:      #checks to see if load waveform has been set
                    print('ERROR: Load wavefrom has not been set!')
                    raise
                value = self._check_error(self.DLL.MCL_Trigger_LoadWaveFormN(axis,self.handle))

            elif key == 'mult_ax':
                if not self.set_mult_ax_waveform:
                    print('ERROR: Multi-axis waveform not set!')
                    raise
                else:
                    value = self._check_error(self.DLL.MCL_WfmaTrigger(self.handle))

    def waveform_acquisition(self, axis=None, num_datapoints=None):
        if not self.set_load_waveform:  # checks to see if load waveform has been set
            print('ERROR: Load wavefrom has not been set!')
            raise
        if not self.set_read_waveform:  # checks to see if read waveform has been set
            print('ERROR: Read wavefrom has not been set!')
            raise
        if axis != None:
            self.settings['axis'] = axis
        if num_datapoints != None:
            self.settings['num_datapoints'] = num_datapoints
        else:
            axis = self._axis_to_internal(self.settings['axis'])
            ArrayType = c_double * self.settings['num_datapoints']
            empty_waveform = ArrayType()  # creates empty array for read data
            value = self._check_error(self.DLL.MCL_TriggerWaveformAcquisition(axis, c_uint(self.settings['num_datapoints']),byref(empty_waveform), self.handle))
            self.read_waveform = list(empty_waveform)
            return self.read_waveform

    def clock_function(self, clock, polarity=None, mode=None, bind_to=None, reset=False, pulse=False):
        #updates clock settings by sending relevant commands to device. See _Default_Settings for polarity, mode, and binding options
        #input output=True for a 250 ns pulse on specified clock
        if reset:
            value = self._check_error(self.DLL.MCL_IssResetDefaults(self.handle))  #if reset is set true sets ALL clocks options to defualt
            reset_settings = {'clock':{'Pixel':{'polarity':0,'mode':0,'binding':'read'}, 'Line':{'polarity': 0,'mode': 0,'binding':'load'}, 'Frame':{'polarity': 0,'mode':0,'binding':'none'}, 'Aux':{'polarity':0,'mode':0,'binding':'none'}}}
            super(MCL_NanoDrive, self).update(reset_settings)
            return None
        clock_name = self._clocks_to_internal(clock, cap=True)  # needed for pulse command and to update settings
        clock = self._clocks_to_internal(clock_name)
        if polarity != None and bind_to == None:
            value = self._check_error(self.DLL.MCL_IssConfigurePolarity(clock, c_int(polarity+2), self.handle))
            self.settings['clock'][clock_name]['polarity'] = polarity
        if mode != None:
            value = self._check_error(self.DLL.MCL_IssSetClock(clock, c_int(mode), self.handle))
            self.settings['clock'][clock_name]['mode'] = mode
        if bind_to != None:
            if polarity == None:
                print('polarity must be specified for binding [0:low-to-high, 1:high-to-low, 2:unbind]')
                raise
            else:
                bind_to_axis = self._bind_axis_to_internal(bind_to)
                value = self._check_error(self.DLL.MCL_IssBindClockToAxis(clock, c_int(polarity+2), bind_to_axis, self.handle))
                self.settings['clock'][clock_name]['binding'] = bind_to
        if pulse:
            value = self._check_error(getattr(self.DLL, f'MCL_{clock}Clock')(self.handle)) #getattr assembles the self.DLL+MCL_PixelClock+(self.handle)
        return None

    def read_probes(self, key, axis=None):
        assert(self._settings_initialized)
        assert key in list(self._PROBES.keys())

        if axis:        #call method with an axis or get reading from last interacted with axis
            self.settings['axis'] = axis

        if key == 'axis_range':
            self.DLL.MCL_GetCalibration.restype = c_double
            value = self._check_error(self.DLL.MCL_GetCalibration(self._axis_to_internal(self.settings['axis']), self.handle))
        elif key == 'position':
            self.DLL.MCL_SingleReadN.restype = c_double
            value = self._check_error(self.DLL.MCL_SingleReadN(self._axis_to_internal(self.settings['axis']), self.handle))

        elif key == 'load_waveform':    #returns last loaded waveform or empty list if none loaded
            value = self.load_waveform
        elif key == 'read_waveform':    #returns last read wavefrom or triggers waveform read on axis
            value = self.update(settings={'axis':self.settings['axis'],'read_waveform':self.empty_waveform})
            self.settings['read_waveform'] = value
        elif key == 'mult_ax_waveform':     #note read waits for mult_ax waveform to stop triggering and stops infinite loops
            empty_waveform = self._multiaxis_waveform([0], empty=True)
            command = self._check_error(self.DLL.MCL_WfmaRead(byref(empty_waveform[0]),byref(empty_waveform[1]),byref(empty_waveform[2]),self.handle))
            self.read_waveform = [list(empty_waveform[0]),list(empty_waveform[1]),list(empty_waveform[2])]
            value = self.read_waveform
            #might want to add an exception to raise if num_datapoints is not equal to length of read data
            #or add self.wfma_numpoints to create proper sized arrays of last loaded waveform

        elif key == 'read_rate':
            value = self.settings['read_rate']
        elif key == 'load_rate':
            value = self.settings['load_rate']
        elif key == 'clock_settings':
            value = self.settings['clock']

        return value

    @property
    def _PROBES(self):
        return {
            #ask device
            'axis_range': 'position range of axis',
            'position': 'current position of axis',
            'load_waveform': 'reads loaded waveform on specified axis or last loaded waveform if axis not specified',
            'mult_ax_waveform': 'reads last multi axis waveform',
            'read_waveform': 'reads current waveform',
            #check code parameters
            'read_rate':'rate to read waveform data',
            'load_rate':'rate to upload waveform data',
            'num_datapoints':'number of data points of waveform',
            'clock_setting':'internal parameters of all clocks'
        }

    @property
    #does not work for some reason. When called returns false even if I can read and write to axes of nanodrive
    def is_connected(self):
        #true if connected, false if not
        self.DLL.MCL_DeviceAttached.restype = c_bool
        return self.DLL.MCL_DeviceAttached(0,self.handle)

    @property
    def device_info(self):
        #prints product name, id, DLL version, firmware version, and other information
        return self.DLL.MCL_PrintDeviceInfo(self.handle)

    def close(self):
        #releases control of ALL HANDLES not just of the specific instance
        self.DLL.MCL_ReleaseHandle(self.handle)

    #2 error functions to see if an error occured when sending a command and raise the error if it does
    def _raise_error(self, message):
        raise Exception(message)
    def _check_error(self, value):  #returns inputed value if not an error value. If error value, triggers raise of error encounted
        check_error = self.mcl_error_dic.get(value, lambda:value)
        return check_error()

    def _axis_to_internal(self, axis):
        if axis == 'x':
            return c_uint(1)
        elif axis == 'y':
            return c_uint(2)
        elif axis == 'z':
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
        if value ==20:
            return c_double(9)
        else:
            print('Read rate invalid. Check _Default_Settings for valid values.')
            raise

    def _load_rate_check(self, value):
        #Value in milliseconds
        if value >= 1/6 and value <= 5:
            return c_double(value)
        else:
            print('Data load rate invalid. Check _Default_Settings for valid values.')
            raise

    def _multiaxis_waveform(self, list, empty=False):
        '''
        Function that determines if x,y, or z are part of inputed waveform list.
        Sets waveform as empty if input is 0 ie [[x_waveform], [0], [z_waveform]]
        '''
        ArrayType = c_double * self.settings['num_datapoints']
        x_waveform = y_waveform = z_waveform = ArrayType()
        if empty:
            return [x_waveform, y_waveform, z_waveform]
        else:
            if list[0] != [0]:
                x_waveform = ArrayType(*list[0])
            if list[1] != [0]:
                y_waveform = ArrayType(*list[1])
            if list[0] != [0]:
                z_waveform = ArrayType(*list[2])
            return [x_waveform, y_waveform, z_waveform]

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

if __name__ == '__main__':
    nd = MCL_NanoDrive()
    print(nd.is_connected)
    nd.close()