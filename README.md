[![FOSSA Status](https://app.fossa.com/api/projects/git%2Bgithub.com%2FIndustryFusion%2Ffusionmqttdataservice.svg?type=shield&issueType=license)](https://app.fossa.com/projects/git%2Bgithub.com%2FIndustryFusion%2Ffusionmqttdataservice?ref=badge_shield&issueType=license)

# Fusion MQTT Data Service

This Python script facilitates the integration between a MQTT broker server and the PDT Gateway services by performing the following tasks:

1. Establishing a subscription with the MQTT broker topics.
2. Connecting to the PDT Gateway platform.
3. Fetching configuration details from provided configuration and data from the MQTT broker server.
4. Registering and continuously updating device properties on the PDT platform.

## Prerequisites

1. Python 3.8.10 or more.
2. Process Digital Twin is already setup either locally or in cloud. [https://github.com/IndustryFusion/DigitalTwin/blob/main/helm/README.md#building-and-installation-of-platform-locally]
3. Working MQTT publisher (Machine) and reciever (MQTT broker) in a central server.
4. The OISP agent must be started in the same system using Docker Container. Use the following command to start the OISP agent in local for development usage.

`docker run -d -e OISP_DEVICE_ID=<Device ID of the asset in PDT> -e OISP_DEVICE_NAME=<Device ID of the asset in PDT> -e OISP_GATEWAY_ID=<Device ID of the asset in PDT> -e OISP_DEVICE_ACTIVATION_CODE=<Activation code from the OISP account> -v /volume/config:/volume/config --security-opt=privileged=true --cap-drop=all -p 41234:41234 -p 7070:7070 <OISP agent docker image>`

OISP agent docker image must be built from here - [https://github.com/Open-IoT-Service-Platform/oisp-iot-agent/blob/development/Dockerfile]

To get the activation code, reach to the https://< PDT endpoint URL >/ui. Then, sign in with the relevant admin  credentials created in Keycloak i.e, https://< PDT endpoint URL >/auth, and then check account details page.

The above docker container also expects a config file with the name config.json located in the /volume/config folder of the host system for mounting. The contents of this file are as follows.

```json
 {
        "data_directory": "./data",
        "listeners": {
                "rest_port": 8000,
                "udp_port": 41234,
                "tcp_port": 7070
        },
        "receivers": {
                "udp_port": 41235,
                "udp_address": "127.0.0.1"
        },
        "logger": {
                "level": "info",
                "path": "/tmp/",
                "max_size": 134217728
        },
        "connector": {
                "rest": {
                        "host": "PDT URL",
                        "port": 443,
                        "protocol": "https",
                        "strictSSL": false,
                        "timeout": 30000,
                        "proxy": {
                                "host": false,
                                "port": false
                        }
                },
                "mqtt": {
                        "host": "PDT URL",
                        "port": 8883,
                        "websockets": false,
                        "qos": 1,
                        "retain": false,
                        "secure": true,
                        "retries": 5,
                        "strictSSL": false,
                        "sparkplugB": true,
                        "version": "spBv1.0"        
                }
        }
    }
```

Update the "host" variable with the correct PDT URL. Also, if the PDT is running locally in the network, and the REST based connector is desired, update the REST port to 80 and protocol to 'http'.


## Local Setup

From the root directory of this project run the below commands to install and activate venv. For the econd time, just use the activate command.

**To install venv**

`python3 -m venv .venv`

**To activate**

`source .venv/bin/activate`

**Install required modules**

`pip3 install -r requirements.txt`

**Run the project (export environment varibales first as shown below)**

`export OISP_API_ROOT="https://<PDT URL>/oisp/v1/api"`

`export USERNAME=<Username from PDT Keycloak>`

`export PASSWORD=<Passowrd from PDT Keycloak>`

`export OISP_DEVICE_ID=<Device ID of the asset in PDT - Scorpio API to which the data must be sent>`

Example: "urn:ngsi-ld:assetv5:2:46"


`export OISP_URL=<URL of the OISP Agent>`

Example: "127.0.0.1", if the agent is started in local as mentioned in the prerequisites. Or a valid DNS or IP from the cloud.


`export OISP_PORT="7070"`

`export BROKER_URL=<URL of the central MQTT Broker>`

Example: "192.168.189.186".


`export BROKER_PORT="1883"`

`export SLEEP=<Explicit Sleep, if needed, or else keep this blank>`

Also, the fusion MQTT service expects a config file with the name config.json in the 'resources' folder in the root project folder containing MQTT topic and selector keys, PDT device property names as shown below in the example.

```json
{
    "fusionmqttdataservice": {
        "specification": [
            {
                "topic": "kjellberg/plasma/Q-Series/Q-4500/system/status/qunit/json",
                "key": ["DEVICE_STATUS"],
                "parameter": ["power-source-v0.1-power-source-runtime-machine-state"]
            },
            {
                "topic": "some topic name",
                "key": ["some key"],
                "parameter": ["some PDT property name"]
            }
        ]
    }
}
```

**Run the service**

`python src/main.py`


## Docker build and run

To build this project using Docker and run it, follow the below instructions.

From the root project folder.

`docker build -t <image name> .`

`docker run -d -e OISP_API_ROOT="https://<PDT URL>/oisp/v1/api" -e USERNAME=<Username from PDT Keycloak> -e PASSWORD=<Passowrd from PDT Keycloak> -e OISP_DEVICE_ID=<Device ID of the asset in PDT - Scorpio API to which the data must be sent> -e OISP_URL=<URL of the OISP Agent> -e OISP_PORT=7070 -e BROKER_URL=<URL of the central MQTT Broker> -e BROKER_PORT="1883" -e SLEEP=<Explicit Sleep, if needed, or else keep this blank> -v <config file path>:resources/config.json`