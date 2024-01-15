# This application uses the DBUS service to read BLE advertisements from the system
# The base code is borrowed from https://ukbaz.github.io/howto/python_gio_2.html
# 
#
import time
import logging
import codecs
from gi.repository import Gio, GLib, GObject

from typing import Any, Dict, Type

from decryptor import decrypt_aes_128_ctr_little_endian
from Devices import *


# DBus Information
bus_type = Gio.BusType.SYSTEM
BLUEZ_NAME = 'org.bluez'
ADAPTER_PATH = '/org/bluez/hci0'
PROP_IFACE = 'org.freedesktop.DBus.Properties'
ADAPTER_IFACE = 'org.bluez.Adapter1'
DEVICE_IFACE = 'org.bluez.Device1'

logging.basicConfig(level=logging.DEBUG)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('scan_app')


def create_variant(py_data):
    """
    convert python native data types to D-Bus variant types by looking up
    their type expected for that key.
    """
    type_lookup = {'Address': 's',
                   'AddressType': 's',
                   'Name': 's',
                   'Icon': 's',
                   'Class': 'u',
                   'Appearance': 'q',
                   'Alias': 's',
                   'Paired': 'b',
                   'Trusted': 'b',
                   'Blocked': 'b',
                   'LegacyPairing': 'b',
                   'RSSI': 'n',
                   'Connected': 'b',
                   'UUIDs': 'as',
                   'Adapter': 'o',
                   'ManufacturerData': 'a{qay}',
                   'ServiceData': 'a{say}',
                   'TxPower': 'n',
                   'ServicesResolved': 'b',
                   'WakeAllowed': 'b',
                   'Modalias': 's',
                   'AdvertisingFlags': 'ay',
                   'AdvertisingData': 'a{yay}',
                   'Powered': 'b',
                   'Discoverable': 'b',
                   'Pairable': 'b',
                   'PairableTimeout': 'u',
                   'DiscoverableTimeout': 'u',
                   'Discovering': 'b',
                   'Roles': 'as',
                   'ExperimentalFeatures': 'as',
                   }
    if py_data is None:
        return GLib.Variant('a{sv}', {})
    for k, v in py_data.items():
        py_data[k] = GLib.Variant(type_lookup[k], v)
    return GLib.Variant('a{sv}', py_data)


class BluezObjectManager(GObject.GObject):
    __gsignals__ = {
        'adapter-added': (GObject.SignalFlags.NO_HOOKS, None,
                          (str, GObject.TYPE_VARIANT)),
        'adapter-removed': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
        'device-added': (GObject.SignalFlags.NO_HOOKS, None,
                         (str, GObject.TYPE_VARIANT)),
        'device-removed': (GObject.SignalFlags.NO_HOOKS, None, (str,)),
    }

    def __init__(self) -> None:
        super().__init__()
        self._object_manager = Gio.DBusObjectManagerClient.new_for_bus_sync(
            bus_type,
            Gio.DBusObjectManagerClientFlags.DO_NOT_AUTO_START,
            BLUEZ_NAME,
            '/', None, None, None)

        self._object_manager.connect("object-added", self._on_object_added)
        self._object_manager.connect("object-removed", self._on_object_removed)

    def _on_object_added(self,
                         _object_manager: Gio.DBusObjectManager,
                         dbus_object: Gio.DBusObject) -> None:
        object_path = dbus_object.get_object_path()
        ifaces = [iface.get_interface_name()
                  for iface in dbus_object.get_interfaces()]
        if ADAPTER_IFACE in ifaces:
            prop_proxy = dbus_object.get_interface(PROP_IFACE)
            adapter_props = prop_proxy.GetAll('(s)', ADAPTER_IFACE)
#            logger.debug('adapter-added %s', object_path, adapter_props)
            self.emit('adapter-added', object_path, adapter_props)
        elif DEVICE_IFACE in ifaces:
            prop_proxy = dbus_object.get_interface(PROP_IFACE)
            dev_props = prop_proxy.GetAll('(s)', DEVICE_IFACE)
#            logger.debug('device-added %s : %s', object_path, dev_props)
            self.emit('device-added', object_path, create_variant(dev_props))

    def _on_object_removed(self,
                           _object_manager: Gio.DBusObjectManager,
                           dbus_object: Gio.DBusObject) -> None:
        object_path = dbus_object.get_object_path()
        ifaces = [iface.get_interface_name()
                  for iface in dbus_object.get_interfaces()]
        if ADAPTER_IFACE in ifaces:
#            logger.debug('adapter-removed %s : %s', object_path)
            self.emit('adapter-removed', object_path)
        elif DEVICE_IFACE in ifaces:
#            logger.debug('device-removed: %s', object_path)
            self.emit('device-removed', object_path)


def bluez_proxy(object_path, interface):
    """Return a BlueZ proxy object for the given D-Bus information"""
    return Gio.DBusProxy.new_for_bus_sync(
        bus_type=bus_type,
        flags=Gio.DBusProxyFlags.NONE,
        info=None,
        name=BLUEZ_NAME,
        object_path=object_path,
        interface_name=interface,
        cancellable=None)


