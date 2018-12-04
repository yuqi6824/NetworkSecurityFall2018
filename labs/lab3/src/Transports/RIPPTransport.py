from playground.network.common import StackingTransport
from ..Packets.RIPPPacket import RIPPPacket
import time
from ..Timer import *


class RIPPTransport(StackingTransport):
    chunk_length = 1500
    timeout = 0.5
    timeout_max = 4

    def __init__(self, transport, protocol=None):
        super().__init__(transport)
        self.protocol = protocol

    def data_resend(self, ack):   #create a timer for each data pkt, resend data after timeout, give up it after timeout_max
        while ack in list(self.protocol.sentDataPkt):
            (dataPkt, timestamp) = self.protocol.sentDataPkt[ack]
            current_time = time.time()
            if current_time - timestamp < self.timeout_max:
                self.protocol.transport.write(dataPkt.__serialize__())
                print("%s Resending data packet with SeqNo: %s" % (self.protocol.__class__.__name__, str(dataPkt.SeqNo)))
                self.protocol.sentDataPkt[ack] = (dataPkt, timestamp)
                timer = Timer(self.timeout, self.data_resend, ack, self.protocol.loop)
                self.protocol.timers[ack] = timer
            else:
                print("%s Over the timeout_max, give up resend data packet  with SeqNo: %s"\
                      % (self.protocol.__class__.__name__, str(dataPkt.SeqNo)))
            break

    def pop(self):
        if len(self.protocol.DataInLine) > 0:
            (nextAck, dataPkt) = self.protocol.DataInLine.pop(0)  #pop the top data pkt from the waiting list
            print("%s Seding next data packet %s in DataInLine..." % (self.protocol.__class__.__name__, str(nextAck)))
            self.protocol.transport.write(dataPkt.__serialize__())   #send the data pkt just popped out of waiting list
            self.protocol.sentDataPkt[nextAck] = (dataPkt, time.time())   #put the data just sent into sent_buffer
            timer = Timer(self.timeout, self.data_resend, nextAck, self.protocol.loop)
            self.protocol.timers[nextAck] = timer   #add that timer into timer_list
            popData = backlog(0.4, self.pop, self.protocol.loop)   #set a timer that could automatically pop data pkt from the waiting list



    def write(self, data):
        print("%s: Get data from the upper layer, wrap it into package, and send it to lower layer..."  \
              % self.protocol.__class__.__name__)
        # receive the data from the upper layer, split it into chunks
        i = 0
        index = 0
        sentData = None
        while (i < len(data)):
            if (i + self.chunk_length < len(data)):  #if the rest of data's length is larger than chunk size, \
                # then get a chunk size of data from it
                sentData = data[i: i + self.chunk_length]
            else:
                sentData = data[i:]
            i += len(sentData)   #unpate i to be the length of the part of data that is already sent
            pkt = RIPPPacket.createDataPkt(self.protocol.seq_number, sentData)
            index += 1
            ackNumber = self.protocol.seq_number + len(sentData)
            if len(self.protocol.sentDataPkt) <= self.protocol.WINDOW_SIZE:
                print("%s: Sending packet, sequence number: %s " % (self.protocol.__class__.__name__, str(pkt.SeqNo)))
                self.protocol.transport.write(pkt.__serialize__())
                self.protocol.sentDataPkt[ackNumber] = (pkt, time.time())
                # resend data
                timer = Timer(self.timeout, self.data_resend, ackNumber, self.protocol.loop)
                self.protocol.timers[ackNumber] = timer
                # pop automatically
                popData = backlog(0.4, self.pop, self.protocol.loop)
            else:
                print("%s Buffering packet" % self.protocol.__class__.__name__)
                self.protocol.DataInLine.append((ackNumber, pkt))
            self.protocol.seq_number = self.protocol.seq_number + len(sentData)
        print("%s Transmission finished" % self.protocol.__class__.__name__)



    def close(self):
        if not self.protocol.isClosing():
            print("%s Preparing to close" % self.protocol.__class__.__name__)
            self.protocol.readyForFin()
        else:
            print("%s: Protocol is closed." % self.protocol.__class__.__name__)

