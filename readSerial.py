# Helping Doorknob
# ECE-4320 Architectural Robotics
# John Walter & Evonne Weeden

# Non-standard Library Requirements:
#	Pyserial
#	Matplotlib
#	Numpy
# 	MySQL Connector

import serial
import datetime
import serial
import serial.tools.list_ports
import mysql.connector
import _thread as thread
import matplotlib.pyplot as plt
import time
import numpy as np

quit = 0				# set to 1 to end the main while loop of the program and exit
close_thread = 0		# set to 1 to close the readSerial thread
serial_connected = 0	# status of serial connection: 1 = connected, 0 = disconnected
samples=[]
maxforces=[]
thresholds=[]
datetimes=[]
first=1

# connect to project3 database on MySQL server
db = mysql.connector.connect(
 	host="127.0.0.1",
 	user="root",
	passwd="",
 	database="project3"
)
# establish cursor for database
mc = db.cursor()

# This function searches for a connected Arduino on the COM ports
# and returns the COM port if one is found, otherwise returns -1.
# Reduces the need to manually enter the COM port.
def findArduinoCOM():
	ports = []
	for p in list(serial.tools.list_ports.comports()):
		if("Arduino" in tuple(p)[1]):
			print("[#] Found Arduino on: "+tuple(p)[0])
			return tuple(p)[0]
	print("[!] Did not find a connected Arduino")
	return -1;

# This function basically clears the table in the database that stores
# all of the data by deleting it and then recreating it.
def purgeTableInDatabase(tablename):
	global close_thread
	# if connected to Arduino over serial, close connection to avoid errors
	if(serial_connected):
		print("[#] Stopping serial connection")
		# tell thread to close
		close_thread = 1;
	try:
		mc.execute("drop table "+tablename)
		print('[#] Dropped table '+tablename)
		mc.execute("create table "+tablename+"(sample int auto_increment primary key, maxforce int, threshold int, dt DateTime)")
		print("[#] Created new table "+tablename)
		db.commit()
	except Exception as e:
		print("[!] Error occurred: "+str(e))

# This function connects to the Arduino via a serial connection and begins reading data from it.
# This function is created within a new thread to allow it to run in the background.
def readSerial():
	global close_thread, serial_connected
	# get Arduino's COM port
	com = findArduinoCOM()
	if(com == -1):
		print("[!] Error connecting to serial")
		exit(0)
	# connect to serial
	try:
		serialRead = serial.Serial(com,9600)
		print("[#] Connected to Arduino on: "+com)
		# if connection successful, set status to 1
		serial_connected = 1
	except Exception as e:
		print("[!] Error setting up serial connection on: "+com)
		#print(str(e))
		exit(0) # this closes the thread
	# while close_thread = 0, read from Arduino
	while(not close_thread):
		# wait for data on serial bus
		if serialRead.inWaiting()!=0 :
			# read packet, decode, and strip extraneous characters
			packet = serialRead.readline().decode("utf-8").strip()
			# split packet at commas l[0]=threshold and l[1]=maxforce
			l = packet.split(',')
			print(">\t\t\t\t\t\t\tReceived: "+str(l))
			# get current time
			now=datetime.datetime.now()
			# insert new data into database
			try:
				command = "insert into Forces(sample,maxforce,threshold,dt) values(NULL,%s,%s,%s)"
				values = (int(l[1]), int(l[0]),now)
				mc.execute(command,values)
				db.commit()
			except Exception as e:
				print(">\t\t\t\t\t\t\tError writting to database")
				print(str(e))
	# when the thread is told to terminate (close_thread = 1) must reset the status indicators
	close_thread = 0
	serial_connected = 0

# This function fetches new data from the database into samples, maxforces, thresholds, and datetimes
def getFromDatabase():
	global first
	global samples
	global maxforces
	global thresholds
	global datetimes
	snew=[]
	mnew=[]
	tnew=[]
	tdnew=[]
	# query database
	mc.execute("select sample from Forces")
	dsamples = mc.fetchall()
	mc.execute("select maxforce from Forces")
	dmaxforces = mc.fetchall()
	mc.execute("select threshold from Forces")
	dthresholds = mc.fetchall()
	mc.execute("select dt from Forces")
	ddatetimes = mc.fetchall()
	# for every tuple in new query, put values into arrays
	for x in range(0,len(dsamples)):
		snew.append(dsamples[x][0])
		mnew.append(dmaxforces[x][0])
		tnew.append(dthresholds[x][0])
		tdnew.append(ddatetimes[x][0])
	# if this is the first query of the database, all of the read values are used
	if(first):
		samples = snew
		maxforces = mnew
		thresholds = tnew
		datetimes = tdnew
		first=0
	# if this is not the first query, then just append new values into the arrays
	else:
		for x in range(len(samples), len(snew)):
			samples.append(snew[x])
			maxforces.append(mnew[x])
			thresholds.append(tnew[x])
			datetimes.append(tdnew[x])
	db.commit()

