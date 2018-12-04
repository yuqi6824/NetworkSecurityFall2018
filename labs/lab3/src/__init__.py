from .Protocols.ClientProtocol import ClientProtocol
from .Protocols.ServerProtocol import ServerProtocol
from playground.network.common import StackingProtocolFactory
from .Protocols.ServerSITHProtocol import ServerSITHProtocol
from .Protocols.ClientSITHProtocol import ClientSITHProtocol

import playground

f_client = StackingProtocolFactory(ClientProtocol, ClientSITHProtocol)
f_server = StackingProtocolFactory(ServerProtocol, ServerSITHProtocol)

ptConnector = playground.Connector(protocolStack=(f_client, f_server))
SithConnector = playground.Connector(protocolStack=(f_client, f_server))
clientSithConnector = playground.Connector(protocolStack=f_client)
serverSithConnector = playground.Connector(protocolStack=f_server)

playground.setConnector("SITH_protocol", SithConnector)