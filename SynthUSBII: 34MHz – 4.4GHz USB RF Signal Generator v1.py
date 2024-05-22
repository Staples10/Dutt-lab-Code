#Code for using Windfreak Technologies SynthUSBII: 34MHz – 4.4GHz USB RF Signal Generator.
#Communicates with device (serial) using Pyvisa.
#Other than initialization and close the 2 main functions are to set a frequency and sweep over a range of frequencies with given freq and time steps.

import pyvisa as visa
from time import sleep

class USB_RFGenerator:

    f_lower_limit = 35.0 #Mhz
    f_upper_limit = 4400.0 #Mhz / 4.4Ghz
    def __init__(self,address):                #initialize device by calling usb = USB_RFGenerator('device addresss') 
        self.rm = visa.ResourceManager()       #Add code to initialize with computer recognizing address (see MicrowaveGenerator class on Dutt Lab Github)
        self.RFGen = self.rm.open_resource(address)        #example address for windows 'ASRL9::INSTR'
        self.RFGen.write('o1')  #turns on
        self.RFGen.write('h1')   #sets power to high

    def set_power(self,power):
        if power not in (0,1,2,3):
            print('Not valid power setting. Input 0-3')
        else:
            self.RFGen.write(f'a{power}')

    def set_frequency(self,frequency):
        freq = float(frequency)
        if freq < self.f_lower_limit or freq > self.f_upper_limit:
            print('Frequency Invalid. Input a frequency between 35 and 4400 (has units of Mhz)')
        else:
            self.RFGen.write(f'f{freq}')

    def read_frequency(self):   #untested
        freq = self.RFGen.write('f?')
        return freq
    
    #this sweep attempts to use the built-in commands on the RF Generator however when run the time step, freq step, and run sweep commands seem to not exist.
    def sweep_not_working(self,low_freq,upper_freq,step_size,time_step):    #Doesnt work. Issue seting freq and time steps and runing sweep.
        low, upper, step, time = float(low_freq), float(upper_freq), float(step_size), float(time_step)
        self.RFGen.write(f'l{low}')         #parameters for sweep
        self.RFGen.write(f'u{upper}')
        self.RFGen.write(f's{step}')
        self.RFGen.write(f't{time}')        #time is in milliseconds
        self.RFGen.write('g1')              #runs sweep

    def sweep(self,low_freq,upper_freq,step_size,time_step):    #longer method of sending each frequency with a desired wait time in between
        low, upper, step, time = float(low_freq), float(upper_freq), float(step_size), float(time_step)
        for i in range(int((upper - low)/step)+1):
            freqency_step = float(low + i*step)
            self.RFGen.write(f'f{freqency_step}')
            sleep(time)     #time each signal step is outputed in seconds

    def option(self):    #function to let user know of all options for communicating with device. Needs coded. Likely just print statements with descriptions
        pass

    def close(self):
        self.RFGen.write('o0')  #turns off
        self.RFGen.close()
