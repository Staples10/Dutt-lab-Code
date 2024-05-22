import pyvisa as visa
from time import sleep

class USB_RFGenerator:

    f_lower_limit = 35.0 #Mhz
    f_upper_limit = 4400.0 #Mhz / 4.4Ghz
    def __init__(self,address):
        self.rm = visa.ResourceManager()
        self.RFGen = self.rm.open_resource(address)
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

    def sweep_not_working(self,low_freq,upper_freq,step_size,time_step):    #Doesnt work. Issue seting freq and time steps and runing sweep.
        low, upper, step, time = float(low_freq), float(upper_freq), float(step_size), float(time_step)
        self.RFGen.write(f'l{low}')         #parameters for sweep
        self.RFGen.write(f'u{upper}')
        self.RFGen.write(f's{step}')
        self.RFGen.write(f't{time}')        #time is in milliseconds
        self.RFGen.write('g1')              #runs sweep

    def sweep(self,low_freq,upper_freq,step_size,time_step):    #long method of sending each frequency
        low, upper, step, time = float(low_freq), float(upper_freq), float(step_size), float(time_step)
        for i in range(int((upper - low)/step)+1):
            freqency_step = float(low + i*step)
            self.RFGen.write(f'f{freqency_step}')
            sleep(time)     #time each signal step is outputed in seconds

    def option(self):
        pass

    def close(self):
        self.RFGen.write('o0')  #turns off
        self.RFGen.close()