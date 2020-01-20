# MQTT Repl for MicroPython by Thorsten von Eicken (c) 2020
#
# Simple repl over MQTT, subscribes to a topic and feeds data received on that topic into the system
# repl. Collects output from the system repl and sends it out to another topic with up to 100ms
# delay in order to accumulate bytes into messages.
#
# Requires asyncio-based MQTT, i.e. mqtt_as
# Inspired by https://github.com/micropython/micropython/blob/master/examples/bluetooth/ble_uart_repl.py

import io, os, binascii, sys, json
import board, machine, time
from mqtt_as import MQTTClient, config
import asynciocb as asyncio

print("\n===== esp32 mqttrepl `{}` starting at {} =====\n".format(board.location, time.time()))

TOPIC = 'esp32/' + board.location + '/repl'
REPL_IN = TOPIC + '/in'
REPL_OUT = TOPIC + '/out'

# ===== Repl helpers

def json_escape(buf):
    str = bytearray

def do_eval(cmd):
    try:
        cmd = str(cmd, 'utf-8')
        result = None
        outbuf = io.BytesIO(1024)
        errbuf = io.BytesIO(256)
        old_term = os.dupterm(outbuf)
        did_exec = False
        try:
            op = compile(cmd, "<mqtt>", "eval")
        except SyntaxError:
            did_exec = True
            op = compile(cmd, "<mqtt>", "exec")
        result = eval(op, globals(), None)
        os.dupterm(old_term)
        print("Result:", str(result))
        outbuf = outbuf.getvalue()
        print("Output:", outbuf)
        errbuf = None
    except Exception as e:
        os.dupterm(old_term)
        outbuf = outbuf.getvalue()
        print("Output:", outbuf)
        sys.print_exception(e, errbuf)
        errbuf = errbuf.getvalue()
        print("Exception: <<", errbuf, ">>")
    finally:
        msg = [ '{"r":', json.dumps(result), ',"o":', json.dumps(outbuf),
                ',"e":', json.dumps(errbuf), ',"x":', str(did_exec), '}' ]
        loop.create_task(mqclient.publish(REPL_OUT, msg))
        print("Pub:", REPL_OUT, msg)

# ===== asyncio and mqtt callback handlers

loop = asyncio.get_event_loop()
mqrepl = None
mqclient = None
outages = 0

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
        do_eval(msg)
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

import socket
async def conn_cb(client):
    print('MQTT connected')
    await client.subscribe(REPL_IN, 1)
    print("Subscribed to", REPL_IN)

# ===== async main loop

async def async_main():
    global mqclient
    # get an initial connection
    board.blue_led(True)
    try:
        await mqclient.connect()
    except OSError:
        print('Connection failed')
        return
    # play watchdog
    while True:
        print("Still running...")
        await asyncio.sleep(10)

last_loop = 0
# looper gets called from a Timer callback as well as from a socket input-ready callback.
# It can also be called from "main" if a repl prompt is not desired/needed.
def looper(s=None):
    #print('looper!')
    delay = loop.run_once()
    while delay < 10:
        time.sleep_ms(delay)
        delay = loop.run_once()
    #print('<{}>'.format(delay), end='')
    global last_loop
    last_loop = time.ticks_ms()
    return delay
def tickle_loop(t=None):
    if time.ticks_diff(time.ticks_ms(), last_loop) > 500:
        looper()

#config['ssl'] = True
#config['ssl_params'] = {'psk_ident':board.mqtt_ident, 'psk_key':board.mqtt_key}

# Start MQTT (and Wifi)
config['subs_cb'] = sub_cb
config['wifi_coro'] = wifi_cb
config['connect_coro'] = conn_cb
config['keepalive'] = 120
config['sock_cb'] = looper
MQTTClient.DEBUG = True
mqclient = MQTTClient(config)

loop.start_run(async_main())
machine.Timer(-1).init(mode=machine.Timer.PERIODIC, period=1000, callback=tickle_loop)
print('Dropping into repl')

