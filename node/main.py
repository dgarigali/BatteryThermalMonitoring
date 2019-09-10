#Import python default libraries
import sys
from time import sleep
from random import randrange
import json
import os
import RPi.GPIO as GPIO

#Import user defined libraries
from MLX90640 import API, ffi, temperature_data_to_ndarray, hertz_to_refresh_rate
from SX127x.LoRa import *
from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config import BOARD
import LoRaWAN
from LoRaWAN.MHDR import MHDR
import Adafruit_DHT

#----------------------------------------------------
#Global funcionts just for checking image locally

#Converts temperature value to RGB pixel
def temp_to_col(temp, T_min, T_max):

  val = 180.0 * (temp - T_min) / (T_max - T_min)
  if (val > 180):
    val = 180

  if(val >= 0 and val < 30):
    R = 0
    G = 0
    B = 20 + (120.0/30.0)*val
    
  elif(val < 60):
    R = (120.0 / 30) * (val - 30.0)
    G = 0
    B = 140 - (60.0/30.0) * (val - 30.0)
    
  elif(val < 90):
    R = 120 + (135.0/30.0) * (val - 60.0)
    G = 0
    B = 80 - (70.0/30.0) * (val - 60.0)
    
  elif(val < 120):
    R = 255
    G = 0 + (60.0/30.0) * (val - 90.0)
    B = 10 - (10.0/30.0) * (val - 90.0)

  elif(val < 150):
    R = 255
    G = 60 + (175.0/30.0) * (val - 120.0)
    B = 0
    
  elif(val <= 180):
    R = 255
    G = 235 + (20.0/30.0) * (val - 150.0)
    B = 0 + 255.0/30.0 * (val - 150.0)

  return tuple([int(R), int(G), int(B)])
  
#Creates .png file
def create_image(img_filename, T_min, T_max):
	norm = mpl.colors.Normalize(vmin=T_min, vmax=T_max)
	cmap = mpl.cm.ScalarMappable(norm=norm, cmap=mpl.cm.jet)
	cmap.set_array([])
	cb = plt.colorbar(cmap)
	cb.set_label("Temperature (Celsius)")
	plt.axis('off')
	plt.savefig("images/" + img_filename, bbox_inches='tight')
	plt.clf() 

from datetime import datetime
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib as mpl

img = Image.new( 'RGB', (24,32), "black")
#----------------------------------------------------

