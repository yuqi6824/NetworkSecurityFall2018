from playground.network.packet import PacketType
from playground.network.packet.fieldtypes import BUFFER, LIST, STRING
from playground.network.packet.fieldtypes.attributes import Optional


class SITHPacket(PacketType):

    TYPE_HELLO = "HELLO"
    TYPE_FINISH = "FINISH"
    TYPE_DATA = "DATA"
    TYPE_CLOSE = "CLOSE"

    DEFINITION_IDENTIFIER = "SITH.kandarp.packet.Base"
    DEFINITION_VERSION = "1.0"

    FIELDS = [
      ("Type", STRING({Optional: True})),  # HELLO, FINISH, DATA, CLOSE
      ("Random", BUFFER({Optional: True})),
      ("PublicValue", BUFFER({Optional: True})),
      ("Certificate", LIST(BUFFER)({Optional: True})),
      ("Signature", BUFFER({Optional: True})),
      ("Ciphertext", BUFFER({Optional: True}))
    ]

    def createHelloPacket(self, random, certs, public_key):
      pkt = SITHPacket()
      pkt.Type = pkt.TYPE_HELLO
      pkt.Random = random
      pkt.Certificate = certs
      pkt.PublicValue = public_key
      return pkt

    def createFinishPacket(self, signed_hello):
      pkt = SITHPacket()
      pkt.Type = pkt.TYPE_FINISH
      pkt.Signature = signed_hello
      return pkt

    def createDataPacket(self, ciphertext):
      pkt = SITHPacket()
      pkt.Type = pkt.TYPE_DATA
      pkt.Ciphertext = ciphertext
      return pkt

    def createClosePacket(self, error):
      pkt = SITHPacket()
      pkt.Type = self.TYPE_CLOSE
      pkt.Ciphertext = bytes(error)
      return pkt