#encoding:UTF-8

'''
Created on 26 Oct 2012

@author: enrico
'''
from collections import deque
import itertools
from datetime import datetime, timedelta
from time import mktime

def total_seconds(td):
    return (td.microseconds + (td.seconds + td.days * 24 * 3600) * 10**6) / 10**6

def to_timestamp(dt):
    return mktime( dt.timetuple() )

def to_datetime(timestamp):
    return datetime.fromtimestamp(timestamp)

def floor_30(dt):
    return dt - timedelta(minutes= dt.minute % 30, 
                          seconds=dt.second, 
                          microseconds = dt.microsecond)

def floor_15(dt):
    return dt - timedelta(minutes= dt.minute % 15, 
                          seconds = dt.second, 
                          microseconds=dt.microsecond)

def round_30(dt):
    timestamp = to_timestamp(dt)
    rounded = round(timestamp / (30 * 60)) * 30 * 60
    return datetime.fromtimestamp(rounded)

def round_15(dt):
    timestamp = to_timestamp(dt)
    rounded = round(timestamp / (15 * 60)) * 15 * 60
    return datetime.fromtimestamp(rounded)
    
def moving_average(iterable, n=3):
    it = iter(iterable)    
    d = deque(itertools.islice(it, n-1))
    d.appendleft(1.0)
    s = sum(d)
    for elem in it:
        s += elem - d.popleft()
        d.append(elem)
        yield s / float(n)

