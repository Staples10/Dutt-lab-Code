from src.Controller.nanodrive import MCL_NanoDrive
import pytest
import numpy as np
import matplotlib.pyplot as plt
from time import sleep

@pytest.fixture
def get_nandrive() -> MCL_NanoDrive:
    return MCL_NanoDrive()

def test_connection(get_nandrive):
    assert get_nandrive.is_connected

def test_position(get_nandrive):
    '''
    Read axis range and ensures it is a float. Sets axis position and read to make sure it is within 10 nm of specified
    '''
    nd = get_nandrive
    ax_range = nd.read_probes('axis_range')
    nd.update(settings={'position':5})
    pos = nd.read_probes('position',axis='x')
    assert isinstance(ax_range, float)
    assert 4.99 <= pos <= 5.01 #check to make sure atleast within 10 nm. Usally closer than 10nm to inputed position but not at exactly 5

@pytest.mark.parametrize('clock',['Pixel','Line','Frame','Aux'])
@pytest.mark.parametrize('mode',[0,1])
def test_clock_mode(get_nandrive,clock,mode):
    '''
    Code Testing: Iterates through mode settings of each clock to make sure there is no error from error dictionary.
        Passes if no 'raise' triggered in code
    Physically tested using an oscilliscope and outputs on back of NanoDrive
        Pass if clock is set to proper mode after command

        Tested using scope 7/22/24 - Dylan
    '''
    get_nandrive.clock_functions(clock, mode=mode)

@pytest.mark.parametrize('clock',['Pixel','Line','Frame','Aux'])
@pytest.mark.parametrize('polarity',[0,1])
def test_clock_polarity(get_nandrive,clock,polarity):
    '''
    Code Testing: Iterates through polarity settings of each clock to make sure there is no error from error dictionary.
        Passes if no 'raise' triggered in code
    Physically tested using an oscilliscope and outputs on back of NanoDrive
        -Mode of each clock is set to low and the polarity is set as low-to-high. Passes if triggering a pulse puts clock to high
        -Also works vice versa (mode: high, polarity: high-to-low)
        -Also a test to confirm pulse command triggers

        Tested using scope 7/22/24 - Dylan
        Code test passed
    '''
    get_nandrive.clock_functions(clock, polarity=polarity)

@pytest.mark.parametrize('clock',['Pixel','Line','Frame','Aux'])
@pytest.mark.parametrize('binding',['x','y','z','read','load'])
@pytest.mark.parametrize('polarity',[0,1,2])
def test_clock_binding(get_nandrive,clock,binding,polarity):
    '''
    Code Testing: Iterates through binding option to make sure commands dont trigger error dictionary
        Passes if no 'raise' triggered in code
    Physically tested using oscilliscope in the same mannor as test_clock_polarity

        Tested using scope 7/22/24 - Dylan
    '''
    nd = get_nandrive
    nd.clock_functions(clock,polarity=polarity, binding=binding)

def test_clock_reset(get_nandrive):
    '''
    Test to see if error when sending reset command. Note pixel input is arbitrary ALL clocks are reset to defaults
    '''
    get_nandrive.clock_functions('Pixel',reset=True)

def test_single_ax_waveform(capsys,get_nandrive):
    '''
    1) Loads waveform and then reads waveform on x axis
    2) Sets up load and sets up read then triggers waveform acquisition on y axis

    -Expected output of plot is that x_read and y_read are slightly off from inputed waveform but
     have same start and end values. This issue appears b/c of some load and read rate disparity.
     I believe reading starts slightly before loading. Will update comment with more issue once tested
    '''
    wf = list(np.arange(0,10.1,0.1)) #wavefrom must be a list for internal conversion/checks
    nd = get_nandrive
    nd.update(settings={'position':0}, axis='x')
    nd.update(settings={'position': 0}, axis='y')

    nd.update(settings={'num_datapoints':len(wf),'load_waveform':wf},axis='x')
    x_read = nd.read_probes('read_waveform',axis='x')
    sleep(1)    #sleep may not be neccesary but I dont want/need to trigger both axes at once

    nd.setup(settings={'num_datapoints':len(wf),'load_waveform':wf},axis='y')
    nd.setup(settings={'read_waveform':nd.empty_waveform})
    nd.waveform_acquisition(axis='y')
    y_read = nd.read_probes('read_waveform',axis='y')

    with capsys.disabled():
        plt.figure(figsize=(10, 6))
        plt.plot(wf, x_read, label='Load than read waveform', marker='o')
        plt.plot(wf, y_read, label='Set load and read then acquisition', marker='x')
        plt.plot(wf, wf, label='Input waveform', linestyle='--')

        plt.xlabel('Input Waveform')
        plt.ylabel('Read Values')
        plt.title('Comparison of read vs inputed waveform')
        plt.legend()
        plt.grid(True)
        plt.show()
    assert len(wf) == len(x_read) == len(y_read)
    #also test with reverse: wf_reveresed = np.arange(0, 10.1, 0.1)[::-1]


def test_mult_ax_waveform(capsys,get_nandrive):
    '''
    Sets up, triggers, then read a multi axis waveform. Plots read data to compare with inputed
    '''
    mult_wf = [list(np.arange(0,10.1,0.1)),list(np.arange(0,10.1,0.1)),[0]]
    nd = get_nandrive
    nd.update(settings={'position': 0}, axis='x')
    nd.update(settings={'position': 0}, axis='y')
    nd.update(settings={'position': 0}, axis='z')

    nd.setup(settings={'mult_ax':{'waveform':mult_wf,'time_step':1,'iterations':1}})
    nd.trigger('mult_ax')
    read_wf = nd.read_probes('mult_ax_waveform')

    with capsys.disabled():
        fig, axs = plt.subplots(1, 3, figsize=(18, 6))

        axs[0].plot(mult_wf[0], label='Loaded waveform')
        axs[0].plot(read_wf[0], label='Read wavefrom', linestyle='--')
        axs[0].set_title('x-axis')

        axs[1].plot(mult_wf[1], label='Loaded waveform')
        axs[1].plot(read_wf[1], label='Read waveform', linestyle='--')
        axs[1].set_title('y-axis')

        axs[2].plot(mult_wf[2], label='Loaded waveform')
        axs[2].plot(read_wf[2], label='Read waveform', linestyle='--')
        axs[2].set_title('z-axis')

        for i in range(3):
            axs[i].set_xlabel('Index')
            axs[i].set_ylabel('Waveform value')
            axs[i].legend()
            axs[i].grid(True)

        plt.suptitle('Loaded and Read Waveforms for Multi-Axis Command')
        plt.show()

    assert len(read_wf[0]) == len(read_wf[1]) == len(read_wf[2])


def test_continuos_mult_ax_waveform():
    '''
    Triggers and infinite mult_ax waveform, waits 1 second then stops
    '''
    mult_wf = [list(np.arange(0, 10.1, 0.1)), list(np.arange(0, 10.1, 0.1)), [0]]
    nd = get_nandrive
    nd.update(settings={'position': 0}, axis='x')
    nd.update(settings={'position': 0}, axis='y')
    nd.update(settings={'position': 0}, axis='z')
    #iterations = 0 is for infinite loop
    nd.setup(settings={'mult_ax': {'waveform': mult_wf, 'time_step': 1, 'iterations': 0}})
    nd.trigger('mult_ax')
    sleep(1)
    nd.trigger('mult_ax',mult_ax_stop=True)





