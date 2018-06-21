      
    var getSensors = function(cb=null) {
        $.getJSON( "/sdstore/sensors/", function( sensors ) {      
            $.each( sensors, function( i, sensor ) {
                if (cb!==null) cb(sensor, null);
            });
        })
        .fail(function() { 
            if (cb!==null) cb(null, "Connection failed");
        });
    }
        
    var getLastReading = function(sensor, channel, cb=null) {
        $.getJSON( "/sdstore/sensor/"+sensor.id+"/"+channel.name+"/last-reading/", function( reading ) {
            console.log(reading);
            if (cb!==null) {
                if (reading.hasOwnProperty('timestamp')) cb(reading, null); else cb(null, null);
            }
        })
        .fail(function() { 
            if (cb!==null) cb(null, "Connection failed");
        });
    }
        
    var getReadings = function(sensor, start, end, cb=null) {
        var d = { 
            "csrfmiddlewaretoken" : $("[name=csrfmiddlewaretoken]").val(),
            "sensor": sensor.id,
            "start": start.format('YYYY-MM-DD HH:mm:ss'),
            "end": end.format('YYYY-MM-DD HH:mm:ss'),
        };
        console.log(d);
        $.ajax({
            url: "/" ,
            method: "POST",
            data: d,
            dataType: "json",
        }).done(function( readings ) {
            if (cb!==null) cb(readings, null);
        }).fail(function() {
            console.log("AJAX error");
            if (cb!==null) cb(null, "Connection failed");
        });
    }