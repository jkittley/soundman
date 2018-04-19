/**
 * This file is part of sd_store
 * 
 * sd_store is free software: you can redistribute it and/or modify
 * it under the terms of the GNU Affero General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 * 
 * sd_store is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU Affero General Public License for more details.
 * 
 * You should have received a copy of the GNU Affero General Public License
 * along with sd_store.  If not, see <http://www.gnu.org/licenses/>.
 */

var sd_store;
if (!sd_store) {
    sd_store = {};
}

sd_store.dataloader = (function () {
    'use strict';
    var load_everything,
        parse_reading,
        format_date;

    parse_reading = function (o) {
        return { 'value': o.value, 't': new Date(o.t) };
    };

    var parse_annotation = function (o) {
        //o.start = new Date(o.start);
        //o.end = new Date(o.end);
        o.start = new Date(o.start.replace(/-/g, "/"));
        o.end = new Date(o.end.replace(/-/g, "/"));
        return o;
    };

    format_date = function (date) {

        var ye = date.getYear() + 1900,
            mo = date.getMonth() + 1,
            da = date.getDate(),
            ho = date.getHours(),
            mi = date.getMinutes(),
            se = date.getSeconds();
        if (mo < 10) {
            mo = '0' + mo;
        }
        if (da < 10) {
            da = '0' + da;
        }
        if (ho < 10) {
            ho = '0' + ho;
        }
        if (mi < 10) {
            mi = '0' + mi;
        }
        if (se < 10) {
            se = '0' + se;
        }
        return ye + '-' + mo + '-' + da + ' ' + ho + ':' + mi + ':' + se;
    };

    // load the sensor by id, by user or by group
    // then select channels 
    // TODO: optionally load also events
    load_everything = function (p, on_data_loaded) {
        var chained_load_readings,
            channel_filter,
            c,
            request_info = [],
            load_by_single_sensor,
            load_by_sensor_group,
            load_by_user,
            load_readings,
            on_everything_loaded;

        //console.log('load_everything');

        load_by_single_sensor = function (sensor) {
            sensor = JSON.parse(sensor);
            return load_readings([sensor]);
        };

        load_by_sensor_group = function (group) {
            group = JSON.parse(group);
            return load_readings(group.sensors);
        };

        load_by_user = function (sensors) {
            sensors = JSON.parse(sensors);
            //console.log('load_by_user', sensors);
            return load_readings(sensors);
        };

        on_everything_loaded = function () {
            var i, curr,
                parsed_data = [],
                checked_arguments;
            // we need to check whether we got more than one group of arguments
            if (arguments.length === 3 && arguments[2].hasOwnProperty('statusText') === true) {
                // this means there is only one group of readings
                checked_arguments = [arguments];
            } else {
                checked_arguments = arguments;
            }

            for (i = 0; i < checked_arguments.length; i += 1) {
                curr = JSON.parse(checked_arguments[i][0]);
                curr.sensor = request_info[i].sensor;
                curr.channel = request_info[i].channel;
                curr.readings = curr.data.map(parse_reading);
                curr.query = request_info[i].query;

                if (p.hasOwnProperty('annotations') === true && p.annotations) {
                    curr.annotations = curr.annotations.map(parse_annotation);
                }
                console.log(curr);
                parsed_data.push(curr);
            }

            on_data_loaded(parsed_data);
        };

        load_readings = function (sensors) {
            var s, c,
                url_data,
                curr_url,
                query,
                requests = [];

            //console.log('load_readings');

            url_data = {
                start: p.start,
                end: p.end,
                sampling_interval: p.sampling_interval,
                annotations: p.annotations
            };

            // for s in all sensors
            for (s = 0; s < sensors.length; s += 1) {
                // for c in all channels
                for (c = 0; c < sensors[s].channels.length; c += 1) {
                    if (channel_filter(sensors[s].channels[c].name)) {
                        // TODO: check here what kind of request(s) we need to make
                        if (p.hasOwnProperty('data')) {
                            curr_url = p.url + "sensor/" + sensors[s].id + "/" +
                                sensors[s].channels[c].name + "/data/";
                            query = 'data';
                        }
                        if (p.hasOwnProperty('baseline')) {
                            curr_url = p.url + "sensor/" + sensors[s].id + "/" +
                                sensors[s].channels[c].name + "/baseline/";
                            query = 'baseline';
                        }
                        if (p.hasOwnProperty('integral')) {
                            curr_url = p.url + "sensor/" + sensors[s].id + "/" +
                                sensors[s].channels[c].name + "/integral/";
                            query = 'integral';
                        }
                        requests.push($.ajax({
                            url: curr_url,
                            data: url_data
                        }).promise());
                        //console.log(curr_url);
                        request_info.push({
                            sensor: sensors[s],
                            channel: sensors[s].channels[c],
                            query: query
                        });
                    }
                }
            }

            // based on http://stackoverflow.com/questions/5627284/pass-in-an-array-of-deferreds-to-when
            return $.when.apply(null, requests);
        };

        p.start = format_date(p.start);
        p.end = format_date(p.end);

        // only load some channels, or load all channels
        if (p.hasOwnProperty('channels') === false) {
            // TODO: get all the channels that this sensor has
            channel_filter = function () { return true; };
        } else {
            channel_filter = function (channel_name) {
                for (c = 0; c < p.channels.length; c += 1) {
                    if (channel_name === p.channels[c]) {
                        return true;
                    }
                }
                return false;
            };
        }
        if (p.hasOwnProperty('annotations') === false) {
            p.annotations = false;
        }
        else {
            p.annotations = true;
        }

        // if (p.hasOwnProperty('events') === false) {
        //     p.events = false;
        // } else {
        //     throw new Error('loading events not yet implemented!');
        // }

        // TODO: change this so that we can load any of data, baseline, integral

        // check if we are getting the sensor(s) by id, user or group
        // throw an error if we get more than one option
        if (p.hasOwnProperty('sensor')) {
            // load the data by sensor id
            chained_load_readings = $.ajax({
                url: p.url + "sensor/" + p.sensor + "/"
            }).then(load_by_single_sensor);
        } else if (p.hasOwnProperty('group')) {
            console.log("Load group");
            // load the data by group
            //console.log('by group');
            chained_load_readings = $.ajax({
                url: p.url + "sensorGroup/" + p.group + '/'
            }).then(load_by_sensor_group);
        } else if (p.hasOwnProperty('user')) {
            // load the data by user id
            // this means getting all the sensors for this user
            //console.log('by user');
            chained_load_readings = $.ajax({
                url: p.url + "sensors/"
            }).then(load_by_user);
        } else {
            throw new Error('load called without sensor identifier (this must be sensor id, sensor group or user id)');
        }

        chained_load_readings.done(on_everything_loaded);
    };

    // export the API
    return {
        load: load_everything
    };
}());