from playground.network.common import StackingTransport
from .RIPPPacket import RIPPPacket
import time
import asyncio
import random
from .Timer import Timer
from .Timer import PopTimer


class RIPPTransport(StackingTransport):
    CHUNK_SIZE = 1500
    TIMEOUT = 0.5
    timeout_max = 4

    def __init__(self, transport, protocol=None):
        super().__init__(transport)
        self.protocol = protocol


    def resend(self, ack):
        while ack in list(self.protocol.sentDataCache):
            (dataPkt, timestamp) = self.protocol.sentDataCache[ack]
            current_time = time.time()
            if current_time - timestamp < self.timeout_max:
                self.protocol.transport.write(dataPkt.__serialize__())
                print("Resending data packet with SeqNo: "+ str(dataPkt.SeqNo))
                self.protocol.sentDataCache[ack] = (dataPkt, timestamp)
                timer = Timer(self.TIMEOUT, self.resend, ack, self.protocol.loop)
                self.protocol.timers[ack] = timer


            else:
                print("Over the timeout_max, give up resend data packet  with SeqNo: "+ str(dataPkt.SeqNo))
            break

    def pop(self):
        if len(self.protocol.sendingDataBuffer) > 0:
            (nextAck, dataPkt) = self.protocol.sendingDataBuffer.pop(0)
            print("Seding next data packet " + str(nextAck) + " in sendingDataBuffer...")
            self.protocol.transport.write(dataPkt.__serialize__())
            self.protocol.sentDataCache[nextAck] = (dataPkt, time.time())
            timer = Timer(self.TIMEOUT, self.resend, nextAck, self.protocol.loop)
            self.protocol.timers[nextAck] = timer

            popTimer = PopTimer(0.4, self.pop, self.protocol.loop)



    def write(self, data):
        #import pdb; pdb.set_trace()
        if self.protocol:
            if not self.protocol.isClosing():
                print("RIPPTransport: Write data to package")
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
                    pkt = RIPPPacket.createDataPacket(self.protocol.seqNum, sentData)
                    index += 1
                    ackNumber = self.protocol.seqNum + len(sentData)
                    #import pdb; pdb.set_trace()
                    if len(self.protocol.sentDataCache) <= self.protocol.WINDOW_SIZE:
                        print("RIPPTransport: Sending packet, sequence number:" + str(pkt.SeqNo))
                        #import pdb; pdb.set_trace()
                        self.protocol.transport.write(pkt.__serialize__())
                        self.protocol.sentDataCache[ackNumber] = (pkt, time.time())
                        #resend datapkt
                        timer = Timer(self.TIMEOUT, self.resend, ackNumber, self.protocol.loop)
                        self.protocol.timers[ackNumber] = timer
                        #pop automatically
                        popTimer = PopTimer(0.4, self.pop, self.protocol.loop)
                    else:
                        #self.protocol.sentDataCache.pop(0)
                        #self.protocol.sentDataCache.pop(1)
                        print("RIPPTransport: Buffering packet")
                        self.protocol.sendingDataBuffer.append((ackNumber, pkt))
                    self.protocol.seqNum += len(sentData)
                print("RIPPTransport: Batch transmission finished")
            else:
                print("RIPPTransport: Closing")

        else:
            print("Writing anyway")
            super().write(data)

    def close(self):
        if not self.protocol.isClosing():
            print("Preparing to close...")
            self.protocol.prepareForFin()
        else:
            print("RIPPTransport: Protocol is closed.")
