from playground.network.common import StackingTransport
from .RIPPPacket import RIPPPacket
import time
from .Timer import Timer
from .Timer import backlog


class RIPPTransport(StackingTransport):
    CHUNK_SIZE = 1500
    TIMEOUT = 0.5
    timeout_max = 4

    def __init__(self, transport, protocol=None):
        super().__init__(transport)
        self.protocol = protocol


    def resend(self, ack):
        while ack in list(self.protocol.sentDataPkt):
            (dataPkt, timestamp) = self.protocol.sentDataPkt[ack]
            current_time = time.time()
            if current_time - timestamp < self.timeout_max:
                self.protocol.transport.write(dataPkt.__serialize__())
                print("Resending data packet with SeqNo: "+ str(dataPkt.SeqNo))
                self.protocol.sentDataPkt[ack] = (dataPkt, timestamp)
                timer = Timer(self.TIMEOUT, self.resend, ack, self.protocol.loop)
                self.protocol.timers[ack] = timer
            else:
                print("Over the timeout_max, give up resend data packet  with SeqNo: "+ str(dataPkt.SeqNo))
            break

    def pop(self):
        if len(self.protocol.DataInLine) > 0:
            (nextAck, dataPkt) = self.protocol.DataInLine.pop(0)
            print("Seding next data packet " + str(nextAck) + " in DataInLine...")
            self.protocol.transport.write(dataPkt.__serialize__())
            self.protocol.sentDataPkt[nextAck] = (dataPkt, time.time())
            timer = Timer(self.TIMEOUT, self.resend, nextAck, self.protocol.loop)
            self.protocol.timers[nextAck] = timer

            popData = backlog(0.4, self.pop, self.protocol.loop)



    def write(self, data):
        if self.protocol:
            print("RIPPTransport: Write data to package")
            # Create data chunks
            i = 0
            index = 0
            sentData = None
            while (i < len(data)):
                #print(111111111111111111111111111111)
                if (i + self.CHUNK_SIZE < len(data)):
                    #print(222222222222222222222222222)
                    sentData = data[i: i + self.CHUNK_SIZE]
                else:
                    #print(3333333333333333333333)
                    sentData = data[i:]
                i += len(sentData)
                pkt = RIPPPacket.createDataPacket(self.protocol.seqNum, sentData)
                index += 1
                ackNumber = self.protocol.seqNum + len(sentData)
                if len(self.protocol.sentDataPkt) <= self.protocol.WINDOW_SIZE:
                    print("RIPPTransport: Sending packet, sequence number:" + str(pkt.SeqNo))
                    self.protocol.transport.write(pkt.__serialize__())
                    self.protocol.sentDataPkt[ackNumber] = (pkt, time.time())
                    # resend data
                    timer = Timer(self.TIMEOUT, self.resend, ackNumber, self.protocol.loop)
                    self.protocol.timers[ackNumber] = timer
                    # pop automatically
                    popData = backlog(0.4, self.pop, self.protocol.loop)
                else:
                    #self.protocol.sentDataPkt.pop(0)
                    #self.protocol.sentDataPkt.pop(1)
                    print("Buffering packet")
                    self.protocol.DataInLine.append((ackNumber, pkt))
                self.protocol.seqNum = self.protocol.seqNum + len(sentData)
            print("Transmission finished")

        else:
            print("Write anyway")
            super().write(data)

    def close(self):
        if not self.protocol.isClosing():
            print("Preparing to close")
            self.protocol.readyForFin()
        else:
            print("RIPPTransport: Protocol is closed.")
