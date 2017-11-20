"""
Available time calculate the free time block of the day.
It also summarize the time block of whole day, including both free and busy time.
"""
import logging
import flask

app = flask.Flask(__name__)
app.logger.setLevel(logging.INFO) ##Used to be .DEBUG


def calculate_free():
	"""
	get the filtered_event is the busy event, busy_to_free time will count toward the free time. The free time is in the range from user defined date and time
	both begin_datetime and the end_datetime are the time including date and time and in the iso format.
	"""
	logging.info("-------Enter available_time")
	filtered_event = flask.session['filtered_event']
	logging.info("Get the filtered_event")
	logging.info(filtered_event)
	busy_to_free = flask.session['busy_to_free']
	#logging.info("Get the busy_to_free")
	#logging.info(busy_to_free)
	
	begin_datetime = flask.session['begin_datetime']
	#logging.info("Get the begin_datetime")
	#logging.info(begin_datetime)
	end_datetime = flask.session['end_datetime']
	#logging.info("Get the end_datetime")
	#logging.info(end_datetime)
	
	# Q: why init_eve = filtered_event[0] is out of range? filtered_event: [{}, {}, ... {}], is it means each dictionary inside cannot be sorted? Would it should allow user to sort it?
	result = []
	for eve in filtered_event:
		weekday = eve['weekday']
		logging.info ("This is weekday: ")
		logging.info(weekday)
		if (weekday in result):
			result['weekday'] += eve
		else:
			result.append({weekday:eve})
	logging.info("This is result: ")
	logging.info(result)
		
	
	result = "abc"
	return result

