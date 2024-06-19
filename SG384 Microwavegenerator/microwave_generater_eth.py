#Same as github code for SG384 Signal Generator but converted to use ethernet connection via socket
import socket
#import pyvisa as visa
#import pyvisa.errors
''' NOTE:
Sometimes get error when initially trying to communicate with SG384 after it has been disconnected and 
powered off. Error says timeout as there is no response. Pinging instrument using command prompt seems 
to initilize communication. The first ping says request timeout but subsequent successfully ping.
After successful ping python code connects properly.
'''

from src.Core.parameter import Parameter
from src.Core.device import Device

_IP = '169.254.146.198'         #IP needs set on device. Auto configurations should be disabled
_PORT = 5025                    #port open for remote commmunication as per manual
# RANGE_MIN = 2025000000 #2.025 GHz
RANGE_MIN = 1012500000
RANGE_MAX = 4050000000 #4.050 GHZ

class MicrowaveGenerator(Device):
    """
    This class implements the Stanford Research Systems SG384 microwave generator. The class commuicates with the
    device over ethernet cable using socket
    """
        # SHOULD BE 4
    ## GD: watch out for the ports this might be different on each computer and might cause issues when running export default
    _DEFAULT_SETTINGS = Parameter([
        #Parameter('connection_type', 'GPIB', ['GPIB', 'RS232'], 'type of connection to open to controller'),
        #Parameter('port', 19, list(range(0, 31)), 'GPIB or COM port on which to connect'),
        #Parameter('GPIB_num', 0, int, 'GPIB device on which to connect'),
        Parameter('enable_output', False, bool, 'Type-N output enabled'),
        Parameter('frequency', 3e9, float, 'frequency in Hz, or with label in other units ex 300 MHz'),
        Parameter('amplitude', -60, float, 'Type-N amplitude in dBm'),
        Parameter('phase', 0, float, 'output phase'),
        Parameter('enable_modulation', True, bool, 'enable modulation'),
        Parameter('modulation_type', 'FM', ['AM', 'FM', 'PhaseM', 'Freq sweep', 'Pulse', 'Blank', 'IQ'],
                  'Modulation Type: 0= AM, 1=FM, 2= PhaseM, 3= Freq sweep, 4= Pulse, 5 = Blank, 6=IQ'),
        Parameter('modulation_function', 'External', ['Sine', 'Ramp', 'Triangle', 'Square', 'Noise', 'External'],
                  'Modulation Function: 0=Sine, 1=Ramp, 2=Triangle, 3=Square, 4=Noise, 5=External'),
        Parameter('pulse_modulation_function', 'External', ['Square', 'Noise(PRBS)', 'External'], 'Pulse Modulation Function: 3=Square, 4=Noise(PRBS), 5=External'),
        Parameter('dev_width', 32e6, float, 'Width of deviation from center frequency in FM Hz'),
        Parameter('mod_rate', 1e7, float, 'Rate of modulation [Hz]')
    ])

    def __init__(self, name=None, settings=None, ip_address=_IP, port=_PORT):
        self.addr = (ip_address,port)       #sets address to communicate with device
        super(MicrowaveGenerator, self).__init__(name, settings)       #runs init of parent class
        #super().__init__(name,settings)

    def send_command(self, command):
        query = '?' in command      #if the command has a ?, query signifies that there will be a response
        if not command.endswith('\n'):
            command += '\n'
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as self.mysocket:
            self.mysocket.connect(self.addr)
            self.mysocket.sendall(command.encode())
            if query:
                reply = b''
                while not reply.endswith(b'\n'):        #recives bytes until the characters \n
                    reply += self.mysocket.recv(1024)   #recives up to size 1024
                return reply.decode()
            else:
                return None

    def update(self, settings):
        """
        Updates the internal settings of the SG384, and then also updates physical parameters such as
        frequency, amplitude, modulation type, etc in the hardware
        Args:
            settings: a dictionary in the standard settings format
            Ex: {'frequency':2e9} sets frequency to 2 GHz
        """
        super(MicrowaveGenerator, self).update(settings)
        #super().update(settings)
        for key, value in settings.items():
            if key == 'connection_type':
                self._connect()
            elif not (key == 'port' or key == 'GPIB_num'):
                if self.settings.valid_values[key] == bool: #converts booleans, which are more natural to store for
                    value = int(value)                      #on/off, to the integers used internally in the SRS
                elif key == 'modulation_type':
                    value = self._mod_type_to_internal(value)
                elif key == 'modulation_function':
                    value = self._mod_func_to_internal(value)
                elif key == 'pulse_modulation_function':
                    value = self._pulse_mod_func_to_internal
                # elif key == 'frequency':
                #     if value > RANGE_MAX or value < RANGE_MIN:
                #         raise ValueError("Invalid frequency. All frequencies must be between 2.025 GHz and 4.050 GHz.")
                key = self._param_to_internal(key)
                # only send update to Device if connection to Device has been established
                if self._settings_initialized:
                    self.send_command(key + ' ' + str(value))

    @property
    def _PROBES(self):
        return{
            'enable_output': 'if type-N output is enabled',
            'frequency': 'frequency of output in Hz',
            'amplitude': 'type-N amplitude in dBm',
            'phase': 'phase',
            'enable_modulation': 'is modulation enabled',
            'modulation_type': 'Modulation Type: 0= AM, 1=FM, 2= PhaseM, 3= Freq sweep, 4= Pulse, 5 = Blank, 6=IQ',
            'modulation_function': 'Modulation Function: 0=Sine, 1=Ramp, 2=Triangle, 3=Square, 4=Noise, 5=External',
            'pulse_modulation_function': 'Pulse Modulation Function: 3=Square, 4=Noise(PRBS), 5=External',
            'dev_width': 'Width of deviation from center frequency in FM',
            'mod_rate': 'Rate of modulation in Hz'
        }

    def read_probes(self, key):
        # assert hasattr(self, 'srs') #will cause read_probes to fail if connection not yet established, such as when called in init
        assert(self._settings_initialized) #will cause read_probes to fail if settings (and thus also connection) not yet initialized
        assert key in list(self._PROBES.keys())

        #query always returns string, need to cast to proper return type
        if key in ['enable_output', 'enable_rf_output', 'enable_modulation']:
            key_internal = self._param_to_internal(key)
            value = int(self.send_command(key_internal + '?'))
            if value == 1:
                value = True
            elif value == 0:
                value = False
        elif key in ['modulation_type', 'modulation_function', 'pulse_modulation_function']:
            key_internal = self._param_to_internal(key)
            value = int(self.send_command(key_internal + '?'))
            if key == 'modulation_type':
                value = self._internal_to_mod_type(value)
            elif key == 'modulation_function':
                value = self._internal_to_mod_func(value)
            elif key == 'pulse_modulation_function':
                value = self._internal_to_pulse_mod_func(value)
        else:
            key_internal = self._param_to_internal(key)
            value = float(self.send_command(key_internal + '?'))
        return value

    @property       #@property mean you call method without () since its not an 'active function' ex. mw.is_connected
    def is_connected(self):
        try:
            self.send_command('*IDN?') # arbitrary call to check connection, throws exception on failure to get response
            return True
        except (socket.timeout, socket.error) as e:
            print(f"Connection error: {e}")
            return False

    def close(self):    #calling socket.socket using WITH command automatically closes after execution.
        pass

    def _param_to_internal(self, param):
        """
        Converts settings parameters to the corresponding key used for GPIB commands in the SRS.
        Args:
            param: settings parameter, ex. enable_output

        Returns: GPIB command, ex. ENBR

        """
        if param == 'enable_output':
            return 'ENBR'
        if param == 'enable_rf_output':
            return 'ENBL'
        elif param == 'frequency':
            return 'FREQ'
        elif param == 'amplitude':
            return 'AMPR'
        elif param == 'amplitude_rf':
            return 'AMPL'
        elif param == 'phase':
            return 'PHAS'
        elif param == 'enable_modulation':
            return 'MODL'
        elif param == 'modulation_type':
            return 'TYPE'
        elif param == 'modulation_function':
            return 'MFNC'
        elif param == 'pulse_modulation_function':
            return 'PFNC'
        elif param == 'dev_width':
            return 'FDEV'
        elif param == 'mod_rate':
            return 'RATE'
        else:
            raise KeyError

    def _mod_type_to_internal(self, value):
        #COMMENT_ME
        if value == 'AM':
            return 0
        elif value == 'FM':
            return 1
        elif value == 'PhaseM':
            return 2
        elif value == 'Freq sweep':
            return 3
        elif value == 'Pulse':
            return 4
        elif value == 'Blank':
            return 5
        elif value == 'IQ':
            return 6
        else:
            raise KeyError

    def _internal_to_mod_type(self, value):
        #COMMENT_ME
        if value == 0:
            return 'AM'
        elif value == 1:
            return 'FM'
        elif value == 2:
            return 'PhaseM'
        elif value == 3:
            return 'Freq sweep'
        elif value == 4:
            return 'Pulse'
        elif value == 5:
            return 'Blank'
        elif value == 6:
            return 'IQ'
        else:
            raise KeyError

    def _mod_func_to_internal(self, value):
        #COMMENT_ME
        if value == 'Sine':
            return 0
        elif value == 'Ramp':
            return 1
        elif value == 'Triangle':
            return 2
        elif value == 'Square':
            return 3
        elif value == 'Noise':
            return 4
        elif value == 'External':
            return 5
        else:
            raise KeyError

    def _internal_to_mod_func(self, value):
        #COMMENT_ME
        if value == 0:
            return 'Sine'
        elif value == 1:
            return 'Ramp'
        elif value == 2:
            return 'Triangle'
        elif value == 3:
            return 'Square'
        elif value == 4:
            return 'Noise'
        elif value == 5:
            return 'External'
        else:
            raise KeyError

    def _pulse_mod_func_to_internal(self, value):
        #COMMENT_ME
        if value == 'Square':
            return 3
        elif value == 'Noise(PRBS)':
            return 4
        elif value == 'External':
            return 5
        else:
            raise KeyError

    def _internal_to_pulse_mod_func(self, value):
        #COMMENT_ME
        if value == 3:
            return 'Square'
        elif value == 4:
            return 'Noise(PRBS)'
        elif value == 5:
            return 'External'
        else:
            raise KeyError



