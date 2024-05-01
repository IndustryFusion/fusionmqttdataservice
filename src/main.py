#
# Copyright (c) 2023 IB Systems GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import paho.mqtt.client as mqtt
import os
import socket
import time
import yaml
import json

# Fetching all environment variables

for key, value in os.environ.items():
    if key.startswith('MQTT_BROKER_URI'):
        akri_broker_url = os.environ.get(key)

broker_url = akri_broker_url.split('//')[1].split(':')[0]
broker_port = akri_broker_url.split('//')[1].split(':')[1]
mqtt_username = os.environ.get('USERNAME')
mqtt_password = os.environ.get('PASSWORD')
oisp_url = os.environ.get('IFF_AGENT_URL')
oisp_port = os.environ.get('IFF_AGENT_PORT')

# Explicit sleep to wait for OISP agent to work
time.sleep(25)
           
iff_agent_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

iff_agent_socket.connect((str(oisp_url), int(oisp_port)))

# Opening JSON config file for MQTT - machine specific config from mounted path in runtime
f = open("../resources/config.yaml")
target_configs = yaml.safe_load(f)
f.close()

# Method to send the value of the MQTT topic to PDT with its property
def sendOispData(n, v):
    try:
        msgFromClient = '{"n": "' + n + '", "v": "' + str(v) + '", "t": "Property", "d": "' + n + '"}'
        iff_agent_socket.send(str.encode(msgFromClient))
        print("Sent data to OISP: " + n + " " + str(v))
        print(msgFromClient)
    except Exception as e:
        print(e)
        print("Could not send data to OISP")


# Method to parse the MQTT message on reception
def parse_mqtt_forward(topic, payload):
    print("Parsing MQTT message")
    print(topic)
    print(payload)
    for item in target_configs['fusionmqttdataservice']['specification']:
        time.sleep(0.5)
        if topic == str(item['topic']):
            if not item['key']:
                time.sleep(0.5)
                oisp_n = "http://www.industry-fusion.org/fields#" + item['parameter'][0]

                check = str(oisp_n).split("-")
                if "state" in check and (str(payload) != "0" or payload != False or str(payload) != "false" or str(payload) != "False" or str(payload) != "Idle" or str(payload) != "0.0" or str(payload) != "Offline"):
                    mqtt_value = 2
                elif "state" in check and (str(payload) == "0" or payload == False or str(payload) == "false" or str(payload) == "False" or str(payload) == "Idle" or str(payload) == "0.0" or str(payload) == "Offline"):
                    mqtt_value = 0
                else:
                    mqtt_value = str(payload)
                    mqtt_value = round(float(mqtt_value), 3)

                sendOispData(n=oisp_n, v=mqtt_value)

            elif item['key']:
                split_check = str(item['key'][0]).split(":")
                if len(split_check) > 1:
                    param_count = 0
                    for i in item['key']:
                        time.sleep(0.5)
                        oisp_n = "http://www.industry-fusion.org/fields#" + item['parameter'][param_count]
                        mqtt_value_json = json.loads(payload)

                        check = str(oisp_n).split("-")
                        if "state" in check and (str(mqtt_value_json[i]) != "0" or mqtt_value_json[i] != False or str(mqtt_value_json[i]) != "false" or str(mqtt_value_json[i]) != "False" or str(mqtt_value_json[i]) != "Idle" or str(mqtt_value_json[i]) != "0.0" or str(mqtt_value_json[i]) != "Offline"):
                            mqtt_value = 2
                        elif "state" in check and (str(mqtt_value_json[i]) == "0" or mqtt_value_json[i] == False or str(mqtt_value_json[i]) == "false" or str(mqtt_value_json[i]) == "False" or str(mqtt_value_json[i]) == "Idle" or str(mqtt_value_json[i]) == "0.0" or str(mqtt_value_json[i]) == "Offline"):
                            mqtt_value = 0
                        else:
                            try:
                                real_var = str(i).split(":")
                                mqtt_value = mqtt_value_json[real_var[0]][real_var[1]] 
                                mqtt_value = round(float(mqtt_value), 3)
                            except Exception as e:
                                print(e)

                        param_count += 1
                    
                        sendOispData(n=oisp_n, v=mqtt_value)

                else:
                    param_count = 0
                    for i in item['key']:
                        time.sleep(0.5)
                        oisp_n = "http://www.industry-fusion.org/fields#" + item['parameter'][param_count]
                        mqtt_value_json = json.loads(payload)

                        check = str(oisp_n).split("-")
                        if "state" in check and (str(mqtt_value_json[i]) != "0" or mqtt_value_json[i] != False or str(mqtt_value_json[i]) != "false" or str(mqtt_value_json[i]) != "False" or str(mqtt_value_json[i]) != "Idle" or str(mqtt_value_json[i]) != "0.0" or str(mqtt_value_json[i]) != "Offline"):
                            mqtt_value = 2
                        elif "state" in check and (str(mqtt_value_json[i]) == "0" or mqtt_value_json[i] == False or str(mqtt_value_json[i]) == "false" or str(mqtt_value_json[i]) == "False" or str(mqtt_value_json[i]) == "Idle" or str(mqtt_value_json[i]) == "0.0" or str(mqtt_value_json[i]) == "Offline"):
                            mqtt_value = 0
                        else:
                            try:
                                mqtt_value = mqtt_value_json[i]
                                mqtt_value = round(float(mqtt_value), 3)
                            except Exception as e:
                                print(e)

                        param_count += 1
                    
                        sendOispData(n=oisp_n, v=mqtt_value)


# Callback method for successful connection
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    for item in target_configs['fusionmqttdataservice']['specification']:
        client.subscribe(item['topic'])


# The callback for when a PUBLISH message is received from the server.
def on_message(client, userdata, msg):
    print(msg.payload.decode())
    parse_mqtt_forward(msg.topic, msg.payload.decode('utf-8'))


if __name__ == "__main__":

    client = mqtt.Client()

    time.sleep(20)

    # Callback method initialization
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(str(broker_url), int(broker_port), 60)

    client.loop_forever()