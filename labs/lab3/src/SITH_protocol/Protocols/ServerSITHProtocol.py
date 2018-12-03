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


class ServerSITHProtocol(SITHProtocol):
    def __init__(self, higherProtocol=None):
        super().__init__(higherProtocol)
        self.state = self.SERVER_HELLO
        # create private/public key pair
        self.private_key = X25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()
        # create random value
        self.random = os.urandom(32)

        self.server_write = None
        self.server_read = None
        self.clientCert_public_key = None
        self.cert_private_key = None
        self.hash_hello = None
        self.certBytes = None

    def connection_made(self, transport):
        super().connection_made(transport)
        # load certs of server
        pwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        with open(pwd + '/Certs/server.cert', 'r') as f0:
            self.certs_chain.append(f0.read())
        with open(pwd + '/Certs/1106_signed.cert', 'r') as f1:
            self.certs_chain.append(f1.read())
        with open(pwd + '/Certs/20184_root_signed.cert', 'r') as f:
            rootCertInStr = f.read()
        original_certs = self.certs_chain
        self.certs_chain = [CipherUtil.getCertFromBytes(c.encode("utf-8")) for c in original_certs]
        self.publicKey = self.certs_chain[0].public_key()
        self.rootCert = CipherUtil.getCertFromBytes(rootCertInStr.encode("utf-8"))

    def data_received(self, data):
        self.deserializer.update(data)
        for pkt in self.deserializer.nextPackets():
            if isinstance(pkt, SITHPacket):
                if (pkt.Type == "HELLO") and (self.state == self.SERVER_HELLO):
                    self.other_side_Certs = [CipherUtil.getCertFromBytes(c) for c in pkt.Certificate]
                    if self.prove_Cert_Chain_Signature(self.other_side_Certs):
                        print("Server: Receive Hello from Client")
                        # store the hello from client
                        self.hello_client = pkt.__serialize__()
                        self.other_side_publicKey = self.other_side_Certs[0].public_key()

                        # create hello packet
                        self.certBytes = [CipherUtil.serializeCert(c) for c in self.certs_chain]
                        print("Server: send Hello to client... ")
                        # store the hello from server
                        helloPkt = SITHPacket.createHelloPacket(self, self.random, self.certBytes, self.public_key.public_bytes())
                        self.hello_server = helloPkt.__serialize__()
                        
                        self.transport.write(helloPkt.__serialize__())
                        self.state = self.SERVER_HELLO_RECEIVED

                        # derive key
                        self.clientCert_public_key = x25519.X25519PublicKey.from_public_bytes(pkt.PublicValue)
                        shared_secret = self.private_key.exchange(self.clientCert_public_key)
                        hash_value = hashes.Hash(hashes.SHA256(), backend = default_backend())
                        hash_value.update(self.hello_client + self.hello_server)
                        self.hash_hello = hash_value.finalize()
                        derived_key = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=self.hash_hello, backend=default_backend()).derive(shared_secret)
                        self.e_iv = derived_key[12:24]
                        self.d_iv = derived_key[:12]
                        self.server_write = derived_key[:16]
                        self.server_read = derived_key[16:]
                        self.data_enc_cipher = AESGCM(self.server_write)
                        self.data_dec_cipher = AESGCM(self.server_read)
                        self.state = self.SERVER_FINISH

                    else:
                        print("Error: certificate verification failure.")
                        self.sendClosePkt(1)

                elif (pkt.Type == "FINISH") and (self.state == self.SERVER_FINISH):

                    print("Server: received handshake_finish packet from client")
                    # prove client's signature
                    clientCert_public_key = self.other_side_Certs[0].public_key()
                    client_signature = pkt.Signature

                    verify_result = self.prove_finish_signature(clientCert_public_key, client_signature, self.hash_hello)

                    if not verify_result:
                        print("Server: wrong signature of client!")
                        print("Server is closing...")
                        self.sendClosePkt(1)
                    else:
                        # Generate Signature for FINISH
                        pwd = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                        path = pwd + '/Certs/server_private_key.pem'
                        with open(path, "rb") as key_file:
                            self.cert_private_key = serialization.load_pem_private_key(key_file.read(), password=None, backend=default_backend())
                        signed_hello = self.cert_private_key.sign(
                            self.hash_hello,
                            ec.ECDSA(hashes.SHA256())
                        )
                        finishPkt = SITHPacket.createFinishPacket(self, signed_hello)
                        self.transport.write(finishPkt.__serialize__())

                        self.state = self.SERVER_TRANSMISSION
                        higherTransport = SITHTransport(self.transport, self)
                        self.higherProtocol().connection_made(higherTransport)

                        higherTransport = SITHTransport(self.transport, self)
                        self.higherProtocol().connection_made(higherTransport)

                elif (pkt.Type == "DATA") and self.state == self.SERVER_TRANSMISSION:
                    print("Server: Received data from client")
                    print("Verification succeeded")
                    self.higherProtocol().data_received(self.data_dec_cipher.decrypt(self.d_iv, pkt.Ciphertext, None))

                elif (pkt.Type == "CLOSE"):
                    self.transport.close()

                else:
                    print("Error: wrong packet type ")
                    self.sendClosePkt(1)

            else:
                print("Wrong packet")
                self.sendClosePkt(1)
