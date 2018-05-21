from django.shortcuts import render_to_response
from sd_store.models import SensorReading

from bokeh.plotting import figure, output_file, show 
from bokeh.embed import components

def timeseries(request):

    readings = SensorReading.objects\
        .filter(sensor_id=6)\
        .order_by("-timestamp")

    x= [ x.timestamp for x in readings]
    y= [ y.value for y in readings]

    plot = figure(title= 'Volume Over time' , 
        x_axis_label= 'Time', 
        x_axis_type="datetime",
        y_axis_label= 'Volume', 
        sizing_mode='stretch_both')

    plot.line(x, y, legend= 'f(x)', line_width = 2)
    #Store components 
    script, div = components(plot)
    #Feed them to the Django template.
    return render_to_response( 'frontend/bokeh.html', {'script' : script , 'div' : div} )

