#
# Copyright (c) 2026 IB Systems GmbH
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

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src'))

from main import Service, readings  # noqa: E402
from transform import Transformer  # noqa: E402

B = 'https://industry-fusion.org/base/v0.1/'
SHELLY = json.dumps({'src': 'shellypro3em', 'params': {'ts': 1, 'em:0': {'a_current': 1.25, 'a_voltage': 230.4}}})


def test_without_keys_the_payload_is_the_first_parameters_value():
    item = {'topic': 'm/relay1', 'key': [], 'parameter': [B + 'machine_state']}
    assert readings(item, 'on') == [(B + 'machine_state', 'on')]


def test_flat_keys_pair_with_parameters_by_position():
    item = {'topic': 'm/data', 'key': ['temp', 'speed'], 'parameter': [B + 'temperature', B + 'speed']}
    assert readings(item, '{"temp": 21.5, "speed": 3}') == [(B + 'temperature', 21.5), (B + 'speed', 3)]


def test_a_missing_key_does_not_shift_the_others():
    # The old service paired every key after a failed one with the wrong parameter
    item = {'topic': 'm/data', 'key': ['a', 'b', 'c'], 'parameter': [B + 'a', B + 'b', B + 'c']}
    assert readings(item, '{"a": 1, "c": 3}') == [(B + 'a', 1), (B + 'c', 3)]


def test_nested_paths_as_in_shelly_meters():
    item = {'topic': 'shelly/events/rpc', 'key': ['params,em:0,a_current', 'params,em:0,a_voltage'],
            'parameter': [B + 'current', B + 'voltage']}
    assert readings(item, SHELLY) == [(B + 'current', 1.25), (B + 'voltage', 230.4)]


def test_a_message_of_another_kind_carries_nothing():
    item = {'topic': 'shelly/events/rpc', 'key': ['params,em:0,a_current'], 'parameter': [B + 'current']}
    assert readings(item, '{"method": "NotifyStatus", "params": {"sys": {}}}') == []


def test_a_payload_that_is_not_json_carries_nothing_when_keys_are_set():
    item = {'topic': 'm/data', 'key': ['temp'], 'parameter': [B + 'temperature']}
    assert readings(item, 'not json') == []


def test_objects_and_lists_are_sent_as_json_text():
    item = {'topic': 'm/data', 'key': ['range'], 'parameter': [B + 'range']}
    assert readings(item, '{"range": [1, 2]}') == [(B + 'range', '[1, 2]')]


class FakeSender:
    def __init__(self):
        self.sent = []

    def send(self, values):
        self.sent.extend(list(values))


def service(spec, transforms=None):
    sender = FakeSender()
    return Service(spec, Transformer(transforms), sender), sender


def test_values_are_sent_as_received_without_rules():
    s, sender = service([{'topic': 'm/power', 'key': [], 'parameter': [B + 'power']}])
    s.handle('m/power', '12.34567')
    assert sender.sent == [(B + 'power', '12.34567')]


def test_no_built_in_machine_state_handling():
    # The old service sent 2 for any message on a "_state" parameter, and
    # machine_state 0 for anything that was not a number
    s, sender = service([{'topic': 'm/state', 'key': [], 'parameter': [B + 'machine_state']},
                         {'topic': 'm/mode', 'key': [], 'parameter': [B + 'mode']}])
    s.handle('m/state', 'Idle')
    s.handle('m/mode', 'Auto')
    assert sender.sent == [(B + 'machine_state', 'Idle'), (B + 'mode', 'Auto')]


def test_rules_from_factory_manager_are_applied():
    transforms = {'version': 1, 'rules': [
        {'parameter': B + 'machine_state', 'map': {'cases': [{'eq': 'Running', 'out': '2'}, {'eq': 'Idle', 'out': '1'}],
                                                   'fallback': {'value': '0'}}, 'on_error': '0'},
        {'parameter': B + 'voltage', 'linear': {'factor': 0.001, 'offset': 0, 'decimals': 3, 'from': 'mV', 'to': 'V'}}]}
    s, sender = service([{'topic': 'm/state', 'key': [], 'parameter': [B + 'machine_state']},
                         {'topic': 'm/data', 'key': ['mv'], 'parameter': [B + 'voltage']}], transforms)
    s.handle('m/state', 'Idle')
    s.handle('m/data', '{"mv": 230400}')
    assert sender.sent == [(B + 'machine_state', '1'), (B + 'voltage', '230.4')]


def test_wildcard_topics_match():
    s, sender = service([{'topic': 'plant/+/temp', 'key': [], 'parameter': [B + 'temperature']}])
    s.handle('plant/line1/temp', '21')
    s.handle('plant/line1/humidity', '40')
    assert sender.sent == [(B + 'temperature', '21')]


def test_unreachable_sends_only_on_error_values():
    transforms = {'version': 1, 'rules': [
        {'parameter': B + 'machine_state', 'map': {'cases': [], 'fallback': {'value': '2'}}, 'on_error': '0'}]}
    s, sender = service([{'topic': 'm/state', 'key': [], 'parameter': [B + 'machine_state']},
                         {'topic': 'm/power', 'key': [], 'parameter': [B + 'power']}], transforms)
    s.unreachable()
    assert sender.sent == [(B + 'machine_state', '0')]
