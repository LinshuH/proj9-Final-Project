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



###
# Pages
###

@app.route("/")
@app.route("/index")
def index():
  app.logger.debug("Main page entry")
  g.memos = get_memos()
  for memo in g.memos: 
      app.logger.debug("Memo: " + str(memo))
  return flask.render_template('index.html')


# create.html connect to this function and this function put the information into db database

@app.route("/create") #connect to the page
def create():
  app.logger.debug("Create")
  return flask.render_template('create.html')




#function that create the memo
def create_memo(free_time):
	logging.info("---------This is free_time get from flask_main------")
	logging.info(free_time)
	user_free = []
	userid = uuid.uuid4()
	
	for eve in free_time:
		record = { "id":eve['id'], 
	       "weekday":eve['weekday'],
	       "start":eve['start'],
	       "end":eve['end'],
	       "summary":eve['summary']
	      }
		user_free.append(eve)
		
	collection.insert({ 'user': userid,
						'record': user_free })
						

def group_freeTime():
	"""
	Connect with the database first and get all the collection inside,
	then merge each collection by calling merge function in the available time.
	After merge all the free time, use them to replace the current database collection.
	"""
	ini_free = collection.find({},{"record":1})
	
	logging.info("--------This line in database is been reached- ---------------")

	group_users = []
	for eve in ini_free:
		group_users.append(eve["record"])
	logging.info("---------This is group_users---------")
	logging.info(len(group_users))
	logging.info(group_users)
	#group_users is a list of list that contain each user's free time.
	first_user = group_users[0]
	logging.info("-----This is first_user--------")
	logging.info(first_user)
	merge_free_time = []
	for i in range(len(group_users)-1):
		merge_free_time = merge_free(first_user,group_users[i+1])
		logging.info("---------This is first_user---------")
		logging.info(first_user) 
		logging.info("---------This is group_users[i+1]---------")
		logging.info(group_users[i+1]) 
		logging.info("---------This is merge_free_time---------")
		logging.info(merge_free_time) 
		logging.info(len(merge_free_time))
		first_user = merge_free_time
				
	return merge_free_time
	
def merge_free(first_free, second_free):
	"""
	Merge two free events.
	"""
	new_free = []
	for free1 in first_free:
		free1_start = arrow.get(free1['start'])
		free1_end = arrow.get(free1['end'])
		
		temp_start = free1_start
		temp_end = free1_end
		
		for free2 in second_free:
			free2_start = arrow.get(free2['start'])
			free2_end = arrow.get(free2['end'])
			
			#part overlap at begining
			if (free2_start<free1_start<free2_end):
				temp_start = free1_start
				temp_end = free2_end
				
			elif (free2_start>=free1_start and free2_end<=free1_end):
				temp_start = free2_start
				temp_end = free2_end
			elif (free2_start<free1_end<free2_end):
				temp_start = free2_start
				temp_end = free1_end
			elif (free2_start<free1_start and free2_end>free1_end):
				temp_start = free1_start
				temp_end = free1_end
				
		new_free.append(
			{ "summary": "free time",
			  "start": temp_start.isoformat(),
			  "end": temp_end.isoformat(),
			  "weekday": arrow.get(temp_start).format('dddd')
			 })
	return new_free
		
		
			

@app.route("/_delete_memo",methods=["POST"])
def delete_memo():
    delete = flask.request.form["delete"]
    delete2 = delete.split(",")
    date = delete2[0]
    text = delete2[1]
    collection.remove({"text":text},{"date":date})
    return index()


@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    return flask.render_template('page_not_found.html',
                                 badurl=request.base_url,
                                 linkback=url_for("index")), 404

#################
#
# Functions used within the templates
#
#################


@app.template_filter( 'humanize' )
def humanize_arrow_date( date ):
    """
    Date is internal UTC ISO format string.
    Output should be "today", "yesterday", "in 5 days", etc.
    Arrow will try to humanize down to the minute, so we
    need to catch 'today' as a special case. 
    """

    try:
        then = arrow.get(date).replace(tzinfo='local')
        now = arrow.now().replace(tzinfo='local')
        if then.shift(days=-1).date() == now.date():
            human = "Tomorrow"
        elif now.shift(days=-1).date() == then.date():
            human = "Yesterday"
        elif then.date() == now.date():
            human = "Today"
        else:
            human = then.humanize(now)
    except: 
        human = date
    return human


#############
#
# Functions available to the page code above
#
##############
def get_memos():
    """
    Returns all memos in the database, in a form that
    can be inserted directly in the 'session' object.
    """
    records = [ ]
    #collection.find({}).sort({"date":1})
    for record in collection.find( { "type": "dated_memo" } ).sort("date", pymongo.ASCENDING):
        record['date'] = arrow.get(record['date']).isoformat()
        del record['_id']
        records.append(record)
	#return sorted(records, key=date)
    return records 

    
