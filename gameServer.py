from roomServer.roomServer import RoomServer
from roomServer.messageHandler import MessageHandler
from roomServer.util.messageWriter import MessageWriter

MESSAGE_PLAYER_CONNECTED = 0
MESSAGE_PLAYER_DISCONNECTED = 1
MESSAGE_PLAYER_MOVED = 2

class GameServer(MessageHandler):
	def __init__(self):
		self.roomServer = RoomServer(self)

	def start(self):
		self.roomServer.start(1955)

	def handleMessage(self,messageId,message,player):
		if messageId == MESSAGE_PLAYER_MOVED:
			self.playerMoved(player,message)

	def playerConnected(self, player):

		messagePlayerConnected = MessageWriter()
		messagePlayerConnected.writeByte(MESSAGE_PLAYER_CONNECTED)
		messagePlayerConnected.writeInt(player.playerID)

		# Notify the other players that the player connected
		for p in player.room.players:
			# commented for testing
			if p != player:			
				p.protocol.sendMessage(messagePlayerConnected)
		print "CONNECTED"

	def playerDisconnected(self,player):
		messagePlayerDisconnected = MessageWriter()
		messagePlayerDisconnected.writeByte(MESSAGE_PLAYER_DISCONNECTED)
		messagePlayerDisconnected.writeInt(player.playerID)

		# Notify the other players that the player disconnected
		for p in player.room.players:			
			if p != player:			
				p.protocol.sendMessage(messagePlayerDisconnected)

	# MESSAGES
	def playerMoved(self,player,message):
		x = message.readFloat()
		y = message.readFloat()
		z = message.readFloat()

		messagePlayerMoved = MessageWriter()
		messagePlayerMoved.writeByte(MESSAGE_PLAYER_MOVED)
		messagePlayerMoved.writeInt(player.playerID)
		messagePlayerMoved.writeFloat(x)
		messagePlayerMoved.writeFloat(y)
		messagePlayerMoved.writeFloat(z)		

		# Send the movement message to all players except the one who moved
		for p in player.room.players:
			# commented for testing
			if p != player:
				print "Sent MESSAGE_PLAYER_MOVED from "+str(player.playerID)+" to " + str(p.playerID) + " " + str(x) + " " + str(y) + " " + str(z)
				p.protocol.sendMessage(messagePlayerMoved)

gameServer = GameServer()
gameServer.start()