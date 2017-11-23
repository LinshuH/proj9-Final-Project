
import available_time
import arrow

event = [{'id': '5llvg9oh71jn2a8nfra2e89vhk', 'start': '2017-11-14T07:00:00-08:00', 'end': '2017-11-14T10:00:00-08:00', 'weekday': 'Tuesday', 'summary': '11.14 7-10 temp_start test'}, {'id': '7eqt0ai3ajf8ul8ru2mqv8v00c', 'start': '2017-11-14T15:00:00-08:00', 'end': '2017-11-14T18:30:00-08:00', 'weekday': 'Tuesday', 'summary': '3-6:30 Yes'}, {'id': '7h38fsoh78mph12mm60r5m2nnc', 'start': '2017-11-15T07:00:00-08:00', 'end': '2017-11-15T10:00:00-08:00', 'weekday': 'Wednesday', 'summary': '7-10a Yes'}, {'id': '38d9m5cqkj8tn0lna1cs25c5j7', 'start': '2017-11-15T09:00:00-08:00', 'end': '2017-11-15T11:30:00-08:00', 'weekday': 'Wednesday', 'summary': 'Merge test'}]
global event
free_time = [{'id': '5llvg9oh71jn2a8nfra2e89vhk', 'start': '2017-11-14T07:00:00-08:00', 'end': '2017-11-14T10:00:00-08:00', 'weekday': 'Tuesday', 'summary': '11.14 7-10 temp_start test'}, {'id': '7eqt0ai3ajf8ul8ru2mqv8v00c', 'start': '2017-11-14T15:00:00-08:00', 'end': '2017-11-14T18:30:00-08:00', 'weekday': 'Tuesday', 'summary': '3-6:30 Yes'}, {'start': '2017-11-15T07:00:00-08:00', 'end': '2017-11-15T11:30:00-08:00', 'weekday': 'Wednesday', 'summary': '7-10a Yes+Merge test'}]
global free_time


def test_merge(events):
	after_merge = [{'id': '7eqt0ai3ajf8ul8ru2mqv8v00c', 'start': '2017-11-14T15:00:00-08:00', 'end': '2017-11-14T18:30:00-08:00', 'weekday': 'Tuesday', 'summary': '3-6:30 Yes'}, {'end': '2017-11-15T11:30:00-08:00', 'start': '2017-11-15T07:00:00-08:00', 'weekday': 'Wednesday', 'summary': '7-10a Yes+Merge test'}]
    assert len(event) == 4
    assert len(after_merge) == 3
	for eve in after_merge:
		if eve.contains('id'):
			assert event.contains(eve) == True
		else:
			assert eve['summary'] == '7-10a Yes+Merge test'

# test whether the free time is successfully generated and whether the result is sorted by the start date and time.
def test_calculate_free(free, event_list):
    new_free = calculate_free(free_time, event)
    global new_free
    
    assert len(new_free) == 2
    new_1 = new_free[0]
    new_2 = new_free[1]
    assert (arrow.get(new_1['start']) = arrow.get(new_2['start'])) == False
    assert (arrow.get(new_1['end']) = arrow.get(new_2['end'])) == False
    assert new_1['start'] == '2017-11-14T10:00:00-08:00'
    assert new_1['end'] == '2017-11-14T15:00:00-08:00'
    assert new_1['weekday'] == 'Tuesday'
    assert new_2['start'] == '2017-11-15T11:30:00-08:00'
    assert new_2['end'] == '2017-11-15T17:00:00-08:00'
    assert new_2['weekday'] == 'Wednesday'

def test_combine_busy_free():
	combine = combine_busy_free()
	assert len(combine) == 6
