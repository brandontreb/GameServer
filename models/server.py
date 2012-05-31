from player import Player

class Server(Player):
	def __init__(self,protocol,playerID):
		Player.__init__(self,protocol,playerID)
		self.load = 0.0
		self.playerCount = 0
		self.openRoomCount = 0
		self.rooms = []
		self.address = None
		self.port = None