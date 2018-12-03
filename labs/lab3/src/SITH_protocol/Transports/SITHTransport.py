from playground.network.common import StackingTransport


class SITHTransport(StackingTransport):
    def __init__(self, transport, protocol=None):
        super().__init__(transport)
        self.protocol = protocol

    def write(self, data):
        print("Write data to lower layer")
        dataPkt = self.protocol.createDataPacket(self.protocol.e_iv, data)
        super().write(dataPkt.__serialize__())

    def close(self):
        self.protocol.sendClosePkt()
