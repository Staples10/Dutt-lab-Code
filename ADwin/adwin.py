'''
Idea:
    The adwin controller houses all the functionality of the ADwin python Driver. Using this code in isolation
    neccesarily is useless. For each experiment or task an ADbasic script(s) should be written and loaded that dictates which
    ports, inputs, outputs, and variables are used. This python controller then interfaces with the code and user
    for changes, reading data/parameters, and saving data.

'''
from src.core import Device, Parameter
import ADwin
from ADwin import ADwinError
from ctypes import *

class ADwin(Device):

    _DEFAULT_SETTINGS = Parameter([
        Parameter('data_type','var',['var','array','fifo'],'Single valued variable, array, or fifo array'),
        Parameter('var_type','int',['int','float','float64'],'Integer, 32bit float, or 64bit float'),
        Parameter('process_delay',0.1,float,'Time interval between 2 events in microseconds (minimum interval is 3.3 ns)'),
        Parameter('array_number',1,list(range(1,201)),'Valid global array numbers: 1-200'),
        Parameter('variable_number',1,list(range(1,81)),'Valid global single variable numbers 1-80. Note: int has 80 and float/float64 have 80 total.'),
        Parameter('overwrite_data',False,bool,'False: saving data appends to file. True: saving data overwrites file.')
    ])

    def __init__(self, name=None, settings=None, boot=True, num_devices=1):
        super(ADwin, self).__init__(name, settings)

        self.adw = ADwin.ADwin(DeviceNo=num_devices, raiseExceptions=1)
        #boots the ADwin which resets processes and global variables. Input boot = False if ADwin is already initilized
        if boot:
            try:
                self.adw.Boot(self.adw.ADwindir+'ADwin11.bt1')  #could add flexibiliy for which processor if device has multiple
            except ADwinError as e:
                print('Issue booting ADwin: ',e)
                raise
        self._process_dic = {}
        self._process_number = 0
        self._remove_process = 1

    def update(self, settings):
        super(ADwin, self).update(settings)

    def load_process(self, name, delay='Default', clear=False):
        '''
        Loads a binary file created using ADbasic (max 10). The file name is then used for
        starting, stoping, etc. through an internal processes dictionary.
        Note: Only variables defined in the file can be interacted with in the python code
        Args:
            name: file location of ADbasic script
                -should define script_description = os.path.join(os.path.dirname(__file__),'ADWIN\\TrialCounter.TB1')
                -calling load_process(script_description) will add to process dictionary and allow the same name
                 name to be used in start and stop process methods [start_process(script_description)]
            delay: Sets a time interval between 2 events in microseconds
            clear: Will clear a process from the ADwin memory. If 10 processes have already been loaded the
                   least recent process will be cleared
        '''
        if clear:
            self.adw.Clear_Process(self._process_dic[name])
            del self._process_dic[name]
            return None
        self._update_process_dic(name)
        self.adw.Load_Process(self._process_dic[name])
        if delay != 'Default':
            self.adw.Set_Processdelay(self._process_dic[name], delay)

    def start_process(self, name):
        '''
        Starts a loaded process
        Args:
            name: same name used in load_process which will find corresponding number in process dictionary
        '''
        self.adw.Start_Process(self._process_dic[name])

    def stop_process(self, name):
        '''
        Stops a running process. Can use read_probes('process_status', {process name}) to see if process is running, stoping, or not running
        Args:
            name: same name used in load_process which will find corresponding number in process dictionary
        '''
        self.adw.Stop_Process(self._process_dic[name])

    def set_variables(self, data_type, var_type, value, id_number):
        '''
        Allows setting of variables in ADbasic script from python. NOTE variables must be defined in script (see ADbasic manual)
        Args:
            data_type: 'var' for single valued variable, 'array' for an arrry, 'fifo' for a fifo array
            var_type: 'int' for 32bit integer, 'float' for 32bit float, 'float64' for 64bit float, 'str' for string
            value: value to set variable as. Can be a number, array, or string depending on data and var type
            id_number: number corresponding to defining in script. Arrays are from 1-200, float and int are 1-80 each

        ex. set_variables(int, array, [1,5,3,4,6,7,6,4], 5)
        '''
        if data_type == 'var':
            var_type = var_type.lower()
            if var_type == 'int':
                specific = 'Set_Par'
            elif var_type == 'float':
                specific = 'Set_FPar'
            elif var_type == 'float64':
                specific = 'Set_FPar_Double'
            command = getattr(self.adw,specific(id_number, value))  #assembles self.adw+Set_Par(id_number, value)

        elif data_type == 'array':
            if var_type == 'str':
                command = self.adw.SetData_String(id_number, value)
            else:
                specific = f'SetData_{self._var_type_to_command(var_type)}' #.SetData_Long
                Array = self._array_from_var_type(var_type, value)
                command = getattr(self.adw, specific(Array, id_number, 1, len(value)))  # assembles self.adw+SetData_Long(id_number, value, 1, len(value))
        elif data_type == 'fifo':
            specific = f'SetFifo_{self._var_type_to_command(var_type)}'
            Array = self._array_from_var_type(var_type, value)
            command = getattr(self.adw, specific(id_number, Array, len(value)))

    def save_data(self, filename, array_number):
        '''
        Should save data of an array in ADbasic process need to use/test to see how it actually works
        '''
        if self.settings['overwrite_data']:
            mode = 0    #mode=0 will overwrite data already in file
        else:
            mode = 1
        data_length = self.read_probes('array_length', array_number)
        self.adw.Data2File(filename, array_number, data_length, mode)

    def read_probes(self, key, id):
        '''
        Sends a command to/through ADbasic script that returns the value of a varible or some other device parameter.
        Args:
            key: see _PROBES for options and descriptions
            id: number of array, variable, or process name. For keys that dont require an id enter an arbitrary one.
                -for processes the name used in load_process should be entered to check status and delay
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

        elif key == 'all_int':
            value = self.adw.Get_Par_All()
        elif key == 'all_float':
            value = self.adw.Get_FPar_All()
        elif key == 'all_float64':
            value = self.adw.Get_FPar_All_Double()

        elif key == 'int_array':
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
            value = self.adw.Get_Processdelay(self._process_dic[id])
        elif key == 'process_status':
            rawvalue = self.adw.Process_Status(self._process_dic[id])
            value = self._internal_to_status(rawvalue)
        elif key == 'last_error':
            value = self.adw.Get_Error_Text(self.adw.Get_Last_Error())

        return value

    @property
    def _PROBES(self):
        return {
            #read variables of different types
            'int_var':'', 'float_var':'', 'float64_var':'',
            'all_int':'', 'all_float':'', 'all_float64':'',
            #data arrays
            'int_array':'', 'float_array':'', 'float64_array':'', 'str_array':'',
            #fifo arrays
            'int_fifo':'', 'float_fifo': '', 'float64_fifo':'',
            'fifo_empty':'number of empty elements',
            'fifo_full':'number of used elements',
            #other
            'array_length':'length of defined array',
            'str_length':'length of string array',
            'process_delay':'checks delay between events of a process',
            'process_status':'checks status of a process',
            'last_error':'checks last error encountered'

        }

    def _update_process_dic(self, name):
        '''
        Adds process to an internal dictionary that corresponds the name entered to the process number the device needs.
        The hope of this dictionary is to make loading and calling process easier but just inputing the name.
        NOTE: There is max 10 processes so if an 11th is entered the 1st will be cleared and the new one will correspond to process 1
        '''
        self._process_number += 1
        #Alerts user if 10 process are loaded
        if self._process_number == 11:
            print('NOTE: MAX NUMBER OF PROCESSES LOADED [10]! Loading more processes will clear existing ones.')
            self._process_number = 1
        #clears process then removes in order loaded
        if len(self._process_dic) == 10:
            if self._remove_process == 11:
                self._remove_process = 1
            key_to_remove = None
            for key, value in self._process_dic.items():
                if value == self._remove_process:
                    key_to_remove = key
                    break
            if key_to_remove:
                self._remove_process += 1
                self.load_process(key_to_remove, clear=True)
                #del self._process_dic[key_to_remove] || shouldnt be needed already have del in clear process

        self._process_dic[name] = self._process_number

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

    def _var_type_to_command(self, type):
        '''
        Converts inputed var_type to proper word for command
        '''
        input = type.lower()
        if input == 'int':
            return 'Long'
        elif input == 'float':
            return 'Float'
        elif input == 'float64':
            return 'Double'
        elif input == 'str':
            return 'String'
        else:
            raise KeyError

    def _array_from_var_type(self, type, input_array):
        '''
        1st step to convert inputed array into an array that can be sent to ADbasic script
        '''
        var_type = type.lower()
        if var_type == 'int':
            dataType = c_int32 * len(input_array)
        elif var_type == 'float':
            dataType = c_float * len(input_array)
        elif var_type == 'float64':
            dataType = c_double * len(input_array)
        else:
            raise KeyError
        Array = dataType(*list(input_array))
        return Array