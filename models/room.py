class Room:
	def __init__(self,roomID):
		self.roomID = roomID
		self.open = True
		self.players = []
		self.playerCount = 0