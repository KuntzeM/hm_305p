#!/usr/bin/python3

import struct
import sys

import serial
from enum import IntEnum
import logging
import binascii
import pandas as pd
import matplotlib.pyplot as plt

logging.basicConfig(format='%(asctime)s %(message)s', level=logging.INFO)


class CRCError(Exception):
    pass


def rint(x):
    return int(round(x))


class HM305:
    class CMD(IntEnum):
        Output = 0x0001  # (R/W)
        Protect_state_address = 0x0002  # (R)
        Model_address = 0x0003  # (R)
        Class_detail = 0x0004  # (R)
        Decimals = 0x0005  # (R)
        Voltage = 0x0010  # (R)
        Current = 0x0011  # (R)
        Power = 0x0012  # (R) 4 byte response
        Power_cal = 0x0014  # (R/W?) 4 byte response
        Protect_Voltage = 0x0020  # (R)
        Protect_Current = 0x0021  # (R)
        Protect_Power = 0x0022  # (R) 4 byte response
        Set_Voltage = 0x0030
        Set_Current = 0x0031
        Set_Time_span = 0x0032
        Power_state = 0x8801
        Default_show = 0x8802
        SCP = 0x8803
        Buzzer = 0x8804
        Device = 0x9999
        SD_Time = 0xCCCC

    def __init__(self, fd=None):
        if fd is None:
            logging.debug("HM305 opened without a serial obj! using defaults.")
            fd = serial.Serial('/dev/ttyUSB0', baudrate=9600, timeout=0.1)
        self.s = fd

    def send(self, data):
        d = data + struct.pack('<H', self.calculate_crc(data))
        logging.debug(f"TX[{len(binascii.hexlify(d))/2:02.0f}]: {binascii.hexlify(d)}")
        ret = self.s.write(d)
        #self.s.flush()
        return ret

    def recv(self, length=1):
        data = b''
        while 1:
            b = self.s.read(length)
            if len(b) == 0:
                break
            data += b

        if len(data) > 2:
            crc = self.calculate_crc(data[:-2])
            packet_crc, = struct.unpack('<H', data[-2:])
            if crc != packet_crc:
                raise CRCError("RX")

            logging.debug(f"RX[{len(binascii.hexlify(data))/2:02.0f}]: {binascii.hexlify(data)}")
            return data[:-2]
        return None

    def send_packet(self, device_address=1, address=5, value=None):

        if value is None:
            read = True
            value = 1
        else:
            read = False

        pack = struct.pack('>BBHH', device_address, (6, 3)[read], address, value)
        self.send(pack)

    def receive_packet(self):
        p = self.recv()
        if p:
            if p[1] == 0x83:
                if p[2] == 0x08:
                    raise CRCError("TX")
                else:
                    raise Exception("Unknown error " + repr(p))
            elif p[1] == 3:
                length = p[2]
                assert len(p[3:]) == length
                if length == 2:
                    ret, = struct.unpack('>H', p[3:])
                    return ret
                else:
                    return p
            elif p[1] == 6:
                assert len(p[2:]) == 4
                addr, val = struct.unpack('>HH', p[2:])
                return addr, val
            else:
                raise Exception("Unknown response %d" % p)

    def x(self, addr, val=None):
        self.send_packet(address=addr, value=val)
        ret = self.receive_packet()
        if val is None:
            return ret
        else:
            assert addr, val == ret

    def x4(self, addr, val=None):
        if val is None:
            return (self.x(addr) << 16) + self.x(addr + 1)
        else:
            self.x(addr, val >> 16)
            self.x(addr + 1, val & 0xffff)

    ###########################################################
    @property
    def v(self):
        return self.x(HM305.CMD.Voltage) / 100

    @v.setter
    def v(self, val):
        self.vset = val

    @property
    def vset(self):
        return self.x(HM305.CMD.Set_Voltage) / 100

    @vset.setter
    def vset(self, v):
        return self.x(HM305.CMD.Set_Voltage, val=rint(v * 100))

    ###########################################################
    @property
    def i(self):
        return self.x(HM305.CMD.Current) / 1000

    @i.setter
    def i(self, val):
        self.iset = val

    @property
    def iset(self):
        return self.x(HM305.CMD.Set_Current) / 1000

    @iset.setter
    def iset(self, i):
        return self.x(HM305.CMD.Set_Current, val=rint(i * 1000))

    ###########################################################
    @property
    def w(self):
        return self.x4(HM305.CMD.Power) / 1000

    def off(self):
        self.x(HM305.CMD.Output, 0)

    def on(self):
        self.x(HM305.CMD.Output, 1)

    @property
    def beep(self):
        return self.x(0x8804)

    @beep.setter
    def beep(self, v):
        self.x(0x8804, v)

    @staticmethod
    def calculate_crc(data):
        """Calculate the CRC16 of a datagram"""
        crc = 0xFFFF
        for i in data:
            crc ^= i
            for _ in range(8):
                if crc & 1:
                    crc >>= 1
                    crc ^= 0xa001
                else:
                    crc >>= 1
        return crc


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()

    serial_parser = parser.add_mutually_exclusive_group(required=True)
    serial_parser.add_argument('--port', type=str, help='serial port')

    volt_parser = parser.add_mutually_exclusive_group()
    volt_parser.add_argument('--voltage', type=float, help='set voltage')
    volt_parser.add_argument('--adj-voltage', metavar="X", type=float, help='adjust voltage by X')
    current_parser = parser.add_mutually_exclusive_group()
    current_parser.add_argument('--current', type=float, help='set current')

    output_parser = parser.add_mutually_exclusive_group()
    output_parser.add_argument('--on', action='store_true', help='switch output on')
    output_parser.add_argument('--off', action='store_true', help='switch output off')
    beep_parser = parser.add_mutually_exclusive_group()
    beep_parser.add_argument('--beep', action='store_true', help='enable beeping')
    beep_parser.add_argument('--nobeep', action='store_true', help='disable beeping')

    parser.add_argument('--debug', action='store_true', help='enable verbose logging')
    parser.add_argument('--get', action='store_true', help='report output measurements')

    args = parser.parse_args()

    if len(sys.argv) == 1:
        # display help message when no args are passed.
        parser.print_help()
        sys.exit(1)

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    with serial.Serial('/dev/ttyUSB0', baudrate=9600, timeout=0.1) as ser:
        hm = HM305(ser)
        if args.voltage is not None:
            logging.info("Setting voltage:")
            hm.v = args.voltage
        elif args.adj_voltage is not None:
            logging.info("Adjusting voltage:")
            hm.v += args.adj_voltage
        if args.current is not None:
            logging.info("Setting current:")
            hm.i = args.current
        if args.beep:
            logging.info("Setting beep: ON")
            hm.beep = 1
        elif args.nobeep:
            logging.info("Setting beep: OFF")
            hm.beep = 0
        if args.off:
            logging.info("Setting output: OFF")
            hm.off()
        elif args.on:
            logging.info("Setting output: ON")
            hm.on()
        if args.get:
            logging.info(f"{hm.v} Volts")
            logging.info(f"{hm.i} Amps")
            logging.info(f"{hm.w} Watts")
    logging.debug("Done")
