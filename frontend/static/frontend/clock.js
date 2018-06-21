    // Update server time
    var serverTime = null;
    var getServerTime = function() {
        $.getJSON('/server/time/', function(datetime) {
            serverTime = moment.utc(datetime.ts);
        });
    };  
    getServerTime();  
    setInterval(getServerTime, 1000 * 60);
    setInterval(function() {
        $('#serverDate').html(serverTime.local().format('MMMM Do YYYY,'));
        $('#serverTime').html(serverTime.local().format('h:mm:ss a'));
        serverTime.add(1,'s');
    }, 1000);