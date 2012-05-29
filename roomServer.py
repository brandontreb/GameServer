from twisted.internet.protocol import Factory
from twisted.internet.protocol import Protocol
from twisted.internet import reactor
from struct import *

from models.player import Player
from models.room import Room
from models.message import Message
from util.messageReader import MessageReader
from util.messageWriter import MessageWriter

import messageHandler

MESSAGE_PLAYER_CONNECTED = 0
MESSAGE_PLAYER_DISCONNECTED = 1
MESSAGE_PLAYER_MOVED = 2

class PlayerConnection(Protocol):

	def __init__(self):		
		self.player = None		
		self.inBuffer = ""
		self.state = "WAITING_FOR_PLAYERS"

	def connectionMade(self):		
		print "Connection Made" 

	def connectionLost(self, reason):
		self.log("Connection lost: %s" % str(reason))
		self.factory.connectionLost(self.player)	

	def log(self, message):
		if (self.player):
			print "%d: %s" % (self.player.playerID, message)
		else:
			print "%s: %s" % (self, message)

	def sendMessage(self, message):
		self.log("Sending message")
		msgLen = pack('!I', len(message.data))
		self.transport.write(msgLen)
		self.transport.write(message.data)

	def playerConnected(self,message):		
		playerID = message.readInt()
		roomID = message.readString()
		self.factory.playerConnected(self,playerID,roomID)

	def processMessage(self, message):
		messageId = message.readByte()

		# We need to process each message to check for player connected
		# This is the only way to ensure player objects get constructed
		if messageId == MESSAGE_PLAYER_CONNECTED:
			self.playerConnected(message)
		
		if self.factory.messageHandler != None:
			self.factory.messageHandler.handleMessage(messageId,message,self.player)		

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

class PlayerConnectionFactory(Factory):

	protocol = PlayerConnection

	def __init__(self,messageHandler):
		self.players = []
		self.rooms = {}
		self.nextPlayerID = 1
		self.messageHandler = messageHandler

	def playerConnected(self,protocol,playerID, roomID):
		player = Player(protocol,self.nextPlayerID)
		player.playerID = playerID
		player.name = str(playerID)
		player.roomID = roomID
		protocol.player = player
		self.players.append(player)
		self.nextPlayerID = self.nextPlayerID + 1	
		
		# Add the player to the room
		if self.rooms.has_key(player.roomID) == False:
			print "Creating Room " + str(player.roomID)			
			self.rooms[player.roomID] = Room(player.roomID)

		self.rooms[player.roomID].players.append(player)
		player.room = self.rooms[player.roomID]

		if self.messageHandler != None:
			self.messageHandler.playerConnected(player)

	def connectionLost(self,player):
		if self.messageHandler != None:
			self.messageHandler.playerDisconnected(player)
		roomID = player.roomID
		self.rooms[roomID].players.remove(player)
		if len(self.rooms[roomID].players) == 0:
			del self.rooms[roomID]

class RoomServer():
	def __init__(self,messageHandler):
		self.messageHandler = messageHandler
		self.factory = PlayerConnectionFactory(self.messageHandler)

	def start(self,port):
		reactor.listenTCP(port, self.factory)
		print "Server started"
		reactor.run()