import flask
from flask import render_template
from flask import request
from flask import url_for
import uuid

import json
import logging

# Date handling 
import arrow # Replacement for datetime, based on moment.js
# import datetime # But we still need time
from dateutil import tz  # For interpreting local times


# OAuth2  - Google library implementation for convenience
from oauth2client import client
import httplib2   # used in oauth2 flow

# Google API for services 
from apiclient import discovery

# Connect with available_time.py
import available_time
import database

###
# Globals
###
import config
if __name__ == "__main__":
    CONFIG = config.configuration()
else:
    CONFIG = config.configuration(proxied=True)

app = flask.Flask(__name__)
app.debug=CONFIG.DEBUG
app.logger.setLevel(logging.INFO) ##Used to be .DEBUG
app.secret_key=CONFIG.SECRET_KEY

SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = CONFIG.GOOGLE_KEY_FILE  ## You'll need this
APPLICATION_NAME = 'MeetMe class project'

#if if __name__ == #not main(from heroku)

#############################
#
#  Pages (routed from URLs)
#
#############################

#Note:
# global variable is only valid in this py file, flask.session[variable] is valid through the whole program.
# to use the global variable, directly call it. To use the flask.session variable, everytime need variable = flask.session[variable]

@app.route("/")
@app.route("/index")
def index():
  app.logger.debug("Entering index")
  if 'begin_date' not in flask.session:
    init_session_values()
  return render_template('index.html')

@app.route("/choose")
def choose():
    ## We'll need authorization to list calendars 
    ## I wanted to put what follows into a function, but had
    ## to pull it back here because the redirect has to be a
    ## 'return' 

    app.logger.debug("Checking credentials for Google calendar access")
    credentials = valid_credentials()
    if not credentials:
      app.logger.debug("Redirecting to authorization")
      return flask.redirect(flask.url_for('oauth2callback'))
    
    # Get the external link
    flask.g.link_external = flask.url_for("index", _external=True)
    # Step 1 Select calendar
    gcal_service = get_gcal_service(credentials)
    app.logger.debug("Returned from get_gcal_service")
    #This is the things that I return to the html

    logging.info("---------This is g.calendars:")
    flask.g.calendars = list_calendars(gcal_service)
    logging.info(flask.g.calendars)
    
    logging.info("------------#####This is flask.session-------")
    logging.info(flask.session)

    # Step 2
    # Based on the selected calendar, date and time to filt the events
    if ('cal_ids' in flask.session):
    	cal_ids = flask.session['cal_ids']
    	logging.info("------------Choose Get cal_ids: ---------")
    	logging.info(cal_ids)
    	events = []  # events is an array that contains the event.
    	temp = []
    	for cal_id in cal_ids:
    		temp = list_events(gcal_service,cal_id)
    		events += temp
    		temp = []
    	#sort the events based on th/choosee start time.
    	events.sort(key=lambda e: e['start'])
    	
    	
    	#The event is finish the calendar filt at here
			#The event been selected by the date and time:
			#Get the date and time
    	begin_datetime = flask.session['begin_datetime']
    	end_datetime = flask.session['end_datetime']
    	
    	#Function to do the filter:
    	filtered_event = date_time_filter(events,begin_datetime,end_datetime)
    	flask.session['filtered_event'] = filtered_event
    	
    	flask.g.events = filtered_event
    	logging.info("--------------This is the g.events")
    	logging.info(flask.g.events)

    	#Section that transfer the busy time to free time by user selection
    	#busy_to_free is a flask session array created by the function to_free()
    if ("busy_to_free" in flask.session):
    	busy_to_free = flask.session['busy_to_free']
    	cal_ids = flask.session['cal_ids']
    	cal_busy_to_free = []
		
		#update the busy_to_free when select the new calendar
    	for eve in busy_to_free:
    		if (eve['calendarId'] in cal_ids and eve not in cal_busy_to_free):
    			cal_busy_to_free.append(eve)
    	flask.session['busy_to_free'] = cal_busy_to_free
    	flask.g.tofree = cal_busy_to_free
    
    if ('filtered_event' and 'busy_to_free' in flask.session):
    	#connect to the available_time.py
    	whole_events = available_time.combine_busy_free()
    	logging.info("-----------####This is the whole summary#####")
    	logging.info("-------------1, This is busy events-------")
    	logging.info(flask.session['filtered_event'])
    	logging.info("-------------2, This is 'busy_to_free'------")
    	logging.info(flask.session['busy_to_free'])
    	logging.info("-------------3, This is 'free_time'------")
    	logging.info(flask.session['free_time'])
    	flask.g.whole = whole_events

    return render_template('index.html')
    ##Q: I used want to combine _choose_cal function with /choose, but server does not allow to do so. Why? 
    ##   Why the event cannot directly call the choose?
    
    
