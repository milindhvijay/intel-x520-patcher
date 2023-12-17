#!/usr/bin/env python3
#
# Simple Intel x520 EEPROM patcher
# Modifies the EEPROM to unlock the card for non-intel branded SFP modules.
#
# Copyright 2020,2021,2022 Andreas Thienemann <andreas@bawue.net>
#
# Licensed under the GPLv3
#
# Based on research described at https://forums.servethehome.com/index.php?threads/patching-intel-x520-eeprom-to-unlock-all-sfp-transceivers.24634/
#
# Quick explanation of what's going on:
# Looking at the Intel driver at e.g. https://elixir.bootlin.com/linux/v5.8/source/drivers/net/ethernet/intel/ixgbe/ixgbe_type.h#L2140 we can see
# that the bit 0x1 at Address 0x58 contains a configuration setting whether the card allows any SFP modules or if Intel specific ones are enforced
# by the driver.
#
# Addr Bitstring
# 0x58 xxxxxxx0 means Intel specific SFPs
# 0x58 xxxxxxx1 means any SFP is allowed.
#
# Using the parameter allow_unsupported_sfp for the kernel module we can tell the driver to accept any SFPs.
# But this tool will flip the right bit 1 to make that change permanent in the configuration bits in the EEPROM,
# thus making kernel module parameters unnecessary.
#
import os
import subprocess
import sys

try:
    intf = sys.argv[1]
except IndexError:
    print("%s <interface>" % sys.argv[0])
    sys.exit(255)

try:
    with open("/sys/class/net/%s/device/vendor" % intf) as f:
        vdr_id = f.read().strip()

    with open("/sys/class/net/%s/device/device" % intf) as f:
        dev_id = f.read().strip()
except IOError:
    print("Can't read interface data.")
    sys.exit(2)

if vdr_id not in ('0x8086') or dev_id not in ('0x10fb', '0x154d'):
    print("Not a recognized Intel x520 card.")
    sys.exit(3)


output = subprocess.check_output(['ethtool', '-e', intf, 'offset', '0x58', 'length', '1']).decode('utf-8')

val = output.strip().split('\n')[-1].split()[-1]
val_bin = int(val, 16)

print("EEPROM Value at 0x58 is 0x%s (%s)" % (val, bin(val_bin)))
if val_bin & 0b00000001 == 1:
    print("Card is already unlocked for all SFP modules. Nothing to do.")
    exit(1)
if val_bin & 0b00000001 == 0:
    print("Card is locked to Intel only SFP modules. Patching EEPROM...")
    new_val = val_bin | 0b00000001
    print("New EEPROM Value at 0x58 will be %s (%s)" % (hex(new_val), bin(new_val)))

magic = "%s%s" % (dev_id, vdr_id[2:])
cmd = ['ethtool', '-E', intf, 'magic', magic, 'offset', '0x58', 'value', hex(new_val), 'length', 1]
print("Running {}".format(cmd))
cmd = ' '.join(map(str, cmd))
os.system(cmd)
print("Reboot the machine for changes to take effect...")
