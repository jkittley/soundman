from django.views.generic import TemplateView
from django.shortcuts import render_to_response
import pandas as pd
from datetime import time
from sd_store.models import Sensor, Channel, SensorReading

from bokeh.io import show
from bokeh.models import (
    ColumnDataSource,
    HoverTool,
    LinearColorMapper,
    BasicTicker,
    PrintfTickFormatter,
    ColorBar,
)
from bokeh.plotting import figure
from bokeh.sampledata.unemployment1948 import data as sampledata
from bokeh.embed import components
from math import pi

class CalendarView(TemplateView):
    template_name = "frontend/calendar.html"
    
    def get(self, request):

        interval_mins = 15

        sensor = Sensor.objects.get(mac='sensor202')
        channel = Channel.objects.get(name="volume") 

        df = pd.DataFrame(list(SensorReading.objects.filter(sensor=sensor, channel=channel).values('timestamp', 'value')))
        # Make the timestamp the index
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        # Resample the data to an hourly interval      
        df = df.resample('{}Min'.format(interval_mins)).mean()
        df = df.sort_index()
        # Drop NaN Rows
        df = df.dropna()
        # Add Date and hour columns
        df['date'] = df.index.strftime('%Y-%m-%d')
        df['intvl'] = df.index.strftime('%H:%M')
            
        intvls = [ time(h, m).strftime('%H:%M') for h in range(0, 24) for m in range(0, 60, interval_mins)]
        dates = df['date'].unique()

        print (df)
        print (intvls)
  
        # this is the colormap from the original NYTimes plot
        colors = ["#75968f", "#a5bab7", "#c9d9d3", "#e2e2e2", "#dfccce", "#ddb7b1", "#cc7878", "#933b41", "#550b1d"]
        mapper = LinearColorMapper(palette=colors, low=df.value.min(), high=df.value.max())

        TOOLS = "hover,save,pan,box_zoom,reset,wheel_zoom"
        p = figure(title="Sensor Data",
                x_range=intvls, y_range=list(reversed(dates)),
                x_axis_location="above", 
                tools=TOOLS, 
                toolbar_location='below',
                sizing_mode='stretch_both')

        p.grid.grid_line_color = None
        p.axis.axis_line_color = None
        p.axis.major_tick_line_color = None
        p.axis.major_label_text_font_size = "12pt"
        p.axis.major_label_standoff = 0
        p.xaxis.major_label_orientation = pi / 3

        # source = ColumnDataSource(df)

        source = ColumnDataSource(
            data=dict(
                date=[ str(x) for i, x in df['date'].iteritems() ],
                intvl=[ str(y) for i, y in df['intvl'].iteritems() ],
                value=[ str(x) for i, x in df['value'].iteritems() ],
            )
        )

        print (source.data)

        p.rect(x="intvl", y="date", width=1, height=1,
            source=source,
            fill_color={'field': 'value', 'transform': mapper},
            line_color=None)

        color_bar = ColorBar(color_mapper=mapper, major_label_text_font_size="5pt",
                            ticker=BasicTicker(desired_num_ticks=len(colors)),
                            formatter=PrintfTickFormatter(format="%d%%"),
                            label_standoff=6, border_line_color=None, location=(0, 0))
        p.add_layout(color_bar, 'right')

        p.select_one(HoverTool).tooltips = [
            ('date', '@date'),
            ('interval', '@intvl'),
            ('value', 'Mean dB: @value{1.11}'),
        ]

        script, div = components(p)
        # script = ''
        # div = ''
        return render_to_response( 'frontend/calendar.html', {'script' : script , 'div' : div, 'bokeh_version': '0.12.16'})