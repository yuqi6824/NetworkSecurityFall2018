from playground.network.common import StackingTransport
from ..RIPPPacket import RIPPPacket
import time
import asyncio
import random


class RIPPTransport(StackingTransport):
    CHUNK_SIZE = 1024

    def __init__(self, transport, protocol=None):
        super().__init__(transport)
        self.protocol = protocol

    def write(self, data):
        if self.protocol:
            if not self.protocol.isClosing():
                print("RIPPTransport: Write got {} bytes of data to package".format(len(data)))
                # Create data chunks
                i = 0
                index = 0
                sentData = None
                while (i < len(data)):
                    if (i + self.CHUNK_SIZE < len(data)):
                        sentData = data[i: i + self.CHUNK_SIZE]
                    else:
                        sentData = data[i:]
                    i += len(sentData)
                    pkt = RIPPPacket.makeDataPacket(self.protocol.seqNum, sentData)
                    index += 1
                    ackNumber = self.protocol.seqNum + len(sentData)
                    if len(self.protocol.sentDataCache) <= self.protocol.WINDOW_SIZE:
                        print("RIPPTransport: Sending packet {!r}, sequence number: {!r}".format(index, pkt.SeqNo))
                        self.protocol.transport.write(pkt.__serialize__())
                        self.protocol.sentDataCache[ackNumber] = (pkt, time.time())
                    else:
                        print("RIPPTransport: Buffering packet {!r}, sequence number: {!r}".format(index, pkt.SeqNo))
                        self.protocol.sendingDataBuffer.append((ackNumber, pkt))
                    self.protocol.seqNum += len(sentData)
                print("RIPPTransport: Batch transmission finished, number of packets sent: {!r}".format(index))
            else:
                print("RIPPTransport: protocol is closing, unable to write anymore.")

        else:
            print("RIPPTransport: Undefined protocol, writing anyway...")
            print("RIPPTransport: Write got {} bytes of data to pass to lower layer".format(len(data)))
            super().write(data)

    def close(self):
        # clear buffer then send FIN
        if not self.protocol.isClosing():
            print("Preparing to close...")
            self.protocol.prepareForFin()
        else:
            print("RIPPTransport: Protocol is closing.")
