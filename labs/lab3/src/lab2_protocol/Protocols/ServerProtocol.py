from ..Packets.RIPPPacket import RIPPPacket
from ..Transports.RIPPTransport import RIPPTransport
from .RIPPProtocol import RIPPProtocol


class ServerProtocol(RIPPProtocol):

    def __init__(self):
        super().__init__()
        self.state = self.SERVER_LISTEN
        print("%s Start server with state %s" % (self.__class__.__name__, self.STATE[self.state]))

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, RIPPPacket):
                if pkt.verify_CRC():
                    if (pkt.Type, self.state) == (RIPPPacket.TYPE_SYN, self.SERVER_LISTEN):
                        print("%s Received SYN packet with sequence number %s" % (self.__class__.__name__, str(pkt.SeqNo)))
                        self.associated_seq_number = pkt.SeqNo + 1
                        synAck_seq = self.seq_number
                        self.sendSynAckPkt(synAck_seq)
                        self.seq_number += 1
                        self.state = self.SERVER_SYN_ACK_SENT

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_ACK, self.SERVER_SYN_ACK_SENT):
                        if pkt.AckNo == self.seq_number:
                            print("%s Received ACK packet with acknowledgement number %s" % (self.__class__.__name__, str(pkt.AckNo)))
                            # establish transmission after receiving the correct ack packet
                            self.state = self.SERVER_TRANSMISSION
                            higherTransport = RIPPTransport(self.transport, self)
                            self.higherProtocol().connection_made(higherTransport)
                        else:
                            print("%s Wrong ACK packet: acknowledgement number:%s" % (self.__class__.__name__, str(pkt.AckNo)))

                    elif pkt.Type == RIPPPacket.TYPE_ACK and self.state in (self.SERVER_TRANSMISSION, self.SERVER_CLOSING):
                        self.handleAckPkt(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_DATA, self.SERVER_TRANSMISSION or self.SERVER_LISTEN):
                        self.handleDataPkt(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.SERVER_TRANSMISSION) or (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.SERVER_CLOSING):
                        self.send_finack_then_close(pkt)

                    elif (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.SERVER_CLOSING, self.seq_number + 1) or (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.SERVER_CLOSED, self.seq_number + 1):
                        self.receive_finack_then_shutdown(self, pkt)
                    else:
                        print("%s Wrong packet" % self.__class__.__name__)
                else:
                    print("%s Wrong packet checksum: %s" % (self.__class__.__name__, str(pkt.CRC)))
            else:
                print("%s Wrong packet class type" % self.__class__.__name__)
