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

$(function () {
    'use strict';
    var parameters;
    
    parameters = {
        url: server_url + 'sdstore/',
        start: new Date(2014, 11, 16, 14, 0),
        end: new Date(2014, 12, 2, 14, 0),
        user: true, // this means get the data by user (the user currently logged in)
        data: true, // this means get the readings (rather than the baseline or the integral)
        channels: ['temperature',],
        sampling_interval: 60*60
    };
    
    sd_store.dataloader.load(parameters, function (data) {
        console.log('data loaded! (by user)');
        // TODO: do something with the data
        console.log('data lenght (by user):', data.length);
    });
    
    parameters = {
            url: server_url + 'sdstore/',
            start: new Date(2014, 11, 16, 14, 0),
            end: new Date(2014, 12, 2, 14, 0),
            group: 1,
            data: true,
            sampling_interval: 60*60
        };
        
    sd_store.dataloader.load(parameters, function (data) {
        console.log('data loaded! (by sensor group)');
        // TODO: do something with the data
        console.log('data lenght (by sensor group):', data.length);
    });
        
    parameters = {
            url: server_url + 'sdstore/',
            start: new Date(2014, 11, 16, 14, 0),
            end: new Date(2014, 12, 2, 14, 0),
            sensor: 1,
            data: true,
            channels: ['temperature',],
            sampling_interval: 60*60
        };
        
    sd_store.dataloader.load(parameters, function (data) {
        console.log('data loaded! (by individual sensor)');
        // TODO: do something with the data
        console.log('data lenght (by individual sensor):', data.length);
    });
        
});
