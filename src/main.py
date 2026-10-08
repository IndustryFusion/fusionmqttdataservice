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

# Subscribes to the configured MQTT topics and sends the values to the IFF
# agent. Values are sent as received; what they mean for the digital twin is
# decided only by the transform rules from Factory Manager (see transform.py).

import json
import logging
import os
import socket
import time
from urllib.parse import urlparse

import paho.mqtt.client as mqtt
import yaml

from transform import Transformer

logger = logging.getLogger('fusionmqttdataservice')

# Messages per UDP datagram; keeps each datagram far below the UDP size limit
BATCH_SIZE = 50

MISSING = object()


class AgentSender:
    """Sends to the IFF agent over UDP: one datagram is one JSON array, so
    messages can never run together the way they can on the TCP listener."""

    def __init__(self, host, port):
        self.address = (host, port)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, values):
        messages = [{'n': parameter, 'v': value, 't': 'Property'} for parameter, value in values]
        for start in range(0, len(messages), BATCH_SIZE):
            batch = messages[start:start + BATCH_SIZE]
            try:
                self.sock.sendto(json.dumps(batch).encode('utf-8'), self.address)
            except OSError as e:
                logger.warning('Could not send to the IFF agent at %s:%s: %s', *self.address, e)
                return
            logger.debug('Sent %s', batch)


def lookup(document, path):
    """The value at a path of keys (and list indexes) in a JSON document, or MISSING."""
    value = document
    for part in path:
        if isinstance(value, dict) and part in value:
            value = value[part]
        elif isinstance(value, list) and part.lstrip('-').isdigit() and -len(value) <= int(part) < len(value):
            value = value[int(part)]
        else:
            return MISSING
    return value


def readings(item, payload):
    """(parameter, value) for each parameter of a mapping that this message carries.

    Without keys the whole payload is the value of the first parameter. With
    keys the payload is JSON, and each key is a comma-separated path into it
    ("temperature", or "params,em:0,a_current"), paired with the parameter at
    the same position. A message that does not contain a key simply carries no
    value for that parameter: one topic often carries several kinds of message.
    """
    parameters = item.get('parameter') or []
    if isinstance(parameters, str):
        parameters = [parameters]
    keys = item.get('key') or []
    if not keys:
        return [(parameters[0], payload)] if parameters else []
    try:
        document = json.loads(payload)
    except ValueError:
        logger.debug('Message on %s is not JSON, so its keys cannot be read', item.get('topic'))
        return []
    found = []
    for key, parameter in zip(keys, parameters):
        value = lookup(document, [part.strip() for part in str(key).split(',')])
        if value is not MISSING:
            # Objects and lists are sent as JSON text
            found.append((parameter, json.dumps(value) if isinstance(value, (dict, list)) else value))
    return found


class Service:
    def __init__(self, specification, transformer, sender):
        self.specification = specification
        self.transformer = transformer
        self.sender = sender
        self.parameters = []
        for item in specification:
            parameters = item.get('parameter') or []
            for parameter in [parameters] if isinstance(parameters, str) else parameters:
                if parameter not in self.parameters:
                    self.parameters.append(parameter)

    def handle(self, topic, payload):
        """Transform and send the values one message carries."""
        values = []
        for item in self.specification:
            if not mqtt.topic_matches_sub(str(item['topic']), topic):
                continue
            for parameter, raw in readings(item, payload):
                value = self.transformer.convert(parameter, raw)
                if value is not None:
                    values.append((parameter, value))
        self.sender.send(values)

    def unreachable(self):
        """The machine cannot be read: send each rule's on_error value."""
        self.sender.send(self.transformer.error_values(self.parameters).items())

    # paho callbacks
    def on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            logger.warning('The broker refused the connection (result code %s)', rc)
            self.unreachable()
            return
        logger.info('Connected to the broker')
        # Subscribing here renews the subscriptions after every reconnect
        for item in self.specification:
            client.subscribe(str(item['topic']))

    def on_message(self, client, userdata, msg):
        try:
            self.handle(msg.topic, msg.payload.decode('utf-8', errors='replace'))
        except Exception:  # one bad message must not stop the client
            logger.exception('Could not handle a message on %s', msg.topic)

    def on_disconnect(self, client, userdata, rc):
        logger.warning('Disconnected from the broker (result code %s); reconnecting', rc)
        self.unreachable()


def load_config(path):
    with open(path) as f:
        service_config = yaml.safe_load(f)['fusionmqttdataservice']
    return service_config['specification'], Transformer(service_config.get('transforms'))


def main():
    logging.basicConfig(level=os.environ.get('LOG_LEVEL', 'INFO').upper(),
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')

    url = os.environ.get('PROTOCOL_URL', '')
    broker = urlparse(url if '//' in url else 'mqtt://' + url)
    agent = AgentSender(os.environ.get('IFF_AGENT_URL', '127.0.0.1'), int(os.environ.get('IFF_AGENT_UDP_PORT', '41234')))
    specification, transformer = load_config(os.environ.get('CONFIG_PATH', '../resources/config.yaml'))
    service = Service(specification, transformer, agent)
    logger.info('Listening to %d topic(s) on %s:%s', len(specification), broker.hostname, broker.port or 1883)

    # Time for the IFF agent in the same pod to come up before the first send
    time.sleep(float(os.environ.get('STARTUP_DELAY', '45')))

    client = mqtt.Client()
    client.on_connect = service.on_connect
    client.on_message = service.on_message
    client.on_disconnect = service.on_disconnect
    while True:
        try:
            client.connect(str(broker.hostname), int(broker.port or 1883), 60)
            break
        except OSError as e:
            logger.warning('Could not reach the broker: %s. Retrying in 5 seconds...', e)
            service.unreachable()
            time.sleep(5)
    # Reconnects by itself after a lost connection
    client.loop_forever()


if __name__ == '__main__':
    main()
