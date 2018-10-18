import asyncio
import os
import random
import time
from playground.network.common import StackingProtocol
from .RIPPPacket import RIPPPacket


class RIPPProtocol(StackingProtocol):
    WINDOW_SIZE = 10
    TIMEOUT = 0.5
    MAX_RIP_RETRIES = 4
    SCAN_INTERVAL = 0.01

    STATE_DESC = {
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

    def sendSyn(self):
        synPacket = RIPPPacket.createSynPacket(self.initialSeq)
        print("Sending SYN packet with sequence number " + str(self.initialSeq) +", current state " + self.STATE_DESC[self.state])
        self.transport.write(synPacket.__serialize__())

    def sendSynAck(self, synAck_seqNum):
        synAckPacket = RIPPPacket.createSynAckPacket(synAck_seqNum, self.associatedSeqNum)
        print("Sending SYN_ACK packet with sequence number " + str(synAck_seqNum) + ", ack number " + str(self.associatedSeqNum) + ", current state " + self.STATE_DESC[self.state])
        self.transport.write(synAckPacket.__serialize__())

    def sendAck(self):
        ackPacket = RIPPPacket.createAckPacket(self.associatedSeqNum)
        print("Sending ACK packet with ack number " + str(self.associatedSeqNum) + ", current state " + self.STATE_DESC[self.state])
        self.transport.write(ackPacket.__serialize__())

    def sendFin(self):
        finPacket = RIPPPacket.createFinPacket(self.seqNum, self.associatedSeqNum)
        print("Sending FIN packet with sequence number " + str(self.seqNum) + ", current state " + self.STATE_DESC[self.state])
        self.transport.write(finPacket.__serialize__())

    def sendFinAck(self):
        finAckPacket = RIPPPacket.createFinAckPacket(self.associatedSeqNum)
        print("Sending FIN-ACK packet with ack number " + str(self.associatedSeqNum) + ", current state " + self.STATE_DESC[self.state])
        self.transport.write(finAckPacket.__serialize__())

    def processDataPkt(self, pkt):
        if self.isClosing():
            print("It is Closing, data packet with sequence number " + str(pkt.SeqNo))
            AckNo = self.associatedSeqNum
            ackPacket = RIPPPacket.createAckPacket(AckNo)
            print("Sending ACK packet with acknowledgement number" + str(AckNo) + ", current state " + self.STATE_DESC[self.state])
            self.transport.write(ackPacket.__serialize__())
        elif pkt.SeqNo == self.associatedSeqNum:
            print("Received DATA packet with sequence number " + str(pkt.SeqNo))
            self.associatedSeqNum = pkt.SeqNo + len(pkt.Data)
            self.higherProtocol().data_received(pkt.Data)
            AckNo = self.associatedSeqNum
            ackPacket = RIPPPacket.createAckPacket(AckNo)
            print("Sending ACK packet with acknowledgement number" + str(AckNo) + ", current state " + self.STATE_DESC[self.state])
            self.transport.write(ackPacket.__serialize__())
            while self.associatedSeqNum in self.receivedDataBuffer:
                nextPkt = self.receivedDataBuffer.pop(self.associatedSeqNum)
                self.associatedSeqNum = nextPkt.SeqNo + len(nextPkt.Data)
                self.higherProtocol().data_received(nextPkt.Data)
        elif pkt.SeqNo > self.associatedSeqNum:
            print("Received DATA packet with higher sequence number " + str(pkt.SeqNo) + ", buffered.")
            self.receivedDataBuffer[pkt.SeqNo] = pkt
            AckNo = self.associatedSeqNum
            ackPacket = RIPPPacket.createAckPacket(AckNo)
            print("Sending ACK packet with acknowledgement number" + str(AckNo) + ", current state " + self.STATE_DESC[self.state])
            self.transport.write(ackPacket.__serialize__())
        else:
            print("Error: Received DATA packet with lower sequence number " + str(pkt.SeqNo) + ",current: {!r}, discarded.".format(self.associatedSeqNum))

    def processAckPkt(self, pkt):
        print("Received ACK packet with acknowledgement number " + str(pkt.AckNo))
        latestAckNo = pkt.AckNo
        for ackNumber in list(self.sentDataCache):
            if ackNumber <= latestAckNo:
                if len(self.sendingDataBuffer) > 0:
                    (nextAck, dataPkt) = self.sendingDataBuffer.pop(0)
                    print("Sending next packet " + str(nextAck) + " in sendingDataBuffer...")
                    self.sentDataCache[nextAck] = (dataPkt, time.time())
                    self.transport.write(dataPkt.__serialize__())
                del self.sentDataCache[ackNumber]

    async def checkState(self, states, callback, maxRetry=-1):
        retry = maxRetry
        while self.state not in states and retry != 0:
            print("checkState at time " + str(time.time()))
            await asyncio.sleep(self.TIMEOUT)
            print("checkState (after sleep) at time " + str(time.time()))
            if self.state not in states:
                print("Timeout on state " + self.STATE_DESC[self.state] +", expected " + str([self.STATE_DESC[state] for state in states]))
                callback()
            if retry > 0:
                retry -= 1

    async def scanCache(self):
        while not self.isClosing():
            for ackNumber in self.sentDataCache:
                (dataPkt, timestamp) = self.sentDataCache[ackNumber]
                currentTime = time.time()
                if currentTime - timestamp >= self.TIMEOUT:
                    # resend data packet after timeout
                    print("Resending packet " + str(dataPkt.SeqNo) + " in cache...")
                    self.transport.write(dataPkt.__serialize__())
                    self.sentDataCache[ackNumber] = (dataPkt, currentTime)
            await asyncio.sleep(self.SCAN_INTERVAL)

    async def checkAllSent(self, callback):
        while self.sentDataCache or self.sendingDataBuffer:
            await asyncio.sleep(self.SCAN_INTERVAL)
        callback()

    def isClosing(self):
        raise NotImplementedError("isClosing() not implemented")