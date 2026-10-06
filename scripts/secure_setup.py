"""Create a private device configuration with unique credentials; never overwrite one."""
import argparse
import base64
from pathlib import Path
import re
import secrets
import yaml

from project import ROOT, devices


def create(device, name, root=ROOT):
    catalogue = {d['id']: d for d in devices(root)}
    if device not in catalogue or catalogue[device]['status'] == 'concept':
        raise ValueError('Choose a supported or experimental device; concepts have no implementation.')
    if not re.fullmatch(r'[a-z][a-z0-9-]{0,30}', name):
        raise ValueError('Use a name starting with a letter, with lowercase letters, digits and hyphens (max 31 characters).')
    destination = root / 'esphome/private' / name
    destination.mkdir(parents=True, exist_ok=False)
    credentials = {
        'wifi_ssid': 'CHANGE_ME',
        'wifi_password': 'CHANGE_ME',
        'api_encryption_key': base64.b64encode(secrets.token_bytes(32)).decode(),
        'fallback_ap_password': secrets.token_urlsafe(24),
    }
    remove_public_ota = '\n  - id: !remove ota_http_request' if device == 'bluetoothproxy' else ''
    config = f'''# Personal credentials are in the adjacent ignored secrets.yaml.
packages:
  device: !include ../../{device}.yaml

substitutions:
  device_name: "{name.replace('-', '_')}"

esphome:
  name: {name}
  name_add_mac_suffix: false

# A public firmware update would replace these personal credentials.
dashboard_import: !remove
wifi:
  ssid: !secret wifi_ssid
  password: !secret wifi_password
  ap:
    password: !secret fallback_ap_password
api:
  encryption:
    key: !secret api_encryption_key
ota:
  - platform: esphome
    encryption:{remove_public_ota}
safe_mode:
'''
    if device == 'bluetoothproxy':
        config += '''
update: !remove
http_request: !remove
button:
  - id: !remove check_for_update_button
'''
    (destination / 'secrets.yaml').write_text(yaml.safe_dump(credentials, sort_keys=False), encoding='utf-8')
    (destination / 'device.yaml').write_text(config, encoding='utf-8')
    print(f'Created {destination / "device.yaml"}. Set Wi-Fi in the adjacent secrets.yaml before flashing over USB.')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('device', choices=[d['id'] for d in devices() if d['status'] != 'concept'])
    parser.add_argument('--name', required=True, help='Unique name, for example living-room-luxmeter')
    args = parser.parse_args()
    create(args.device, args.name)
