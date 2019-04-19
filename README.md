# gcal-stats

A [Flask](http://flask.pocoo.org/) web application that fetches Google Calendar event information and displays information about how you have been spending your time over the past year. 

Currently, no data is stored on the server, and there is no persistance layer.
The obvious next step would be to add a database to reduce API calls. 

There is a function to generate a word cloud based on the text within the events, but haven't yet implemented it within the app. 

cal_analyze.py handles calls to the API, reshapes the data into a useable form, and generates the plot

gcal_flask.py generates the app and handles authentication

Deployed on Heroku at https://frozen-basin-79689.herokuapp.com/

Started from here:
https://developers.google.com/api-client-library/python/auth/web-app

Requirements are listed in requirements.txt
