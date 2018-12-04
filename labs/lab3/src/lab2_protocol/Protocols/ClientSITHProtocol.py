from ..Packets.SITHPackets import SITHPacket
from ..Transports.SITHTransport import SITHTransport
from .SITHProtocol import SITHProtocol
from playground.common import CipherUtil
import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.asymmetric import x25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.asymmetric import ec


class ClientSITHProtocol(SITHProtocol):
    def __init__(self, higherProtocol=None):
        super().__init__(higherProtocol)
        # create private/pubic key pair
        self.private_key = X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        # create random value
        self.random = os.urandom(32)

        self.client_write = None
        self.client_read = None
        self.serverCert_public_key = None
        self.cert_private_key = None
        self.hash_hello = None
        self.certBytes = None

    def connection_made(self, transport):
        super().connection_made(transport)
        # load the certs of client
        pwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        with open(pwd + '/Certs/client.cert', 'r') as f0:
            self.certs_chain.append(f0.read())
        with open(pwd + '/Certs/1106_signed.cert', 'r') as f1:
            self.certs_chain.append(f1.read())
        with open(pwd + '/Certs/20184_root_signed.cert', 'r') as f:
            rootCertInStr = f.read()
        original_certs = self.certs_chain
        self.certs_chain = [CipherUtil.getCertFromBytes(c.encode("utf-8")) for c in original_certs]
        self.publicKey = self.certs_chain[0].public_key()
        self.rootCert = CipherUtil.getCertFromBytes(rootCertInStr.encode("utf-8"))
        # create hello packet
        self.certBytes = [CipherUtil.serializeCert(c) for c in self.certs_chain]
        helloPkt = SITHPacket.createHelloPacket(self, self.random, self.certBytes, self.public_key.public_bytes())
        self.hello_client = helloPkt.__serialize__()
        self.transport.write(helloPkt.__serialize__())
        self.state = self.CLIENT_HELLO
        print("Client: Send Hello to Server")

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, SITHPacket):
                if (pkt.Type == "HELLO") and (self.state == self.CLIENT_HELLO):
                    # Deserialize certs
                    self.other_side_Certs = [CipherUtil.getCertFromBytes(c) for c in pkt.Certificate]
                    if self.prove_Cert_Chain_Signature(self.other_side_Certs):
                        print("Client: received SithHello packet from server")
                        self.hello_server = pkt.__serialize__()
                        self.state = self.CLIENT_HELLO_RECEIVED

                        # derive key
                        self.serverCert_public_key = x25519.X25519PublicKey.from_public_bytes(pkt.PublicValue)
                        shared_secret = self.private_key.exchange(self.serverCert_public_key)
                        hash_value = hashes.Hash(hashes.SHA256(), backend = default_backend())
                        hash_value.update(self.hello_client + self.hello_server)
                        self.hash_hello = hash_value.finalize()
                        derived_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=self.hash_hello, backend=default_backend()).derive(shared_secret)
                        self.e_iv = derived_key[:12]
                        self.d_iv = derived_key[12:24]
                        self.client_read = derived_key[:16]
                        self.client_write = derived_key[16:]

                        # generate the cipher for data transmission
                        self.data_dec_cipher = AESGCM(self.client_read)
                        self.data_enc_cipher = AESGCM(self.client_write)
                        self.state = self.CLIENT_FINISH

                        # Generate signature for finish
                        pwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                        path = pwd + '/Certs/client_private_key.pem'
                        with open(path, "rb") as key_file:
                            self.cert_private_key = serialization.load_pem_private_key(key_file.read(), password=None, backend=default_backend())

                        signed_hello = self.cert_private_key.sign(
                            self.hash_hello,
                            ec.ECDSA(hashes.SHA256())
                        )

                        finishPkt = SITHPacket.createFinishPacket(self, signed_hello)
                        self.transport.write(finishPkt.__serialize__())

                    else:
                        print("Error: certificate verification failure.")
                        self.sendClosePkt(1)

                elif (pkt.Type == "FINISH") and self.state == self.CLIENT_FINISH:
                    print("Client: received handshake_finish packet from server")

                    # prove server's signature
                    serverCert_public_key = self.other_side_Certs[0].public_key()
                    server_signature = pkt.Signature

                    verify_result = self.prove_finish_signature(serverCert_public_key, server_signature, self.hash_hello)

                    if not verify_result:
                        print("Client: wrong signature of client")
                        print("Client is closing...")
                        self.sendClosePkt(1)
                    else:
                        self.state = self.CLIENT_TRANSMISSION

                        higherTransport = SITHTransport(self.transport, self)
                        self.higherProtocol().connection_made(higherTransport)

                elif (pkt.Type == "DATA") and self.state == self.CLIENT_TRANSMISSION:
                    print("Client: received application data from server")

                    self.higherProtocol().data_received(self.data_dec_cipher.decrypt(self.d_iv, pkt.Ciphertext, None))
                elif (pkt.Type == "CLOSE"):
                    self.transport.close()

                else:
                    print("Error: wrong packet type ")
                    self.sendClosePkt(1)

            else:
                print("Wrong packet")
                self.sendClosePkt(1)
