#!/bin/python3

import libm2k
import adi
import matplotlib.pyplot as plt
import numpy as np
import subprocess
import sys

buffer_size = 40000
sample_delay = -1000
out_oversampling = 750
spi_test_val = 3987
#show_plot = True
show_plot = False
show_decode = False
#show_decode = True
decode_sh = "../bash/decode.sh"

m2k_uri = "ip:192.168.2.1"
ad5592r_uri = "ip:127.0.0.1"

def voltage4(ad):
    return ad.voltage4_adc.raw * (ad.voltage4_adc.scale / 1000.0)

def voltage3_w(ad, val):
    ad.voltage3_dac.raw  = clamp((val / ad.voltage3_dac.scale * 1000),0,4095)
    
def voltage3_r(ad):
    return ad.voltage3_adc.raw * (ad.voltage3_adc.scale / 1000.0)

def voltage2_w(ad, val):
    ad.voltage2_dac.raw = clamp(val / ad.voltage2_dac.scale * 1000.0, 0, 4095)
    
def voltage2_r(ad):
    return ad.voltage2_adc.raw * (ad.voltage2_adc.scale / 1000.0)

_result_overall="OK"

def verify_range(val, th):
    global _result_overall
    if val <= th+0.1 and val >= th-0.1:
        return "OK"
    _result_overall = "NOK"
    return "NOK";

def verify_string_occurence(data, st):
    global _result_overall
    ret = data.find(st)
    if ret == -1:
        _result_overall = "NOK"
        return "NOK"
    return "OK"

    

def clamp(val , min, max):
    if val < min:
        return min
    if val > max:
        return max
    return val

def demux_digital_channels(digital_data):
    
    arr = []
    for i in range(16):
        bit = [((val & (1<<i)) >> i) for val in digital_data]
        arr.append(np.array(bit))
    return arr

ad=adi.ad5592r(ad5592r_uri)
m2k=libm2k.m2kOpen(m2k_uri)

# m2k.calibrate()

aout=m2k.getAnalogOut()
ain=m2k.getAnalogIn()
dig=m2k.getDigital()
trig=ain.getTrigger()

aout.setCyclic(0,True)
aout.setSampleRate(0,75000000)
aout.setOversamplingRatio(0, out_oversampling)
aout.enableChannel(0, True)

ain.setSampleRate(10000000)
ain.setRange(0, -2.5, 2.5)
ain.setRange(1, -2.5, 2.5)
ain.enableChannel(0,True)
ain.enableChannel(1,True)

dig.setSampleRateIn(10000000)
# channels are set to input by default
trig.reset()


if hasattr(ad,"voltage4_adc"):
    print("OK - Check existence of ad5592r - ch4")
else:
    print("NOK - Check existence of ad5592r - ch4")
    print("Check devicetree/iio_info")
    exit()


print("Checking M2k W1 to AD5592R-CH4 ...")
ad.voltage4_adc.scale = ad.voltage4_adc.scale_available[0]

val = voltage4(ad)
result = verify_range(val , 0)
print(result," - M2k W1 off - AD5592R-CH4: ", val)

val = ain.getVoltage(1)
result = verify_range(val , 0)
print(result, " - M2k W1 off - M2k 2+ : ", val)

outbuf = [1.1] * 1024
aout.push(0,outbuf);

val = voltage4(ad)
result = verify_range(val, 1.1)
print(result, " - M2k-W1 1.1V - AD5592R-CH4 in range: ", val)

val = ain.getVoltage(1)
result = verify_range(val, 1.1)
print(result, " - M2k W1 1.1V - M2k 2+ in range: ", val)

aout.stop()

voltage2_w(ad, 0)
voltage3_w(ad, 0)

val = voltage3_r(ad)
result = verify_range(val , 0)
print(result, " - AD5592R-CH3-out 0V - AD5592R-CH3-in: ", val)

val = ain.getVoltage(0)
result = verify_range(val , 0)
print(result, " - AD5592R-CH3-out 0V - M2k 1+: ", val)

voltage3_w(ad,0)
voltage2_w(ad,2.5)
print("STATUS - RED LED ON")

val = voltage2_r(ad)
result = verify_range(val , 2.5)
print(result, " - AD5592R-CH3-out 2.5V - AD5592R-CH3-in: ", val)

val = ain.getVoltage(0)
result = verify_range(val , 0.1)
print(result, " - AD5592R-CH3-out 2.5V - M2k 1+: ", val)

