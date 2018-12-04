from ..Packets.RIPPPacket import RIPPPacket
from ..Transports.RIPPTransport import RIPPTransport
from .RIPPProtocol import RIPPProtocol


class ClientProtocol(RIPPProtocol):

    def __init__(self):
        super().__init__()
        self.state = self.CLIENT_INITIAL
        print("%s Start client with state %s" % (self.__class__.__name__, self.STATE[self.state]))

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, RIPPPacket):
                if pkt.verify_CRC():
                    if  (RIPPPacket.TYPE_SYN + RIPPPacket.TYPE_ACK) in pkt.Type:
                        if self.state == self.CLIENT_SYN_SENT:
                            # check ackNo
                            if (pkt.AckNo >= self.seq_number):  #received syn_ack pkt from server
                                print("%s Received SYN_ACK packet with sequence number %s, ack number %s" \
                                      % (self.__class__.__name__, str(pkt.SeqNo), str(pkt.AckNo)))
                                self.state = self.CLIENT_TRANSMISSION
                                self.associated_seq_number = pkt.SeqNo + 1
                                # send the Ack packet
                                self.sendAckPkt()
                                higherTransport = RIPPTransport(self.transport, self)
                                self.higherProtocol().connection_made(higherTransport)
                            else:
                                print("%s Wrong SYN_ACK packet: ACK number %s " % (self.__class__.__name__, str(pkt.AckNo)))
                        else:
                            self.sendAckPkt()   #send ack anyway

                    elif pkt.Type == RIPPPacket.TYPE_ACK:
                        if self.state in (self.CLIENT_TRANSMISSION, self.CLIENT_CLOSING):
                            self.handleAckPkt(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_DATA, self.CLIENT_TRANSMISSION):
                        self.handleDataPkt(pkt)

                    elif (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.CLIENT_TRANSMISSION) or (pkt.Type, self.state) == (RIPPPacket.TYPE_FIN, self.CLIENT_CLOSING):
                        # terminate transmission when receive FIN
                        self.send_finack_then_close(pkt)

                    elif (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.CLIENT_CLOSING, self.seq_number + 1) or (pkt.Type, self.state, pkt.AckNo) == (RIPPPacket.TYPE_FIN + RIPPPacket.TYPE_ACK, self.CLIENT_CLOSED, self.seq_number + 1):
                        self.receive_finack_then_shutdown(self, pkt)
                    else:
                        print("%s Wrong packet: sequence num:%s, type:%s" % (self.__class__.__name__, str(pkt.SeqNo), str(pkt.Type)))
                else:
                    print("%s Wrong packet checksum: %s" % (self.__class__.__name__, str(pkt.CRC)))
            else:
                print("%s Wrong packet class type:%s ,state: %s" % (self.__class__.__name__, str(type(pkt), self.STATE[self.state])))
