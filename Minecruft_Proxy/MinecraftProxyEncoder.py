#!/usr/bin/python3

import multiprocessing
from twisted.internet import reactor
from quarry.net.proxy import DownstreamFactory, Upstream, UpstreamFactory, Bridge
from quarry.types import uuid
from Crypto.Cipher import AES

#Each Client and Proxy needs to keep track of which enemy is their own. 
class MinecraftProxyBridge(Bridge):
	quiet_mode = False
	events_enabled = False
	
	def __init__(self, downstream_factory, downstream): 
		self.clients_and_positions = []
		self.packet_done = False
		self.block_len = AES.block_size

		#We will need one for each client
		self.out_enc_buff = bytearray() #going out to client
		self.in_enc_buff = bytearray() #coming from client

		super().__init__(downstream_factory, downstream)

	def get_byte_from_buff(self, buff): 
		buff = self.check_buff(buff)
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
		if len(buff) < 1 and self.downstream.factory.forwarding_packet_queue.qsize() > 0: 
			data = self.downstream.factory.forwarding_packet_queue.get()
			if(data != None): 
				buff = bytearray(data)
			self.packet_done = True
		return buff

	def check_packet_done_flag(self): 
		if self.packet_done: 
			self.enemy_enc_look()
			self.packet_done = False

	def encode(self): 
		if self.downstream.factory.forwarding_packet_queue.qsize() > 0 or len(self.out_enc_buff) > 0:
			if len(self.out_enc_buff) > 0: 
				self.enemy_enc_head_look(21445)
				self.enemy_enc_head_look(21446)
				self.enemy_enc_head_look(21447)
				self.enemy_enc_head_look(21448)
			else: 
				self.out_enc_buff = self.check_buff(self.out_enc_buff)

			self.check_packet_done_flag()

	def enemy_enc_head_look(self, enemy_id): 
		val = 0
		yaw = self.get_byte_from_buff(self.out_enc_buff)
		self.downstream.send_packet("entity_head_look", self.downstream.buff_type.pack_varint(enemy_id), self.downstream.buff_type.pack("B", yaw ))

	def enemy_enc_look(self): 
		mid = 21445
		yaw = 1 
		val = 2 
		self.downstream.send_packet("entity_look", self.downstream.buff_type.pack_varint(mid), self.downstream.buff_type.pack("BB?", yaw, val, True ))
		#mid is the entity id - we need to assign ids to clients - gen id, and then watch for that id.
		#self.downstream.send_packet("entity_relative_move", self.downstream.buff_type.pack_varint(mid), self.downstream.buff_type.pack("hhh?", 300, 0, 0, True)) 

	def enemy_enc_move(self, position):
		#self.downstream.send_packet
		#self.logger.info("sent")
		if(position): 
			chosen_client = self.downstream
			x = position[0] - 1
			y = position[1]  
			z = position[2] + 1 
			z1 = 1
			z2 = 1
			z3 = 1 
			z4 = 1
			z5 = 1
			z6 = 1
			mid = 21445
			did =  58 

			chosen_client.send_packet("spawn_mob",chosen_client.buff_type.pack_varint(mid) + chosen_client.buff_type.pack_uuid(uuid.UUID.random()) + self.downstream.buff_type.pack_varint(did) + chosen_client.buff_type.pack("dddbbbhhhB", x, y, z, z1, z2, z3, z4, z5, z6, 255))

			chosen_client.send_packet("spawn_mob",chosen_client.buff_type.pack_varint(mid+1) + chosen_client.buff_type.pack_uuid(uuid.UUID.random()) + self.downstream.buff_type.pack_varint(did) + chosen_client.buff_type.pack("dddbbbhhhB", x+1, y, z+3, z1, z2, z3, z4, z5, z6, 255))
			
			chosen_client.send_packet("spawn_mob",chosen_client.buff_type.pack_varint(mid+2) + chosen_client.buff_type.pack_uuid(uuid.UUID.random()) + self.downstream.buff_type.pack_varint(did) + chosen_client.buff_type.pack("dddbbbhhhB", x-2, y, z-6, z1, z2, z3, z4, z5, z6, 255))
			
			chosen_client.send_packet("spawn_mob",chosen_client.buff_type.pack_varint(mid+3) + chosen_client.buff_type.pack_uuid(uuid.UUID.random()) + self.downstream.buff_type.pack_varint(did) + chosen_client.buff_type.pack("dddbbbhhhB", x+7, y, z-20, z1, z2, z3, z4, z5, z6, 255))
