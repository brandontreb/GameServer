from twisted.internet.protocol import Factory
from twisted.internet.protocol import ClientFactory
from twisted.internet.protocol import Protocol
from twisted.internet import reactor
from struct import *

from models.player import Player
from models.server import Server
from models.room import Room
from models.message import Message
from util.messageReader import MessageReader
from util.messageWriter import MessageWriter
from lobbyClient import LobbyClientFactory

import messageHandler
import settings
import uuid

class PlayerConnection(Protocol):

	def __init__(self):		
		self.player = None		
		self.inBuffer = ""
		self.state = "WAITING_FOR_PLAYERS"

	def connectionMade(self):		
		yield

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
		if messageId == settings.MESSAGE_PLAYER_CONNECTED:
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

	def __init__(self,messageHandler,clientLobbyFactory):
		self.players = []
		self.playerCount = 0
		self.rooms = {}
		self.messageHandler = messageHandler
		self.lobbyClientFactory = clientLobbyFactory

	def playerConnected(self,protocol,playerID, roomID):
		
		# Normal player connection
		player = Player(protocol,playerID)
		player.playerID = playerID
		player.name = str(playerID)
		
		player.roomID = roomID
		protocol.player = player
		self.players.append(player)
		self.playerCount = self.playerCount + 1

		# Add the player to the room
		if self.rooms.has_key(player.roomID) == False or self.rooms[player.roomID].open == False:
			if(player.roomID == None or player.roomID == "Create" or (self.rooms.has_key(player.roomID) and self.rooms[player.roomID].open == False)):
				# Let the server create a room
				player.roomID = str(uuid.uuid1())
				self.rooms[player.roomID] = Room(player.roomID)
				print "Creating Generated Room " + str(player.roomID)
			else:				
				print "Creating Room " + str(player.roomID)			
				self.rooms[player.roomID] = Room(player.roomID)	

		self.rooms[player.roomID].players.append(player)
		player.room = self.rooms[player.roomID]

		if self.messageHandler != None:
			self.messageHandler.playerConnected(player)

		if self.lobbyClientFactory != None:
			self.lobbyClientFactory.client.sendServerStatus(None)


	def connectionLost(self,player):
		if self.messageHandler != None:
			self.messageHandler.playerDisconnected(player)
		
		if player != None and player.roomID != None:
			roomID = player.roomID
			if(self.rooms.has_key(roomID)):
				self.rooms[roomID].players.remove(player)
				if len(self.rooms[roomID].players) == 0:
					del self.rooms[roomID]

		self.playerCount = self.playerCount - 1
		
		if self.lobbyClientFactory != None:
			self.lobbyClientFactory.client.sendServerStatus(None)

	def getServerStatus(self):		
				
		rooms = self.rooms
		openRoomCount = 0

		for roomKey in self.rooms:
			room = self.rooms[roomKey]
			if room.open == True:
				openRoomCount = openRoomCount + 1			

		message = MessageWriter()
		message.writeByte(settings.MESSAGE_SERVER_STATUS)
		try:
			message.writeInt(self.playerCount)
		except:
			print "Unable to write player count " + str(self.playerCount)
			message.writeInt(0)
			
		message.writeInt(openRoomCount)

		for roomKey in self.rooms:
			room = self.rooms[roomKey]
			if room.open == True:
				message.writeString(room.roomID)
				message.writeInt(len(room.players))
		
		return message


""" Main class """
class RoomServer():
	def __init__(self,messageHandler):
		self.messageHandler = messageHandler
		self.clientLobbyFactory = LobbyClientFactory(self)			
		self.factory = PlayerConnectionFactory(self.messageHandler,self.clientLobbyFactory)
		self.port = settings.PORT_ROOM_DEFAULT

	def start(self,port,remoteServerAddress = None, remoteServerPort = None):
		self.port = port
		reactor.listenTCP(self.port, self.factory)

		# Connect to lobby
		if remoteServerAddress != None and remoteServerPort != None:
			reactor.connectTCP(remoteServerAddress, remoteServerPort, self.clientLobbyFactory)			

		reactor.run()
