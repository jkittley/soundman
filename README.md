# Sound System - Server
This repository is part of a larger project which brings together Raspberry PI's, SDStore, Arduino style microcontrollers, Smart phones, BLE and RFM69 radios, to create a sound level monitoring local area sensor network. In this repository you will find code to initialise and run a local Raspberry Pi based, SD-Store server. For more information see http://kittley.com.

![Example](_res/server.jpg)

## Setup 
Weather you are want to run this project locally or deploy to a Raspberry Pi there are a few steps we need to complete.

1. Create a python 3 environment on your local machine using your favourite virtual environment manager e.g. using Anaconda, and activate it: 

```
conda create --name soundsystem-server

source activate soundsystem-server
```

3. Clone this repository and open the folder.
```
cd /path/to/save/location/

git clone https://github.com/jkittley/soundsystem-server.git 

cd soundsystem-server
```

4. Install the required Python packages:

```
pip install -r requirements_local.txt
```

## Run locally
If you want to run the project locally then you need to tell Django that the project is on a local machine. You can do this by creating a environmental variable before you run the server:

```
export LOCAL=1 & python manage.py runserver
```

## Deploy to a remote Raspberry Pi
I am going to assume you have:

* A PI connected with a [clean install of Raspbian NOOBs](https://www.raspberrypi.org/documentation/installation/noobs.md)
* That is is [connected to local network](https://www.raspberrypi.org/documentation/configuration/wireless/) 
* Has the default hostname of "raspberrypi"
* [SSH is enabled](https://www.raspberrypi.org/documentation/remote-access/ssh/)
* **VERY IMPORTANT** You have [changed the default password](https://www.raspberrypi.org/documentation/linux/usage/users.md)

The following commands below will no doubt work on other versions of linux based operating systems, however we have not tested them. Also keep an eye on the progress of the following commands and be sure to correct any errors as they occur. If you need help then please [add an issue](https://github.com/jkittley/soundsystem-server/issues).

1. The first command will turn your Raspberry Pi into a webserver.
```
fab install_webserver -H raspberrypi.local
``` 
**Note:** If you get an error like this: "Fatal error: Host key for raspberrypi.local did not match pre-existing key!". You may need to remove a previously registered SSH key for the domain raspberrypi.local. Do do this run: `ssh-keygen -R raspberrypi.local`.

2. Now we need to upload the website for the first time.
```
fab setup_website -H raspberrypi.local
``` 
3. Next we need to create a Admin user so we can login and make changes.
```
fab create_superuser -H raspberrypi.local
```

## Making changes
The project is based on [Django](https://www.djangoproject.com/) and [SD-Store](https://bitbucket.org/ecostanza/sd_store/src/master/README.md). To make modifications you first should verse yourself in how to manipulate Django based websites and how to interact with SD-Store.

## Deploy changes to remote Raspberry Pi
Once you have made changes to the code, you will need to redeploy them to the Raspberry Pi server. The following command will copy across the source files and reboot all the necessary services automatically.

```
fab redeploy -H raspberrypi.local
```
