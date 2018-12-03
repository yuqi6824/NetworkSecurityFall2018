from .RIPPPacket import RIPPPacket
from .RIPPTransport import RIPPTransport
from .RIPPProtocol import RIPPProtocol
import time
from .Timer import Timer


class ClientProtocol(RIPPProtocol):

    def __init__(self):
        super().__init__()
        self.state = self.CLIENT_INITIAL_SYN
        print("Start client with state " + self.STATE[self.state])

    def connection_made(self, transport):
        self.transport = transport
        super().connection_made(transport)
        if self.state == self.CLIENT_INITIAL_SYN:
            self.sendSyn()
            self.seqNum += 1
            self.state = self.CLIENT_SYN_SENT

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, RIPPPacket):
                if pkt.verifyChecksum():
                    if pkt.Type == (RIPPPacket.TYPE_SYN + RIPPPacket.TYPE_ACK):
                        if self.state == self.CLIENT_SYN_SENT:
                            # check ackNo
                            if (pkt.AckNo >= self.seqNum):
                                print("Received SYN_ACK packet with sequence number " + str(pkt.SeqNo) + ", ack number " + str(pkt.AckNo))
                                self.state = self.CLIENT_TRANSMISSION
                                self.associatedSeqNum = pkt.SeqNo + 1
                                # send the Ack packet
                                self.sendAck()
                                higherTransport = RIPPTransport(self.transport, self)
                                self.higherProtocol().connection_made(higherTransport)
                            else:
                                print("Wrong SYN_ACK packet: ACK number" + str(pkt.AckNo))
                        else:
                            self.sendAck()

                    elif pkt.Type == RIPPPacket.TYPE_ACK:
                        if self.state in (self.CLIENT_TRANSMISSION, self.CLIENT_CLOSING):
                            self.handleAckPacket(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_DATA, self.CLIENT_TRANSMISSION):
                        self.handleDataPacket(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.CLIENT_TRANSMISSION) or (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.CLIENT_CLOSING):
                        # terminate transmission when receive FIN
                        print("Received FIN packet with sequence number " + str(pkt.SeqNo))
                        self.associatedSeqNum = pkt.SeqNo + 1
                        # send fin_ack and stop
                        self.sendFinAck()
                        time.sleep(1)
                        self.transport.close()
                        self.state = self.CLIENT_CLOSED

                    elif (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.CLIENT_CLOSING, self.seqNum + 1) or (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.CLIENT_CLOSED, self.seqNum + 1):
                        print("Received FIN_ACK packet with ack number " + str(pkt.AckNo))
                        self.state = self.CLIENT_CLOSED
                        self.transport.close()

                    else:
                        print("Wrong packet: sequence num:" + str(pkt.SeqNo) + ", type:" + str(pkt.Type))
                else:
                    print("Wrong packet checksum: " + str(pkt.CRC))
            else:
                print("Wrong packet class type:" + str(type(pkt) + ",state: " + self.STATE[self.state]))

    def readyForFin(self):
        print("Preparing for FIN")
        self.state = self.CLIENT_CLOSING
        self.transport.close()

    def connection_lost(self, exc):
        print("Connection closed")
        self.higherProtocol().connection_lost(exc)
        self.transport = None

    def isClosing(self):
        return self.state == self.CLIENT_CLOSING or self.state == self.CLIENT_CLOSED