####
#
#  Google calendar authorization:
#      Returns us to the main /choose screen after inserting
#      the calendar_service object in the session state.  May
#      redirect to OAuth server first, and may take multiple
#      trips through the oauth2 callback function.
#
#  Protocol for use ON EACH REQUEST: 
#     First, check for valid credentials
#     If we don't have valid credentials
#         Get credentials (jump to the oauth2 protocol)
#         (redirects back to /choose, this time with credentials)
#     If we do have valid credentials
#         Get the service object
#
#  The final result of successful authorization is a 'service'
#  object.  We use a 'service' object to actually retrieve data
#  from the Google services. Service objects are NOT serializable ---
#  we can't stash one in a cookie.  Instead, on each request we
#  get a fresh serivce object from our credentials, which are
#  serializable. 
#
#  Note that after authorization we always redirect to /choose;
#  If this is unsatisfactory, we'll need a session variable to use
#  as a 'continuation' or 'return address' to use instead. 
#
####

def valid_credentials():
    """
    Returns OAuth2 credentials if we have valid
    credentials in the session.  This is a 'truthy' value.
    Return None if we don't have credentials, or if they
    have expired or are otherwise invalid.  This is a 'falsy' value. 
    """
    if 'credentials' not in flask.session:
      return None

    credentials = client.OAuth2Credentials.from_json(
        flask.session['credentials'])

    if (credentials.invalid or
        credentials.access_token_expired):
      return None
    return credentials


def get_gcal_service(credentials):
  """
  We need a Google calendar 'service' object to obtain
  list of calendars, busy times, etc.  This requires
  authorization. If authorization is already in effect,
  we'll just return with the authorization. Otherwise,
  control flow will be interrupted by authorization, and we'll
  end up redirected back to /choose *without a service object*.
  Then the second call will succeed without additional authorization.
  """
  app.logger.debug("Entering get_gcal_service")
  http_auth = credentials.authorize(httplib2.Http())
  service = discovery.build('calendar', 'v3', http=http_auth)
  app.logger.debug("Returning service")
  return service

@app.route('/oauth2callback')
def oauth2callback():
  """
  The 'flow' has this one place to call back to.  We'll enter here
  more than once as steps in the flow are completed, and need to keep
  track of how far we've gotten. The first time we'll do the first
  step, the second time we'll skip the first step and do the second,
  and so on.
  """
  app.logger.debug("Entering oauth2callback") 
  flow =  client.flow_from_clientsecrets(
      CLIENT_SECRET_FILE, #client_secret_json file
      scope= SCOPES,
      redirect_uri=flask.url_for('oauth2callback', _external=True))
  #else:
  
  ## Note we are *not* redirecting above.  We are noting *where*
  ## we will redirect to, which is this function. 
  
  ## The *second* time we enter here, it's a callback 
  ## with 'code' set in the URL parameter.  If we don't
  ## see that, it must be the first time through, so we
  ## need to do step 1. 
  app.logger.debug("Got flow")
  if 'code' not in flask.request.args:
    app.logger.debug("Code not in flask.request.args")
    auth_uri = flow.step1_get_authorize_url()
    return flask.redirect(auth_uri)
    ## This will redirect back here, but the second time through
    ## we'll have the 'code' parameter set
  else:
    ## It's the second time through ... we can tell because
    ## we got the 'code' argument in the URL.
    app.logger.debug("Code was in flask.request.args")
    auth_code = flask.request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    flask.session['credentials'] = credentials.to_json()
    ## Now I can build the service and execute the query,
    ## but for the moment I'll just log it and go back to
    ## the main screen
    app.logger.debug("Got credentials")
    return flask.redirect(flask.url_for('choose'))

