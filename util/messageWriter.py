from struct import *

class MessageWriter:

	def __init__(self):
		self.data = ""

	def writeByte(self, value):        
		self.data = self.data + pack('!B', value)

	def writeInt(self, value):
		self.data = self.data + pack('!I', value)

	def writeFloat(self, value):
		self.data = self.data + pack('<f', value)		

	def writeString(self, value):
		self.writeInt(len(value))
		packStr = '!%ds' % (len(value))
		self.data = self.data + pack(packStr, value)