from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import UINT16, STRING, UINT8, UINT32, BUFFER
from playground.network.packet.fieldtypes.attributes import Optional
import hashlib

class RIPPPacket(PacketType):
    TYPE_DESC = {
        0: "SYN",
        1: "ACK",
        2: "FIN",
        3: "DATA",
    }

    TYPE_SYN = "SYN"
    TYPE_ACK = "ACK"
    TYPE_FIN = "FIN"
    TYPE_DATA = "DATA"

    DEFINITION_IDENTIFIER = "RIPP.kandarp.packet"
    DEFINITION_VERSION = "1.0"

    FIELDS = [
        ("Type", STRING),
        ("SeqNo", UINT32({Optional: True})),
        ("AckNo", UINT32({Optional: True})),
        ("CRC", BUFFER({Optional: True})),
        ("Data", BUFFER({Optional: True}))
    ]

    def __init__(self):
        super().__init__()
        self.CRC = b""

    def calculateChecksum(self):
        oldChecksum = self.CRC
        self.CRC = b""
        bytes = self.__serialize__()
        self.CRC = oldChecksum
        return hashlib.sha256(bytes).hexdigest().encode()
        
    def verifyChecksum(self):
        return self.CRC == self.calculateChecksum()

    @classmethod
    def makeSynPacket(cls, seq):
        pkt = cls()
        pkt.Type = cls.TYPE_SYN
        pkt.SeqNo = seq
        pkt.CRC = pkt.calculateChecksum()
        return pkt

    @classmethod
    def makeSynAckPacket(cls, seq, ack):
        pkt = cls()
        pkt.Type = cls.TYPE_SYN + cls.TYPE_ACK
        pkt.SeqNo = seq
        pkt.AckNo = ack
        pkt.CRC = pkt.calculateChecksum()
        return pkt

    @classmethod
    def makeAckPacket(cls, ack):
        pkt = cls()
        pkt.Type = cls.TYPE_ACK
        pkt.AckNo = ack
        pkt.CRC = pkt.calculateChecksum()
        return pkt

    @classmethod
    def makeFinPacket(cls, seq, ack):
        pkt = cls()
        pkt.Type = cls.TYPE_FIN
        pkt.SeqNo = seq
        pkt.AckNo = ack
        pkt.CRC = pkt.calculateChecksum()
        return pkt

    @classmethod
    def makeFinAckPacket(cls, ack):
        pkt = cls()
        pkt.Type = cls.TYPE_FIN + cls.TYPE_ACK
        pkt.AckNo = ack
        pkt.CRC = pkt.calculateChecksum()
        return pkt

    @classmethod
    def makeDataPacket(cls, seq, data):
        pkt = cls()
        pkt.Type = cls.TYPE_DATA
        pkt.SeqNo = seq
        pkt.Data = data
        pkt.CRC = pkt.calculateChecksum()
        return pkt
