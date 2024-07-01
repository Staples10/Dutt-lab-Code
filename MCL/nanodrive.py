from src.core import Device,Parameter

from ctypes import *
import os
import sys


class MCL_NanoDrive(Device):

    _DEFAULT_SETTINGS = Parameter([Parameter('serial',2850,int,'serial of specific Nano Drive. LP100:2849 & HS3:2850'),
                                   Parameter('axis','X',['X','Y','Z','AUX'],'axis of Nano Drive '),
                                   Parameter('axis_position',5.0,float,'position of axis in microns'),
                                   Parameter('read_rate',2.0,float,
                                             'value in ms. Allowed values and mapping: 3=0.267ms, 4=0.5ms, 5=1ms, 6=2ms, 7=10ms, 8=17ms, 9=20ms'),
                                   Parameter('write_rate',2,float,'ms/point load rate. Valid values 1/6-5'),
                                   Parameter('num_datapoints',1,list(range(1,6667)),'number of data points used for waveforms'),
                                   Parameter('write_waveform',[0],list, 'waveform to be loaded to nanodrive'),
                                   Parameter('read_waveform',[0],list,'waveform read from nanodrive'),
                                   Parameter('mult_ax_waveform',[0,0,0],list,'lists for multi axis waveform trigger. Ex: [[x_wf],0,[z_wf]]. Input in update method [0,0,0] to stop.'),
                                   Parameter('mult_ax_iterations',1,int,'Number of iterations to run through multi axis waveform trigger. 0 = infinite'),
                                   Parameter('clock','Pixel',['Pixel','Line','Frame','Aux','Reset'],'Clock on back of device. Input "Reset" to reset clock options to defualt.'),
                                   Parameter('clock_polarity',0,[0,1,2],'defaults clock to low=1. high=1, unbind=2'),
                                   Parameter('error_type',0,list(range(0,9)),'error type encounted')
                                   ])

    def __init__(self, name=None, settings=None, serial=None, debug=False):
        #loads DLL file. madlib.dll should be in same folder as nanodrive.py
        super(MCL_NanoDrive, self).__init__(name, settings)
        if serial:
            self.settings['serial'] = serial        #change to have serial in settings once it is known how to incorporate (same issue as SG384)
        try:
            self.DLL = windll.LoadLibrary(os.path.join(os.path.dirname(__file__),'madlib.dll'))
        except (OSError, WindowsError):
            print('Unable to load Mad City Labs DLL')
            raise
        self._initilize_handle()

        # initiates self objects so that no error occurs if called before being defined
        ArrayType = c_double * self.settings['num_datapoints']
        self.empty_waveform = ArrayType()       #make an inital empty waveform for read data. Can enter update(settings={'axis':'','read_waveform':MCL_NanoDrive.empty_waveform}) and the empty wavefrom will be updated to correct length etc within update method
        #self.read_waveform = [0]       #causes error when initilizing. Dont call MCL_NanoDrive.read_waveform before actually reading a waveform
        #self.load_waveform = [0]
        self.set_read_waveform = False      #sets setup status to false so that a trigger doesnt occur without a setup
        self.set_load_waveform = False
        self.set_mult_ax_waveform = False

        if debug:
            success = lambda: sys.stdout.write("SUCCESS\n")
        else:
            success = lambda: None
        err1 = lambda: sys.stderr.write("GENERAL_ERROR: These errors generally occur due to an internal sanity check failing.\n")
        err2 = lambda: sys.stderr.write("DEVICE_ERROR: A problem occurred when transferring data to the Nano Drive. It is likely that the Nano Drive will have to be power cycled to correct these errors.\n")
        err3 = lambda: sys.stderr.write("DEVICE_NOT_ATTACHED: The Nano Drive cannot complete the task because it is not attached.\n")
        err4 = lambda: sys.stderr.write("USAGE_ERROR: Using a function from the library which the Nano Drive does not support causes these errors.\n")
        err5 = lambda: sys.stderr.write("DEVICE_NOT_READY: The Nano Drive is currently completing or waiting to complete another task.\n")
        err6 = lambda: sys.stderr.write("ARGUMENT_ERROR: An argument is out of range or a required pointer is equal to NULL.\n")
        err7 = lambda: sys.stderr.write("INVALID_AXIS: Attempting an operation on an axis that does not exist in the Nano Drive.\n")
        err8 = lambda: sys.stderr.write("INVALID_HANDLE: The handle is not valid or at least not valid in this instance of DLL.\n")
        self.ErrorDic = {0: success, -1: err1, -2: err2, -3: err3, -4: err4, -5: err5, -6: err6, -7: err7, -8: err8}

    def _initilize_handle(self):
        #Grabs all handles and controls handle given when class is called or default handle if not specified
        numDevices = self.DLL.MCL_GrabAllHandles()
        self.handle = self.DLL.MCL_GetHandleBySerial(c_short(self.settings['serial']))
        return numDevices,self.handle

    def __del__(self):
        #releases control of handle if not already closed
        self.DLL.MCL_ReleaseHandle(self.handle)

    def update(self, settings):
        #includes commands that set and trigger nanodrive and return a response
        super(MCL_NanoDrive, self).update(settings) #updates settings as per entered with method
        '''
        ex update(settings = {'axis':'x','axis_position':5}) for write and read of axis position
        or update(settings = {'axis':'x','read_wavefrom':MCL_NanoDrive.empty_waveform}) for loading a waveform
        '''
        ArrayType = c_double * self.settings['num_datapoints']      #creates empty array with correct number of datapoints
        self.empty_waveform = ArrayType()                           #to load sensor data from read_waveform

        for key, value in settings.items():     #goes through inputed settings to see what parameter and command needs updated
            axis = self._axis_to_internal(self.settings['axis'])
            if key == 'axis_position':
                self.DLL.MCL_MonitorN.restype = c_double
                position = self.DLL.MonitorN(value,axis,self.handle) #sets position and return
                return position
            elif key == 'read_waveform':
                #reads waveform for given axis and stores sensor data in read_waveform
                read_rate = self._read_rate_to_internal(self.settings['read_rate'])
                self.DLL.MCL_ReadWaveFormN(axis,c_uint(self.settings['num_datapoints']),read_rate,byref(self.empty_waveform),self.handle)
                self.read_waveform = list(self.empty_waveform)
                return self.read_waveform
            elif key == 'load_waveform':
                if self.settings['num_datapoints'] != len(self.settings['load_waveform']):
                    sys.stderr.write('Error: Length of wavefrom imput list does not match number of data points')
                    return None
                load_rate = self._load_rate_check(self.settings['load_rate'])
                self.load_waveform = self.settings['load_waveform']
                #load_waveform = ArrayType(*self.settings['load_waveform'])      #CHECK TO MAKE SURE THIS DOES WHAT IT SHOULD DO!!
                self.DLL.MCL_LoadWaveFromN(axis,c_uint(self.settings['num_datapoints']),load_rate,byref(self.load_waveform),self.handle)
                #To read loaded waveform use update(settings={'axis':'','read_waveform':MCL_NanoDrive.empty_waveform})
            elif key == 'mult_ax_waveform' and value == [0,0,0]:     #stops clock pulses only if input value is 0 for all axis
                self.DLL.MCL_WfmaStop(self.handle)
            elif key == 'clock':
                if value == 'reset':
                    self.DLL.MCL_IssResetDefaults(self.handle)
                    return None
                clock_name = f'MCL_{value}Clock'
                getattr(self.DLL, clock_name)(self.handle)

    def setup(self, settings):
        #commands that sets up nanodrive for a trigger
        super(MCL_NanoDrive, self).update(settings)  # updates settings as per entered with method

        for key, value in settings.items():
            axis = self._axis_to_internal(self.settings['axis'])
            if key == 'read_waveform':
                read_rate = self._read_rate_to_internal(self.settings['read_rate'])
                self.DLL.MCL_Setup_ReadWaveFormN(axis,c_uint(self.settings['num_datapoints']),read_rate,self.handle)
                self.set_read_waveform = True   #lets trigger_read and trigger_acquisition run

            elif key == 'load_waveform':
                if self.settings['num_datapoints'] != len(self.settings['load_waveform']):
                    sys.stderr.write('Error: Length of wavefrom imput list does not match number of data points')
                    return None
                load_rate = self._load_rate_check(self.settings['load_rate'])
                self.load_waveform = self.settings['load_waveform']     #for read_probes to see last loaded waveform
                self.DLL.MCL_Setup_LoadWaveFormN(axis,c_uint(self.settings['num_datapoints']),load_rate,byref(self.settings['load_waveform']))
                self.set_load_waveform = True    #lets trigger_load and tirgger_acquisition run
            elif key == 'mult_ax_waveform':
                self.load_waveform = self._multiaxis_waveform(self.settings['mult_ax_waveform'])
                if not self.settings['num_datapoints']==len(self.load_waveform[0])==len(self.load_waveform[1])==len(self.load_waveform[2]):
                    sys.stderr.write('ERROR: Length of waveform input lists do not match number of data points')
                    return None
                #setup command looks confusing but the lengh is just from converting python variable types to c variable types
                self.DLL.MCL_WfmaSetup(byref(self.load_waveform[0]), byref(self.load_waveform[1]), byref(self.load_waveform[2]), c_uint(self.settings['num_datapoints']), c_double(self.settings['load_rate']), c_ushort(self.settings['mult_ax_iterations']), self.handle)
                self.set_mult_ax_waveform = True

    def trigger(self, settings, Acquisition=False):
        #commands that triggers a setup and return a response
        super(MCL_NanoDrive, self).update(settings) #Updates the self.settings so that axis, num_datapoints, etc. are as specified

        ArrayType = c_double * self.settings['num_datapoints']
        empty_waveform = ArrayType()       #creates empty array for read data
        axis = self._axis_to_internal(self.settings['axis'])

        if Acquisition:
            if not self.set_load_waveform:  # checks to see if load waveform has been set
                return 'Load Waveform not set!'
            if not self.set_read_waveform:  # checks to see if read waveform has been set
                return 'Read Waveform not set!'
            else:
                self.DLL.MCL_TriggerWaveformAcquisition(axis, c_uint(self.settings['num_datapoints']),byref(empty_waveform), self.handle)
                self.read_waveform = list(empty_waveform)
                return self.read_waveform

        for key, value in settings.items():
            if key == 'read_waveform':
                if not self.set_read_waveform:      #checks to see if read waveform has been set
                    return 'Read Waveform not set!'
                else:
                    self.DLL.MCL_Trigger_ReadWaveFormN(axis,c_uint(self.settings['num_datapoints']),byref(empty_waveform),self.handle)
                    self.read_waveform = list(empty_waveform)
                    return self.read_waveform

            elif key == 'load_waveform':
                if not self.set_load_waveform:      #checks to see if load waveform has been set
                    return 'Load Waveform not set!'
                self.DLL.MCL_Trigger_LoadWaveFormN(axis,self.handle)

            elif key == 'wfma':
                if not self.set_wfma:
                    return 'wfma not set!'
                else:
                    self.DLL.MCL_WfmaTrigger(self.handle)

            elif key == 'axis_position':
                self.DLL.MCL_SingleWriteN(c_double(self.settings['axis_position']),axis, self.handle)

    def read_probes(self, key, axis=None):
        assert(self._settings_initialized)
        assert key in list(self._PROBES.keys())
        if axis:
            self.settings['axis'] = self._axis_to_internal(axis)

        if key == 'axis_range':
            self.DLL.MCL_GetCalibration.restype = c_double
            value = self.DLL.MCL_GetCalibration(self._axis_to_internal(self.settings['axis']), self.handle)
        elif key == 'axis_position':
            self.DLL.MCL_SingleReadN.restype = c_double
            value = self.DLL.MCL_SingleReadN(self._axis_to_internal(self.settings['axis']), self.handle)

        elif key == 'load_waveform':    #returns last loaded waveform or None
            value = self.load_waveform
        elif key == 'read_waveform':    #returns last read wavefrom or None
            value = self.read_waveform

        elif key == 'read_rate':
            value = self.settings['read_rate']
        elif key == 'load_rate':
            value = self.settings['load_rate']

        return value

    @property
    def _PROBES(self):
        return {
            #ask device
            'axis_range': 'position range of axis',
            'axis_position': 'current position of axis',
            'load_waveform': 'returns last loaded waveform',
            'read_waveform': 'returns last read waveform',
            #check code parameters
            'clock_polarity': 'if clock on state is low or high',
            'read_rate':'rate to read waveform data',
            'load_rate':'rate to upload waveform data',
            'num_datapoints':'number of data points of waveform'
        }

    @property
    def is_connected(self):
        #true if connected, false if not
        self.DLL.MCL_DeviceAttached.restype = c_bool
        return self.DLL.MCL_DeviceAttached(self.handle)

    @property
    def device_info(self):
        #prints product name, id, DLL version, firmware version, and other information
        return self.DLL.MCL_PrintDeviceInfo(self.handle)

    def close(self):
        #releases control of ALL HANDLES not just of the specific instance
        self.DLL.MCL_ReleaseAllHandles()

    def _axis_to_internal(self, value):
        value = value.upper()
        if value == 'X':
            return c_uint(1)
        elif value == 'Y':
            return c_uint(2)
        elif value == 'Z':
            return c_uint(3)
        elif value == 'AUX':
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
            raise 'Read rate invalid. Check _Default_Settings for valid values.'

    def _write_rate_check(self, value):
        #Value in milliseconds
        if value >= 1/6 and value <= 5:
            return c_double(value)
        else:
            raise 'Data write rate invalid. Check _Default_Settings for valid values.'

    def _multiaxis_waveform(self, list, empty=False):
        '''
        Function that determines if x,y, or z are part of inputed waveform list.
        Sets waveform as empty if input is 0 ie [x_waveform, 0, z_waveform]
        '''
        ArrayType = c_double * self.settings['num_datapoints']
        x_waveform = y_waveform = z_waveform = ArrayType()
        if empty:
            return [x_waveform, y_waveform, z_waveform]
        else:
            if list[0] != 0:
                x_waveform = ArrayType(*list[0])
            if list[1] != 0:
                y_waveform = ArrayType(*list[1])
            if list[0] != 0:
                z_waveform = ArrayType(*list[2])
            return [x_waveform, y_waveform, z_waveform]

if __name__ == '__main__':
    nd = MCL_NanoDrive()
    print(nd.is_connected)
    nd.close()