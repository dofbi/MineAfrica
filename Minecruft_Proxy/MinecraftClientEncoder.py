#!/usr/bin/python3

import multiprocessing
from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ClientEndpoint
from quarry.net.client import ClientFactory, SpawningClientProtocol
from quarry.net.auth import ProfileCLI
from Crypto.Cipher import AES

#This class handles encoding/decoding byte data to/from
#minecraft network packets. Uses a Reactor Design pattern
#for handling asynchronous packet delivery/receiving

class MinecraftClientEncoder(SpawningClientProtocol):
	def __init__(self, factory, remote_addr):
		self.packet_done = False
		self.AES_Block_Len = AES.block_size
		self.out_enc_buff = bytearray() 
		self.in_enc_buff = bytearray()
		super(MinecraftClientEncoder, self).__init__(factory, remote_addr)

	def update_player_full(self): 
		self.send_packet("player_position", self.buff_type.pack("ddd?", self.pos_look[0], self.pos_look[1], self.pos_look[2], True))

#Encoding Functions*************************************************************** 
	def get_byte_from_buff(self, buff): 
		if(len(buff) == 0): 
			buff_byte = 256; 
		else:
			buff_byte = buff.pop(0)
		return buff_byte

	def get_bytes_from_buff(self, buff, num_bytes): 
		buff_bytes = []
		for num in range(0, num_bytes):
			buff_byte = self.get_byte_from_buff(buff)
			buff_bytes.append(buff_byte)
		return buff_bytes

	def check_buff(self, buff):
		if len(buff) < 1 and self.factory.forwarding_packet_queue.qsize() > 0: 
			data = self.factory.forwarding_packet_queue.get()
			if(data != None): 
			#	print("Buff Len = " + str(len(data)))
				buff = bytearray(data)
			self.encode_player_look()
		return buff

	def check_packet_done_flag(self): 
		if self.packet_done: 
			self.encode_player_look()
			self.packet_done = False

	#This is the primary encoding method, it checks for data in the packet queue
	#and then turns the packets into Minecraft movements
	def encode(self): 
		if self.factory.forwarding_packet_queue.qsize() > 0 or len(self.out_enc_buff) > 0:
			if len(self.out_enc_buff) > 0: 
				self.encode_inventory_action()
				self.encode_player_position_and_look()
			
			self.out_enc_buff = self.check_buff(self.out_enc_buff)

			

	def encode_inventory_action(self):
		slot_id = 36 #perhaps add three bits here later 
		item_id = int(self.get_byte_from_buff(self.out_enc_buff))
		#self.logger.info(item_id)
		self.send_packet("creative_inventory_action", self.buff_type.pack('h',slot_id) + self.buff_type.pack_slot(item_id))
	
	#These movement methods rely on player positional data which was received from the server
	def encode_player_look(self):
		look_yaw = self.pos_look[3]
		look_pitch = self.pos_look[4]
		on_ground =	True 
		
		self.send_packet("player_look", self.buff_type.pack( 'ff?', look_yaw, look_pitch, on_ground))

	def encode_player_position(self):
		pos_x = self.pos_look[0]
		pos_y = self.pos_look[1]
		pos_z = self.pos_look[2]
		on_ground =	True 

		self.send_packet("player_position", self.buff_type.pack('ddd?', pos_x, pos_y, pos_z, on_ground))

	def encode_player_position_and_look(self): 
		out_bytes = self.get_bytes_from_buff(self.out_enc_buff, 2)
		
		#x_offset = int(out_bytes[0])
		#z_offset = int(out_bytes[1])
		yaw = int(out_bytes[0])
		pitch = int(out_bytes[1])
		#print(out_bytes)

		pos_x = self.pos_look[0] + 0.1 #x_offset/128.0 - 1.0
		pos_y = self.pos_look[1]
		pos_z = self.pos_look[2] + 0.1 #z_offset/128.0 - 1.0
		look_yaw = float(yaw * 1.0)
		look_pitch = float(pitch * 1.0) 
		on_ground =	True 

		self.send_packet("player_position_and_look", self.buff_type.pack( 'dddff?', pos_x, pos_y, pos_z, look_yaw, look_pitch, True))
	

	#def encode_place_and_remove_block(self):

	#This is when we set our hooks for the encode event to check for new web requests. 
	#def packet_login_success(self, buff):
		#super(MinecraftClientEncoder,self).packet_login_success(buff)

	#This method needed to be overloaded from the Spawning client protocol class
	#because it added unessary event loops
	def packet_player_position_and_look(self, buff):
		p_pos_look = buff.unpack('dddff')

		# 1.7.x
		if self.protocol_version <= 5:
			p_on_ground = buff.unpack('?')
			self.pos_look = p_pos_look

		# 1.8.x
		else:
			p_flags = buff.unpack('B')

		for i in range(5):
			if p_flags & (1 << i):
				self.pos_look[i] += p_pos_look[i]
			else:
				self.pos_look[i] = p_pos_look[i]

		# 1.9.x
		if self.protocol_version > 47:
			teleport_id = buff.unpack_varint()

		# Send Player Position And Look

		# 1.7.x
		if self.protocol_version <= 5:
			self.send_packet("player_position_and_look", self.buff_type.pack( 'ddddff?', self.pos_look[0], self.pos_look[1] - 1.62, self.pos_look[1], self.pos_look[2], self.pos_look[3], self.pos_look[4], True))

		# 1.8.x
		elif self.protocol_version <= 47:
			self.send_packet("player_position_and_look", self.buff_type.pack( 'dddff?', self.pos_look[0], self.pos_look[1], self.pos_look[2], self.pos_look[3], self.pos_look[4], True)) 
						        
        # 1.9.x
		else:
			self.send_packet("teleport_confirm", self.buff_type.pack_varint( teleport_id))

		if not self.spawned:
			#self.ticker.add_loop(1, self.update_player_inc)
			self.ticker.add_loop(1,self.encode)
			self.ticker.add_loop(20, self.update_player_full)
			self.spawned = True

