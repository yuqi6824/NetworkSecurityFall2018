import asyncio
from ..Packets.RIPPPacket import RIPPPacket
from ..Transports.RIPPTransport import RIPPTransport
from .RIPPProtocol import RIPPProtocol
import time
from ..Timer import Timer


class ServerProtocol(RIPPProtocol):

    def __init__(self):
        super().__init__()
        self.state = self.STATE_SERVER_LISTEN
        print("Initialized server with state " + self.STATE[self.state])

    def connection_made(self, transport):
        super().connection_made(transport)
        self.transport = transport

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, RIPPPacket):
                if pkt.verifyChecksum():
                    if (pkt.Type, self.state) == (RIPPPacket.TYPE_SYN, self.STATE_SERVER_LISTEN):
                        print("Received SYN packet with sequence number " + str(pkt.SeqNo))
                        self.state = self.STATE_SERVER_SYN_ACK_SENT
                        self.associatedSeqNum = pkt.SeqNo + 1
                        synAck_seq = self.seqNum
                        self.sendSynAck(synAck_seq)
                        self.seqNum += 1

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_ACK, self.STATE_SERVER_SYN_ACK_SENT):
                        if pkt.AckNo == self.seqNum:
                            print("Received ACK packet with acknowledgement number " + str(pkt.AckNo))
                            self.state = self.STATE_SERVER_TRANSMISSION
                            higherTransport = RIPPTransport(self.transport, self)
                            self.higherProtocol().connection_made(higherTransport)
                        else:
                            print("Server: Wrong ACK packet: acknowledgement number: {!r}, seq number: {!r}, expected: {!r}, {!r}".format(pkt.AckNo, pkt.SeqNo, self.seqNum, self.associatedSeqNum))

                    elif pkt.Type == RIPPPacket.TYPE_ACK and self.state in (self.STATE_SERVER_TRANSMISSION, self.STATE_SERVER_CLOSING):
                        self.processAckPkt(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_DATA, self.STATE_SERVER_TRANSMISSION or self.STATE_SERVER_LISTEN):
                        self.processDataPkt(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.STATE_SERVER_TRANSMISSION) or\
                    (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.STATE_SERVER_CLOSING):
                        print("Received FIN packet with sequence number " + str(pkt.SeqNo))
                        self.associatedSeqNum = pkt.SeqNo + 1
                        # send fin ack and stop immediately
                        self.sendFinAck()
                        time.sleep(1)
                        self.transport.close()
                        self.state = self.STATE_SERVER_CLOSED

                    elif (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.STATE_SERVER_CLOSING, self.seqNum + 1) or \
                    (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.STATE_SERVER_CLOSED, self.seqNum + 1):
                        print("Received FIN_ACK packet with ack number " + str(pkt.AckNo))
                        self.state = self.STATE_SERVER_CLOSED
                        print("Closing...")
                        self.transport.close()

                    else:
                        print("Server: Wrong packet: seq num {!r}, type {!r}， current state: {!r}".format(pkt.SeqNo, pkt.Type, self.STATE[self.state]))
                else:
                    print("Wrong packet checksum: " + str(pkt.CRC))
            else:
                print("Wrong packet class type: {!r}, state: {!r} ".format(str(type(pkt)), self.STATE[self.state]))

    def prepareForFin(self):
        print("Preparing for Fin...")
        self.state = self.STATE_SERVER_CLOSING
        self.transport.close()

    def connection_lost(self, exc):
        print("Connection closed")
        self.higherProtocol().connection_lost(exc)

    def isClosing(self):
        return self.state == self.STATE_SERVER_CLOSING or self.state == self.STATE_SERVER_CLOSED
