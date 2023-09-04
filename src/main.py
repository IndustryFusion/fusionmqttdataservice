import json
import paho.mqtt.client as mqtt
import os
import socket
import time
import oisp

OISP_API_ROOT = os.environ.get('OISP_API_ROOT')
USERNAME = os.environ.get('USERNAME')
PASSWORD = os.environ.get('PASSWORD')
device_id = os.environ.get('OISP_DEVICE_ID')
broker_url = os.environ.get('BROKER_URL')
broker_port = os.environ.get('BROKER_PORT')
oisp_url = os.environ.get('OISP_URL')
oisp_port = os.environ.get('OISP_PORT')
sleepInp = os.environ.get('SLEEP')
oisp_client = oisp.Client(api_root=OISP_API_ROOT)
oisp_client.auth(USERNAME, PASSWORD)

time.sleep(25)
time.sleep(int(sleepInp))
           
oisp_agent_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#client = Client(opc_url + ":" + opc_port)

#client.connect()
oisp_agent_socket.connect((str(oisp_url), int(oisp_port)))
#root = client.get_root_node()

# Opening JSON file
f = open("../resources/config.json")
target_configs = json.load(f)
f.close()

def registerComponent(n, t):
    try:
        msgFromClient = '{"n": "' + n + '", "t": "' + t + '"}'
        print(msgFromClient)
        oisp_agent_socket.send(str.encode(msgFromClient))
        print("Registered component to OISP: " + n + " " + t)
    except Exception as e:
        print(e)
        print("Could not register component to OISP")


def sendOispData(n, v):
    try:
        msgFromClient = '{"n": "' + n + '", "v": "' + str(v) + '"}'
        oisp_agent_socket.send(str.encode(msgFromClient))
        print("Sent data to OISP: " + n + " " + str(v))
        print(msgFromClient)
    except Exception as e:
        print(e)
        print("Could not send data to OISP")


def parse_mqtt_forward(topic, payload):
    print("Parsing MQTT message")
    print(topic)
    print(payload)
    for item in target_configs['fusionmqttdataservice']['specification']:
        time.sleep(0.5)
        if topic == str(item['topic']):
            if not item['key']:
                time.sleep(0.5)
                oisp_n = "Property/http://www.industry-fusion.org/fields#" + item['parameter'][0]

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
                        oisp_n = "Property/http://www.industry-fusion.org/fields#" + item['parameter'][param_count]
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
                        oisp_n = "Property/http://www.industry-fusion.org/fields#" + item['parameter'][param_count]
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

    accounts = oisp_client.get_accounts()
    account = accounts[0]
    devices = account.get_devices()
    
    for j in range(len(devices)):
        if str(device_id) == str(devices[j].device_id):
            device = devices[j]
            print(device.components)
            for components in device.components:
                print("Deleting component: " + components['cid'])
                time.sleep(2)
                device.delete_component(components['cid'])


    for item in target_configs['fusionmqttdataservice']['specification']:
        for j in item['parameter']:
            oisp_n = "Property/http://www.industry-fusion.org/fields#" + j
            oisp_t = "property.v1.0"
            registerComponent(oisp_n, oisp_t)
            time.sleep(10)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(str(broker_url), int(broker_port), 60)

    client.loop_forever()