class Node(LoRa):
    
    #Constructor
    def __init__(self, verbose = False):
        super(Node, self).__init__(verbose)
        self.join_flag = False
        self.counter = 0
        self.nwskey = None
        self.appskey = None
        self.devaddr = None
        self.T_min = None
        self.former_payload = None
        self.read_json()	
        if(self.cfg["fan"] == "on"):
          self.fanON()
        else:
          self.fanOFF()
        self.check_threshold()
        
    #Read node parameters from .json local file
    def read_json(self):
        if(not os.path.isfile(filename)):
          print("Missing .json configuration file!")
          sys.exit(0)
        else:
          self.cfg = json.load(open(filename))
          
    #Update .json local file with node parameters
    def write_json(self):
        with open(filename, 'w') as outfile:  
          json.dump(self.cfg, outfile)
        
    #Turn on fan
    def fanON(self):
        GPIO.output(fan_pin, True)
        
    #Turn off fan
    def fanOFF(self):
        GPIO.output(fan_pin,False)

    #Called when message is received from gateway
    def on_rx_done(self):
        
        print("RxDone")

        #Get message payload
        self.clear_irq_flags(RxDone=1)
        payload = self.read_payload(nocheck=True)
        if(self.join_flag):
          lorawan = LoRaWAN.new(self.nwskey, self.appskey)
        else: 
          lorawan = LoRaWAN.new([], appkey)
        lorawan.read(payload)    
        payload = lorawan.get_payload()

        #Check if it is join ack
        if lorawan.get_mhdr().get_mtype() == MHDR.JOIN_ACCEPT:
            print("Got LoRaWAN join accept")
            self.nwskey = lorawan.derive_nwskey(devnonce)
            self.appskey = lorawan.derive_appskey(devnonce)
            self.devaddr = lorawan.get_devaddr()
            self.get_temp_array(); # Dummy values at beginning
            self.join_flag = True 
            
        else:
            
            print("Got LoRaWAN message") 
            
            #Check if messages are duplicated
            if (self.former_payload != payload): #Check message ID (2 most significant bits of first byte)
            
              ID = (payload[0] & 192) >> 6
              self.former_payload = payload
              
              #Check message ID
              if (ID == 3):
              
                #Temperature threshold
                MSB = payload[0] & 15
                #Check if number is negative
                if (MSB >> 2 == 3):
                  MSB |= 240
                temp_array = []
                temp_array.append(MSB)
                temp_array.append(payload[1])
                temp = int.from_bytes(temp_array, byteorder='big', signed=True)
                if (temp != self.cfg["threshold"]):
                  print("Temperature threshold changed to: " + str(temp))
                  self.cfg["threshold"] = temp
                  self.check_threshold()
                
                #Fan control
                fan_control = (payload[0] & 32) >> 5
                if (fan_control == 0 and self.cfg["fan"] == "on"):
                  print("Fan off!")
                  self.cfg["fan"] = "off"
                  #Turn off if threshold temperature is not achieved
                  if ((self.cfg["temp_max"]/10.0) <= self.cfg["threshold"]):
                    self.fanOFF()
                elif (fan_control == 1 and self.cfg["fan"] == "off"):
                  print("Fan on!")
                  self.cfg["fan"] = "on"
                  self.fanON()
                  
                #Transmission mode
                mode_control = (payload[0] & 16) >> 4
                if (mode_control == 0 and self.cfg["mode"] == "fast"):
                  print("Mode Slow!")
                  self.cfg["mode"] = "slow"
                  self.counter = 0
                elif (mode_control == 1 and self.cfg["mode"] == "slow"):
                  print("Mode Fast!")
                  self.cfg["mode"] = "fast"
                  self.counter = 0
                  
                #Update json file
                self.write_json()
              else:
                print("Received unknown message!")

    #Called when message was sent from gateway 
    def on_tx_done(self):
        print("TxDone")
        self.clear_irq_flags(TxDone=1)
        self.set_dio_mapping([0,0,0,0,0,0])
        self.set_invert_iq(1) 
        self.reset_ptr_rx()
        self.set_mode(MODE.RXCONT)
		self.counter += 1

    def start(self):
    
        #Send join request
        lorawan = LoRaWAN.new(appkey)
        lorawan.create(MHDR.JOIN_REQUEST, {'deveui': deveui, 'appeui': appeui, 'devnonce': devnonce})
        self.set_dio_mapping([1,0,0,0,0,0])
        self.write_payload(lorawan.to_raw())
        self.set_mode(MODE.TX)        
        
        #Wait for join acceptance
        while not self.join_flag:
          sleep(1)
        self.counter = 100
		  
		 #Send reset message
        print("Sending reset message to gateway!")
        
        self.set_dio_mapping([1,0,0,0,0,0])
        lorawan = LoRaWAN.new(self.nwskey, self.appskey)  
        lorawan.create(MHDR.UNCONF_DATA_UP, {'devaddr': self.devaddr, 'fcnt': self.counter, 'data': [0] })
        self.write_payload(lorawan.to_raw())
        self.set_mode(MODE.TX)  
        sleep(20)
        self.counter = 0
         
        #Loop
        while True:
		
		  #Dummy read
          self.get_temp_array();
        
          #Check if it is to read new_frame
          if ( (self.counter == 0) or (self.counter == 24 and self.cfg["mode"] == "slow") or (self.counter == 2 and self.cfg["mode"] == "fast")):
            self.counter = 0
            self.matrix = self.get_temp_array();
            self.matrix_red = []
			
            #Create image locally (just for debugging)
            timestamp = datetime.now()
            img_filename = str(int(timestamp.timestamp())) + ".png"
            for x in range(24):
              for y in range(32):
                img.putpixel((x, y), temp_to_col(round(self.matrix[x][y],1), round(min(map(min, self.matrix)),1), round(max(map(max, self.matrix)),1)))
            plt.imshow(img.resize((480,640), Image.BICUBIC))
            create_image(img_filename, round(min(map(min, self.matrix)),1), round(max(map(max, self.matrix)),1))			
            
            #Obtain critical points frame
            aux = [-50]*8
            for x11 in range(2):
              aux2 = []
              for x12 in range(3):
                for x2 in range(4):
                  for y1 in range(8):
                    for y2 in range(4):
                      value = round(self.matrix[(x11*3+x12)*4+x2][y1*4+y2], 1)
                      if (aux[y1] < value):
                        aux[y1] = value
                      if(x2 == 3 and y2 == 3):
                        aux2.append(aux[y1])
                        aux[y1] = -50
              self.matrix_red.append(aux2)
            
		  #Turn on fan case temperature is greater than threshold
          last_flag = (self.counter == 23 and self.cfg["mode"] == "slow") or (self.counter == 1 and self.cfg["mode"] == "fast")
          if (last_flag):
              self.cfg["temp_max"] = int(round(max(map(max, self.matrix)),1)*10)
              self.T_min = round(min(map(min, self.matrix)),1)
              self.write_json()				
              
          #Send frame line
          self.check_threshold()
          self.camara_line(last_flag)
          self.send_message()
          sleep(25)

    #Read temperature matrix from thermal camera
    def get_temp_array(self):
        API.GetFrameData(MLX_I2C_ADDR, frame_buffer);
        tr = API.GetTa(frame_buffer, params) - TA_SHIFT
        API.CalculateTo(frame_buffer, params, emissivity, tr, image_buffer);
        return temperature_data_to_ndarray(image_buffer)
        
    #Prepare camara data to be sent in bytes
    def camara_line(self, last_flag):
    
        self.byte_array = [] 
        
        #Check transmission mode
        if (self.cfg["mode"] == "slow"):
          aux_matrix = self.matrix
          if (last_flag):
              lenght = 34
          else:
              lenght = 32
		
        else:
          aux_matrix = self.matrix_red
          if (last_flag):
              lenght = 26
          else:
              lenght = 24
        
        #Prepare line be sent
        for y in range(0, lenght, 2):
            if (last_flag and y == lenght - 2):
                value1 = self.int_to_bytes(int(self.T_min*10),2)
                value2 = self.int_to_bytes(int(self.cfg["temp_max"]),2)
            else:
                value1 = self.int_to_bytes(int(round(aux_matrix[self.counter][y],1)*10),2)
                value2 = self.int_to_bytes(int(round(aux_matrix[self.counter][y+1],1)*10),2)
            self.byte_array.append(value1[1]) #LSB1(8b)
            self.byte_array.append((value1[0]&15)<<4 | (value2[0]&15)) #MSB1(4b) & MSB2(4b)
            self.byte_array.append(value2[1]) #LSB2 (8b)
            
        #Add DHT11 measurement and fan state to message
        humidity, temperature = Adafruit_DHT.read_retry(11, dht_pin)
        fan_state = GPIO.input(fan_pin)
        val = fan_state << 7 | int(temperature)
        self.byte_array.append(self.int_to_bytes(val,1)[0])
            
    #Send data to LoRa Gateway
    def send_message(self): 
    
        print("Sending message to gateway!")
    
        self.set_dio_mapping([1,0,0,0,0,0])
        lorawan = LoRaWAN.new(self.nwskey, self.appskey)  
        lorawan.create(MHDR.UNCONF_DATA_UP, {'devaddr': self.devaddr, 'fcnt': self.counter, 'data': self.byte_array })
        self.write_payload(lorawan.to_raw())
        self.set_mode(MODE.TX)  
        
    #Convert int to bytes
    def int_to_bytes(self, value, length):
        result = []
        for i in range(0, length):
          result.append(value >> (i * 8) & 0xff)
        result.reverse()
        return result
        
    #Actuates in fan depending on threshold temperature
    def check_threshold(self):
      if ((self.cfg["temp_max"]/10.0) > self.cfg["threshold"]):
        self.fanON()
      #Turn off fan case temperature is lower than threshold and user did not ask to turn it on
      elif (not(self.cfg["fan"] == "on")):
        self.fanOFF()
 
