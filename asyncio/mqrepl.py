# MQTT Repl for MicroPython by Thorsten von Eicken (c) 2020
#
# Simple repl over MQTT, subscribes to a topic and feeds data received on that topic into the system
# repl. Collects output from the system repl and sends it out to another topic with up to 100ms
# delay in order to accumulate bytes into messages.
#
# Requires asyncio-based MQTT, i.e. mqtt_as
# Inspired by https://github.com/micropython/micropython/blob/master/examples/bluetooth/ble_uart_repl.py

import io, os, _thread
import uasyncio as asyncio

class MQTTRepl(io.IOBase):

    # Create a repl interface and start publishing repl output using the pub function passed as
    # argument. Pub must accept a byte buffer.
    def __init__(self):
        self.tx_buf = bytearray()
        self.rx_len = 0

    def input(self, msg):
        if self.rx_len == 0:
            self.rx_buf = io.BytesIO(msg)
            self.rx_len = len(msg)
        else:
            self.rx_buf.write(msg)
            self.rx_len += len(msg)
        print("input: rx_len={}".format(self.rx_len), _thread.get_ident())
        # Needed for ESP32 & ESP8266.
        if hasattr(os, 'dupterm_notify'):
            os.dupterm_notify(None)

    def read(self, sz=None):
        if self.rx_len == 0: return None
        got = self.buf.read(sz)
        self.rx_len -= len(got)
        print("read: rx_len={}".format(self.rx_len))
        return got

    def readinto(self, buf):
        if self.rx_len == 0: return None
        self.rx_len = 0
        print("readinto", _thread.get_ident())
        return self.rx_buf.readinto(buf)

    def ioctl(self, op, arg):
        if op == _MP_STREAM_POLL and self.rx_len > 0:
            return _MP_STREAM_POLL_RD
        return 0

    async def sender(self, pub):
        print("sender", _thread.get_ident())
        while True:
            while len(self.tx_buf) > 0:
                data = self.tx_buf[0:1024]
                self.tx_buf = self.tx_buf[1024:]
                await pub(data)
            await asyncio.sleep_ms(100)

    def write(self, buf):
        if buf[:4] == b'TADA': return
        self.tx_buf += buf
        #print("TADA:write({})->{}".format(len(buf), len(self.tx_buf)))

import board, machine, time
from mqtt_as import MQTTClient, config
import uasyncio as asyncio

print("\n===== esp32 mqttrepl `{}` starting at {} =====\n".format(board.location, time.time()))

TOPIC = 'esp32/' + board.location + '/repl'
REPL_IN = TOPIC + '/in'
REPL_OUT = TOPIC + '/out'

loop = asyncio.get_event_loop()
mqrepl = None
mqclient = None
outages = 0

# ===== asyncio and mqtt callback handlers

# pulse blue LED
async def pulse():
    board.blue_led(True)
    await asyncio.sleep_ms(100)
    board.blue_led(False)

# handle the arrival of an MQTT message
def sub_cb(topic, msg, retained):
    topic = str(topic, 'utf-8')
    print("MQTT:", (topic, msg))
    loop.create_task(pulse())
    if topic == REPL_IN:
        if mqrepl is not None:
            mqrepl.input(msg)
        return

async def wifi_cb(state):
    board.wifi_led(not state)  # Light LED when WiFi down
    if state:
        print('WiFi connected')
    else:
        global outages
        outages += 1
        print('WiFi or broker is down')

async def conn_cb(client):
    print('MQTT connected')
    await client.subscribe(REPL_IN, 1)
    print("Subscribed to", REPL_IN)

# ===== REPL helpers

async def repl_pub(buf):
    await mqclient.publish(REPL_OUT, buf, qos=0)

# ===== main loop

async def main():
    global mqclient
    # get an initial connection
    board.blue_led(True)
    try:
        await mqclient.connect()
    except OSError:
        print('Connection failed')
        return
    # Start repl
    global mqrepl
    mqrepl = MQTTRepl()
    loop.create_task(mqrepl.sender(repl_pub))
    await asyncio.sleep_ms(10)
    os.dupterm(mqrepl, 0)
    await asyncio.sleep_ms(10)
    # TODO: wait for time sync
    # launch tasks
    #loop.create_task(query_sensors(client))
    #loop.create_task(poll_uarts(client))
    # play watchdog
    while True:
        print("Still running...")
        await asyncio.sleep(10)

# Start MQTT (and Wifi)
config['subs_cb'] = sub_cb
config['wifi_coro'] = wifi_cb
config['connect_coro'] = conn_cb
config['keepalive'] = 120
#MQTTClient.DEBUG = True
mqclient = MQTTClient(config)

#import uasyncio, logging
#logging.basicConfig(level=logging.DEBUG)
#uasyncio.set_debug(True)

print("Starting loop...")
try:
    loop.run_until_complete(main())
finally:  # Prevent LmacRxBlk:1 errors.
    mqclient.close()
    board.blue_led(True)
