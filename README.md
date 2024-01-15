#############################################################
# SmartLithium_BT

# Overview
The goal of this project is to retrieve the status information broadcast from Victron products via Bluetooth Low Energy (BLE) and 
store that data locally and/or in the future via DBUS (to allow logging to the Victron VRM Portal).  Specifically the project is 
capturing the data from the SmartLithium line of batteries.

Acknowledgements to: 
    kwindrem - for SetupHelper and applications that demonstrate it's use for installing apps to Victron Cerbo https://github.com/kwindrem/
    keshavdv - for victron-ble https://github.com/keshavdv/victron-ble which provided a reference for getting keys, decryption, and decoding of BLE
    

# BLE Advertisement
The Victron BLE protocol is documented here https://community.victronenergy.com/questions/187303/victron-bluetooth-advertising-protocol.html However, several 
important points are either missing or subtly mentioned.  From the cerbo command line you can use bluetoothctl to display the BLE advertisements.  

bluetoothctl scan on     - this command displays the bluetooth packets including the BLE Manufacturer Data advertisements we are interested in.
Discovery started
[CHG] Device F9:D3:0B:95:3A:BD ManufacturerData Value:
  10 02 89 a3 02 7e 32 0f d5 72 51 dc 74 52 2e 13  .....~2..rQ.tR..
  09 ec 63 4f cc 9a 73 
  
## Victron-BLE

The Victron-BLE project https://github.com/keshavdv/victron-ble was used as a reference through this initiative as they had a working version from a 
linux machine; however, there were too many external dependencies to run on the cerbo.

victron-ble -v read "1c085f9c-cabe-953f-d36e-037e9135a1d5@0fc8d1b686829cbd0e0a916d625a0c20"
DEBUG:victron_ble.scanner:Received data from 1c085f9c-cabe-953f-d36e-037e9135a1d5: 100289a3027e320fd57251dc74522e1309ec634fcc9a73
Decrypted data  b'ffff3f05000000000b2700000080fed4'
{
  "name": "SmartShunt HQ2120DJDNX",
  "address": "1C085F9C-CABE-953F-D36E-037E9135A1D5",
  "rssi": -95,
  "payload": {
    "aux_mode": "disabled",
    "consumed_ah": 0.0,
    "current": 2.498,
    "model_name": "SmartShunt 500A/50mV",
    "remaining_mins": 65535,
    "soc": 100.0,
    "voltage": 13.43
  }
}

The packet format is:
    Full packet hex: 100289a3027e320fd57251dc74522e1309ec634fcc9a73
    10      Manufacturer Data Type packet
    0289    Model - SmartShunt
    a3      Readout Type
    02      Record Type
    7e32    nonce for decryption (more accurately initial counter value)
    0f      First byte of the encryption key
    d57251dc74522e1309ec634fcc9a73 Encrypted payload of the BLE advertisement
    
    

# Decryption
The Victron BLE protocol is documented here https://community.victronenergy.com/questions/187303/victron-bluetooth-advertising-protocol.html    
I leveraged the work of keshavdv to retrieve the necessary decryption keys and the comments of Jake Baldwin to understand the decryption process.  
The encryption/decryption keys are generated when a new pin is generated, so the above examples are useful as they provide actual values; however, my keys
have been changed.  

A couple notes - the Victron process uses AES-128-CTR with a little endian counter.  Note that for the AES-CTR algorithm the counter value is 
incremented for each 16 byte chunk to be decrypted.  This allows a single block or byte to be decrypted without having to decrypt everything before as you would have to
do with a block cipher (AES-CTR is a stream cipher).  OpenSSL doesn't support the little endian counter by default, but since Victron currently only 
uses a single chunk (16 bytes) it is possible to perform a decryption by passing the IV value as a little endian representation.

    echo 'd57251dc74522e1309ec634fcc9a73' | xxd -r -plain | openssl enc -aes-128-ctr -d -nopad -nosalt -K 0fc8d1b686829cbd0e0a916d625a0c20 -iv 7e32 | xxd

    hex string is too short, padding with zero bytes to length
    00000000: ffff 3f05 0000 0000 0b27 0000 0080 fe    ..?......'.....

Note: the missing byte on the end is because I didn't pad the input string with 01 (repeating).  Since the bytes at the end are ignored and as a stream cipher it doesn't 
change the outcome I didn't pad the input text.

# Decoding the Advertisement
To pack as much data as possible Victron has efficiently used the bits in the advertisement; however, on the reading side this means some bit manipulation is required.  
Each element is little endian encoded.  Several projects have used the Construct Python module to facilitate decoding the advertisement, but to remove dependencies as much
as possible this project breaks the advertisement up with a more brute force approach.  Devices.py breaks the advertisement apart, changes from the little endian encoding, 
and applies any necessary math to the value.  The Victron document https://community.victronenergy.com/storage/attachments/48745-extra-manufacturer-data-2022-12-14.pdf describes
the contents of these advertisements.  Note, the document starts at bit 32, which is the first bit of the encrypted payload.  Also note that each value (for example a 
16 bit number) is little endian encoded in the string.  In our above example the decrypted string is ffff 3f05 0000 0000 0b27 0000 0080 fe for a SmartShunt which is decoded 
as a Battery monitor.  Signed integers are another trick.
    ffff = TTG
    3f05 = Battery voltage (but that is 0x053f big endian = 1343 / 100 = 13.43V)

# Future
This project eventually will be installed with PackageManager (see kwindrem SetupHelper https://github.com/kwindrem/SetupHelper ) and run as a service publishing to dbus.  

# Running 
Currently the project can simply be run from the commandline with "python3 BLE_monitor.py" output is to stdout.