class RFGenerator(MicrowaveGenerator):
    """
    Just a clone of MWGenerator, except that this only allows BNC output
    """

    _DEFAULT_SETTINGS = Parameter([
        #Parameter('connection_type', 'GPIB', ['GPIB', 'RS232'], 'type of connection to open to controller'),
        #Parameter('port', 19, list(range(0, 31)), 'GPIB or COM port on which to connect'),
        ## JG: what out for the ports this might be different on each computer and might cause issues when running export default
        #Parameter('GPIB_num', 0, int, 'GPIB device on which to connect'),
        Parameter('enable_rf_output', False, bool, 'BNC output enabled'),
        Parameter('frequency', 3e9, float, 'frequency in Hz, or with label in other units ex 300 MHz'),
        Parameter('amplitude_rf', -60, float, 'BNC amplitude in dBm'),
        Parameter('phase', 0, float, 'output phase'),
        Parameter('enable_modulation', True, bool, 'enable modulation'),
        Parameter('modulation_type', 'FM', ['AM', 'FM', 'PhaseM', 'Freq sweep', 'Pulse', 'Blank', 'IQ'],
                  'Modulation Type: 0= AM, 1=FM, 2= PhaseM, 3= Freq sweep, 4= Pulse, 5 = Blank, 6=IQ'),
        Parameter('modulation_function', 'External', ['Sine', 'Ramp', 'Triangle', 'Square', 'Noise', 'External'],
                  'Modulation Function: 0=Sine, 1=Ramp, 2=Triangle, 3=Square, 4=Noise, 5=External'),
        Parameter('pulse_modulation_function', 'External', ['Square', 'Noise(PRBS)', 'External'],
                  'Pulse Modulation Function: 3=Square, 4=Noise(PRBS), 5=External'),
        Parameter('dev_width', 32e6, float, 'Width of deviation from center frequency in FM')
    ])

    @property
    def _PROBES(self):
        return{
            'enable_rf_output': 'if BNC output is enabled',
            'frequency': 'frequency of output in Hz',
            'amplitude_rf': 'BNC amplitude in dBm',
            'phase': 'phase',
            'enable_modulation': 'is modulation enabled',
            'modulation_type': 'Modulation Type: 0= AM, 1=FM, 2= PhaseM, 3= Freq sweep, 4= Pulse, 5 = Blank, 6=IQ',
            'modulation_function': 'Modulation Function: 0=Sine, 1=Ramp, 2=Triangle, 3=Square, 4=Noise, 5=External',
            'pulse_modulation_function': 'Pulse Modulation Function: 3=Square, 4=Noise(PRBS), 5=External',
            'dev_width': 'Width of deviation from center frequency in FM'
        }

if __name__ == '__main__':


    mw = MicrowaveGenerator()
    #arbitrarty call to see if device is connected and communicating properly
    print(mw.is_connected)
    print("Frequency is {} Hz".format(mw.read_probes('frequency')))