#####
#
#  Option setting:  Buttons or forms that add some
#     information into session state.  Don't do the
#     computation here; use of the information might
#     depend on what other information we have.
#   Setting an option sends us back to the main display
#      page, where we may put the new information to use. 
#
#####

@app.route('/setrange', methods=['POST'])
def setrange(): #get the input date
    """
    User chose a date range with the bootstrap daterange
    widget.
    # This function is used to get the inpute date, time from user. These data are use later to determine what kind of information need to be adding into flask.return
    
    """
    app.logger.debug("Entering setrange")  
    flask.flash("Setrange gave us '{}'".format(
      request.form.get('daterange')))
    daterange = request.form.get('daterange')
    flask.session['daterange'] = daterange
    daterange_parts = daterange.split()
    
    # add the time to the begin_date and end_date: 
    flask.session['begin_time'] = request.form.get('begin_time')
    flask.session['end_time'] = request.form.get('end_time')

    flask.session['begin_datetime'] = interpret_date(daterange_parts[0]+" "+flask.session['begin_time']) 
    
    flask.session['end_datetime'] = interpret_date(daterange_parts[2]+" "+flask.session['end_time'])
    
    logging.info("Get begin_time {}, get end_time: {}".format(flask.session['begin_time'], flask.session['end_time']))
    app.logger.debug("Setrange parsed {} - {}  dates as {} - {}".format(
      daterange_parts[0], daterange_parts[1], 
      flask.session['begin_date'], flask.session['end_date']))
      
    return flask.redirect(flask.url_for("choose"))


@app.route('/_select_calendar', methods=['POST'])
def select_cal_get_events():
    """
    get the id of the calendars that user choose from checkbox
    """    
    # Get the selected calendar ids
    cal_ids = request.form.getlist('summary')
    flask.session['cal_ids'] = cal_ids
    return flask.redirect(flask.url_for("choose"))
    #return render_template('index.html')


 
busy_to_free = []
@app.route('/_to_free_time', methods=['POST'])
def to_free():
	"""
	set the selected busy time to free, busy_to_free is the list that contain the events been set as the free time from the busy time list.
	"""
	busy_to_freeId = request.form.getlist('to_free')
	filtered_event = flask.session["filtered_event"]
	
	for eve_id in busy_to_freeId:
		for eve in filtered_event:
			if (eve_id == eve['id']):
				busy_to_free.append(eve)
	
	flask.session['busy_to_free'] = busy_to_free
	flask.session['busy_to_freeId'] = busy_to_freeId

	return flask.redirect(flask.url_for("choose"))


@app.route('/_send_to_database', methods=['POST'])
def to_database():
	"""
	This function send the free meeting time to database as long as the user confirm.
	"""
	free_time = flask.session['free_time']
	#logging.info("-------#########This is to_Database function's free_times")
	#logging.info(free_time)
	#for free in free_time:
	database.create_memo(free_time)
	#logging.info("-------#########This is to_Database function's free_times AFTER")
	#logging.info(free_time)
	
	#After every time in free_time was added to the database, they are automatically add an "_id" key in free_time.

	return flask.redirect(flask.url_for("choose"))


@app.route('/_group_free_time', methods=['POST'])
def group_free():
	"""
	This function connect to the database.py file, get the .
	"""
	group_free = database.group_freeTime()
	logging.info("---------This is group_free database flask_main -----#####")
	logging.info(group_free)
	flask.g.group = group_free
	logging.info("---------This is group_free database flask.g.group -----#####")
	logging.info(flask.g.group)
	
	return flask.redirect(flask.url_for("choose"))
	
	


