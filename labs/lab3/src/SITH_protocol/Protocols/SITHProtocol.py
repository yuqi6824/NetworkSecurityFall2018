from playground.network.common import StackingProtocol
from ..Packets.SITHPackets import SITHPacket
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidSignature

class SITHProtocol(StackingProtocol):

    SERVER_HELLO = 10
    SERVER_HELLO_RECEIVED = 11
    SERVER_FINISH = 12
    SERVER_TRANSMISSION = 13
    SERVER_CLOSED = 14

    CLIENT_HELLO = 20
    CLIENT_HELLO_RECEIVED = 21
    CLIENT_FINISH = 22
    CLIENT_TRANSMISSION = 23
    CLIENT_CLOSED = 24

    STATE_DESC = {
        10: "SERVER_HELLO",
        11: "SERVER_HELLO_RECEIVED",
        12: "SERVER_FINISH",
        13: "SERVER_TRANSMISSION",
        14: "SERVER_CLOSED",
        20: "CLIENT_HELLO",
        21: "CLIENT_HELLO_RECEIVED",
        22: "CLIENT_FINISH",
        23: "CLIENT_TRANSMISSION",
        24: "CLIENT_CLOSED"
    }

    def __init__(self, higherProtocol=None):
        if higherProtocol:
            print("Initializing SITH layer")
        super().__init__(higherProtocol)
        self.deserializer = SITHPacket.Deserializer()
        self.hello_client = None
        self.hello_server = None
        self.privateKey = None
        self.publicKey = None
        self.rootCert = None
        self.certs_chain = []
        self.other_side_publicKey = None
        self.other_side_Certs = None
        self.data_enc_cipher = None
        self.data_dec_cipher = None
        self.e_iv = None # encrypt in client and decrypt in server
        self.d_iv = None # encrypt in server and decrypt in client
        self.verifier = None

    def connection_made(self, transport):
        print("Connection has been established at SITH layer")
        self.transport = transport

    def connection_lost(self, exc):
        print("Connection lost at SITH layer")
        self.higherProtocol().connection_lost(exc)
        self.transport = None

    def createDataPacket(self, nonce, data):
        ciphertext = self.data_enc_cipher.encrypt(nonce, data, None)
        dataPkt = SITHPacket.createDataPacket(self, ciphertext)
        return dataPkt

    def sendClosePkt(self, error=None):
        if error:
            print("Send Close with error: ")
        else:
            print("Send Close...")

    def prove_finish_signature(self, public_key, signature, hash_hello):
        try:
            public_key.verify(signature, hash_hello, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature:
            return False

    def prove_Cert_Chain_Signature(self, certs_chain):
        for i in range(len(certs_chain) - 1):
            cert = certs_chain[i]
            key = certs_chain[i + 1].public_key()
            self.verifier = key.verify
            try:
                # input signature and tbs_bytes
                self.verifier(cert.signature, cert.tbs_certificate_bytes, ec.ECDSA(hashes.SHA256()))
                result = True
            except InvalidSignature:
                print("InvalidSignature")
                result = False
            if not result:
                print("not authenticated certificate")
                return False
        print("Proved certificate")
        return True
