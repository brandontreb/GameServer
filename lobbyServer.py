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

from messageHandler import MessageHandler
import settings

class LobbyPlayerConnection(Protocol):

	def __init__(self):		
		self.player = None		
		self.inBuffer = ""		

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

	def serverStatus(self,message):
		# ip is the server name
		ip,port = self.transport.socket.getpeername()
		# Find the server named ip in the RoomServer room
		server = None
		for s in self.factory.rooms["RoomServer"].players:
			if s.name == ip:
				server = s

		# Build a local representation of its open rooms
		# Used to determine which server the player should connect to
		server.rooms = []
		server.openRoomCount = 0

		if server != None:
			server.playerCount = message.readInt()
			print "PCount " + str(server.playerCount)
			server.openRoomCount = message.readInt()
			for i in range(0,server.openRoomCount):
				room = Room(message.readString())								
				room.playerCount = message.readInt()
				server.rooms.append(room)

			print str(server.rooms)
		else:
			print "No server with name " + ip + " found in " + str(self.factory.rooms)

		print "***Server Status***"
		print server.name
		print "Players: " + str(server.playerCount)
		print "Rooms: ("+str(server.openRoomCount)+")"
		for r in server.rooms:
			print r.roomID + " " + str(r.playerCount)

	def processMessage(self, message):
		messageId = message.readByte()

		# We need to process each message to check for player connected
		# This is the only way to ensure player objects get constructed
		if messageId == settings.MESSAGE_PLAYER_CONNECTED:
			self.playerConnected(message)		
		elif messageId == settings.MESSAGE_SERVER_STATUS:
			self.serverStatus(message)

		if self.factory.messageHandler != None:
			self.factory.messageHandler.handleMessage(messageId,message,self.player)		

	def dataReceived(self, data):		

		self.inBuffer = self.inBuffer + data
        
		while(True):
			if (len(self.inBuffer) < 4):
				return;
            
			msgLen = unpack('!I', self.inBuffer[:4])[0]			
			
			if (len(self.inBuffer) < msgLen):				
				return;
            
			messageString = self.inBuffer[4:msgLen+4]
			self.inBuffer = self.inBuffer[msgLen+4:]
            
			message = MessageReader(messageString)
			self.processMessage(message)			

class LobbyPlayerConnectionFactory(Factory):

	protocol = LobbyPlayerConnection

	def __init__(self,messageHandler):
		self.players = []		
		self.rooms = {}		
		self.messageHandler = messageHandler		

	def playerConnected(self,protocol,playerID, roomID):
		ip, port = protocol.transport.socket.getpeername()		

		if roomID != "RoomServer":
			# Normal player connection
			player = Player(protocol,playerID)
			player.playerID = playerID
			player.name = str(playerID)
		else: 
			# Special case where a room server connected to the lobby
			player = Server(protocol,playerID)
			player.address = ip
			player.port = settings.PORT_ROOM_DEFAULT
			player.playerID = playerID
			player.name = ip
		
		player.roomID = roomID
		protocol.player = player
		self.players.append(player)

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
		
		if player != None and player.roomID != None:
			roomID = player.roomID
			self.rooms[roomID].players.remove(player)
			if len(self.rooms[roomID].players) == 0:
				del self.rooms[roomID]

class GameLobby(MessageHandler):
	def __init__(self):
		self.messageHandler = self		
		self.factory = LobbyPlayerConnectionFactory(self.messageHandler)

	def start(self,port):
		self.port = port
		reactor.listenTCP(self.port, self.factory)
		reactor.run()

	def handleMessage(self,messageId,message,player):
		pass

	def getServerStatuses(self):
		# Refresh all server status when a player/server connects		
		if self.factory.rooms.has_key("RoomServer") == True:			
			roomServers = self.factory.rooms["RoomServer"].players			
			message = MessageWriter()
			message.writeByte(settings.MESSAGE_REQUEST_SERVER_STATUS)

			for roomServer in roomServers:
				roomServer.protocol.sendMessage(message)

	def playerConnected(self, player):
		if player.roomID != "Lobby" and player.roomID != "RoomServer":
			player.protocol.transport.loseConnection()
			print "Kicked non-lobby/non-server player."

		self.flushLobby()

	def flushLobby(self):
		if self.factory.rooms.has_key("Lobby") == True and self.factory.rooms.has_key("RoomServer") == True:
			print "flushing lobby"
			roomServers = self.factory.rooms["RoomServer"].players
			players = self.factory.rooms["Lobby"].players

			for player in players:
				# First check which server has an open room (highest priority)
				playerServer = None
				for roomServer in roomServers:
					openRooms = len(roomServer.rooms)
					if openRooms > 0:
						playerServer = roomServer
						print "Open room called " + roomServer.name
						break
				# Next pass, see which server has the LEAST amount of players
				# This fires only if there are no open rooms				
				if playerServer == None:
					playerServer = roomServers[0]
					for roomServer in roomServers:
						playerCount = roomServer.playerCount
						if playerCount < playerServer.playerCount:
							playerServer = roomServer		

				# At this point playerServer should not be None
				print "Sending player to " + playerServer.address+ " " + str(playerServer.port)			
				message = MessageWriter()
				message.writeByte(settings.MESSAGE_PLAYER_JOIN_ROOMSERVER)
				message.writeInt(playerServer.port)
				message.writeString(playerServer.address)				
				player.protocol.sendMessage(message)

		# after we are done, update the server status
		self.getServerStatuses()


	def playerDisconnected(self,player):
		pass

print "Lobby server listening on " + str(settings.PORT_LOBBY_DEFAULT)
gameLobby = GameLobby()
gameLobby.start(settings.PORT_LOBBY_DEFAULT)