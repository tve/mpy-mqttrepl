MicroPython experiments with an MQTT-based Repl
===============================================

This repo contains work in progress, it may or may not be useful to you...

Prerequisites
-------------
- ESP32 with MicroPython v1.12 or newer, based on ESP-IDF 4.x
- An MQTT server, configured for MQTTS using PSK cipher suites if desired
- cli tools to publish messages and subscribe to topics, e.g. `mosquitto_pub`/`..._sub`

`mqtt_as` (asyncio) based repl in callbacks
-------------------------------------------

The `src` directory contains a proof of concept repl that uses *the awesome mqtt_as* by
Peter Hinch from https://github.com/peterhinch/micropython-mqtt/blob/master/mqtt_as/mqtt_as.py.
It has been modified a bit and uses a slightly altered version of uasyncio (from the
micropython-lib) to allow for one-shot running of coroutines instead of `run_forever`.

The `src/mqrepl.py` "main" starts the MQTT connection and registers some callbacks such that
the MQTT client and the associated subscription keep running in the background, very similar to
the webrepl. When everything is set-up, mqrepl drops back into the repl prompt.

Commands can be sent to the repl using the topic defined by `REPL_IN`, for example:

```
> mosquitto_pub -h 192.168.0.14 --debug -p 8883 -u core --psk-identity core --psk bb000000000000000000000000000030 -t esp32/mqtest/repl/in -m "print('hello')
              "
Client mosq-QcEKHJzNtxQEMWtzzk sending CONNECT
Client mosq-QcEKHJzNtxQEMWtzzk received CONNACK (0)
Client mosq-QcEKHJzNtxQEMWtzzk sending PUBLISH (d0, q0, r0, m1, 'esp32/mqtest/repl/in', ... (15 bytes))
Client mosq-QcEKHJzNtxQEMWtzzk sending DISCONNECT
```

The esp32 will `eval` or `exec` the python expression/statement and send the reply back on the
topic defined by `REPL_OUT` in json form, for example:

```
> mosquitto_sub -h 192.168.0.14 --debug -p 8883 -u core --psk-identity c
ore --psk bb5ec51f995a1c995eeccbdc47898530 -t esp32/mqtest/repl/out
Client mosq-a32XHgSJkfXmVTLUkA sending CONNECT
Client mosq-a32XHgSJkfXmVTLUkA received CONNACK (0)
Client mosq-a32XHgSJkfXmVTLUkA sending SUBSCRIBE (Mid: 1, Topic: esp32/mqtest/repl/out, QoS: 0, Opti
ons: 0x00)
Client mosq-a32XHgSJkfXmVTLUkA received SUBACK
Subscribed (mid: 1): 0
Client mosq-a32XHgSJkfXmVTLUkA sending PINGREQ
Client mosq-a32XHgSJkfXmVTLUkA received PINGRESP
...
Client mosq-a32XHgSJkfXmVTLUkA received PUBLISH (d0, q0, r0, m0, 'esp32/mqtest/repl/out', ... (45 by
tes))
{"r":null,"o":"hello\r\n","e":null,"x":False}
```
Where `r` is the expression result, `o` is the output, and `e` is any exception printout.

Note that the way the MQTT async loop is currently run is rather hackinsh and needs further work!

`mqtt_simple` based repl
------------------------

The `mqtt-simple` directory contains a callback-based repl experiment that uses  a slightly modified
version of `umqtt.simple` from the micropython-lib.

asyncio repl experiment
-----------------------

The asyncio directory contains a first repl experiment based on `mqtt_as`.

