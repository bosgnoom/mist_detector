# Mist detector

This Python script will process a saved image from a webcam. 
Based on the brightness and variation in the ROI, the probability of 
a foggy situation will be determined.

After processing, the results are uploaded to a Google sheet (code included) 
using a POST request and to a local instance of Influx DB.

If there's doubt whether it is foggy outside, an image with values will 
be send to people using Signal's messaging service.

