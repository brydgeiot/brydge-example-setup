# brydge-example-setup

Once you've signed up for Brydge, you will recieve an email with the subject "Your Brydge Platform API Link"

The setup script needs two things from that email:
- `BRYDGE_SECRET_API_KEY` environment variable to be set 
- `server_provisioning_key.pem` file in this directory

**NOTE:** ⚠️ Only Run this script after you've flashed your board with the VSCode ESP-IDF extension or our firmware tool included in the .zip.

```bash
export BRYDGE_SECRET_API_KEY={{ YOUR_BRYDGE_SECRET_API_KEY }}
python ./provisioning.py
```

It does quite a few things automatically for you such as creating an interaction, a user, handling the key exchange, and configuring your device.

### Manually

If you wanted to reproduce this setup flow manually, you might do this

- API: Create an Interaction `POST /api/v1/interactions`
- API: Create a User  `POST /api/v1/users`
- API: Add Interaction to a User `POST /api/v1/users/{userId}/interactions`
- Build and flash firmware with ESP-IDF or esptool
- Device: Set Server Provisioning Key over Serial `set_server_key public-brydge.1234abc341c2363277c84b9d.m.1234abcd-339a-48e1-b58f-0e4b28e9c011`
- Device: Get Device Provisioning Key on the Device over Serial `get_pub_key`
- Device: Set Device ID `set_device_id test-device`
- API: Create a first Device `POST /api/v1/devices`
- API: Get your first Device `POST /api/v1/devices/test-device`

## Troubleshooting

- If you have an issue with running this script or flashing your ESP32 board with the Brydge firmware, make sure it's connected directly to your computer. You can also manually change the `SERIAL_PORT` in the `provision.py` script if necessary. You also may experience issues using a USB hub or if other devices are connected at the same time, so unplug all other devices.

```bash
FileNotFoundError: [Errno 2] No such file or directory: '/dev/cu.usbserial-10'
```

- You may need to erase the flash of your board occasionally with `python -m esptool --chip esp32 erase_flash`

```bash
python -m esptool --chip esp32 erase_flash

# Erasing flash (this may take a while)...
# Chip erase completed successfully in 21.1s
# Hard resetting via RTS pin...
```

- It may take a few seconds the first time you flash your board. Generating the RSA key pair takes many seconds.

```bash
I (509) BrydgeApplication: No saved time in storage
W (509) BrydgeApplication: Reboot reason: power on

E (660) KeyValueStore: Error opening NVS partition: 0x1102

E (802) BrydgeApplication: Error loading app config: storage driver error
W (942) SPIFFS: mount failed, -10025. formatting...
I (1673) BrydgeApplication: Generating RSA key-pair, this might take a few seconds...
I (42665) BrydgeApplication: Key generation done
```

- Don't use incorrect serial commands through. If you need a reference, the board lists all available commands via `help`

```bash
# ✅︎ CORRECT
get_pub_key

# ❌ WRONG!!!!!
get_public_key
# Unrecognized command
```

- Don't use the public or secret keys when using `set_server_key`

```bash
# ✅︎ CORRECT
set_server_key -----BEGIN RSA PUBLIC KEY-----abcde12345==-----END RSA PUBLIC KEY-----
# Server key set

# ❌ WRONG!!!!!
set_server_key public-brydge.1234abc341c2363277c84b9d.m.1234abcd-339a-48e1-b58f-0e4b28e9c011
# Invalid number of arguments: args: 2
# arg 0: set_server_key
# Command returned non-zero error code: 0x1 (ERROR)
```

- If you incorrectly set your key, you may see these errors.

```bash
E (11315355) security:  failed
  ! mbedtls_pk_parse_public_keyfile returned -0x3b60

E (11315357) security:  failed
  ! mbedtls_pk_parse_public_keyfile returned -0x3b60

E (11315478) ledgerview: Ledger encryption failed
```