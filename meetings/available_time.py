"""
Available time calculate the free time block of the day.
It also summarize the time block of whole day, including both free and busy time.
"""
import logging
import flask
import arrow
from dateutil import tz

app = flask.Flask(__name__)
app.logger.setLevel(logging.INFO) ##Used to be .DEBUG


def combine_busy_free():
	"""
	get the filtered_event is the busy event, busy_to_free time will count toward the free time. The free time is in the range from user defined date and time
	both begin_datetime and the end_datetime are the time including date and time and in the iso format.
	"""
	#logging.info("-------Enter available_time")
	filtered_event = flask.session['filtered_event']
	logging.info("Get the filtered_event")
	logging.info(filtered_event)
	busy_to_free = flask.session['busy_to_free']
	#logging.info("Get the busy_to_free")
	#logging.info(busy_to_free)
	global begin_datetime
	begin_datetime = arrow.get(flask.session['begin_datetime'])
	
	#logging.info("Get the begin_datetime")
	#logging.info(begin_datetime)
	global end_datetime
	end_datetime = arrow.get(flask.session['end_datetime'])
	
	#logging.info("Get the end_datetime")
	#logging.info(end_datetime)
	busy_free_combine = []
	
	
	#Generates the free time array every date from user defined time
	ini_free = []
	datetime_diff = end_datetime - begin_datetime
	
	#Set the daily end time.
	free_end_datetime = arrow.get(begin_datetime.date().isoformat()+"T"+end_datetime.time().isoformat()).replace(tzinfo=tz.tzlocal())
		
	for i in range(datetime_diff.days+1):
		free_start = begin_datetime.shift(hours=+24*i).isoformat()
		free_end = free_end_datetime.shift(hours=+24*i).isoformat()
		
		ini_free.append(
			{ "summary": "free time",
			  "start": free_start,
			  "end": free_end,
			  "weekday": arrow.get(free_start).format('dddd')
			})
	
	logging.info("-----------This is the ini_Free--------")
	logging.info(ini_free)
		
	merge_events = merge(filtered_event)
	free_times = calculate_free(ini_free,merge_events)
	
	#The merge_events is used for combine the overlapping events, for the view of the user, still display the original events
	for eve in filtered_event:
		busy_free_combine.append(eve)
	
	#These events used to be the busy, changing the title to infor the users that this events can be free.
	for eve in busy_to_free:
		eve["summary"] += "--( Can be free )"
		busy_free_combine.append(eve)
	
	for eve in free_times:
		busy_free_combine.append(eve)

	busy_free_combine.sort(key=lambda e: e['start'])
		
	return busy_free_combine
	

def merge(events):
	"""
	Merge the events time.
	Combine the overlap part.
	"""	
	logging.info("This is the range: ----------")
	logging.info(range(len(events)))
	logging.info(len(events))
	logging.info(events)
	merge_events = []
	
	merge_count = 0
	if len(events) == 0:
		return [ ]
	merge_events.append(events[0])
	# merge_events[0] = events[0] will not work since the merge_events is an empty array, user cannot "change" the value in a empty position. 
	# the eve['weekday'] would work is because eve is a dictionary, this data structure allow user to do so.
	for i in range(len(events)-1):
		next_eve = events[i+1]
		
		merge_begin = arrow.get(merge_events[merge_count]['start'])
		merge_end = arrow.get(merge_events[merge_count]['end'])
		next_begin = arrow.get(next_eve['start'])
		next_end = arrow.get(next_eve['end'])
		
		
		if (merge_end >= next_begin):
			busy_begin = merge_begin.isoformat()
			
			if (merge_end >= next_end):
				busy_end = merge_end.isoformat()
			else:
				busy_end = next_end.isoformat()
			
			merge_events[merge_count] = { "start": busy_begin, "end": busy_end, "summary": merge_events[merge_count]["summary"]+ "+" + next_eve["summary"], "weekday": arrow.get(busy_begin).format('dddd')}
		else:
			merge_events.append(next_eve)
			merge_count += 1
			
	# Sort based on the start time		
	merge_events.sort(key=lambda e: e['start'])
	
	logging.info("This is the events after the merge: ")
	logging.info(range(len(merge_events)))
	logging.info(merge_events)
	return merge_events
			


def calculate_free(free_time,busy_events):
	"""
	Args:
	free_time: the list of the free time before substracting the busy_events. The initial date and time range of the free_time is set by the users. Shows the daily free time. For example, if the start and end datetime is 11-13 09:00 - 11-15 20:00, then free time contains 3 events, every events start at 9am end at 8pm, and in date 11-13, 11-14, 11-15
	busy_events: this is generated from the flask_main as the events shown on the calendar.
	"""
	new_free = []
	for free in free_time:
		free_start = arrow.get(free['start'])
		free_end = arrow.get(free['end'])
				
		temp_start = free_start
		temp_end = free_end

		for eve in busy_events:
			eve_start = arrow.get(eve['start'])
			eve_end = arrow.get(eve['end'])
			
			#part overlap at begining
			if (eve_start<free_start<eve_end):
				temp_start = eve_end
				logging.info("----------This is temp_start in first if: ")
				logging.info(temp_start)
			#whole eve is in the free time range
			elif (eve_start>temp_start and eve_end<free_end):
				temp_end = eve_start
				new_free.append(
				{ "summary": "free time",
				  "start": temp_start.isoformat(),
				  "end": temp_end.isoformat(),
				  "weekday": arrow.get(temp_start).format('dddd')
				 })
				temp_start = eve_end
				temp_end = free_end
			#part overlap at the end
			elif (eve_start<free_end<eve_end):
				temp_end = eve_start
				
		new_free.append(
			{ "summary": "free time",
			  "start": temp_start.isoformat(),
			  "end": temp_end.isoformat(),
			  "weekday": arrow.get(temp_start).format('dddd')
			 })
			 
	new_free.sort(key=lambda e: e['start'])
	
	logging.info("-------------This is the new_free: ---------")
	logging.info(new_free)
				 
	return new_free





