"""
Flask web app connects to Mongo database.
Keep a simple list of dated memoranda.

Representation conventions for dates: 
   - We use Arrow objects when we want to manipulate dates, but for all
     storage in database, in session or g objects, or anything else that
     needs a text representation, we use ISO date strings.  These sort in the
     order as arrow date objects, and they are easy to convert to and from
     arrow date objects.  (For display on screen, we use the 'humanize' filter
     below.) A time zone offset will 
   - User input/output is in local (to the server) time.  
"""

import flask
from flask import g
from flask import render_template
from flask import request
from flask import url_for

import json
import logging

import sys
import uuid

# Date handling 
import arrow   
from dateutil import tz  # For interpreting local times

# Mongo database
import pymongo
from pymongo import MongoClient

import available_time


import config
CONFIG = config.configuration()


MONGO_CLIENT_URL = "mongodb://{}:{}@{}:{}/{}".format(
    CONFIG.DB_USER,
    CONFIG.DB_USER_PW,
    CONFIG.DB_HOST, 
    CONFIG.DB_PORT, 
    CONFIG.DB)


print("Using URL '{}'".format(MONGO_CLIENT_URL))


###
# Globals
###

app = flask.Flask(__name__)
app.secret_key = CONFIG.SECRET_KEY
app.logger.setLevel(logging.INFO) 

####
# Database connection per server process
###

try: 
    dbclient = MongoClient(MONGO_CLIENT_URL)
    app.logger.info(MONGO_CLIENT_URL)
    db = getattr(dbclient, CONFIG.DB)
    collection = db.meeting

except:
    print("Failure opening database.  Is Mongo running? Correct password?")
    sys.exit(1)


#function that create the memo
def create_memo(events):
	"""
	This function get a group of free time, store the free time for each user individually and assign each user an unique id.
	Meanwhile, under the else statement, program check whether the database already contain the same record, if yes, them not add the extra information.
	"""
	#logging.info("---------This is free_time get from flask_main------")
	#logging.info(events)
	

	# get free time in database
	temp_database_free = collection.find()
	database_free = []
	for free in temp_database_free:
		database_free.append(free)
	logging.info("-----------database_freetime in database.memo-----")
	logging.info(database_free)
	logging.info ("-----length of database_free")
	logging.info (len(database_free))
	
	if len(database_free) == 0:
		userid = uuid.uuid4()
		collection.insert({ 'user': userid, 'record': events })
	else:
		database_records = []
		for free in database_free:
			database_records.append(free['record'])
		if events not in database_records:
			userid = uuid.uuid4()
			collection.insert({ 'user': userid, 'record': events })
			
	
	

def group_freeTime():
	"""
	Connect with the database first and get all the collection inside,
	then merge each collection by calling merge function in the available time.
	After merge all the free time, use them to replace the current database collection.
	Since the database_Free is sorted by the start time, for the case that second free time is larger than the first free time, this time the case is handleing by the second case when it is doing the calculation.
	"""
	# get free time in database
	temp_database_free = collection.find()
	database_free = []
	for free in temp_database_free:
		#del free['_id']
		database_free.append(free)
	database_free.sort(key=lambda e: e['start'])
	logging.info("-------database_free in database.py---------")
	logging.info(database_free)
	
	# start to find the overlap time
	overlap_free = []
	for free1 in database_free:
		free1_start = arrow.get(free1['start'])
		free1_end = arrow.get(free1['end'])
		
		#temp_start = free1_start
		#temp_end = free1_end
		
		for free2 in database_free:
			free2_start = arrow.get(free2['start'])
			free2_end = arrow.get(free2['end'])
			
			if (free2_start <= free1_start < free2_end):
				temp_start = free1_start
				if (free2_end <= free1_end):
					temp_end = free2_end
				else:
					temp_end = free1_end
					
				overlap_free.append(
						{ "summary": "free time",
							"start": temp_start.isoformat(),
							"end": temp_end.isoformat(),
							"weekday": arrow.get(free2_start).format('dddd')
						})
						
			elif (free1_start < free2_start < free1_end):
				temp_start = free2_start
				if (free2_end <= free1_end):
					temp_end = free2_end
				else:
					temp_end = free1_end
					
				overlap_free.append(
						{ "summary": "free time",
							"start": temp_start.isoformat(),
							"end": temp_end.isoformat(),
							"weekday": arrow.get(free2_start).format('dddd')
						})	
			
			# remove the repeated overlap time
			new_overlap_free = []
			for eve in overlap_free:
				if eve not in new_overlap_free:
					new_overlap_free.append(eve)
			"""
			#if (free1_start <= free2_start < free1_end):
				#if (free1_start == free2_start and free1_end
				#the free2 is totally overlap with(inside) free1
			if (free1_start < free2_start and free1_end >= free2_end):
				temp_start = free2_start
				temp_end = free2_end
				
			# second free is start later but also end later than first free.	
			elif (free1_start < free2_start and free1_end < free2_end):
				temp_start = free2_start
				temp_end = free1_end
				
			elif (free1_start >= free2_start and free1_end >= free2_end):
				temp_start = free1_start
				temp_end = free2_end
					
			elif (free1_start >= free2_start and free1_end < free2_end):
				temp_start = free1_start
				temp_end = free1_end
				

			# avoid the repetetion.	
			for eve in overlap_free:
				if (eve["start"] != temp_start and eve["end"] != temp_end):
					overlap_free.append(
						{ "summary": "free time",
							"start": temp_start.isoformat(),
							"end": temp_end.isoformat(),
							"weekday": arrow.get(free2_start).format('dddd')
						})
			
			overlap_free.append(
						{ "summary": "free time",
							"start": temp_start.isoformat(),
							"end": temp_end.isoformat(),
							"weekday": arrow.get(free2_start).format('dddd')
						})
			"""
	logging.info("-------new_overlap_free in database.py---------")
	logging.info(new_overlap_free)
	
	return new_overlap_free
