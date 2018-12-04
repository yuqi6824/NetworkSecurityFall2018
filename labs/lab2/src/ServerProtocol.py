from .RIPPPacket import RIPPPacket
from .RIPPTransport import RIPPTransport
from .RIPPProtocol import RIPPProtocol
import time


class ServerProtocol(RIPPProtocol):

    def __init__(self):
        super().__init__()
        self.state = self.SERVER_LISTEN
        print("Start server with state " + self.STATE[self.state])

    def connection_made(self, transport):
        super().connection_made(transport)
        self.transport = transport

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, RIPPPacket):
                if pkt.verifyChecksum():
                    if (pkt.Type, self.state) == (RIPPPacket.TYPE_SYN, self.SERVER_LISTEN):
                        print("Received SYN packet with sequence number " + str(pkt.SeqNo))
                        self.associatedSeqNum = pkt.SeqNo + 1
                        synAck_seq = self.seqNum
                        self.sendSynAck(synAck_seq)
                        self.seqNum += 1
                        self.state = self.SERVER_SYN_ACK_SENT

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_ACK, self.SERVER_SYN_ACK_SENT):
                        if pkt.AckNo == self.seqNum:
                            print("Received ACK packet with acknowledgement number " + str(pkt.AckNo))
                            # establish transmission after receiving the correct ack packet
                            self.state = self.SERVER_TRANSMISSION
                            higherTransport = RIPPTransport(self.transport, self)
                            self.higherProtocol().connection_made(higherTransport)
                        else:
                            print("Wrong ACK packet: acknowledgement number:"+str(pkt.AckNo))

                    elif pkt.Type == RIPPPacket.TYPE_ACK and self.state in (self.SERVER_TRANSMISSION, self.SERVER_CLOSING):
                        self.handleAckPacket(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_DATA, self.SERVER_TRANSMISSION or self.SERVER_LISTEN):
                        self.handleDataPacket(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.SERVER_TRANSMISSION) or (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.SERVER_CLOSING):
                        print("Received FIN packet with sequence number " + str(pkt.SeqNo))
                        self.associatedSeqNum = pkt.SeqNo + 1
                        # send fin_ack packet and stop immediately
                        self.sendFinAck()
                        time.sleep(1)
                        self.transport.close()
                        self.state = self.SERVER_CLOSED

                    elif (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.SERVER_CLOSING, self.seqNum + 1) or (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.SERVER_CLOSED, self.seqNum + 1):
                        print("Received FIN_ACK packet with ack number " + str(pkt.AckNo))
                        self.state = self.SERVER_CLOSED
                        self.transport.close()

                    else:
                        print("Wrong packet")
                else:
                    print("Wrong packet checksum: " + str(pkt.CRC))
            else:
                print("Wrong packet class type")

    def readyForFin(self):
        print("Preparing for Fin")
        self.state = self.SERVER_CLOSING
        self.transport.close()

    def connection_lost(self, exc):
        print("Connection closed")
        self.higherProtocol().connection_lost(exc)
