# soundman
This is an SDStore based project designed for the collection of data over a RFM69 Radio network

![The original soundman](https://media.giphy.com/media/ehv46k6WpKW2Y/giphy.gif)

## Setup 
Weather you are want to run this project locally or deploy to a Raspberry Pi there are a few steps we need to complete.

1. Create a python 3 environment on your local machine using your favourite virtual environment manager e.g. using Anaconda: 
```
conda create --name soundman
```
2. Activate the environment e.g. using Anaconda: 
```
source activate soundman
```
3. Clone this repository to a location of your choice.
```
cd /path/to/save/location/
git clone https://github.com/jkittley/soundman.git 
```

4. Open the newly created folder:
```
cd soundman
```
5. Install the requirements:
```
pip install -r requirements.txt
```

This will install everything we need to run the project locally and deploy to a remote Raspberry PI.

## Run locally
If you want to run the project locally then you need to tell Django that the project is on a local machine. You can do this by creating a environmental variable before you run the server:

```
export LOCAL=1 & python manage.py runserver
```

## Deploy to remote Raspberry Pi

1. The first command will turn your Raspberry Pi into a webserver.
```
fab install_webserver -H raspberrypi.local
``` 
2. Now we need to upload the Soundman website for the first time.
```
fab setup_website -H raspberrypi.local
``` 
3. Next we need to create a Amin user so we can login and make changes.
```
fab create_superuser -H raspberrypi.local
```
## Deploy changes to remote Raspberry Pi
If you make changes to the code and want to redeloy them to the Raspberry pi you can use the following command. It will copy accross the source files and reboot all the nessesary services automatically.
```
fab redeploy -H raspberrypi.local
```
