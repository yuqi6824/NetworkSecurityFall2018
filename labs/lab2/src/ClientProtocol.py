import asyncio
from .RIPPPacket import RIPPPacket
from .RIPPTransport import RIPPTransport
from .RIPPProtocol import RIPPProtocol
import time
from .Timer import Timer


class ClientProtocol(RIPPProtocol):

    def __init__(self):
        super().__init__()
        self.state = self.STATE_CLIENT_INITIAL_SYN
        print("Initialized client with state " + self.STATE_DESC[self.state])

    def connection_made(self, transport):
        self.transport = transport
        super().connection_made(transport)
        if self.state == self.STATE_CLIENT_INITIAL_SYN:
            self.sendSyn()
            self.seqNum += 1
            self.state = self.STATE_CLIENT_SYN_SENT

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, RIPPPacket):
                if pkt.verifyChecksum():
                    if pkt.Type == (RIPPPacket.TYPE_SYN + RIPPPacket.TYPE_ACK):
                        if self.state == self.STATE_CLIENT_SYN_SENT:
                            # check ackNo
                            if (pkt.AckNo >= self.seqNum):
                                print("Received SYN_ACK packet with sequence number " + str(pkt.SeqNo) + ", ack number " + str(pkt.AckNo))
                                self.state = self.STATE_CLIENT_TRANSMISSION
                                self.associatedSeqNum = pkt.SeqNo + 1
                                self.sendAck()
                                higherTransport = RIPPTransport(self.transport, self)
                                self.higherProtocol().connection_made(higherTransport)
                            else:
                                print("Client: Wrong SYN_ACK packet: ACK number: {!r}, expected: {!r}".format(pkt.AckNo, self.seqNum + 1))
                        else:
                            self.sendAck()

                    elif pkt.Type == RIPPPacket.TYPE_ACK:
                        if self.state in (self.STATE_CLIENT_TRANSMISSION, self.STATE_CLIENT_CLOSING):
                            self.processAckPkt(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_DATA, self.STATE_CLIENT_TRANSMISSION):
                        self.processDataPkt(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.STATE_CLIENT_TRANSMISSION) or \
                    (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.STATE_CLIENT_CLOSING):
                        print("Received FIN packet with sequence number " + str(pkt.SeqNo))
                        self.associatedSeqNum = pkt.SeqNo + 1
                        # send fin_ack and stop
                        self.sendFinAck()
                        time.sleep(1)
                        self.transport.close()
                        self.state = self.STATE_CLIENT_CLOSED



                    elif (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.STATE_CLIENT_CLOSING, self.seqNum + 1) or \
                    (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.STATE_CLIENT_CLOSED, self.seqNum + 1):
                        print("Received FIN_ACK packet with ack number " + str(pkt.AckNo))
                        self.state = self.STATE_CLIENT_CLOSED
                        print("Closing...")
                        self.transport.close()

                    else:
                        print("Client: Wrong packet: sequence num {!r}, type {!r}， current state: {!r}".format(pkt.SeqNo, pkt.Type, self.STATE_DESC[self.state]))
                else:
                    print("Wrong packet checksum: " + str(pkt.CRC))
            else:
                print("Wrong packet class type: {!r}, state: {!r} ".format(str(type(pkt)), self.STATE_DESC[self.state]))

    def prepareForFin(self):
        print("Preparing for FIN...")
        self.state = self.STATE_CLIENT_CLOSING
        self.transport.close()

    def connection_lost(self, exc):
        print("Connection closed")
        self.higherProtocol().connection_lost(exc)
        self.transport = None

    def isClosing(self):
        return self.state == self.STATE_CLIENT_CLOSING or self.state == self.STATE_CLIENT_CLOSED
