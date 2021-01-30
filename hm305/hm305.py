import binascii
import logging
import struct
from enum import IntEnum

import serial

from hm305 import CRCError, rint


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

    def __init__(self, port):

        self.s = serial.Serial(port, baudrate=9600, timeout=0.1)

    def send(self, data):
        d = data + struct.pack('<H', self.calculate_crc(data))
        logging.debug(f"TX[{len(binascii.hexlify(d)) / 2:02.0f}]: {binascii.hexlify(d)}")
        ret = self.s.write(d)
        # self.s.flush()
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

            logging.debug(f"RX[{len(binascii.hexlify(data)) / 2:02.0f}]: {binascii.hexlify(data)}")
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
        if ret is None:
            raise serial.SerialException("could not read measurement")
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
