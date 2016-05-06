#! /usr/bin/env python3

import logging
import os
import subprocess
import sys
import time

from systemd import journal

import lirc
from pywakeonlan.wakeonlan import wol

_MAC_ADDRESS    = "78:2B:CB:AF:22:EA"
_IP_ADDRESS     = "192.168.1.30"
_HOSTNAME       = "OpenELEC"
_USERNAME       = "root"
_UN_AND_ADDRESS = _USERNAME + '@' + _IP_ADDRESS

verbose = "-v" in sys.argv
repeat_time = 1.0

def log_and_print(*args, **kwargs):
    journal.send(*args, MESSAGE_ID="remote_wol")
    if verbose:
        print(*args, **kwargs)

def init_ir():
    log_and_print("Init... ",)
    sockid = lirc.init("remote_wol", blocking = False)
    time.sleep(1)
    log_and_print("Done.")

def power_tv(toggle_on=None):
    log_and_print("  Sending TV power!")
    os.system("irsend SEND_ONCE VizioTV KEY_POWER -# 10")
    time.sleep(0.2)

def power_receiver(toggle_on=None):
    log_and_print("  Sending receiver power!")
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
            log_and_print(str(ex))
    time.sleep(0.2)

def check_pc_power():
    return not os.system("ping -c 1 -w1 %s > /dev/null 2>&1" % _HOSTNAME)

def count_presses():
    press_start_time = time.time()
    press_end_time = time.time()
    counting = True
    log_and_print("Counting...")

    press_count = 1

    while counting:
        time.sleep(0.1)
        code = lirc.nextcode()
        if code:
            press_end_time = time.time()
            press_count += 1
            log_and_print("  Presses: " + str(press_count))
        elif time.time() - press_end_time > repeat_time:
            log_and_print("  Done.")
            counting = False

    log_and_print("Press count: " + str(press_count))
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
            log_and_print("Powering on all!")
            power_tv()
            power_receiver()
            power_pc(True)

        # Power all off
        elif press_count is 2:
            log_and_print("Powering off all!")
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
