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

## Configuration

All settings come from environment variables. In a gateway deployment the
onboarding controller (iff-akri-controller) sets them from the Factory Manager
onboarding form.

| Variable | Meaning | Default |
|---|---|---|
| `PROTOCOL_URL` | MQTT broker, e.g. `mqtt://192.168.189.186:1883` | required |
| `IFF_AGENT_URL` | Host of the IFF IoT agent | `127.0.0.1` |
| `IFF_AGENT_UDP_PORT` | UDP port of the IFF IoT agent (`listeners.udp_port`) | `41234` |
| `CONFIG_PATH` | Path of the topic configuration | `../resources/config.yaml` |
| `STARTUP_DELAY` | Seconds to wait for the agent before connecting | `45` |
| `LOG_LEVEL` | `DEBUG` also logs every value sent | `INFO` |

`USERNAME` and `PASSWORD` are not used. The onboarding controller passes the
same pair to every data service in a pod, so they belong to the OPC-UA server
when both run together.

Values are sent to the agent over UDP, one JSON array per datagram.
`IFF_AGENT_PORT` (TCP) is no longer used.

The topic configuration (`config.yaml`) lists the topics to subscribe to and,
optionally, how to transform their values:

```yaml
fusionmqttdataservice:
  specification:
    - topic: "machine/status"            # no key: the whole payload is the value
      key: []
      parameter: ["https://industry-fusion.org/base/v0.1/machine_state"]
    - topic: "machine/data"              # keys: the payload is JSON
      key: ["temp", "mv"]
      parameter:
        - "https://industry-fusion.org/base/v0.1/temperature"
        - "https://industry-fusion.org/base/v0.1/voltage"
    - topic: "shellypro3em/events/rpc"   # a key can be a path: comma-separated
      key: ["params,em:0,a_current"]
      parameter: ["https://industry-fusion.org/base/v0.1/current"]
  transforms:
    version: 1
    rules:
      - parameter: "https://industry-fusion.org/base/v0.1/machine_state"
        map:
          cases:
            - { eq: "Running", out: "2" }
            - { eq: "Idle", out: "1" }
          fallback: { value: "0" }
        on_error: "0"                    # sent when the broker connection is lost
      - parameter: "https://industry-fusion.org/base/v0.1/voltage"
        linear: { factor: 0.001, offset: 0, decimals: 3, from: mV, to: V }
```

How the values are taken from a message:
- **No key:** the whole payload is the value of the first parameter.
- **Keys:** each key is paired with the parameter at the same position. A key is
  a path into the JSON payload; separate the levels with commas.
- **A missing key:** a message that does not contain a key carries no value for
  that parameter. One topic often carries several kinds of message.
- **Wildcards:** topics may use them (`plant/+/temp`).

## Value transforms

The service sends what it receives. It has no built-in knowledge of what any
property means. Every interpretation comes from `transforms`, which Factory
Manager writes from the "Value Transforms" step of its onboarding form. The
engine (`src/transform.py`) is the same as in the OPC-UA data service, and so
are its tests (`tests/transform_cases.json`). Change them in both places.

- **No rule:** the value is sent as received.
- **`map`:** cases are tried in order and the first match wins.
  - `eq` compares numbers numerically and text without regard to case or
    surrounding spaces.
  - `min`/`max` is an inclusive range.
  - `bit` matches when that bit of a whole, non-negative value is set.
  - If nothing matches, `fallback` decides: `drop` (send nothing), `raw` (send
    the value as received), or `{value: ...}`.
- **`linear`:** sends `value × factor + offset`, rounded half away from zero to
  `decimals`. With a `map` as well, the map runs first and its numbers are then
  converted.
- **`on_error`:** sent when the connection to the broker is lost or refused.
- **A rule that is not valid** drops its parameter's values and logs an error.

## Local Setup

```sh
python3 -m venv .venv
source .venv/bin/activate
pip3 install -r requirements.txt
export PROTOCOL_URL=mqtt://192.168.189.186:1883
export IFF_AGENT_URL=127.0.0.1
export CONFIG_PATH=$PWD/resources/config.yaml
export STARTUP_DELAY=0
python src/main.py
```

## Tests

The image runs Python 3.8, so run the tests there:

```sh
docker run --rm -v "$PWD":/work -w /work python:3.8 \
  sh -c 'pip install -q -r requirements.txt -r requirements-dev.txt && python -m pytest -q tests'
```

## Docker build and run

From the root project folder:

```sh
docker build -t <image name> .
docker run -d --network host -e PROTOCOL_URL=mqtt://<broker>:1883 -e IFF_AGENT_URL=127.0.0.1 \
  -v <config file path>:/resources/config.yaml <image name>
```
