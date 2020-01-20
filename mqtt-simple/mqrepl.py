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
from mqtt_client import MQTTClient

print("\n===== esp32 mqttrepl `{}` starting at {} =====\n".format(board.location, time.time()))

TOPIC = 'esp32/' + board.location + '/repl'
REPL_IN = TOPIC + '/in'
REPL_OUT = TOPIC + '/out'

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
        mqclient.publish(REPL_OUT, msg)

def msg_in(topic, msg):
    topic = str(topic, 'utf-8')
    print("msg in: {}: {}".format(topic, msg))
    do_eval(msg)

def main():
    global mqclient
    mqclient = MQTTClient(board.location, board.mqtt_server, ssl=True,
            ssl_params={'psk_ident':board.mqtt_ident, 'psk_key':board.mqtt_key})
    print("Connect:", mqclient.connect())

    mqclient.set_callback(msg_in)
    mqclient.subscribe(REPL_IN)
    print("Subscribed to", REPL_IN)

    #while True:
    #    mqclient.wait_msg()


#main()
