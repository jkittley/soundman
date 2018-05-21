from django.views.generic import TemplateView
from django.shortcuts import render_to_response
import pandas as pd

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
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['bokeh_version'] = '0.12.16'
        return context

    def get(self, request):

        sensor = Sensor.objects.get(mac='sensor202')
        channel = Channel.objects.get(name="volume") 

        df = pd.DataFrame(list(SensorReading.objects.filter(sensor=sensor, channel=channel).values('timestamp', 'value')))
        # Make the timestamp the index
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        # Resample the data to an hourly interval      
        df = df.resample('1H').mean()
        # Drop NaN Rows
        df = df.dropna()
        # Add Date and hour columns
        df['date'] = df.index.date
        df['hour'] = df.index.hour
        df['hour'].apply(str)

        print (df)
        hours = [str(x) for x in range(0, 24)]
        days = df['date'].unique()
  
        # this is the colormap from the original NYTimes plot
        colors = ["#75968f", "#a5bab7", "#c9d9d3", "#e2e2e2", "#dfccce", "#ddb7b1", "#cc7878", "#933b41", "#550b1d"]
        mapper = LinearColorMapper(palette=colors, low=df.value.min(), high=df.value.max())

        source = ColumnDataSource(df)


        TOOLS = "hover,save,pan,box_zoom,reset,wheel_zoom"

        p = figure(title="Sensor Data",
                x_range=hours, y_range=list(reversed(days)),
                x_axis_location="above", 
                tools=TOOLS, 
                toolbar_location='below',
                sizing_mode='stretch_both')

        p.grid.grid_line_color = None
        p.axis.axis_line_color = None
        p.axis.major_tick_line_color = None
        p.axis.major_label_text_font_size = "5pt"
        p.axis.major_label_standoff = 0
        p.xaxis.major_label_orientation = pi / 3

        p.rect(x="date", y="hour", width=1, height=1,
            source=source,
            fill_color={'field': 'value', 'transform': mapper},
            line_color=None)

        color_bar = ColorBar(color_mapper=mapper, major_label_text_font_size="5pt",
                            ticker=BasicTicker(desired_num_ticks=len(colors)),
                            formatter=PrintfTickFormatter(format="%d%%"),
                            label_standoff=6, border_line_color=None, location=(0, 0))
        p.add_layout(color_bar, 'right')

        p.select_one(HoverTool).tooltips = [
            ('date', '@date @hour'),
            ('value', '@value%'),
        ]

        script, div = components(p)
        # script = ''
        # div = ''
        return render_to_response( 'frontend/bokeh.html', {'script' : script , 'div' : div} )