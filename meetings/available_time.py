"""
Available time calculate the free time block of the day.
It also summarize the time block of whole day, including both free and busy time.
"""
import logging
import flask
import arrow

app = flask.Flask(__name__)
app.logger.setLevel(logging.INFO) ##Used to be .DEBUG


def combine_busy_free():
	"""
	get the filtered_event is the busy event, busy_to_free time will count toward the free time. The free time is in the range from user defined date and time
	both begin_datetime and the end_datetime are the time including date and time and in the iso format.
	"""
	#logging.info("-------Enter available_time")
	filtered_event = flask.session['filtered_event']
	#logging.info("Get the filtered_event")
	#logging.info(filtered_event)
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
	global busy_free_combine
	busy_free_combine = []
	
	
	merge_events = merge(filtered_event)
	for i in range(len(merge_events)-1):
		first_begin = arrow.get(merge_events[i]['start'])
		first_end = arrow.get(merge_events[i]['end'])
		second_begin = arrow.get(merge_events[i+1]['start'])
		second_end = arrow.get(merge_events[i+1]['end'])
		if (i == 0):
			calculate_free(begin_datetime, first_begin)
			calculate_free(first_end, second_begin)
		elif (i == len(filtered_event) - 2):
			calculate_free(first_end, second_begin)
			calculate_free(second_end, end_datetime)
		else: 
			calculate_free(first_end, second_begin)
	
	for eve in merge_events:
		busy_free_combine.append(eve)
	for eve in free:
		busy_free_combine.append(eve)
		
	busy_free_combine.sort(key=lambda e: e['start'])
	return busy_free_combine
	
	# Q: why init_eve = filtered_event[0] is out of range? filtered_event: [{}, {}, ... {}], is it means each dictionary inside cannot be sorted? Would it should allow user to sort it?


def merge(events):	
	logging.info("This is the range: ----------")
	logging.info(range(len(events)))
	merge_events = []
	n = 0
	merge_count = 0
	for i in range(len(events)-1):
		#Use this block to initialize the merge_events
		
		if (n<1):
			merge_events.append(events[0])
			n = 2	
			
		#first = events[i]
		next_eve = events[i+1]
		logging.info("This is the current merge: ----")
		logging.info(merge_events[merge_count])
		logging.info("This is the next_eve: ----")
		logging.info(next_eve)
		
		
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
	return merge_events
			


global free
free = []
def calculate_free(first_end,second_begin):
	# Cases that second event happen after the first event finish, therefore, there are some free time.
	# subcase when the date start time is in between the events.
	if (first_end.time() < begin_datetime.time() < second_begin.time() ):
		start = second_begin.date()+"T"+begin_datetime.time()
		free_start = arrow.get(start).replace(tzinfo=tz.tzlocal()).isoformat()
		free_end = second_begin.isoformat()
		free.append(
			{ "summary": "free time",
			  "start": free_start,
			  "end": free_end,
			  "weekday": arrow.get(free_start).format('dddd')
			})
	# subcase when the date end time is between the events
	elif (first_end.time() < end_datetime.time() < second_begin.time() ):
		free_start = first_end.isoformat()
		end = first_end.date()+"T"+end_datetime.time()
		free_end = arrow.get(end).replace(tzinfo=tz.tzlocal()).isoformat()
		free.append(
			{ "summary": "free time",
			  "start": free_start,
			  "end": free_end,
			  "weekday": arrow.get(free_start).format('dddd')
			})
	# subcase that free time is in between
	else:
		if (first_end.date() == second_begin.date()):
			free_start = first_end.isoformat()
			free_end = second_begin.isoformat()
			free.append(
				{ "summary": "free time",
				  "start": free_start,
				  "end": free_end,
				  "weekday": arrow.get(free_start).format('dddd')
				})
		else:
			datetime_diff = second_begin - first_end
			for i in range(datetime_diff.days):
				start = begin_datetime.shift(hours=+24*i).isoformat()
				end = end_datetime.shift(hours=+24*i).isoformat()
				free.append(
				{ "summary": "free time",
				  "start": start,
				  "end": end,
				  "weekday": arrow.get(free_start).format('dddd')
				 })
			
	free.sort(key=lambda e: e['start'])
	return free
	
'''
new_free = []
for free in free_time:
	free_start = arrow.get(free['start'])
	free_end = arrow.get(free['end'])
	for eve in busy_events:
		eve_start = arrow.get(eve['start'])
		eve_end = arrow.get(eve['end'])
		temp_start = free_start
		temp_end = free_end
		
		if (eve_start<free_start<eve_end):
			temp_start = eve_end
		if (eve_start>free_start and eve_end<free_end):
			temp_end = eve_start
'''
			
