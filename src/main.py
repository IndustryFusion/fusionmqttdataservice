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
target_configs = os.environ.get('TARGET_CONFIGS').split(",")
broker_url = os.environ.get('BROKER_URL')
broker_port = os.environ.get('BROKER_PORT')
oisp_url = os.environ.get('OISP_URL')
oisp_port = os.environ.get('OISP_PORT')

oisp_client = oisp.Client(api_root=OISP_API_ROOT)
oisp_client.auth(USERNAME, PASSWORD)

time.sleep(25)

oisp_agent_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#client = Client(opc_url + ":" + opc_port)

#client.connect()
oisp_agent_socket.connect((str(oisp_url), int(oisp_port)))
#root = client.get_root_node()


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
    for item in target_configs:
        time.sleep(1)
        if topic == str(item.split("|")[0]):
            mqtt_topic = item.split("|")[0]
            mqtt_variable = item.split("|")[1]
            oisp_n = item.split("|")[2]
            mqtt_value_json = json.loads(payload)

            if str(oisp_n) == "Property/http://www.industry-fusion.org/fields#status" and int(mqtt_value_json[mqtt_variable]) == 7:
                mqtt_value = 2

            elif str(oisp_n) == "Property/http://www.industry-fusion.org/fields#status":
                mqtt_value = 1
            else:
                mqtt_value = mqtt_value_json[mqtt_variable]
                mqtt_value = round(float(mqtt_value), 3)
        
            sendOispData(n=oisp_n, v=mqtt_value)


def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))
    # Subscribing in on_connect() means that if we lose the connection and
    # reconnect then subscriptions will be renewed.
    for item in target_configs:
        client.subscribe(item.split("|")[0])


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
            
    for item in target_configs:
        oisp_n = item.split("|")[2]
        oisp_t = item.split("|")[3]
        registerComponent(oisp_n, oisp_t)
        time.sleep(20)

    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(str(broker_url), int(broker_port), 60)

    client.loop_forever()