####
#
#   Initialize session variables 
#
####

def init_session_values():
    """
    Start with some reasonable defaults for date and time ranges.
    Note this must be run in app context ... can't call from main. 
    # Initiate the value of the the key. 
    # These value are make by the server rather than ask from html. 
    # The values are redefined on the /setrange function
    """
    # Default date span = tomorrow to 1 week from now
    now = arrow.now('local')     # We really should be using tz from browser
    tomorrow = now.replace(days=+1)
    nextweek = now.replace(days=+7)
    flask.session["begin_date"] = tomorrow.floor('day').isoformat()
    flask.session["end_date"] = nextweek.ceil('day').isoformat()
    flask.session["daterange"] = "{} - {}".format(
        tomorrow.format("MM/DD/YYYY"),
        nextweek.format("MM/DD/YYYY"))
    # Default time span each day, 9 to 5
    flask.session["begin_time"] = interpret_time("9am")
    flask.session["end_time"] = interpret_time("5pm")

def interpret_time( text ):
    """
    Read time in a human-compatible format and
    interpret as ISO format with local timezone.
    May throw exception if time can't be interpreted. In that
    case it will also flash a message explaining accepted formats.
    """
    app.logger.debug("Decoding time '{}'".format(text))
    time_formats = ["ha", "h:mma",  "h:mm a", "H:mm"]
    try: 
        as_arrow = arrow.get(text, time_formats).replace(tzinfo=tz.tzlocal())
        as_arrow = as_arrow.replace(year=2017) #HACK see below
        app.logger.debug("Succeeded interpreting time")
    except:
        app.logger.debug("Failed to interpret time")
        flask.flash("Time '{}' didn't match accepted formats 13:30 or 1:30pm"
              .format(text))
        raise
    return as_arrow.isoformat()
    #HACK #Workaround
    # isoformat() on raspberry Pi does not work for some dates
    # far from now.  It will fail with an overflow from time stamp out
    # of range while checking for daylight savings time.  Workaround is
    # to force the date-time combination into the year 2016, which seems to
    # get the timestamp into a reasonable range. This workaround should be
    # removed when Arrow or Dateutil.tz is fixed.
    # FIXME: Remove the workaround when arrow is fixed (but only after testing
    # on raspberry Pi --- failure is likely due to 32-bit integers on that platform)


def interpret_date( text ):
    """
    Convert text of date to ISO format used internally,
    with the local time zone.
    """
    try:
      as_arrow = arrow.get(text, "MM/DD/YYYY HH:mm").replace(
          tzinfo=tz.tzlocal())
    except:
        flask.flash("Date '{}' didn't fit expected format 12/31/2001")
        raise
    return as_arrow.isoformat()

def next_day(isotext):
    """
    ISO date + 1 day (used in query to Google calendar)
    """
    as_arrow = arrow.get(isotext)
    return as_arrow.replace(days=+1).isoformat()

####
#
#  Functions (NOT pages) that return some information
#
####
  
def list_calendars(service):
    """
    Given a google 'service' object, return a list of
    calendars.  Each calendar is represented by a dict.
    The returned list is sorted to have
    the primary calendar first, and selected (that is, displayed in
    Google Calendars web app) calendars before unselected calendars.
    
    # This function check the calendars inside this google calendar account
    # summary: title of the calendar
    # id: Identifier of the calendar
    # details description: https://developers.google.com/google-apps/calendar/v3/reference/calendarList

    """
    app.logger.debug("Entering list_calendars")  
    calendar_list = service.calendarList().list().execute()["items"]
    result = [ ]
    for cal in calendar_list:
        kind = cal["kind"]
        id = cal["id"]
        if "description" in cal: 
            desc = cal["description"]
        else:
            desc = "(no description)"
        summary = cal["summary"]
        # Optional binary attributes with False as default
        selected = ("selected" in cal) and cal["selected"]
        primary = ("primary" in cal) and cal["primary"]        

        result.append(
          { "kind": kind,
            "id": id,
            "summary": summary,
            "selected": selected,
            "primary": primary,
            "description": desc
            })
    return sorted(result, key=cal_sort_key)

