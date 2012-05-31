from twisted.internet.protocol import Factory
from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import Protocol
from twisted.internet import reactor
from util.messageReader import MessageReader
from util.messageWriter import MessageWriter
from struct import *
import settings

"""Lobby Client """
class LobbyClient(Protocol):

	def __init__(self):
		self.inBuffer = ""		

	def sendMessage(self, message):
		msgLen = pack('!I', len(message.data))
		self.transport.write(msgLen)
		self.transport.write(message.data)

	def sendServerStatus(self,message):		
		server = self.factory.roomServer.factory
		self.sendMessage(server.getServerStatus())

	def processMessage(self,message):
		
		messageId = message.readByte()
		if messageId == settings.MESSAGE_REQUEST_SERVER_STATUS:
			self.sendServerStatus(message)

	def dataReceived(self, data):                
		self.inBuffer = self.inBuffer + data
        
		while(True):
			if (len(self.inBuffer) < 4):
				return;
            
			msgLen = unpack('!I', self.inBuffer[:4])[0]			
			
			if (len(self.inBuffer) < msgLen):
				print "returning " + str(len(self.inBuffer)) + " M:" + str(msgLen)
				return;
            
			messageString = self.inBuffer[4:msgLen+4]
			self.inBuffer = self.inBuffer[msgLen+4:]
            
			message = MessageReader(messageString)
			self.processMessage(message)			

	def connectionMade(self):
		print "Connected to Lobby Server"
		# Send message to join the RoomServer room		
		messagePlayerConnected = MessageWriter()
		messagePlayerConnected.writeByte(settings.MESSAGE_PLAYER_CONNECTED)
		messagePlayerConnected.writeInt(0)
		messagePlayerConnected.writeString("RoomServer")
		self.sendMessage(messagePlayerConnected)
		self.factory.setClient(self)

	def connectionLost(self, reason):
		print "connection lost"

class LobbyClientFactory(ClientFactory):
	protocol = LobbyClient

	def __init__(self,roomServer):
		self.roomServer = roomServer
		self.client = None

	def clientConnectionFailed(self, connector, reason):
		print "Connection failed - goodbye!"
		reactor.stop()

	def clientConnectionLost(self, connector, reason):
		print "Connection lost - goodbye!"

	def setClient(self,client):
		self.client = client
