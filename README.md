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
4. The IFF IoT agent must be started in the same system using Docker Container. Use the following command to start the IFF IoT agent in local for development usage.

IFF IoT agent docker image must be built from here - [https://github.com/IndustryFusion/DigitalTwin/tree/main/NgsildAgent/Dockerfile]

`docker run -d -e DEVICE_ID=<Device ID of the asset in PDT> GATEWAY_ID=<Device ID of the asset in PDT> -e KEYCLOAK_URL=<PDT Keycloak URL> -e REALM_ID=iff -e REALM_USER_PASSWORD=<Password of Keycloak REALM_USER> -v /volume/config:/volume/config --security-opt=privileged=true --cap-drop=all -p 41234:41234 -p 7070:7070 <IFF IoT agent docker image>`

To get the REALM_USER_PASSWORD, run the following command on the PDT cluster.

`kubectl -n iff get secret/credential-iff-realm-user-iff -o jsonpath='{.data.password}'| base64 -d | xargs echo`

The above docker container also expects a config file with the name config.json located in the /volume/config folder of the host system for mounting. The contents of this file are as follows.

```json
 {
        "data_directory": "./data",
        "listeners": {
                "udp_port": 41234,
                "tcp_port": 7070
        },
        "logger": {
                "level": "info",
                "path": "/tmp/",
                "max_size": 134217728
        },
        "dbManager": {
                "file": "metrics.db",
                "retentionInSeconds": 3600,
                "housekeepingIntervalInSeconds": 60,
                "enabled": false
        },
        "connector": {
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

Update the "host" variable with the correct PDT URL.

## Local Setup

From the root directory of this project run the below commands to install and activate venv. For the econd time, just use the activate command.

**To install venv**

`python3 -m venv .venv`

**To activate**

`source .venv/bin/activate`

**Install required modules**

`pip3 install -r requirements.txt`

**Run the project (export environment varibales first as shown below)**

`export IFF_AGENT_URL=<URL of the IFF IoT Agent>`

Example: "127.0.0.1", if the agent is started in local as mentioned in the prerequisites. Or a valid DNS or IP from the cloud.

`export IFF_AGENT_PORT="7070"`


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
                "parameter": ["machine-state"]
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

`docker run -d -e IFF_AGENT_URL=<URL of the IFF IoT Agent> -e IFF_AGENT_PORT=7070 -e BROKER_URL=<URL of the central MQTT Broker> -e BROKER_PORT="1883" -e SLEEP=<Explicit Sleep, if needed, or else keep this blank> -v <config file path>:resources/config.json`