def list_events(service,calendar):
	"""
	Based on the calendar, return a list of events, events are all the events inside that calendar. 
	Each event is represented by a dict.
	"""
	app.logger.debug("Entering list_events")
	event_list = service.events().list(calendarId=calendar).execute()["items"]
	# ,orderBy="startTime", singleEvents=True
	result = [ ]
	for eve in event_list:
		#logging.info("------This is event_list in list_events-----")
		#logging.info(event_list)
		if "transparency" in eve:
			continue
		else:
			id = eve["id"]
			start = eve["start"]["dateTime"]
			end = eve["end"]["dateTime"]
			summary = eve["summary"]
			result.append(
			      { "id": id,
				"start": start,
				"end": end,
				"summary": summary,
				"calendarId":calendar
				})
	return result
	
def date_time_filter(events,begin_datetime,end_datetime):
	"""
	events is an list that contain the calender event. The start and end key are the string including the date and time in iso formate.
	"""
	#Initialize all the input date and time to the arrow object
	# eb = event_begin_datetime, ee = event_end_datetime, ib = input(user defined)_begin_datetime, ie = input_end_time
	ibegin = arrow.get(begin_datetime)
	iend = arrow.get(end_datetime)
	result = []
	
	for eve in events:
		#Turn the event's date and time to arrow object
		ebegin = arrow.get(eve["start"])
		eend = arrow.get(eve["end"])
		
		#event date is inside the defined range
		if (ebegin.date()>= ibegin.date() and eend.date()<=iend.date()):
			#case that whole inside the time
			if (ebegin.time()>=ibegin.time() and eend.time()<=iend.time()):
				result.append(eve)
			#start earlier and end in the range
			elif (ebegin.time()<ibegin.time() and eend.time() > ibegin.time()):
				result.append(eve)
			#start in the range and go over the range
			elif (ebegin.time()<iend.time() and eend.time()>= iend.time()):
				result.append(eve)
		#event date start early and end in the date range
		elif (ebegin.date()<ibegin.date() and eend.date()>ibegin.date()):
			# end between start and end time
			if (ibegin.time()<eend.time()<=iend.time()):
				result.append(eve)
		#event date begin in the date range over end date
		elif (ebegin.date()<iend.date() and eend.date()>= iend.date()):
			# Start time in the input start and end range
			if (ibegin.time()<=ebegin.time()<iend.time()):
				result.append(eve)
	
	if ("busy_to_freeId" in flask.session):
		busy_to_freeId = flask.session['busy_to_freeId']
		for freeId in busy_to_freeId:
			for eve in result:
				if (eve["id"] == freeId):
					result.remove(eve)
	
	for eve in result:
		eve["weekday"] = arrow.get(eve["start"]).format('dddd')
		
	logging.info("----------This is events after filter: ")
	logging.info(result)

	return result
  


def cal_sort_key( cal ):
    """
    Sort key for the list of calendars:  primary calendar first,
    then other selected calendars, then unselected calendars.
    (" " sorts before "X", and tuples are compared piecewise)
    """
    if cal["selected"]:
       selected_key = " "
    else:
       selected_key = "X"
    if cal["primary"]:
       primary_key = " "
    else:
       primary_key = "X"
    return (primary_key, selected_key, cal["summary"])


#################
#
# Functions used within the templates
#
#################

@app.template_filter( 'fmtdate' )
def format_arrow_date( date ):
    try: 
        normal = arrow.get( date )
        return normal.format("ddd MM/DD/YYYY")
    except:
        return "(bad date)"

@app.template_filter( 'fmttime' )
def format_arrow_time( time ):
    try:
        normal = arrow.get( time )
        return normal.format("HH:mm")
    except:
        return "(bad time)"
    
#############


if __name__ == "__main__":
  # App is created above so that it will
  # exist whether this is 'main' or not
  # (e.g., if we are running under green unicorn)
  app.run(port=CONFIG.PORT,host="0.0.0.0")
    
