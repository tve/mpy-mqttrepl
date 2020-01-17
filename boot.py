# This file is executed on every boot (including wake-boot from deepsleep)

import sys
sys.path.append('/src')

import board

#import webrepl
#webrepl.start()

if True:
    import network
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(board.wifi_ssid, board.wifi_pass)
    print('Waiting on Wifi...')
    while not wlan.isconnected():
        pass
    print('Connected!')
