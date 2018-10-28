import asyncio
import os
import random
import time
from playground.network.common import StackingProtocol
from .RIPPPacket import RIPPPacket
from .Timer import Timer
from .Timer import shutdown


class RIPPProtocol(StackingProtocol):
    WINDOW_SIZE = 60

    STATE = {
        0: "DEFAULT",
        10: "SERVER_LISTEN",
        11: "SERVER_SYN_ACK_SENT",
        12: "SERVER_TRANSMISSION",
        13: "SERVER_CLOSING",
        14: "SERVER_CLOSED",
        20: "CLIENT_INITIAL_SYN",
        21: "CLIENT_SYN_SENT",
        22: "CLIENT_TRANSMISSION",
        23: "CLIENT_CLOSING",
        24: "CLIENT_CLOSED"
    }

    STATE_DEFAULT = 0

    STATE_SERVER_LISTEN = 10
    STATE_SERVER_SYN_ACK_SENT = 11
    STATE_SERVER_TRANSMISSION = 12
    STATE_SERVER_CLOSING = 13
    STATE_SERVER_CLOSED = 14

    STATE_CLIENT_INITIAL_SYN = 20
    STATE_CLIENT_SYN_SENT = 21
    STATE_CLIENT_TRANSMISSION = 22
    STATE_CLIENT_CLOSING = 23
    STATE_CLIENT_CLOSED = 24

    RUN_TIME = 40

    def __init__(self):
        super().__init__()
        self.state = self.STATE_DEFAULT
        self.transport = None
        self.deserializer = RIPPPacket.Deserializer()
        self.seqNum = random.randrange(1000, 99999)
        self.initialSeq = self.seqNum
        self.associatedSeqNum = None
        self.sentDataCache = {}
        self.sendingDataBuffer = []
        self.receivedDataBuffer = {}
        self.tasks = []
        self.loop = asyncio.get_event_loop()
        self.timers = {}
        self.timer = shutdown(self.RUN_TIME, self.loop.stop, self.loop)

    def sendSyn(self):
        synPacket = RIPPPacket.createSynPacket(self.initialSeq)
        print("Sending SYN packet with sequence number " + str(self.initialSeq) +", current state " + self.STATE[self.state])
        self.transport.write(synPacket.__serialize__())

    def sendSynAck(self, synAck_seqNum):
        synAckPacket = RIPPPacket.createSynAckPacket(synAck_seqNum, self.associatedSeqNum)
        print("Sending SYN_ACK packet with sequence number " + str(synAck_seqNum) + ", ack number " + str(self.associatedSeqNum) + ", current state " + self.STATE[self.state])
        self.transport.write(synAckPacket.__serialize__())

    def sendAck(self):
        ackPacket = RIPPPacket.createAckPacket(self.associatedSeqNum)
        print("Sending ACK packet with ack number " + str(self.associatedSeqNum) + ", current state " + self.STATE[self.state])
        self.transport.write(ackPacket.__serialize__())

    def sendFin(self):
        finPacket = RIPPPacket.createFinPacket(self.seqNum, self.associatedSeqNum)
        print("Sending FIN packet with sequence number " + str(self.seqNum) + ", current state " + self.STATE[self.state])
        self.transport.write(finPacket.__serialize__())

    def sendFinAck(self):
        finAckPacket = RIPPPacket.createFinAckPacket(self.associatedSeqNum)
        print("Sending FIN-ACK packet with ack number " + str(self.associatedSeqNum) + ", current state " + self.STATE[self.state])
        self.transport.write(finAckPacket.__serialize__())

    def processDataPkt(self, pkt):
        if self.isClosing():
            print("It is Closing, data packet with sequence number " + str(pkt.SeqNo))
            AckNo = self.associatedSeqNum
            ackPacket = RIPPPacket.createAckPacket(AckNo)
            print("Sending ACK packet with acknowledgement number" + str(AckNo) + ", current state " + self.STATE[self.state])
            self.transport.write(ackPacket.__serialize__())
        elif pkt.SeqNo == self.associatedSeqNum:
            print("Received DATA packet with sequence number " + str(pkt.SeqNo))
            self.associatedSeqNum = pkt.SeqNo + len(pkt.Data)
            self.higherProtocol().data_received(pkt.Data)
            AckNo = self.associatedSeqNum
            ackPacket = RIPPPacket.createAckPacket(AckNo)
            print("Sending ACK packet with acknowledgement number" + str(AckNo) + ", current state " + self.STATE[self.state])
            self.transport.write(ackPacket.__serialize__())
            while self.associatedSeqNum in self.receivedDataBuffer:
                nextPkt = self.receivedDataBuffer.pop(self.associatedSeqNum)
                self.associatedSeqNum = nextPkt.SeqNo + len(nextPkt.Data)
                self.higherProtocol().data_received(nextPkt.Data)
        elif pkt.SeqNo > self.associatedSeqNum:
            print("Received DATA packet with higher sequence number " + str(pkt.SeqNo) + ", buffered.")
            self.receivedDataBuffer[pkt.SeqNo] = pkt
            # AckNo = self.associatedSeqNum
            # ackPacket = RIPPPacket.createAckPacket(AckNo)
            # print("Sending ACK packet with acknowledgement number" + str(AckNo) + ", current state " + self.STATE[self.state])
            # self.transport.write(ackPacket.__serialize__())
        else:
            print("Error: Received DATA packet with lower sequence number " + str(pkt.SeqNo) + ",current: {!r}, discarded.".format(self.associatedSeqNum))
            AckNo = pkt.SeqNo + len(pkt.Data)
            ackPacket = RIPPPacket.createAckPacket(AckNo)
            self.transport.write(ackPacket.__serialize__())
            print("Sending ACK packet with acknowledgement number" + str(AckNo) + ", current state " + self.STATE[self.state])

    def processAckPkt(self, pkt):
        print("Received ACK packet with acknowledgement number " + str(pkt.AckNo))
        latestAckNo = pkt.AckNo
        while latestAckNo in list(self.timers):
            self.timers[latestAckNo].cancel()
            del self.timers[latestAckNo]
            break
        while latestAckNo in list(self.sentDataCache):
            del self.sentDataCache[latestAckNo]
            break

    def isClosing(self):
        raise NotImplementedError("isClosing() not implemented")
