#Import native libraries
import json
import sys
from datetime import datetime
import base64
import os
from math import floor
import threading
from time import sleep
import requests

#Import user installed libraries
from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO
import ttn
from PIL import Image
import matplotlib.pyplot as plt
import matplotlib as mpl
from DB import DB

#User defined
filename = "conf.json"
images_folder = "images/"

#Flask object
app = Flask(__name__)
socketio = SocketIO(app)
	
#Image variables
bytes_matrix = []
img = Image.new( 'RGB', (24,32), "black")
img_red = Image.new( 'RGB', (6,8), "black")
flag_fan = True
flag_mode = True

#------------------- General Purpose Functions-----------------

#Convert int to bytes
def int_to_bytes(value, length):
	result = []
	for i in range(0, length):
		result.append(value >> (i * 8) & 0xff)
	result.reverse()
	return result

#Inits image space
def init_plt():
	plt.imshow(img)
	create_image("trash.png", 0, 50)
	print("done initializing image")

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

#Decode message image data
def decode_bytes(x, y):

	#Extract most and least significant bytes
	MSB1 = bytes_matrix[x][y+1]>>4
	MSB2 = bytes_matrix[x][y+1]&15
	LSB1 = bytes_matrix[x][y]
	LSB2 = bytes_matrix[x][y+2]
	
	#Check if numbers are negative
	if (MSB1>>2 == 3):
	  MSB1 |= 240
	if (MSB2>>2 == 3):
	  MSB2 |= 240
	
	#Compose byte arrays
	val1_a = []
	val1_a.append(MSB1)
	val1_a.append(LSB1)
	val2_a = []
	val2_a.append(MSB2)
	val2_a.append(LSB2)
	
	#Convert byte arrays to temperature values
	val1 = int.from_bytes(val1_a, byteorder='big', signed=True)/10.0
	val2 = int.from_bytes(val2_a, byteorder='big', signed=True)/10.0
	return [val1, val2]
  
#Creates .png file
def create_image(img_filename, T_min, T_max):
	norm = mpl.colors.Normalize(vmin=T_min, vmax=T_max)
	cmap = mpl.cm.ScalarMappable(norm=norm, cmap=mpl.cm.jet)
	cmap.set_array([])
	cb = plt.colorbar(cmap)
	cb.set_label("Temperature (Celsius)")
	plt.axis('off')
	plt.savefig(images_folder + img_filename, bbox_inches='tight')
	plt.clf()  
 
#Checks if node has sent data on last minute
def check_node():
	last_seen_epoch = int(handler.application().device(node_id).lorawan_device.last_seen/1000000000)
	last_seen_date = datetime.fromtimestamp(last_seen_epoch)
	current_date = datetime.now()
	return ((current_date - last_seen_date).seconds <= 30)
 
# ---------------------- TTN Integration ---------------------

