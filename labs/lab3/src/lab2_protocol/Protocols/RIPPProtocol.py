import asyncio
import random
import time
from playground.network.common import StackingProtocol
from ..Packets.RIPPPacket import RIPPPacket
from ..Timer import shutdown


class RIPPProtocol(StackingProtocol):

    STATE = {
        10: "SERVER_LISTEN",
        11: "SERVER_SYN_ACK_SENT",
        12: "SERVER_TRANSMISSION",
        13: "SERVER_CLOSING",
        14: "SERVER_CLOSED",
        20: "CLIENT_INITIAL",
        21: "CLIENT_SYN_SENT",
        22: "CLIENT_TRANSMISSION",
        23: "CLIENT_CLOSING",
        24: "CLIENT_CLOSED"
    }

    SERVER_LISTEN = 10
    SERVER_SYN_ACK_SENT = 11
    SERVER_TRANSMISSION = 12
    SERVER_CLOSING = 13
    SERVER_CLOSED = 14

    CLIENT_INITIAL = 20
    CLIENT_SYN_SENT = 21
    CLIENT_TRANSMISSION = 22
    CLIENT_CLOSING = 23
    CLIENT_CLOSED = 24

    RUN_TIME = 20
    WINDOW_SIZE = 100

    def __init__(self):
        super().__init__()
        self.state = None
        self.transport = None
        self.deserializer = RIPPPacket.Deserializer()
        self.seq_number = random.randrange(1000, 99999)
        self.initialSeq = self.seq_number
        self.associated_seq_number = None
        self.sentDataPkt = {}
        self.DataInLine = []
        self.DataReceived = {}
        self.loop = asyncio.get_event_loop()
        self.timers = {}
        self.timer = shutdown(self.RUN_TIME, self.loop.stop, self.loop)

    def connection_made(self, transport):
        print("%s made connection successfully..." % self.__class__.__name__)
        self.transport = transport
        super().connection_made(transport)
        if self.__class__.__name__ == 'ClientProtocol':
            # print("456456456")
            if  self.state == self.CLIENT_INITIAL:
                self.sendSynPkt()   #send syn pkt from client to server
                self.seq_number += 1
                self.state = self.CLIENT_SYN_SENT
        # else(self.__class__.__name__ == 'ServerProtocol')


    def sendSynPkt(self):
        synPkt = RIPPPacket.createSynPkt(self.initialSeq)
        print("%s Sending SYN packet with sequence number %s" % (self.__class__.__name__, str(self.initialSeq)))
        self.transport.write(synPkt.__serialize__())

    def sendSynAckPkt(self, synAck_seqNum):
        synAckPkt = RIPPPacket.createSynAckPkt(synAck_seqNum, self.associated_seq_number)
        print("%s Sending SYN_ACK packet with sequence number %s, ack number %s" \
              % (self.__class__.__name__, str(synAck_seqNum), str(self.associated_seq_number)))
        self.transport.write(synAckPkt.__serialize__())

    def sendAckPkt(self):
        ackPkt = RIPPPacket.createAckPkt(self.associated_seq_number)
        print("%s Sending ACK packet with ack number %s" % (self.__class__.__name__, str(self.associated_seq_number)))
        self.transport.write(ackPkt.__serialize__())

    def sendFinPkt(self):
        finPkt = RIPPPacket.createFinPkt(self.seq_number, self.associated_seq_number)
        print("%s Sending FIN packet with sequence number %s" % (self.__class__.__name__, str(self.seq_number)))
        self.transport.write(finPkt.__serialize__())

    def sendFinAckPkt(self):
        finAckPkt = RIPPPacket.createFinAckPkt(self.associated_seq_number)
        print("%s Sending FIN-ACK packet with ack number %s" % (self.__class__.__name__, str(self.associated_seq_number)))
        self.transport.write(finAckPkt.__serialize__())

    def handleDataPkt(self, pkt):
        if self.state == self.SERVER_CLOSING or self.state == self.SERVER_CLOSED or self.state == self.CLIENT_CLOSING or self.state == self.CLIENT_CLOSED:
            print("%s It is Closing, data packet with sequence number %s" % (self.__class__.__name__, str(pkt.SeqNo)))
            AckNo = self.associated_seq_number
            ackPkt = RIPPPacket.createAckPkt(AckNo)
            print("%s Sending ACK packet with acknowledgement number %s" % (self.__class__.__name__, str(AckNo)))
            self.transport.write(ackPkt.__serialize__())
        elif pkt.SeqNo == self.associated_seq_number:
            print("%s Receive DATA packet with sequence number %s" % (self.__class__.__name__, str(pkt.SeqNo)))
            self.associated_seq_number = pkt.SeqNo + len(pkt.Data)
            self.higherProtocol().data_received(pkt.Data)
            AckNo = self.associated_seq_number
            ackPkt = RIPPPacket.createAckPkt(AckNo)
            print("%s Sending ACK packet with acknowledgement number %s" % (self.__class__.__name__, str(AckNo)))
            self.transport.write(ackPkt.__serialize__())
            while self.associated_seq_number in self.DataReceived:
                nextPkt = self.DataReceived.pop(self.associated_seq_number)
                self.associated_seq_number = nextPkt.SeqNo + len(nextPkt.Data)
                self.higherProtocol().data_received(nextPkt.Data)
        elif pkt.SeqNo > self.associated_seq_number:
            print("%s Received DATA packet with higher sequence number %s, buffered." % (self.__class__.__name__, str(pkt.SeqNo)))
            self.DataReceived[pkt.SeqNo] = pkt

        else:
            print("%s Error: Received DATA packet with lower sequence number" % self.__class__.__name__, )
            AckNo = pkt.SeqNo + len(pkt.Data)
            ackPkt = RIPPPacket.createAckPkt(AckNo)
            self.transport.write(ackPkt.__serialize__())
            print("%s Sending ACK packet with acknowledgement number%s" % (self.__class__.__name__,  str(AckNo)))

    def handleAckPkt(self, pkt):
        print("%s Received ACK packet with acknowledgement number %s" % (self.__class__.__name__, str(pkt.AckNo)))
        latestAckNo = pkt.AckNo
        while latestAckNo in list(self.timers):
            self.timers[latestAckNo].cancel()
            del self.timers[latestAckNo]
            break
        while latestAckNo in list(self.sentDataPkt):
            del self.sentDataPkt[latestAckNo]
            break

    def readyForFin(self):
        print("%s Preparing for FIN" % self.__class__.__name__)
        if self.__class__.__name__ == 'ClientProtocol':
            self.state = self.CLIENT_CLOSING
        elif self.__class__.__name__ == 'ServerProtocol':
            self.state = self.SERVER_CLOSING
        self.transport.close()

    def send_finack_then_close(self, pkt):
        if self.__class__.__name__ == 'ClientProtocol':
            print("%s Received FIN packet with sequence number %s" % (self.__class__.__name__, str(pkt.SeqNo)))
            self.associated_seq_number = pkt.SeqNo + 1
            # send fin_ack and stop
            self.sendFinAckPkt()
            time.sleep(1)
            self.transport.close()
            self.state = self.CLIENT_CLOSED
        elif self.__class__.__name__ == 'ServerProtocol':
            print("%s Received FIN packet with sequence number %s" % (self.__class__.__name__, str(pkt.SeqNo)))
            self.associated_seq_number = pkt.SeqNo + 1
            # send fin_ack packet and stop immediately
            self.sendFinAckPkt()
            time.sleep(1)
            self.transport.close()
            self.state = self.SERVER_CLOSED

    def receive_finack_then_shutdown(self, pkt):
        print("%s Received FIN_ACK packet with ack number %s" % (self.__class__.__name__, str(pkt.AckNo)))
        self.state = self.CLIENT_CLOSED
        self.transport.close()

    def connection_lost(self, exc):
        print("%s Connection closed" % self.__class__.__name__)
        self.higherProtocol().connection_lost(exc)
        self.transport = None
