try:
    import serial
except ImportError:
    raise ImportError('Please install `pyserial` with `pip install pyserial`.')
import json
import os
import re
import time
import urllib.error
import urllib.request
from serial.tools import list_ports

BASE_URL              = os.environ.get('BASE_URL', 'https://backend.brydge.dev')
BRYDGE_SECRET_API_KEY = os.environ.get('BRYDGE_SECRET_API_KEY')
DEVICE_NAME           = os.environ.get('DEVICE_NAME', 'test-device')
USER_ID               = os.environ.get('USER_ID', 'test-user')
INTERACTION           = os.environ.get('INTERACTION', 'test-interaction')
KEY_FILENAME          = 'server_provisioning_key.pem'
BAUD_RATE             = 115200
SERIAL_PORT           = os.environ.get('SERIAL_PORT')

BRYDGE_TEXT = '''
 __   __       __   __   ___     ___    __                   __   ___ 
|__) |__) \ / |  \ / _` |__     |__  | |__)  |\/| |  |  /\  |__) |__  
|__) |  \  |  |__/ \__> |___    |    | |  \  |  | |/\| /~~\ |  \ |___ 
                                                                      
                                                                          
=========================================================================
hello@brydge.dev

Brydge is an IoT protocol that enables interactive smart devices
powered by Bluetooth Low Energy (BLE) to leverage the benefits
of the cloud.

Documentation: https://docs.brydge.dev
=========================================================================
'''

CONFIG_TEXT = '''
 __   __        ___    __        __          __          __        __      __   ___         __   ___ 
/  ` /  \ |\ | |__  | / _` |  | |__) | |\ | / _`    \ / /  \ |  | |__)    |  \ |__  \  / | /  ` |__  
\__, \__/ | \| |    | \__> \__/ |  \ | | \| \__>     |  \__/ \__/ |  \    |__/ |___  \/  | \__, |___ 
'''

SUCCESS_TEXT = '''
 __   ___       __         ___  __      __               __  
|__) |__   /\  |  \ \ /     |  /  \    |__) |  | | |    |  \ 
|  \ |___ /~~\ |__/  |      |  \__/    |__) \__/ | |___ |__/ 
'''


class BColors:
    HEADER = '\033[95m'
    OK_BLUE = '\033[94m'
    OK_CYAN = '\033[96m'
    OK_GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def color_debug(*args):
    msg = ''.join(args)
    print(f'{BColors.WARNING}{msg}{BColors.ENDC}')


def color_fail(*args):
    msg = ''.join(args)
    print(f'{BColors.FAIL}{msg}{BColors.ENDC}')


def color_green(*args):
    msg = ''.join(args)
    print(f'{BColors.OK_GREEN}{msg}{BColors.ENDC}')


class Error(Exception):
    def __init__(self, message):
        super().__init__(BColors.FAIL + message + BColors.ENDC)


class BrydgeSetupException(Error):
    pass


if not os.path.isfile(KEY_FILENAME):
    raise BrydgeSetupException(
        f'There is no key file at {KEY_FILENAME}. '
        f'Please download from your email and place in this directory.')


if not os.environ.get('BRYDGE_SECRET_API_KEY'):
    raise BrydgeSetupException(f'Please set the environment variable BRYDGE_SECRET_API_KEY')


def clean_serial(input):
    return input.replace('>', '').rstrip()


# use urllib so there's no dependencies
def send_request(url, method, payload):
    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': BRYDGE_SECRET_API_KEY,
        'Accept': '*/*'
    }
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url=url, data=data, headers=headers, method=method)
    print(data)
    try:
        with urllib.request.urlopen(req) as response:
            res_data = response.read().decode('utf-8')
            print(res_data)
            handle_response(response.status, res_data)
    except urllib.error.HTTPError as e:
        res_data = e.read().decode('utf-8')
        handle_response(e.code, res_data)


def handle_response(status_code, response_data):
    if status_code in [409, 200, 201]:
        print('Success:', response_data)
    else:
        print('Error:', response_data)

port = list(list_ports.comports())
for p in port:
    print(p.device)
    if 'usbserial' in p.device and not SERIAL_PORT:
        SERIAL_PORT = p.device

ser = serial.Serial(SERIAL_PORT, BAUD_RATE)

color_green(BRYDGE_TEXT)

# send a command to the ESP32
ser.write(b'help\r\n')
time.sleep(0.5)
response1 = ser.read_all().decode('utf-8')
if not response1.strip():
    raise BrydgeSetupException(
        'Try replugging in your board, plugging into a different USB port, '
        'or close any other serial outputs (such as the ESP-IDF VSCode window)'
    )
