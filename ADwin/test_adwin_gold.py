from src.Controller.adwin import ADwin_Gold
import pytest
import os
import numpy as np
import matplotlib.pyplot as plt
from time import sleep

@pytest.fixture
def get_adwin() -> ADwin_Gold:
    return ADwin_Gold()

def test_connection(get_adwin):
    assert get_adwin.is_connected

def test_processes(get_adwin,capsys):
    '''
    Loads a test process, sets delay, starts, waits 0.25 sec, stops, reads variable, then clears
    '''
    adw = get_adwin
    #get adbasic file path
    root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
    simple_adbasic = os.path.join(root_directory, 'src', 'Controller', 'binary_files', 'Test_ADbasic.TB4')

    #load script and set delay to 16.5 microseconds (5000x3.3ns)
    adw.update({'process_4':{'load':simple_adbasic,'delay':5000}})
    delay = adw.read_probes('process_delay',id=4)
    assert delay == 5000

    status1 = adw.read_probes('process_status',id=4)    #reads process status for process 4
    assert status1 == 'Not Running'

    adw.update({'process_4':{'start':True}})
    sleep(0.125)
    status2 = adw.read_probes('process_status',id=4)
    assert status2 == 'Running'

    adw.update({'process_4':{'stop':True}})
    sleep(0.125) #gives time for process to stop
    status3 = adw.read_probes('process_status',id=4)
    assert status3 == 'Not Running'

    #set FPar_12 = 5.0, Data_56 = [0,1,2,3,4,5], and Data_8 = 'Hello' in script
    FPar_12 = adw.read_probes('float_var',id=12)
    length_data_56 = adw.read_probes('array_length',id=56)
    Data_56 = adw.read_probes('int_array',id=56,length=length_data_56)
    length_str = adw.read_probes('str_length',id=8)
    str_Data_8 = adw.read_probes('str_array',id=8,length=length_str)
    assert FPar_12 == 5.0 and Data_56 == [0,1,2,3,4,5] and str_Data_8 == 'Hello'

    adw.update({'process_4':{'load':''}})   #clears process by entering load as an empty string

    with capsys.disabled():
        print('Statuses: ',status1,' ',status2,' ',status3,'\n',
              'Variables: ',FPar_12,' ',Data_56,' ',str_Data_8,'\n')

def test_counter(get_adwin,capsys):
    root_directory = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    counter_file = os.path.join(root_directory, 'src', 'Controller', 'binary_files', 'Trial_Counter.TB1')
    #counter_file = 'D:PycharmProjects\pittqlabsys\src\Controller\binary_files\ADbasis\\Trial_Counter.TB1'

    adw = get_adwin
    data = []   #array to hold counts data
    i = 0
    adw.update({'process_1':{'load':counter_file,'start':True}})    #loads and start process
    cnt_status = adw.read_probes('process_status',id=1)
    assert cnt_status == 'Running'

    while i < 20:
        raw_value = adw.read_probes('int_var',id=1)
        data.append(raw_value)
        i += 1
        sleep(0.1)      #sleep for short time to make bins of 'size' 0.1 seconds

    with capsys.disabled():
        print(counter_file)
        print(data)

