from datetime import date, datetime, timedelta, tzinfo
import pdb
import pandas as pd
import numpy as np
import matplotlib as mpl
mpl.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from timezone import LocalTimezone
import pytz
from wordcloud import WordCloud, STOPWORDS
import random
from os import path
import nvd3 
from markupsafe import Markup

#Google calendar uses RFC3339 datetime standards, so we need to generate those to request 
#datetime ranges. The LocalTimezone class handles DST cases
Local = LocalTimezone()

def get_prev_week():
    d = date.today()- timedelta(weeks = 1)
    while d.weekday() != 0:
        d = d - timedelta(days = 1)
    startTime = datetime.combine(d, datetime.min.time())
    endTime = startTime + timedelta(weeks = 1)
    return (startTime.replace(tzinfo = Local).isoformat("T"), 
        endTime.replace(tzinfo = Local).isoformat("T"))

def get_last_year():
    endTime = datetime.now(Local)
    startTime = endTime.replace(year = endTime.year-1)
    return (startTime.replace(tzinfo = Local).isoformat("T"), 
        endTime.replace(tzinfo = Local).isoformat("T"))



(startTimeDefault, endTimeDefault) = get_prev_week()

def get_events(service, calID = 'primary', startTime = startTimeDefault, 
    endTime = endTimeDefault):
    #returns a list of events corresponding to a partiular calendar, within a given time period
    eventsResult = service.events().list(
        calendarId=calID, timeMin=startTime, timeMax = endTime, singleEvents=True,
        orderBy='startTime',maxResults = 1000).execute()
    events = eventsResult.get('items', [])
    for i in range(len(events)):
        events[i]['sourceCal'] = calID
    return events

def get_calendar_list(service):
    #produce two dictionaries, one going from calendar name to calendar id, 
    #and one being the reverse.
    calendar_list = service.calendarList().list().execute()
    name2id = {}
    id2name = {}

    for calendar_list_entry in calendar_list['items']:

        key = calendar_list_entry.get('summaryOverride',calendar_list_entry.get('summary'))
        if key in name2id.keys():
            #Sometimes multiple calendars have the same name, 
            #here I just rename them 'dup_cal_2', 'dup_cal_3...'
            i = 2
            while key in name2id.keys():
                key = key + '_{}'.format(i)
                i = i + 1
        name2id[key] = calendar_list_entry['id']
        id2name[calendar_list_entry['id']] = key
    return name2id, id2name, calendar_list['items']


eastern = pytz.timezone('US/Eastern')
def get_event_duration(event):    
    #for what I am doing, it doesn't matter too much what timezone to be in, since
    #I am mostly interested in durations, however it needs to be in some timezone.
    #For simplicity, I use eastern timezone.
    startTime = pd.to_datetime(event['start'].get('dateTime',
        event['start'].get('date'))).tz_localize(pytz.utc).tz_convert(eastern)
    endTime = pd.to_datetime(event['end'].get('dateTime',
        event['end'].get('date'))).tz_localize(pytz.utc).tz_convert(eastern)
    dur = endTime - startTime
    if ('dateTime' in event['start']):
        allDay = False
    else:
        allDay = True
    return startTime, dur, allDay

def gen_event_table(events, id2name):
    #Returns a pandas df represinting a list of events
    columns = ['StartTime','Duration','Description','Calendar','AllDay','Creator','Tags']
    lst = []
    for event in events:
        (startTime, dur,allDay) = get_event_duration(event)
        if 'sourceCal' in event.keys():
            calName = id2name[event['sourceCal']]
        else:
            calName = event['organizer']['displayName']
        eventCreator = event.get('creator').get('displayName',event['creator'].get('email'))
        eventTitle = event.get('summary','')
        lst.append([startTime, dur, eventTitle,
            calName,allDay, eventCreator,[]])

    data = pd.DataFrame(lst,columns = columns)
    data = data.set_index("StartTime")
    return data

def get_data(service,cals_to_include = 'all'):    
    #requests all available events from particular calendars from the last year.
    #returns the list of dicts outputted by the gcal API. 
    (name2id,id2name, calendar_list) = get_calendar_list(service)
    (startTime,endTime) = get_last_year()

    if cals_to_include is 'all':
        cals_to_include = name2id.keys()
    events = []

    for CalName in cals_to_include:
        #import events from each calendar
        events.extend(get_events(service,name2id[CalName],startTime,endTime))
    #convert to pandas df
    data = gen_event_table(events,id2name)
    data = data[(~data.AllDay)].fillna(value=0)
    return data


def word_cloud(data):
    #Currently not implemented in the app, but could be at some point
    text = data.Description.T.tolist()
    text = [i.encode("utf-8") for i in text]
    strs = " ".join(text)
    wc = WordCloud(width=1600, height=800,max_words=500,random_state=1).generate(strs)
    stopwords = set(STOPWORDS)
    default_colors = wc.to_array()
    plt.title("Custom colors")
    plt.imshow(wc.recolor(color_func=white_color_func, random_state=3),
    interpolation="bilinear")
    plt.axis("off")


def plot_cal_bars(data):

    #group data by calendar and week, use units of hours
    weekShow = ((data['Duration']/np.timedelta64(1,'h')).groupby(data.Calendar)
            .resample('W').sum().unstack(level = 0)).round(1)

    #xlabels
    weekShow = weekShow.fillna(value=0)
    weekNames =  weekShow.set_index(weekShow.index.strftime("%b %d")).index.tolist()
    #mini bar names
    calNames = weekShow.columns.tolist()
    #generate some D3 code
    chart = nvd3.multiBarChart(width=1600, height=400, x_axis_format=None)
    xdata = weekNames
    #add hover tooltips
    extra_serie = {"tooltip": {"y_start": "You spent ", "y_end": " hours"}}
    for cal_name in weekShow:
        chart.add_serie(name=cal_name, y=weekShow[cal_name].tolist(), x=xdata,extra=extra_serie)
    chart.buildhtml()
    #make safe for HTML
    plot = Markup(chart.htmlcontent)
    return plot