if 'invalid header' in response1:
    raise BrydgeSetupException(
        'Your board has not been provisioned yet. Please flash your board using the '
        'one click firmware bundle, esptool directly, or ESP-IDF.'
    )
print('All Available ESP32 Commands:', response1)

ser.write(b'brydge_version\r\n')
time.sleep(0.1)
response2 = ser.read_all().decode('utf-8')
color_green('Device: Checking Brydge Version')
print(clean_serial(response2))

color_green(f'{CONFIG_TEXT}')

ser.write(bytes(f'get_pub_key \r\n', 'utf-8'))
time.sleep(5)
response_device_provisioning_key = ser.read_all().decode('utf-8')
device_provisioning_key_stripped = response_device_provisioning_key.replace('>', '').rstrip()


def find_key_regex(in_str):
    return re.search(r'(-----BEGIN PUBLIC KEY-----(\n|\r|\r\n)([0-9a-zA-Z\+\/=]{64}(\n|\r|\r\n))*([0-9a-zA-Z\+\/=]{1,63}(\n|\r|\r\n))?-----END PUBLIC KEY-----)|(-----BEGIN PRIVATE KEY-----(\n|\r|\r\n)([0-9a-zA-Z\+\/=]{64}(\n|\r|\r\n))*([0-9a-zA-Z\+\/=]{1,63}(\n|\r|\r\n))?-----END PRIVATE KEY-----)', in_str)[0]


try:
    device_provisioning_key = find_key_regex(device_provisioning_key_stripped)
except TypeError:
    raise BrydgeSetupException(
        'Try replugging in your board, plugging into a different USB port, '
        'or close any other serial outputs (such as the ESP-IDF VSCode window)'
    )
color_green('Device: Received Device Provisioning Key\n')
print(device_provisioning_key)

color_green('API: Creating Interaction')
send_request(
    f'{BASE_URL}/api/v1/interactions',
    'POST',
    {
        'interactionId': INTERACTION,
        'name': INTERACTION,
        'commands': [
            {
                'data': 'payload'
            }
        ]
    }
)

color_green('API: Creating User')
send_request(
    f'{BASE_URL}/api/v1/users',
    'POST',
    {
        'userId': USER_ID
    }
)

color_green('API: Updating User with Interaction')
send_request(
    f'{BASE_URL}/api/v1/users/{USER_ID}/interactions',
    'POST',
    {
        'interactionId': INTERACTION,
        'deviceId': DEVICE_NAME,
        'ttl': 300000
    }
)

color_green('API: Creating Device')
send_request(
    f'{BASE_URL}/api/v1/devices',
    'POST',
    {
        'deviceId': DEVICE_NAME,
        'deviceProvisioningKey': device_provisioning_key
    }
)

color_green('API: Updating Device with Device Provisioning Key')
send_request(
    f'{BASE_URL}/api/v1/devices/{DEVICE_NAME}',
    'PATCH',
    {
        'deviceProvisioningKey': device_provisioning_key
    }
)

color_green('API: Uploading Interactions to Device')
send_request(
    f'{BASE_URL}/api/v1/devices/{DEVICE_NAME}/interactions',
    'POST',
    {
        'interactionIds': [
            INTERACTION
        ]
    }
)

color_green('API: Checking tokens to ensure Mobile SDK will work correctly')
send_request(
    f'{BASE_URL}/api/v1/users/{USER_ID}/tokens',
    'POST',
    {}
)

ser.write(bytes(f'set_device_id {DEVICE_NAME}\r\n', 'utf-8'))
time.sleep(0.1)
response3 = ser.read_all().decode('utf-8')
color_green('Device: Successfully Set Device ID:\n')
print(clean_serial(response3))

print(f'Device: Loading Server Key from {KEY_FILENAME}')

with open(KEY_FILENAME, 'r') as f:
    KEY = f.read().replace('\n', '\\n')
    print(KEY)
    if KEY:
        color_green(f'Device: Successfully loaded Server Key from {KEY_FILENAME}')

ser.write(bytes(f'set_server_key {KEY}\r\n', 'utf-8'))
time.sleep(5)
response4 = ser.read_all().decode('utf-8')

color_green('Device: Successfully Set Server Key\n')
print(clean_serial(response4))

time.sleep(0.1)
ser.write(bytes(f'reboot\r\n', 'utf-8'))
color_green('Device: Rebooting: \n')
time.sleep(0.5)

color_green(f'{SUCCESS_TEXT}')
print(f'Your device has been configured with your Server Provisioning Key and a Device called `{DEVICE_NAME}`')
print('Visit https://docs.brydge.dev for more information')

ser.close()
