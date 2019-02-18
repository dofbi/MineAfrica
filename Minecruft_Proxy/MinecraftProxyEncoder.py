#!/usr/bin/python3

import multiprocessing
from twisted.internet import reactor
from quarry.net.proxy import DownstreamFactory, Bridge
from quarry.types import uuid
from Crypto.Cipher import AES

#Each Client and Proxy needs to keep track of which enemy is their own. 
class QuietBridge(Bridge):
	quiet_mode = False
	events_enabled = False
	
	def __init__(self, downstream_factory, downstream): 
		self.clients_and_positions = []
		self.block_len = AES.block_size

		#We will need one for each client
		self.out_enc_buff = bytearray() #going out to client
		self.in_enc_buff = bytearray() #coming from client

		super().__init__(downstream_factory, downstream)
		
	def packet_upstream_player_position_and_look(self, buff):
		buff.save()
		message = buff.read() 
		#print(self.downstream.connect_host + str(self.downstream.connect_port))
		#self.downstream_factory.receiving_packet_queue.put(message)
		#self.logger.info(self.downstream_factory.receiving_packet_queue)
		buff.restore()
		self.upstream.send_packet("player_position_and_look", buff.read())
	
	def check_buff(self): 
		data = self.downstream_factory.forwarding_packet_queue.get()
		if data != None: 
			self.out_enc_buff = bytearray(data)
		else: 
			self.enemy_enc_look()

	def encode(self): 
		if self.downstream_factory.forwarding_packet_queue.qsize() > 0 or len(self.out_enc_buff) > 0:
			if len(self.out_enc_buff) > 0: 
				self.enemy_enc_head_look(21445)
			else: 
				self.check_buff()
    
	def enemy_enc_head_look(self, enemy_id): 
		yaw = self.out_enc_buff.pop(0)
		val = 0
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

#--------------------------------------------------------------------
	def check_incoming_buffer(self):
		if(len(self.in_enc_buff) == self.block_len):
			self.downstream_factory.receiving_packet_queue.put(self.in_enc_buff)
			#print(self.in_enc_buff)
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
			self.check_incoming_buffer()
			self.in_enc_buff.append(item_num)

		buff.restore()
		self.upstream.send_packet("creative_inventory_action", buff.read())

	#When the player sends just a look command, that means the packet
	#is finished
	def packet_upstream_player_look(self, buff): 
		buff.save()
		self.check_incoming_buffer()
		self.downstream_factory.receiving_packet_queue.put(None)
		buff.restore()
		self.upstream.send_packet("player_look", buff.read())

	def packet_upstream_player_position_and_look(self, buff): 
		buff.save()
		buff.restore()
		self.upstream.send_packet("player_position", buff.read())

	def packet_upstream_player_position_and_look(self, buff): 
		buff.save()
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
	

class QuietDownstreamFactory(DownstreamFactory):
	bridge_class = QuietBridge
	motd = "Proxy Server"
	forwarding_packet_queue = None
	def __init__(self, c_p_queue = None, s_p_queue = None):
		self.receiving_packet_queue = s_p_queue
		self.forwarding_packet_queue = c_p_queue
		super(QuietDownstreamFactory, self).__init__()


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
	factory = QuietDownstreamFactory(melist, melist2)
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



#	def packet_received(self, buff, direction, name):
	#	self.logger.info(name + ' ' + direction)
	#	if(name == "time_update" and self.events_enabled == False): 
			#self.downstream.ticker.add_loop(50, self.enemy_enc_move)
	#		self.events_enabled = True
		#if(name =="spawn_mob"):
			#print(len(buff))
		#	buff.save()
		#	msg = buff.unpack_varint()
		#	uids = buff.unpack_uuid()
	#		msg2 = buff.unpack_varint()
	#		h = buff.unpack("dddbbb")	
	#		arr = [msg, uids, msg2, h]
			#self.logger.info(arr)
	#		buff.restore()
#		super(QuietBridge, self).packet_received(buff, direction, name)