#Define filename with node parameters
filename = "conf.json"

#DHT11 setup
dht_pin = 4
       
#LoRa setup
BOARD.setup()

#Fan setup
fan_pin = 18
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(fan_pin, GPIO.OUT)

# Camara parameters
MLX_I2C_ADDR = 0x33
hertz = 8

# Camara API
API.SetRefreshRate(MLX_I2C_ADDR, hertz_to_refresh_rate[hertz])
API.SetChessMode(MLX_I2C_ADDR)

# Extract calibration data from EEPROM and store in RAM
eeprom_data = ffi.new("uint16_t[832]")
params = ffi.new("paramsMLX90640*")
API.DumpEE(MLX_I2C_ADDR, eeprom_data)
API.ExtractParameters(eeprom_data, params)

# The default shift for a MLX90640 device in open air
TA_SHIFT = 8 
emissivity = 0.95
frame_buffer = ffi.new("uint16_t[834]")
image_buffer = ffi.new("float[768]")

# TTN Configuration
#deveui = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
#appeui = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
#appkey = [0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
devnonce = [randrange(256), randrange(256)]
node = Node(False)

# LoRa radio module configuration
node.set_mode(MODE.SLEEP)
node.set_dio_mapping([1,0,0,0,0,0])
node.set_freq(868.1)
node.set_pa_config(pa_select=1)
node.set_spreading_factor(7)
node.set_pa_config(max_power=0x0F, output_power=0x0E)
node.set_sync_word(0x34)
node.set_rx_crc(True)
assert(node.get_agc_auto_on() == 1)

# Main program
try:
    print("Sending LoRaWAN join request")
    node.start()
except KeyboardInterrupt:
    node.fanOFF()
    sys.stdout.flush()
    print("\nKeyboardInterrupt")
finally:
    sys.stdout.flush()
    node.set_mode(MODE.SLEEP)
    BOARD.teardown()