def uplink_callback(msg, client):

	try:
	
		#Get bytes array
		global bytes_matrix, flag_fan, flag_mode
		bytes_array = list(base64.b64decode(msg.payload_raw))
		print(msg.counter)
		
		#Check if this was reset message
		if (len(bytes_array) == 1):
			
			#Reset downlink counter
			downlink["counter"] = handler.application().device(node_id).lorawan_device.f_cnt_down
			obj_DB.reset_downlink(node_id)
			bytes_matrix = []
			
		#Check if downlink request was pending
		if (downlink["flag"]):
		
			#Read node downstream counter from TTN
			cnt = handler.application().device(node_id).lorawan_device.f_cnt_down
			
			#Check if downlink was handled
			if (downlink["counter"] == cnt):
				print("Downlink failed!")
				json_data = json.dumps({"msg": "Downlink failed!"}, ensure_ascii=False)
				requests.post("http://127.0.0.1:3002/downlink", data = json_data)
			else:
				print("Downlink done!")
				json_data = json.dumps({"msg": "Downlink done!"}, ensure_ascii=False)
				requests.post("http://127.0.0.1:3002/downlink", data = json_data)
				
			#Check if transmission mode changed
			if (downlink["mode"] != node["mode"]):
				print("Changed transmission mode!")
				flag_mode = False
				node["mode"] = downlink["mode"]			
				obj_DB.set_mode(node_id, node["mode"])
				json_data = json.dumps({"mode": node["mode"]}, ensure_ascii=False)
				requests.post("http://127.0.0.1:3002/mode", data = json_data)
				#Update image
				if (node["mode"] == "fast"):
					image = obj_DB.get_last_red_image(node_id)
				else:   
					image = obj_DB.get_last_image(node_id)
				if (image["success"] and image["data"]):
					image = image["data"][0]
					json_data = json.dumps({"timestamp": image["timestamp"].strftime('%Y-%m-%d %H:%M:%S'), "temp_max" : int(image["temp_max"]*10), "temp_min" : int(image["temp_min"]*10), "img_filename" : image["path"]}, ensure_ascii=False)
					requests.post("http://127.0.0.1:3002/image", data = json_data)
				
			#Check if threshold changed
			if (downlink["threshold"] != node["threshold"]):
				print("Changed temperature threshold!")
				node["threshold"] = downlink["threshold"]
				if(node["temp_max"] > node["threshold"]):
					node["fan"] = "on"
					json_data = json.dumps({"fan": node["fan"]}, ensure_ascii=False)
					requests.post("http://127.0.0.1:3002/fan", data = json_data)
					flag_fan = False
				obj_DB.set_threshold(node_id, node["threshold"])
				json_data = json.dumps({"threshold": node["threshold"]}, ensure_ascii=False)
				requests.post("http://127.0.0.1:3002/threshold", data = json_data)

			#Check if fan state changed
			if (downlink["fan"] != node["fan"] and node["temp_max"] < node["threshold"]):
				node["fan"] = downlink["fan"]
				obj_DB.set_fan_state(node_id, node["fan"])
				json_data = json.dumps({"fan": node["fan"]}, ensure_ascii=False)
				requests.post("http://127.0.0.1:3002/fan", data = json_data)
				flag_fan = False
				print("Changed fan state!")

			#Update downlink status
			downlink["flag"] = False
			downlink["counter"] = cnt
			obj_DB.request_done(node_id, downlink["counter"])

		#Check if it was a data message
		if (len(bytes_array) != 1):
		
			#Remove environment temperature from array
			val = bytes_array[len(bytes_array)-1]
			del bytes_array[-1]
			
			#Update reading from temperature sensor
			temp = val & 127
			timestamp = datetime.now()
			obj_DB.set_temp(node_id, timestamp.strftime('%Y-%m-%d %H:%M:%S'), temp)
			json_data = json.dumps({"timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S'), "temp": temp}, ensure_ascii=False)
			requests.post("http://127.0.0.1:3002/env_temp", data = json_data)
			
			#Check fan state
			if (flag_fan):
				fan = val >> 7
				if (fan == 0 and node["fan"] == "on"):
					node["fan"] = "off"
					obj_DB.set_fan_state(node_id, "off")
					json_data = json.dumps({"fan": node["fan"]}, ensure_ascii=False)
					requests.post("http://127.0.0.1:3002/fan", data = json_data)	
					print("From val: " + node["fan"])
				
				elif (fan == 1 and node["fan"] == "off"):
					node["fan"] = "on"
					obj_DB.set_fan_state(node_id, "on")
					json_data = json.dumps({"fan": node["fan"]}, ensure_ascii=False)
					requests.post("http://127.0.0.1:3002/fan", data = json_data)
					print("From val: " + node["fan"])	
			else:
				flag_fan = True
				
			#Check if message from current image being formed
			if (len(bytes_matrix) == msg.counter and flag_mode):
				
				#Add pixels to image
				bytes_matrix.append(bytes_array)

				#Check if fast mode image is done
				if (len(bytes_matrix) == 2 and msg.counter == 1 and node["mode"] == "fast"):
						
					#Read max and min temperatures
					temp_array = decode_bytes(1, len(bytes_matrix[1])-3)
				
					#Create fast mode image
					itr = 0;
					for x in range(2):
						for y in range(0, 36, 3):
							pixel_array = decode_bytes(x, y)
							img_red.putpixel((x*3 + floor(y/12), itr), temp_to_col(pixel_array[0], temp_array[0],  temp_array[1]))
							img_red.putpixel((x*3 + floor(y/12), itr+1), temp_to_col(pixel_array[1], temp_array[0],  temp_array[1]))
							if (itr == 6):
								itr = 0
							else:
								itr += 2
							
					#Create image file
					img_filename = str(int(timestamp.timestamp())) + ".png"
					plt.imshow(img_red.resize((480,640), Image.BICUBIC))
					create_image(img_filename, temp_array[0],  temp_array[1])
					bytes_matrix = []
					obj_DB.set_image_red(node_id, timestamp.strftime('%Y-%m-%d %H:%M:%S'), img_filename, temp_array[0],  temp_array[1])
					obj_DB.set_max_temp(node_id, temp_array[1])
					json_data = json.dumps({"timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S'), "temp_max" : int(temp_array[1]*10), "temp_min" : int(temp_array[0]*10), "img_filename" : img_filename}, ensure_ascii=False)
					requests.post("http://127.0.0.1:3002/image", data = json_data)
					
				#Check if slow mode image is done
				elif (len(bytes_matrix) == 24 and msg.counter == 23 and node["mode"] == "slow"):
				
					#Read max and min temperatures
					temp_array = decode_bytes(23, len(bytes_matrix[23])-3)
				
					#Create slow mode image
					f = open("test.txt", "w")
					f.seek(0)
					for x in range(24):
						for y in range(0, 48, 3):
							pixel_array = decode_bytes(x, y)
							img.putpixel((x, floor(y/3)*2), temp_to_col(pixel_array[0], temp_array[0],  temp_array[1]))
							img.putpixel((x, floor(y/3)*2+1), temp_to_col(pixel_array[1], temp_array[0],  temp_array[1]))
							f.write(str(pixel_array[0]) + " " + str(pixel_array[1]) + " ")
						f.write("\n")
					f.write(str(temp_array[0]) + " " + str(temp_array[1]) + " ")
					f.close()  
					
					#Create image file
					img_filename = str(int(timestamp.timestamp())) + ".png"
					plt.imshow(img.resize((480,640), Image.BICUBIC))
					create_image(img_filename, temp_array[0],  temp_array[1])
					bytes_matrix = []
					obj_DB.set_image(node_id, timestamp.strftime('%Y-%m-%d %H:%M:%S'), img_filename, temp_array[0],  temp_array[1])
					obj_DB.set_max_temp(node_id, temp_array[1])
					json_data = json.dumps({"timestamp": timestamp.strftime('%Y-%m-%d %H:%M:%S'), "temp_max" : int(temp_array[1]*10), "temp_min" : int(temp_array[0]*10), "img_filename" : img_filename}, ensure_ascii=False)
					requests.post("http://127.0.0.1:3002/image", data = json_data)
					print("Sent new image message!")

			else:
					
				#Reset image data
				print("Dicarding frame")
				bytes_matrix = []
				flag_mode = True
	
	except Exception as e:
		print(e)
  
def connect_callback(res, client):
	if(res):
		print("Connection successful!")
	else:
		print("Connection unsuccessful!")
		sys.exit(0)
		
def close_callback(res, client):
	print("Connection closed!")
	  
# ----------------------- SocketIO API ------------------------

@socketio.on('new_client')
def connect():

	#Send fan state
	json_data = json.dumps({"fan": node["fan"]}, ensure_ascii=False)
	socketio.emit("fan", json_data)		
	
	#Send transmission mode
	json_data = json.dumps({"mode": node["mode"]}, ensure_ascii=False)
	socketio.emit("mode", json_data)
	
	#Send temperature threshold
	json_data = json.dumps({"threshold": node["threshold"]}, ensure_ascii=False)
	socketio.emit("threshold", json_data)
	
	#Send sensor values if existing
	env_temp = obj_DB.get_temp(node_id)
	if (env_temp["success"]):
		env_temp = env_temp["data"][0]
		if(env_temp["timestamp"] and env_temp["env_temp"]):
			json_data = json.dumps({"timestamp": env_temp["timestamp"].strftime('%Y-%m-%d %H:%M:%S'), "temp": env_temp["env_temp"]}, ensure_ascii=False)
			socketio.emit("env_temp", json_data)
	
	#Send last image if existing
	if (node["mode"] == "fast"):
		image = obj_DB.get_last_red_image(node_id)
	else:   
		image = obj_DB.get_last_image(node_id)
	if (image["success"] and image["data"]):
		image = image["data"][0]
		with open(images_folder + image["path"], 'rb') as f:
			image_data = f.read()
		json_data = json.dumps({"timestamp": image["timestamp"].strftime('%Y-%m-%d %H:%M:%S'), "temp_max" : int(image["temp_max"]*10), "temp_min" : int(image["temp_min"]*10)}, ensure_ascii=False)
		socketio.emit("camara", json_data)
		socketio.emit("image", image_data)
		
# ----------------------- REST API ----------------------------

#Main page
@app.route('/')
def index():
    return render_template("mainPage.html") 
	
#Route for sending downlink alert
@app.route('/downlink', methods=['POST'])
def downlink_route():
	json_data = json.loads(request.data.decode('utf-8'))
	socketio.emit("downlink", json.dumps(json_data))
	return ""
	
#Route for updating fan state
@app.route('/fan', methods=['POST'])
def fan():
	json_data = json.loads(request.data.decode('utf-8'))
	socketio.emit("fan", json.dumps(json_data))
	return ""
	
#Route for updating transmission mode
@app.route('/mode', methods=['POST'])
def mode():
	json_data = json.loads(request.data.decode('utf-8'))
	socketio.emit("mode", json.dumps(json_data))
	return ""
	
#Route for updating temperature threshold
@app.route('/threshold', methods=['POST'])
def threshold():
	json_data = json.loads(request.data.decode('utf-8'))
	socketio.emit("threshold", json.dumps(json_data))
	return ""
	
#Route for updating image
@app.route('/image', methods=['POST'])
def image():
	json_data = json.loads(request.data.decode('utf-8'))
	with open(images_folder + json_data["img_filename"], 'rb') as f:
		image_data = f.read()
	socketio.emit("camara", json.dumps(json_data))
	socketio.emit("image", image_data)
	return ""
	
#Route for updating environmental temperature
@app.route('/env_temp', methods=['POST'])
def env_temp():
	json_data = json.loads(request.data.decode('utf-8'))
	socketio.emit("env_temp", json.dumps(json_data))
	return ""
 
#Route for sending downstream message
@app.route('/request', methods=['GET', 'POST'])
def downlink_request():

	#Get parameters
	json_data = json.loads(request.data.decode('utf-8'))
	if ("data" in json_data):
		json_data = json.loads(json_data["data"])

	#Check if another request is being handled
	if (downlink["flag"]):
		resp = {"success" : False, "msg" : "Another request is currently being handled"}
	
	#If node is online, send downlink request to node
	elif (check_node()):
		
		#Update downlink object
		downlink["flag"] = True
		downlink["fan"] = json_data["fan"]
		downlink["mode"] = json_data["mode"]
		downlink["threshold"] = int(json_data["threshold"])
		downlink["counter"] = handler.application().device(node_id).lorawan_device.f_cnt_down
		
		#Encode message
		if (json_data["fan"] == "off"):
			fan_value = 0
		else:
			fan_value = 2
		if (json_data["mode"] == "slow"):
			mode_value = 0
		else:
			mode_value = 1
		aux = int_to_bytes(int(json_data["threshold"]), 2)
		byte_max = 12 + fan_value + mode_value
		LSB = aux[1]
		MSB = aux[0] & 15
		data = [byte_max << 4 | MSB, LSB]
		
		#Send downstream message
		base64EncodedStr = base64.b64encode(bytes(data)).decode("utf-8")
		mqtt_client.send(dev_id = node_id, pay = base64EncodedStr, port = 1, conf = False, sched = "replace")
		obj_DB.set_request(node_id, json_data["fan"], json_data["mode"], json_data["threshold"])
		resp = {"success" : True}
		
	else:
		resp = {"success" : False, "msg" : "Node is offline (not sending data for 1 minute)"}
	return jsonify(resp)

# ----------------------- Program ----------------------------

#Init image space (for some reason, takes some time in server, so it is implemented in a thread)
threading.Thread(target=init_plt).start()

#Read configuration file
if(not os.path.isfile(filename)):
	print("Missing .json configuration file!")
	sys.exit(0)
else:
	cfg = json.load(open(filename))
	app_id = cfg["app_id"]
	access_key = cfg["access_key"]
	node_id = cfg["node_id"]
		
#Read node parameters from DB
obj_DB = DB()
node = obj_DB.get_node_info(node_id)
downlink = obj_DB.get_downlink(node_id)
if (node["success"] and downlink["success"]):
	node = node["data"][0]
	downlink = downlink["data"][0]
else:
	print("Problem reading from DB!")
	sys.exit(0)

#Thread for running flask server	
def run_server():
	socketio.run(app, debug=True, use_reloader=False, host = "0.0.0.0", port = 3002)

#Run flask server
try:
	print("Starting web server")
	thread = threading.Thread(target=run_server)
	thread.setDaemon(True)
	thread.start()
	
	#Prepare TTN MQTT client
	handler = ttn.HandlerClient(app_id, access_key)
	mqtt_client = handler.data()
	mqtt_client.set_uplink_callback(uplink_callback)
	mqtt_client.set_connect_callback(connect_callback)
	mqtt_client.set_close_callback(close_callback)
	mqtt_client.connect()
	
	while(True):
		sleep(10)

except KeyboardInterrupt:
    sys.stdout.flush()
    print("\nKeyboardInterrupt")

finally:
	obj_DB.close()
	if 'mqtt_client' in locals():
		mqtt_client.close()
	sys.stdout.flush()
	exit(0)