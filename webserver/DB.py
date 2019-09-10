import pymysql
from collections import OrderedDict
import datetime
import json

filename = "credentials.json"

class DB:
    
    #Inits connection to mysql server
    def __init__(self):
        
        #Database credentials
        db = json.load(open(filename, encoding='utf-8'))["mysql"]
        db_user = db["user"]
        db_password = db["password"]
        db_name = db["name"]
        host = db["host"]
        self.db = pymysql.connect(host, db_user, db_password, db_name)
		
	 #Close mysql connection
    def close(self):
        self.db.close()
        
    #Returns all rows from a cursor as a list of dicts
    def dictFetchAll(self, cursor):
        desc = cursor.description
        return [OrderedDict(zip([col[0] for col in desc], row)) 
            for row in cursor.fetchall()]

	#Database read operation	
    def read_operation(self, query):  
        try:
            cursor = self.db.cursor()
            cursor.execute(query)
            data = {"success": True, "data": self.dictFetchAll(cursor)}
        except Exception as error:
            print(str(error) + " at " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            data = {"success": False}
        finally:
            if 'cursor' in locals():
                cursor.close()            
            return data
        
    #Database write operation
    def write_operation(self, query):
        try:
            cursor = self.db.cursor()
            cursor.execute(query)
            self.db.commit()
            data = {"success": True}
        except Exception as error:
            self.db.rollback()
            print(str(error)+" at "+datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            data = {"success": False}
        finally:
            if 'cursor' in locals():
                cursor.close()            
            return data  
			
	#Get node info
    def get_node_info(self, node_id):
        query = "SELECT * from node where id = '%s'" %(node_id)
        return self.read_operation(query)
		
	#Get node environment temperature
    def get_temp(self, node_id):
        query = "SELECT * from temp_sensor where node_id = '%s'" %(node_id)
        return self.read_operation(query)
		
	#Get last node image
    def get_last_image(self, node_id):
        query = "SELECT * from image where node_id = '%s' order by timestamp desc limit 1" %(node_id)
        return self.read_operation(query)
		
	#Get last node reduced image
    def get_last_red_image(self, node_id):
        query = "SELECT * from red_image where node_id = '%s' order by timestamp desc limit 1" %(node_id)
        return self.read_operation(query)
		
	#Get downlink info
    def get_downlink(self, node_id):
        query = "SELECT * from downlink where node_id = '%s'" %(node_id)
        return self.read_operation(query)
		
	#Set node environment temperature
    def set_temp(self, node_id, timestamp, temp):
        query = "UPDATE temp_sensor set timestamp = '%s', env_temp = %s where node_id = '%s'" %(timestamp, temp, node_id)
        self.write_operation(query)
		
	#Update node fan state
    def set_fan_state(self, node_id, state):
        query = "UPDATE node set fan = '%s' where id = '%s'" %(state, node_id)
        self.write_operation(query) 
		
	#Update node transmission mode
    def set_mode(self, node_id, mode):
        query = "UPDATE node set mode = '%s' where id = '%s'" %(mode, node_id)
        self.write_operation(query) 
		
	#Update node temperature threshold
    def set_threshold(self, node_id, threshold):
        query = "UPDATE node set threshold = %s where id = '%s'" %(threshold, node_id)
        self.write_operation(query) 
		
	#Update max temperature
    def set_max_temp(self, node_id, temp):
        query = "UPDATE node set temp_max = %s where id = '%s'" %(temp, node_id)
        self.write_operation(query) 
		
	#Insert new image
    def set_image(self, node_id, timestamp, path, temp_min, temp_max):
        query = "INSERT into image value('%s', '%s', '%s', %s, %s)" %(node_id, timestamp, path, temp_max, temp_min)
        self.write_operation(query) 
		
	#Insert new reduced image
    def set_image_red(self, node_id, timestamp, path, temp_min, temp_max):
        query = "INSERT into red_image value('%s', '%s', '%s', %s, %s)" %(node_id, timestamp, path, temp_max, temp_min)
        self.write_operation(query) 
		
	#Set new downlink request
    def set_request(self, node_id, fan, mode, threshold):
        query = "UPDATE downlink set flag = true, fan = '%s', mode = '%s', threshold = %s where node_id = '%s'" %(fan, mode, threshold, node_id)
        self.write_operation(query) 
		
	#Update request status
    def request_done(self, node_id, counter):
        query = "UPDATE downlink set flag = false, counter = %s where node_id = '%s'" %(counter, node_id)
        self.write_operation(query) 
		
	#Set counter to 0
    def reset_downlink(self, node_id):
        query = "UPDATE downlink set counter = 0 where node_id = '%s'" %(node_id)
        self.write_operation(query) 