#Decoding Functions***********************************************************************************
	#The decoding packet handlers fire whenever a new packet is sent by the server and
	#add each received TCP packet to the packet handler
	def update_incoming_buffer(self):
		incoming_q = self.factory.receiving_packet_queue
		incoming_q.put(self.in_enc_buff)	
		self.in_enc_buff = bytearray()

	def check_entity(self, data): 
		return True

	def packet_entity_head_look(self, buff): 
		entity_data = buff.unpack_varint()
		head_pos = buff.unpack("B")
		if self.check_entity(entity_data): 
			self.in_enc_buff.append(head_pos)
	
	def packet_spawn_mob(self, buff):
		buff.read()
	
	def packet_entity_relative_move(self, buff):
		enemy_id = buff.unpack_varint()
		enemy_pos = buff.unpack("hhh?")

	def packet_entity_look(self, buff):
		self.update_incoming_buffer()
		enemy_id = buff.unpack_varint()
		self.update_incoming_buffer()
		#Agreed enemy id for sending messages, negotiate with packages later
		if(enemy_id == 21445): 
			self.factory.receiving_packet_queue.put(None)

		enemy_look = buff.unpack("bb?")
		enemy_yaw = enemy_look[0]
		#print(enemy_yaw)
		buff.discard()

	def packet_entity_look_and_relative_move(self, buff):
		enemy_id = buff.unpack_varint()
		buff.read()


class MinecraftEncoderFactory(ClientFactory):
	protocol = MinecraftClientEncoder
	def __init__(self, profile = None, f_queue = None, r_queue = None ): 
		self.forwarding_packet_queue = f_queue
		self.receiving_packet_queue = r_queue
		super(MinecraftEncoderFactory, self).__init__(profile)


@defer.inlineCallbacks
def run(args):
	listy = multiprocessing.Queue()
	listy.put(bytearray(b'chocolate'))
	hold = multiprocessing.Queue()
	# Log in
	profile = yield ProfileCLI.make_profile(args)
# Create factory
	factory = MinecraftEncoderFactory(profile, listy, hold)
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