def new_device_hndlr(proxy: BluezObjectManager,
                     object_path: str,
                     device_props: GObject.TYPE_VARIANT) -> None:
    """Event handler for New device has been detected with scan"""
    encryption_keys={"F9:D3:0B:95:3A:BD":"0fc8d1b686829cbd0e0a916d625a0c20","E0:24:7D:A0:29:35":"070c3f4774ac795d8066816c8e3102f6","F6:C7:97:B6:79:D4":"e205915d6a4b001fc2cb499972364b26","E0:79:E0:0D:17:59":"14ae2969d687e51b491f36bb5c1dbee7","CB:CD:8A:DE:C5:C7":"7828e04088d3e83af339ec4fd8a0e6da","D6:47:C3:80:79:3F":"77cb663d432bd92d12294e033ae7dd5f","F7:F8:AD:C6:25:6D":"aaed0bae17f58353f179c4d775dafa35","F5:22:27:CC:1B:52":"9df4f1292d3208225a713605d2c94f91","D1:A2:51:17:6E:B9":"14182c136c8a77a241872ca9949d93c9"}
    battery_map={"CB:CD:8A:DE:C5:C7":"HQ2217CCURN","D6:47:C3:80:79:3F":"HQ2233XHV4J","E0:24:7D:A0:29:35":"HQ2217CQG9H","E0:79:E0:0D:17:59":"HQ2217CMF9T","F6:C7:97:B6:79:D4":"HQ2217QFFTW","F7:F8:AD:C6:25:6D":"HQ2217C64JW"}
    props = device_props.unpack()
    address = props.get('Address')
    ManufacturerData = props.get('ManufacturerData')
    if address in encryption_keys:
#        logger.debug('New Device Handler: %s : %s', object_path, props)
        ManufacturerData_hex = ''.join(f'{i:02x}' for i in ManufacturerData[737])
#              f'Removing from BlueZ cache')
#        print(f'  ManufacturerData is {ManufacturerData[737]}  type:', type(ManufacturerData[737]))
#        print(f'  ManufacturerData is ', ''.join(f'{i:02x}' for i in ManufacturerData[737]))
# adapter.RemoveDevice('(o)', GLib.Variant.new_object_path(object_path))
#        print('  ManufacturerData_Hex ',ManufacturerData_hex, ' type ',type(ManufacturerData_hex))
        length = len(ManufacturerData_hex)
        encrypted_hex=ManufacturerData_hex[16:length]
        encrypted=bytes.fromhex(ManufacturerData_hex[16:length])
#        print(f'Device with address {address} found. ManufacturerData in hex is:', ManufacturerData_hex)
        akey = bytes.fromhex(encryption_keys[address])
        # NOTE!!! IV bytes are flipped from the broadcast string and then the counter is decremented by 1 as the decrypt function increments before use
        iv = int(ManufacturerData_hex[12:14] + ManufacturerData_hex[10:12],16) - 1
#        print('  Raw IV is ', hex(iv), ' integer version is ', iv, ' ByteSwapped version is ', ManufacturerData_hex[12:14] + ManufacturerData_hex[10:12])
#        print(f'      Encrypted Data is {encrypted.hex()} and key is {encryption_keys[address]} and iv is {iv}') 
        ciphertext_chunks = [encrypted]
        for plaintext in decrypt_aes_128_ctr_little_endian(akey,iv, ciphertext_chunks):
#             print(f'{address},', ManufacturerData_hex,',',codecs.encode(plaintext,"hex"))
             devicer="No matching decoder"
             if (ManufacturerData_hex[2:6] =="0289"):
                 devicer=BatteryMonitor(battery_map[address])
                 devicer.parse_hex(codecs.encode(plaintext,"hex"))
                 BLE_data.update(address:devicer)
#                 print(f'{int(time.time())}, {address},{battery_map[address]},{devicer}')
                     
             if (ManufacturerData_hex[2:6] =="00ee"):
                 devicer = Smart_Lithium(address)
                 devicer.parse_hex(codecs.encode(plaintext,"hex"))
                 BLE_data.update(address:devicer)
#                 print(f'{int(time.time())}, {address},{battery_map[address]},{devicer}')
#             print('     Decrypted text in hex: ', codecs.encode(plaintext,"hex"))
#    else:
#        print(f'Device with address {address} not in the list of known keys')
        if (int(time.time()) - lastlog > 60):
            print(BLE_data)
            BLE_data={}
            lastlog = int(time.time()
    adapter.RemoveDevice('(o)', object_path)
    

def stop_scan():
    """Stop scanning for new devices and quit event loop"""
    logger.info('Stopping Discovery')
    adapter.StopDiscovery()
    mainloop.quit()
    return False


if __name__ == '__main__':
    # setup dbus
    mngr = BluezObjectManager()
    adapter = bluez_proxy(ADAPTER_PATH, ADAPTER_IFACE)
    disco_filters = adapter.GetDiscoveryFilters()
    lastlog=0
    BLE_data={}
#    print(disco_filters)
    # Link device-added event to callback function
    mngr.connect('device-added', new_device_hndlr)
    # Start discovering (scanning) for devices
    adapter.StartDiscovery()

    # Enable eventloop for notifications
    mainloop = GLib.MainLoop()
    # Create a timed event to call the stop_scan function
    GLib.timeout_add_seconds(interval=60, function=stop_scan)

    print('Starting BLE monitoring')
    try:
        mainloop.run()
    except KeyboardInterrupt:
        mainloop.quit()
        adapter.StopDiscovery()
