import pyvisa as visa
from time import sleep

class USB_RFGenerator:

    f_lower_limit = 35.0 #Mhz
    f_upper_limit = 4400.0 #Mhz / 4.4Ghz
    def __init__(self,address): #ASRL9::INSTR for this usb
        self.rm = visa.ResourceManager()
        self.RFGen = self.rm.open_resource(address)
        self._send_command('o','1')     #turns on
        self._send_command('h','1')     #sets power to high
        self._send_command('x','1')     #sets internal reference

    def _send_command(self,command_letter,value):
        self.RFGen.write(f'{command_letter}{value}')
        sleep(0.25)     #sleep time of 0.25 secs to ensure a second command is not sent before the first one is recieved by device

    def _ask_value(self,command_letter):
        self.RFGen.write(f'{command_letter}?')
        sleep(0.1)
        return self.RFGen.read().strip()

    def set_power(self,power):
        if power not in (0,1,2,3):
            print('Not valid power setting. Input 0-3')
        else:
            self._send_command('a',power)

    def set_frequency(self,frequency):
        freq = float(frequency)
        if freq < self.f_lower_limit or freq > self.f_upper_limit:
            print('Frequency Invalid. Input a frequency between 35 and 4400 (Mhz)')
        else:
            self._send_command('f',freq)

    def read_frequency(self):
        return self._ask_value('f')

    def sweep(self,low_freq,upper_freq,step_size,time_step):
        low, upper, step, time = float(low_freq), float(upper_freq), float(step_size), float(time_step)
        self._send_command('l',low)     #parameters for sweep
        self._send_command('u',upper)
        self._send_command('s',step)
        self._send_command('t',time)    #time step is in milliseconds
        self._send_command('g','1')     #runs sweep
        return 'running sweep'

    def pulse(self):
        pass        #options for pulse on and pulse off timing can add if required/useful

    def options(self):
        pass

    def close(self):
        self._send_command('f',0)   #clears frequncy being generated
        self._send_command('o',0)   #turns off output
        self.RFGen.close()

'''
stuff to add to model:
    - continuous sweep that sweeps continuously for a specific time, number of cycles, or 
    - return values with units and better user readability

'''