#--------------------------------------------------------------------
	def update_incoming_buffer(self):
		self.downstream_factory.receiving_packet_queue.put(self.in_enc_buff)
		self.in_enc_buff = bytearray()


	#def packet_downstream_spawn_mob(self, buff):
		#buff.discard()

	#def packet_downstream_entity_relative_move(self, buff): 
		#buff.discard()

	def packet_upstream_creative_inventory_action(self, buff): 
		buff.save()
		buff.unpack("h")
		slot_num  = buff.unpack_slot()
		item_num = slot_num["item"]
		if(item_num < 256): 
			self.in_enc_buff.append(item_num)

		buff.restore()
		self.upstream.send_packet("creative_inventory_action", buff.read())

	#When the player sends just a look command, that means the packet
	#is finished
	def packet_upstream_player_look(self, buff): 
		buff.save()
		self.update_incoming_buffer()
		self.downstream_factory.receiving_packet_queue.put(None)
		buff.restore()
		self.upstream.send_packet("player_look", buff.read())

	def packet_upstream_player_position(self, buff): 
		buff.save()
		buff.restore()
		self.upstream.send_packet("player_position", buff.read())

	def packet_upstream_player_position_and_look(self, buff): 
		buff.save()

		pos_x = buff.unpack("d")
		buff.unpack("d")
		pox_z = buff.unpack("d")

		#pos_x = self.pos_look[0] + x_offset/128.0 - 1.0
		#pos_y = self.pos_look[1]
		#pos_z = self.pos_look[2] + z_offset/128.0 - 1.0
	
		yaw = int(buff.unpack("f")) 
		pitch = int(buff.unpack("f"))
	
		if yaw != 256:
			self.in_enc_buff.append(yaw)

		if pitch != 256:
			self.in_enc_buff.append(pitch)

		buff.restore()
		self.upstream.send_packet("player_position_and_look", buff.read())

	#This packet is only sent if the player dies, or if he is joining
	def packet_downstream_player_position_and_look(self, buff): 
		buff.save()
		pos_and_look_struct = buff.unpack("dddff")
		self.downstream.ticker.add_loop(1, self.encode)
		self.clients_and_positions.append((self.downstream, pos_and_look_struct))
		self.enemy_enc_move(pos_and_look_struct)
		buff.restore()
		self.downstream.send_packet("player_position_and_look", buff.read())
	
class MinecraftProxyFactory(DownstreamFactory):
	bridge_class = MinecraftProxyBridge
	motd = "Proxy Server"
	forwarding_packet_queue = None
	def __init__(self, c_p_queue = None, s_p_queue = None):
		self.receiving_packet_queue = s_p_queue
		self.forwarding_packet_queue = c_p_queue
		super(MinecraftProxyFactory, self).__init__()


def main(argv):
# Parse options
	import argparse
	parser = argparse.ArgumentParser()
	parser.add_argument("-a", "--listen-host", default="", help="address to listen on")
	parser.add_argument("-p", "--listen-port", default=25565, type=int, help="port to listen on")
	parser.add_argument("-b", "--connect-host", default="127.0.0.1", help="address to connect to")
	parser.add_argument("-q", "--connect-port", default=25565, type=int, help="port to connect to")
	args = parser.parse_args(argv)

# Create factory
	melist = multiprocessing.Queue()
	melist2 = multiprocessing.Queue()
	factory = MinecraftProxyFactory(melist, melist2)
	factory.online_mode = False
	factory.force_protocol_version = 340 
	factory.connect_host = args.connect_host
	factory.connect_port = args.connect_port

# Listen
	factory.listen(args.listen_host, args.listen_port)
	reactor.run()

if __name__ == "__main__":
	import sys
	main(sys.argv[1:])





