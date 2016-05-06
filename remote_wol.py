#! /usr/bin/env python3

import logging
import os
import subprocess
import sys
import time

from systemd import journal
journal.send('Hello world')
journal.send('Hello, again, world', FIELD2='Greetings!', FIELD3='Guten tag')
journal.send('Binary message', BINARY=b'\xde\xad\xbe\xef')

import lirc
from wakeonlan import wol

_MAC_ADDRESS    = "78:2B:CB:AF:22:EA"
_IP_ADDRESS     = "192.168.1.30"
_HOSTNAME       = "OpenELEC"
_USERNAME       = "root"
_UN_AND_ADDRESS = _USERNAME + '@' + _IP_ADDRESS

verbose = "-v" in sys.argv
repeat_time = 1.0

def init_ir():
    if verbose: print("Init... ",)
    sockid = lirc.init("remote_wol", blocking = False)
    time.sleep(1)
    if verbose: print("Done.")

def power_tv(toggle_on=None):
    if verbose: print("  Sending TV power!")
    os.system("irsend SEND_ONCE VizioTV KEY_POWER -# 10")
    time.sleep(0.2)

def power_receiver(toggle_on=None):
    if verbose: print("  Sending receiver power!")
    os.system("irsend SEND_ONCE SonyReceiver KEY_POWER -# 10")
    time.sleep(0.2)

def power_pc(toggle_on=None):
    if toggle_on:
        wol.send_magic_packet(_MAC_ADDRESS)
    else:
        try:
            subprocess.check_output(["ssh", _UN_AND_ADDRESS, "\"poweroff\""],
                                    stderr=subprocess.STDOUT, timeout=2.0)
        except subprocess.TimeoutExpired as ex:
            if verbose: print(ex)
    time.sleep(0.2)

def check_pc_power():
    return not os.system("ping -c 1 -w1 %s > /dev/null 2>&1" % _HOSTNAME)

def count_presses():
    press_start_time = time.time()
    press_end_time = time.time()
    counting = True
    if verbose: print("Counting...")

    press_count = 1

    while counting:
        time.sleep(0.1)
        code = lirc.nextcode()
        if code:
            press_end_time = time.time()
            press_count += 1
            if verbose: print("  Presses: " + str(press_count))
        elif time.time() - press_end_time > repeat_time:
            if verbose: print("  Done.")
            counting = False

    if verbose: print("Press count: ", press_count)
    return press_count

def process_code():
    last_code_time = time.time()
    while True:
        time.sleep(0.2)

        code = lirc.nextcode()

        if not code:
            continue

        press_count = count_presses()

        # Power all on
        if press_count is 1:
            if verbose: print("Powering on all!")
            power_tv()
            power_receiver()
            power_pc(True)

        # Power all off
        elif press_count is 2:
            if verbose: print("Powering off all!")
            power_tv()
            power_receiver()
            power_pc(False)

        # Power only media PC
        elif press_count is 3:
            print("PC Power: ", check_pc_power())
            power_pc(not check_pc_power())


def main():
    while True:
        init_ir()
        try:
            process_code()
        except lirc.NextCodeError as ex:
            print(ex)



if __name__ == "__main__":
    main()
