'''
Added to this version:
    -Changed parameters to include all 10 processes and function though those (specifically for ease of use in GUI)
    -Add device description
    -imporved some comments
    -process dictionary removed in favor of regular process numbers

    might want to add a way to check that processes are not loaded over each other

'''
from src.core import Device, Parameter
import ADwin
from ADwin import ADwinError
#from ctypes import *

class ADwin_Gold(Device):
    '''
    This class implements the ADwin Gold II by booting it with the T11 processor. It does not yet implement TiCO processes.
    Processes should be written in an ADbasic script and then loaded using this controller.
    The processor and priority can be changed for each process and is left to the user writing the ADbasic script.
    '''

    _DEFAULT_SETTINGS = Parameter([
        Parameter('process_1',[
            Parameter('load','',str,'Filename to load. Should be .__1 for number 1'),
            Parameter('delay',3000.0,float,'Time interval between 2 events (delay = value x 3.3ns)'),
            Parameter('start',False,bool,'Trigger to start process'),
            Parameter('stop',False,bool,'Trigger to stop process'),
            Parameter('clear',False,bool,'Trigger to clear process')
            ]),
        Parameter('process_2', [
            Parameter('load', '', str, 'Filename to load. Should be .__2 for number 2'),
            Parameter('delay', 3000.0, float,'Time interval between 2 events (delay = value x 3.3ns)'),
            Parameter('start', False, bool, 'Trigger to start process'),
            Parameter('stop', False, bool, 'Trigger to stop process'),
            Parameter('clear', False, bool, 'Trigger to clear process')
            ]),
        Parameter('process_3', [
            Parameter('load', '', str, 'Filename to load. Should be .__3 for number 3'),
            Parameter('delay', 3000.0, float,'Time interval between 2 events (delay = value x 3.3ns)'),
            Parameter('start', False, bool, 'Trigger to start process'),
            Parameter('stop', False, bool, 'Trigger to stop process'),
            Parameter('clear', False, bool, 'Trigger to clear process')
        ]),
        Parameter('process_4', [
            Parameter('load', '', str, 'Filename to load. Should be .__4 for number 4'),
            Parameter('delay', 3000.0, float,'Time interval between 2 events (delay = value x 3.3ns)'),
            Parameter('start', False, bool, 'Trigger to start process'),
            Parameter('stop', False, bool, 'Trigger to stop process'),
            Parameter('clear', False, bool, 'Trigger to clear process')
        ]),
        Parameter('process_5', [
            Parameter('load', '', str, 'Filename to load. Should be .__5 for number 5'),
            Parameter('delay', 3000.0, float,'Time interval between 2 events (delay = value x 3.3ns)'),
            Parameter('start', False, bool, 'Trigger to start process'),
            Parameter('stop', False, bool, 'Trigger to stop process'),
            Parameter('clear', False, bool, 'Trigger to clear process')
        ]),
        Parameter('process_6', [
            Parameter('load', '', str, 'Filename to load. Should be .__6 for number 6'),
            Parameter('delay', 3000.0, float,'Time interval between 2 events (delay = value x 3.3ns)'),
            Parameter('start', False, bool, 'Trigger to start process'),
            Parameter('stop', False, bool, 'Trigger to stop process'),
            Parameter('clear', False, bool, 'Trigger to clear process')
        ]),
        Parameter('process_7', [
            Parameter('load', '', str, 'Filename to load. Should be .__7 for number 7'),
            Parameter('delay', 3000.0, float,'Time interval between 2 events (delay = value x 3.3ns)'),
            Parameter('start', False, bool, 'Trigger to start process'),
            Parameter('stop', False, bool, 'Trigger to stop process'),
            Parameter('clear', False, bool, 'Trigger to clear process')
        ]),
        Parameter('process_8', [
            Parameter('load', '', str, 'Filename to load. Should be .__8 for number 8'),
            Parameter('delay', 3000.0, float,'Time interval between 2 events (delay = value x 3.3ns)'),
            Parameter('start', False, bool, 'Trigger to start process'),
            Parameter('stop', False, bool, 'Trigger to stop process'),
            Parameter('clear', False, bool, 'Trigger to clear process')
        ]),
        Parameter('process_9', [
            Parameter('load', '', str, 'Filename to load. Should be .__9 for number 9'),
            Parameter('delay', 3000.0, float,'Time interval between 2 events (delay = value x 3.3ns)'),
            Parameter('start', False, bool, 'Trigger to start process'),
            Parameter('stop', False, bool, 'Trigger to stop process'),
            Parameter('clear', False, bool, 'Trigger to clear process')
        ]),
        Parameter('process_10', [
            Parameter('load', '', str, 'Filename to load. Should be .__10 for number 10'),
            Parameter('delay', 3000.0, float,'Time interval between 2 events (delay = value x 3.3ns)'),
            Parameter('start', False, bool, 'Trigger to start process'),
            Parameter('stop', False, bool, 'Trigger to stop process'),
            Parameter('clear', False, bool, 'Trigger to clear process')
        ]),
    ])

    def __init__(self, name=None, settings=None, boot=True, num_devices=1):
        super(ADwin_Gold, self).__init__(name, settings)

        self.adw = ADwin.ADwin(DeviceNo=num_devices, raiseExceptions=1)
        #boots the ADwin which resets processes and global variables. Input boot = False if ADwin is already initilized
        if boot:
            try:
                #boots with T11 processor. 3.333.. ns minimum time resolution for low and high priority processes
                btl = self.adw.ADwindir+'ADwin11.bt1' #could add flexibiliy for which processor if device has multiple
                self.adw.Boot(btl)
            except ADwinError as e:
                print('Issue booting ADwin: ',e)
                raise

    def update(self, settings):
        super(ADwin_Gold, self).update(settings)

        if self._settings_initialized:
            for key, value in settings.items():
                process_number = int(key.split('_')[-1]) #gets number after '_' in process_# key
                for param, param_value in value.items():
                    if param == 'load':
                        if 'load' == '':
                            self.clear_process(process_number)
                        else:
                            self.load_process(param_value)  #loads binary file ex. 'D:/PyCharmProjects/.../test_process.TB2'
                    elif param == 'delay':
                        self.adw.Set_Processdelay(process_number, param_value)
                    elif param == 'start' and param_value == True:      #only triggers if true. For GUI need to check and uncheck box
                        self.start_process(process_number)
                        self.settings[key]['start'] = False
                    elif param == 'stop' and param_value == True:
                        self.stop_process(process_number)
                        self.settings[key]['stop'] = False
                    elif param == 'clear' and param_value == True:
                        self.clear_process(process_number)
                        self.settings[key]['clear'] = False

    def load_process(self, filepath):
        '''
        Loads a binary file created using ADbasic (max 10).
        Note: Only variables defined in the ADbasic script can be interacted with in the python code else will return 0.
        Args:
            filepath: file location of ADbasic script
                -If the ADbasic files are in an 'ADbasic' subfolder in the same location as the controller can use
                    os.path.join(os.path.dirname(__file__),'ADWIN\\__name__.__(processor & number)__')
                -If using in GUI can copy path and paste.

            Note: There is some subtlties with python handling paths. The direction and number of slashes should follow
                  the example path of test_script

        test_script located at 'D:/PyCharmProjects/pittqlabsys-main/src/Controller\ADbasic\\Test_controller.TB1'
        '''
        self.adw.Load_Process(filepath)

    def clear_process(self, number):
        '''
        Clears a process from ADwin memory
        Args:
            number: number corresponding to process defined in file path (test_process.TB1)
        '''
        self.adw.Clear_Process(number)


    def start_process(self, number):
        '''
        Starts a loaded process
        Args:
            number: number corresponding to process defined in file path (test_process.TB1)
        '''
        self.adw.Start_Process(number)

    def stop_process(self, number):
        '''
        Stops a running process. Can use read_probes('process_status', {process name}) to see if process is running, stoping, or not running
        Args:
            number: number corresponding to process defined in file path (test_process.TB1)
        '''
        self.adw.Stop_Process(number)

    def read_probes(self, key, id):
        '''
        Sends a command to/through ADbasic script that returns the value of a varible or some other device parameter.
        Args:
            key: see _PROBES for options and descriptions
            id: number of array, variable, or process. For keys that don't require an id enter an arbitrary one.
        '''
        assert(self._settings_initialized)
        assert key in list(self._PROBES.keys())

        if key == 'array_length':
            value = self.adw.Data_Length(id)

        elif key == 'int_var':
            value = self.adw.Get_Par(id)
        elif key == 'float_var':
            value = self.adw.Get_FPar(id)
        elif key == 'float64_var':
            value = self.adw.Get_FPar_Double(id)

        elif key == 'all_ints':
            value = self.adw.Get_Par_All()
        elif key == 'all_floats':
            value = self.adw.Get_FPar_All()
        elif key == 'all_float64s':
            value = self.adw.Get_FPar_All_Double()

        elif key == 'int_array':    #start index of 1 and end index of length is set to return whole array
            length = self.read_probes('array_length',id)
            value = self.adw.GetData_Long(id,1,length)
        elif key == 'float_array':
            length = self.read_probes('array_length', id)
            value = self.adw.GetData_Float(id, 1, length)
        elif key == 'float64_array':
            length = self.read_probes('array_length', id)
            value = self.adw.GetData_Double(id, 1, length)
        elif key == 'str_array':
            length = self.read_probes('str_length',id)
            value = self.adw.GetData_String(id, length)

        elif key == 'int_fifo':
            length = self.read_probes('array_length', id)
            value = self.adw.GetFifo_Long(id, 1, length)
        elif key == 'float_fifo':
            length = self.read_probes('array_length', id)
            value = self.adw.GetFifo_Float(id, 1, length)
        elif key == 'float_64_fifo':
            length = self.read_probes('array_length', id)
            value = self.adw.GetFifo_Double(id, 1, length)
        elif key == 'fifo_empty':
            value = self.adw.Fifo_Empty(id)
        elif key == 'fifo_full':
            value = self.adw.Fifo_Full(id)

        elif key == 'str_length':
            value = self.adw.String_Length(id)
        elif key == 'process_delay':
            value = self.adw.Get_Processdelay(id)
        elif key == 'process_status':
            rawvalue = self.adw.Process_Status(id)
            value = self._internal_to_status(rawvalue)
        elif key == 'last_error':
            value = self.adw.Get_Error_Text(self.adw.Get_Last_Error())

        return value

    @property
    def _PROBES(self):
        return {
            #read variables of different types
            'int_var':'Returns Par_{id}', 'float_var':'Returns FPar_{id}', 'float64_var':'Returns 64bit FPar_{id}',
            'all_ints':'Returns all Par', 'all_floats':'Returns all FPar', 'all_float64s':'Returns all 64bit FPar',
            #data arrays
            'int_array':'Returns Data_{id} defined as Long',
            'float_array':'Returns Data_{id} defined as Float',
            'float64_array':'Returns Data_{id} defined as Float64',
            'str_array':'Returns Data_{id} defined as String',
            #fifo arrays
            'int_fifo':'Returns Data_{id} defined as Long as Fifo',
            'float_fifo': 'Returns Data_{id} defined as Float as Fifo',
            'float64_fifo':'Returns Data_{id} defined as Float64 as Fifo',
            'fifo_empty':'number of empty elements',
            'fifo_full':'number of used elements',
            #other
            'array_length':'length of defined array',
            'str_length':'length of string array',
            'process_delay':'checks delay between events of a process',
            'process_status':'checks status of a process',
            'last_error':'checks last error encountered'

        }

    @property
    def is_connected(self):
        try:
            self.adw.Test_Version()     #arbitrary query to test for a response
            return True
        except ADwinError:
            return False

    def _internal_to_status(self, value):
        '''
        Quality of life function to let the user know the status of a process instead of seeing a number
        '''
        if value == 0:
            return 'Not running'
        elif value == 1:
            return 'Running'
        else:
            return 'Being stopped'