voltage3_w(ad,2.5) 
val = voltage3_r(ad)
result = verify_range(val , 2.5)
print(result, " - AD5592R-CH3-out 2.5V - AD5592R-CH3-in: ", val)

result = verify_range(val , 2.5)
print(result, " - AD5592R-CH3-out 2.5V - M2k 1+: ", val)

######
# SETUP AD5592R SIGNAL
######
voltage2_w(ad,0) # reset voltage to 0
voltage3_w(ad,0) # reset voltage to 0

#####
## START STAIR STEP
#####
outbuf = [0] * 10 + [0.5]*10 + [1]*10 + [1.5]*10
aout.enableChannel(0, True)
aout.push(0,outbuf)

#####
## SETUP MIXED SIGNAL MODE
#####
print("STATUS - SETUP MIXED SIGNAL ACQUISITION")
trig.setAnalogDelay(sample_delay)
#trig.setAnalogLevel(0, 1.2)
#trig.setAnalogCondition(0, libm2k.RISING_EDGE_ANALOG)
trig.setAnalogSource(libm2k.SRC_DIGITAL_IN)
trig.setAnalogMode(0, libm2k.ANALOG)
trig.setDigitalDelay(sample_delay)
trig.setDigitalSource(libm2k.SRC_NONE)
trig.setDigitalCondition(0, libm2k.NONE)
trig.setDigitalCondition(1, libm2k.NONE)
trig.setDigitalCondition(2, libm2k.NONE)
trig.setDigitalCondition(3, libm2k.FALLING_EDGE_DIGITAL)

#ain.startAcquisition(4000) # non-blocking capture
#dig.startAcquisition(4000) # non-blocking capture
print("STATUS - STARTED MIXED SIGNAL ACQUISITION")
m2k.startMixedSignalAcquisition(buffer_size)

#####
# STIMULUS
#####
# voltage2_w(ad,0)
ad.voltage3_dac.raw = spi_test_val # set known raw value
v3 = ad.voltage3_adc.raw           # read raw value 
print("STATUS - GREEN LED ON")

#####
# Get Samples from M2k
#####
analog_data = ain.getSamples(buffer_size) # GET SAMPLES FROM M2k
digital_data = dig.getSamples(buffer_size) # GET SAMPLES FROM M2k
m2k.stopMixedSignalAcquisition()

#####
# SAVE TO FILE
#####
with open("analog_capture.csv","w") as f:
    for samp in range(len(analog_data[0])):
        f.write(str(analog_data[0][samp]) + "," +str(analog_data[1][samp]) + "\n")
print("STATUS - Saved analog data to analog_capture.csv")

with open("digital_capture.csv","w") as f:
    for val in digital_data:
        f.write(str(val) + "\n")
print("STATUS - Saved digital data to digital_capture.csv")

#####
# SEND TO SIGROK
#####
data = np.array(digital_data,dtype='<u2').tobytes()
with open("digital_capture.bin","wb") as f:
    f.write(data)

#####
# UNFORTUNATELY THERE IS NO SIGROK INTERFACE IN PYTHON
# WE RELY ON SIGROK-CLI
#####

proc = subprocess.run(["/bin/bash",decode_sh], input=data,  capture_output=True)
decoded_data = proc.stdout.decode()
with open("decoded_data.txt","w") as f:
    f.write(decoded_data)
if show_decode:
    print(decoded_data)

result = verify_string_occurence(decoded_data, str(spi_test_val))
print(result," - Sniffing MOSI, SCLK, CS - ", spi_test_val)
result = verify_string_occurence(decoded_data, str(v3))
print(result," - Sniffing MISO too - ", str(v3))

print("STATUS - Saved decoded messages to decoded_data.txt")


#####
# pretty plotting
######

processed_digital_data = demux_digital_channels(digital_data)
plt.plot(analog_data[0])
plt.plot(analog_data[1])
plot_offset = 6
plot_spacing = 1.2
for ch in [0,1,2,3]:
    plt.plot(processed_digital_data[ch] + plot_spacing * ch + plot_offset)
if show_plot:
    plt.show()
plt.savefig("plot.png")
print("STATUS - Saved to plot.png")

#####
# CLEANUP
#####
print("STATUS - CLEANUP")
print("TEST RESULT - ", _result_overall)
if(_result_overall == "NOK"):
    print("Check calibration, check GND, check connections")

aout.stop()
trig.reset()
libm2k.contextClose(m2k)
