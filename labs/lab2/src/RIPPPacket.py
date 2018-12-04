from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import STRING, UINT32, BUFFER
from playground.network.packet.fieldtypes.attributes import Optional
import hashlib


class RIPPPacket(PacketType):
    DEFINITION_IDENTIFIER = "RIPP.kandarp.packet"
    DEFINITION_VERSION = "1.0"

    TYPE_SYN = "SYN"
    TYPE_ACK = "ACK"
    TYPE_FIN = "FIN"
    TYPE_DATA = "DATA"

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

    def createSynPkt(seq):
        pkt = RIPPPacket()
        pkt.Type = pkt.TYPE_SYN
        pkt.SeqNo = seq
        pkt.CRC = pkt.calculate_CRC()
        return pkt

    def createSynAckPkt(seq, ack):
        pkt = RIPPPacket()
        pkt.Type = pkt.TYPE_SYN + pkt.TYPE_ACK
        pkt.SeqNo = seq
        pkt.AckNo = ack
        pkt.CRC = pkt.calculate_CRC()
        return pkt

    def createAckPkt(ack):
        pkt = RIPPPacket()
        pkt.Type = pkt.TYPE_ACK
        pkt.AckNo = ack
        pkt.CRC = pkt.calculate_CRC()
        return pkt

    def createFinPkt(seq, ack):
        pkt = RIPPPacket()
        pkt.Type = pkt.TYPE_FIN
        pkt.SeqNo = seq
        pkt.AckNo = ack
        pkt.CRC = pkt.calculate_CRC()
        return pkt

    def createFinAckPkt(ack):
        pkt = RIPPPacket()
        pkt.Type = pkt.TYPE_FIN + pkt.TYPE_ACK
        pkt.AckNo = ack
        pkt.CRC = pkt.calculate_CRC()
        return pkt

    def createDataPkt(seq, data):
        pkt = RIPPPacket()
        pkt.Type = pkt.TYPE_DATA
        pkt.SeqNo = seq
        pkt.Data = data
        pkt.CRC = pkt.calculate_CRC()
        return pkt

    def calculate_CRC(self):
        previousChecksum = self.CRC
        self.CRC = b""
        bytes = self.__serialize__()
        self.CRC = previousChecksum
        return hashlib.sha256(bytes).digest()
        
    def verify_CRC(self):
        return self.CRC == self.calculate_CRC()
