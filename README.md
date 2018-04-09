# soundman
This is an SDStore based project designed for the collection of data over a RFM69 Radio network

![The original soundman](https://media.giphy.com/media/ehv46k6WpKW2Y/giphy.gif)

## Install locally

1. Create a python 3 environment using your favorite virtual environment manager.
2. Install the requirements using ```pip install -r requirements.txt```
3. Run ```python manage.py runserver``` to run locally

## Install remotely on Raspberry Pi

1. Run ```fab install_webserver -H raspberrypi.local``` to turn the pi into a webserver
2. Run ```fab setup_website -H raspberrypi.local``` to install the website
3. Run ```fab create_superuser -H raspberrypi.local``` to create a new user

To redploy the website e.g. after making changes to the code run ```fab redeploy -H raspberrypi.local```
