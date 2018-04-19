Notes for MySQL indexing:

Run this on the newly created DB to ensure fast selection:


```
ALTER TABLE sd_store_sensorreading ADD KEY ix1(sensor_id, channel_id, timestamp, id, value);
```