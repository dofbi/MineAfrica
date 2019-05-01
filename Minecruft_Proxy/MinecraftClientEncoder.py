#!/usr/bin/python3
#Author: Nathan Tusing
#
"""
Python 3 module with core classes for establishing and maintaing
Minecraft Client connections, encoding encrypted byte streams, and
factory class as an interface to build different types of Minecraft
Class Encoders.
"""

from quarry.net.client import ClientFactory, SpawningClientProtocol
from Crypto.Cipher import AES

class MinecraftClientEncoder(SpawningClientProtocol):
    """
    The MinecraftClient Encoder is a class that represents a Minecraft Client connection and performs the FTE encoding of an encrypted bit stream.
    """
    def __init__(self, factory, remote_addr):
        self.packet_done = False
        self.AES_Block_Len = AES.block_size
        self.out_enc_buff = bytearray() #
        self.in_enc_buff = bytearray() 	#
        super(MinecraftClientEncoder, self).__init__(factory, remote_addr)

    def update_player_full(self):
        """
        Sends a player's position to the server every 20 ticks (1 second).
        """
        self.send_packet("player_position", self.buff_type.pack("ddd?", self.pos_look[0], self.pos_look[1], self.pos_look[2], True))

    def get_byte_from_buff(self, buff):
        """
        Reads one byte from the queued buffer. If the buffer is empty, the
        function returns 256.
        """
        if len(buff) == 0:
            buff_byte = 256
        else:
            buff_byte = buff.pop(0)
        return buff_byte

    def get_bytes_from_buff(self, buff, num_bytes):
        """
        Get <num_bytes> out of the given buffer.
        """
	#return [buff.pop(0) for i in range(num_bytes)]
        buff_bytes = []
        for num in range(0, num_bytes):
            buff_byte = self.get_byte_from_buff(buff)
            buff_bytes.append(buff_byte)
        return buff_bytes

    def check_buff(self, buff):
        """
        Update the buffer if empty by reading from the queue provided
        by the factory class. Send a player_look to the server to
        notify that the encoded packet has finished sending.
        """
        if len(buff) < 1 and self.factory.forwarding_packet_queue.qsize() > 0:
            data = self.factory.forwarding_packet_queue.get()
            if data != None:
                buff = bytearray(data)
            self.encode_player_look()
        return buff

    def encode(self):
        """
        Encode packet bytes as minecraft movements. Currently just encodes
        as creative mode inventory actions, but this can be expanded to
        other movement types.
        """
        if self.factory.forwarding_packet_queue.qsize() > 0 or len(self.out_enc_buff) > 0:
            if len(self.out_enc_buff) > 0:
                #This range accounts for the 8 on screen inventory windows
                #for a client
                for i in range(1, 100):
                    self.encode_inventory_action(i)

            self.out_enc_buff = self.check_buff(self.out_enc_buff)
   
    def encode_inventory_action(self, slot_num):
        """
        Injects a byte from the buff as the item id type (currently a subset
        of all item types) and sets the given window slot <slot_num>.
        Finally, it sends the packet to the minecraft proxy server.
        """
        item_id = int(self.get_byte_from_buff(self.out_enc_buff))
        self.send_packet("creative_inventory_action", self.buff_type.pack('h',slot_num) + self.buff_type.pack_slot(item_id))

    def encode_player_look(self):
        """
        Sends the retrieved players look from the beginning of the game
        session each time. Currently used to notify when the outgoing buffer
        has finished sending.
        """
        look_yaw = self.pos_look[3]
        look_pitch = self.pos_look[4]
        on_ground = True
        self.send_packet("player_look", self.buff_type.pack('ff?', look_yaw, look_pitch, on_ground))

    def encode_player_position(self):
        """
        Encode and send original player's position from the start of the
        game.
        """
        pos_x = self.pos_look[0]
        pos_y = self.pos_look[1]
        pos_z = self.pos_look[2]
        on_ground = True

        self.send_packet("player_position", self.buff_type.pack('ddd?', pos_x, pos_y, pos_z, on_ground))

    def encode_player_position_and_look(self):
        """
        Not currently used. Bytes can be injected in to the expected fields
        for the server such as x, y, z, yaw, and pitch.
        """
        out_bytes = self.get_bytes_from_buff(self.out_enc_buff, 2)

        #x_offset = int(out_bytes[0])
        #z_offset = int(out_bytes[1])
        yaw = int(out_bytes[0])
        pitch = int(out_bytes[1])
   
        pos_x = self.pos_look[0] + 0.1 #x_offset/128.0 - 1.0
        pos_y = self.pos_look[1]
        pos_z = self.pos_look[2] + 0.1 #z_offset/128.0 - 1.0
        look_yaw = float(yaw * 1.0)
        look_pitch = float(pitch * 1.0)
        on_ground =    True

        self.send_packet("player_position_and_look", self.buff_type.pack('dddff?', pos_x, pos_y, pos_z, look_yaw, look_pitch, True))

    def packet_player_position_and_look(self, buff):
        """
        Receives the inital player position from the server and store the
        player's information for other turns.
        """
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
            self.send_packet("player_position_and_look", self.buff_type.pack('ddddff?', self.pos_look[0], self.pos_look[1] - 1.62, self.pos_look[1], self.pos_look[2], self.pos_look[3], self.pos_look[4], True))

        # 1.8.x
        elif self.protocol_version <= 47:
            self.send_packet("player_position_and_look", self.buff_type.pack('dddff?', self.pos_look[0], self.pos_look[1], self.pos_look[2], self.pos_look[3], self.pos_look[4], True))

        # 1.9.x
        else:
            self.send_packet("teleport_confirm", self.buff_type.pack_varint(teleport_id))

        if not self.spawned:
            self.ticker.add_loop(1, self.encode)
            self.ticker.add_loop(20, self.update_player_full)
            self.spawned = True

    def update_incoming_buffer(self):
        """
        When the packet from the client in the incoming buffer (server to
        client) is fully reconstructed, add it to the recieving queue to
        be processed.
        """
        incoming_q = self.factory.receiving_packet_queue
        incoming_q.put(self.in_enc_buff)
        self.in_enc_buff = bytearray()

    def check_entity(self, data):
        """
        Checks an entity if its ID is over 20000. Should be depreciated
        due to how enitity IDs are assigned.
        """
        return data >= 20000

    def packet_entity_head_look(self, buff):
        """
        Extracts a byte from the head angle field of a enitity head look
        network packet and appends it to the incoming buffer.
        """
        entity_data = buff.unpack_varint()
        head_pos = buff.unpack("B")
        if self.check_entity(entity_data):
            self.in_enc_buff.append(head_pos)

    def packet_entity_relative_move(self, buff):
        """
        Currently not used, but bytes can be encoded into entity's
        positions.
        """
        enemy_id = buff.unpack_varint()
        enemy_pos = buff.unpack("hhh?")

    def packet_entity_look(self, buff):
        """
        Current delienator for knowing when an encoded packet has finished
        sending from the server. Checks if look movement is from proxy or
        another player by verifying entity ID. - Currently the ID is hard
        coded.
        """
        self.update_incoming_buffer()
        enemy_id = buff.unpack_varint()
        self.update_incoming_buffer()
        #Agreed enemy id for sending messages, negotiate with packets later
        if enemy_id == 21445:
            self.factory.receiving_packet_queue.put(None)

        enemy_look = buff.unpack("bb?")
        enemy_yaw = enemy_look[0]
        buff.discard()

class MinecraftEncoderFactory(ClientFactory):
    """
    Factory for building Client Connections. Also serves as the interface
    for the two packet queues for encoded packets being set between the
    client and server of the Pluggable Transport.
    """
    protocol = MinecraftClientEncoder
    def __init__(self, profile=None, f_queue=None, r_queue=None):
        self.forwarding_packet_queue = f_queue
        self.receiving_packet_queue = r_queue
        super(MinecraftEncoderFactory, self).__init__(profile)