# Start of main program
# Prompt the user if they want to begin reading values from Arduino
c = int(input("Begin collecting data from device?\n\t(1) Yes\n\t(2) No\n> "))
# if yes, create thread for the readSerial function
if(c == 1):
	thread.start_new_thread(readSerial,())
	time.sleep(1.5)
	# verify that thread created and serial connection established
	if(not serial_connected):
		exit(0)
# while not told to quit
while(not quit):
	# get new database values
	getFromDatabase()
	# user prompt for what to do
	c = int(input("Select:\n\t(1) Display Table\n\t(2) Graph All\n\t(3) Graph Subset\n\t(4) Real-time Graph (10s)\n\t(5) Purge Database\n\t(6) Connect to serial\n\t(7) Disconnect from serial\n\t(0) Quit\n>\n"))
	# if Quit
	if(c == 0):
		# exit main loop
		quit = 1
		# close readSerial thread
		close_thread = 1
	# if Graph All
	elif(c == 2):
		# update values
		getFromDatabase()
		# verify arrays are not empty
		if(len(samples)>0):
			# create a regression line for the maxforces
			fit = np.polyfit(samples,maxforces,1)
			fit_fn = np.poly1d(fit)
			# graph max forces
			plt.plot(samples,maxforces,label="Max Force")
			# graph thresholds
			plt.plot(samples,thresholds,label="Threshold")
			# graph regression line
			plt.plot(samples,fit_fn(samples),'--k',label="Regression")
			# configure plot
			plt.legend(loc="upper left")
			plt.title("Doorknob Data")
			plt.ylabel("Max Force (lbs)")
			plt.xlabel("Sample")
			# show plot
			plt.show()
		else:
			print("[!] Table is empty")
	# if Graph Subset
	elif(c == 3):
		# ask for min and max values (the sample values)
		mini = int(input("Enter min: "))
		maxi = int(input("Enter max: "))
		# graph the subarray of the maxforces
		plt.plot(samples[mini-1:maxi],maxforces[mini-1:maxi])
		# graph the subarray of the thresholds
		plt.plot(samples[mini-1:maxi], thresholds[mini-1:maxi])
		# show plot
		plt.show()
	# if Real-time Graph
	elif(c == 4):
		# if not connected to Arduino, connect to allow for real-time
		if(not serial_connected):
			print("[!] Serial connection not open. Connecting...")
			thread.start_new_thread(readSerial,())
			time.sleep(0.5)
		# verify connected to serial
		if(serial_connected):
			while(1):
				# update values
				getFromDatabase()
				# verify arrays not empty
				if(len(samples) >0):
					# create a regression line for the maxforces
					fit = np.polyfit(samples,maxforces,1)
					fit_fn = np.poly1d(fit)
					# graph max forces
					plt.plot(samples,maxforces,label="Max Force")
					# graph thresholds
					plt.plot(samples,thresholds,label="Threshold")
					# graph regression line
					plt.plot(samples,fit_fn(samples),'--k',label="Regression")
					# configure plot
					plt.legend(loc="upper left")
					plt.title("Doorknob Data")
					plt.ylabel("Max Force (lbs)")
					plt.xlabel("Sample")
					# show plot
					plt.show()
					# this try catch is used to catch the closing of the graph window to stop realtime display and go back to main menu
					try:
						# refresh every 5 seconds
						plt.pause(5)
						# clear current plot for new one
						plt.clf()
					except Exception as e:
						if("application has been destroyed" in str(e)):
							# stop realtime display
							break;
				else:
					print("[!] Table is empty")
					break;
	# if Purge Database
	elif(c == 5):
		# call function to drop table and recreate it
		purgeTableInDatabase("Forces")
		# reset to first query
		first = 1;
		# clear arrays
		samples.clear()
		maxforces.clear()
		thresholds.clear()
		datetimes.clear()
	# if Show Table
	elif(c == 1):
		# update values
		getFromDatabase()
		print("###")
		print("Sample\tMax Force\tThreshold\tDate Time")
		# show each tuple from table
		for i in range(0,len(samples)):
			print(str(samples[i])+"\t"+str(maxforces[i])+"\t\t"+str(thresholds[i])+"\t\t"+str(datetimes[i]))
		print("###")
	# if Connect to serial
	elif(c == 6):
		# if not already connected
		if(not serial_connected):
			# create new thread for readSerial function
			thread.start_new_thread(readSerial,())
			time.sleep(0.5)
		else:
			print("[#] Already connected to serial")
	# if Disconnect from serial
	elif(c == 7):
		# if connected
		if(serial_connected):
			# tell thread to close
			close_thread = 1
			print("[#] Closed serial connection")
		else:
			print("[#] Serial not connected")




			

