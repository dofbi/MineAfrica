#!/usr/bin/python3
"""
Chat logger example client
This client stays in-game after joining. It prints chat messages received from
the server and slowly rotates (thanks c45y for the idea).
"""


from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ClientEndpoint
from quarry.net.client import ClientFactory, SpawningClientProtocol
from quarry.net.auth import ProfileCLI

class ChatLoggerProtocol(SpawningClientProtocol):
	def __init__(self, factory, remote_addr):
		# x, y, z, yaw, pitch
		self.incval = 0
		super(ChatLoggerProtocol, self).__init__(factory, remote_addr)
	def update_player_full(self): 
		pass
	def gogo(self):
		self.incval = self.incval + 0.1 
		print(self.incval)
		
		self.send_packet("player_position_and_look", self.buff_type.pack( 'dddff?', self.pos_look[0] + self.incval, self.pos_look[1], self.pos_look[2], self.pos_look[3], self.pos_look[4], True))

	def packet_chat_message(self, buff):
		p_text = buff.unpack_chat()

# 1.7.x
		if self.protocol_version <= 5:
			pass
			# 1.8.x
		else:
			p_position = buff.unpack('B')

			self.logger.info(":: %s" % p_text)

#This is when we set our hooks for our function call
	def packet_login_success(self, buff):
		super(ChatLoggerProtocol,self).packet_login_success(buff)
		self.ticker.add_loop(1, self.gogo)
		window_id = 0
		slot_id = 36
		item_id = 276
		self.send_packet("creative_inventory_action", self.buff_type.pack('h',slot_id) + self.buff_type.pack_slot(item_id))
		#self.send_packet("player_position_and_look", self.buff_type.pack("dddff?",-850, 3, 414, 1, 1, True))
class ChatLoggerFactory(ClientFactory):
	protocol = ChatLoggerProtocol
#	def connect(self, host, port=25565):
#		myconn = TCP4ClientEndpoint(reactor, host, port)
#		return myconn



@defer.inlineCallbacks
def run(args):
# Log in
	profile = yield ProfileCLI.make_profile(args)
# Create factory
	factory = ChatLoggerFactory(profile)
# Connect!
	factory.connect(args.host, args.port)

def main(argv):
	parser = ProfileCLI.make_parser()
	parser.add_argument("host")
	parser.add_argument("-p", "--port", default=25565, type=int)
	args = parser.parse_args(argv)

	run(args)
	reactor.run()

if __name__ == "__main__":
	import sys
	main(sys.argv[1:])
