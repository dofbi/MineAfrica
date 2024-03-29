#!/usr/bin/python3

import random
import multiprocessing
from twisted.internet import reactor
from quarry.net.proxy import DownstreamFactory, Upstream, UpstreamFactory, Bridge
from quarry.types import uuid
from Crypto.Cipher import AES

#Development notes:
#Currently mob spawning is handled by the proxy, but other mob logic is not
#either we allow a real minecraft server to allocate resources, or handle
#all enitity movements and responses on the Proxy.

#Enemy spawning ID currently is hard-coded to 30000. This is unrealistic.
#Each new entity spawning ID would be incremented from the last one. For
#example, a player could be assigned id 10, and then three enemies would be
#assigned 11, 12, and 13.

class UpstreamEncoder(Upstream):
    """
    Inherits from Upstream Class. Represents the Client Connection to the
    Minecraft Server. Contains a buffer <Proxy_bound_buff>  for holding packets
    destined for the Minecruft Client.     
    """
    proxy_bound_buff = bytearray()
    assigned_enemy = 0
    assigned_id = 0

class UpstreamEncoderFactory(UpstreamFactory):
    """
    Factory class for Upstream encoder for easy instantiation of multiple
    Upstreams for multiple Minecraft PT clients.
    """
    protocol = UpstreamEncoder

#Each Client and Proxy needs to keep track of which enemy is their own.
#Think of this as a operating system problem of sharing limited resources.
class MinecraftProxyBridge(Bridge):
    """
    Class that holds references to both Upstream and Downstream. Waits for
    both client (Upstream) and server (Downstream) connections to be
    established before forwarding packets through the proxy.
    """
    quiet_mode = False
    events_enabled = False
    upstream_factory_class = UpstreamEncoderFactory

    def __init__(self, downstream_factory, downstream):
        self.clients_and_positions = []
        self.client_bound_buff = bytearray()
        self.old_enc_buff = bytearray()
        self.mobs_per_client = 100
        self.first_enemy_id = 30000
        self.packet_done = False
        self.is_waiting = False
        self.block_len = AES.block_size

        #We will need one for each client
        #self.client_bound_buff = bytearray() #going out to client
        #self.proxy_bound_buff = bytearray() #coming from client

        super().__init__(downstream_factory, downstream)

    def get_byte_from_buff(self, buff):
        """
        Right now returns 256 for no bytes in buff. Later change to None
        to be more Pythonic.
        """
        buff_byte = 256
        if buff:
            buff_byte = buff.pop(0)
        return buff_byte

    def get_bytes_from_buff(self, buff, num_bytes):
        """
        Read num_bytes from a buffer. Returns a list of bytes. 
        """
        buff_bytes = []
        for num in range(0, num_bytes):
            buff_byte = self.get_byte_from_buff(buff)
            buff_bytes.append(buff_byte)
        return buff_bytes

    def check_buff(self, buff):
        """
        Checks when a buffer or queue is emptied. When a buffer is emptied, that means
        a full TCP packet has been transmitted to the client. When a full TCP packet is transmitted,
        it signals the Minecruft client with an encode_enemy_look packet.
        """
        if len(buff) < 1 and self.downstream.factory.forwarding_packet_queue.qsize() > 0:
            data = self.downstream.factory.sync_buff(self.old_enc_buff)
            if(data != None and data != self.old_enc_buff):
                buff = bytearray(data)
                self.old_enc_buff = self.client_bound_buff

            self.encode_enemy_look()
        return buff

    def encode(self):
        """
        This is the main encode function that encodes packet bytes as
        minecraft movements. This is where any new encoder functions
        should be called. 
        """
        if self.downstream.factory.forwarding_packet_queue.qsize() > 0 or len(self.client_bound_buff) > 0:
            if len(self.client_bound_buff) > 0:
                for i in range (self.first_enemy_id, self.first_enemy_id + self.mobs_per_client):
                    self.encode_enemy_head_look(i)
                    #TODO ADD ENCODER FUNCTIONS HERE

            self.client_bound_buff = self.check_buff(self.client_bound_buff)


    def encode_enemy_head_look(self, enemy_id):
        """
        Read a byte from client_bound_buff and send in entity head 
        look packet. 
        """
        yaw = self.get_byte_from_buff(self.client_bound_buff)
        if(yaw != 256):
            self.downstream.send_packet("entity_head_look", self.downstream.buff_type.pack_varint(enemy_id), self.downstream.buff_type.pack("B", yaw ))

    def gen_rand(self, bound):
        """
        Uses os.urandom to generate random integer. 
        """
        rand_gen = random.SystemRandom()
        return rand_gen.randint(0, bound)

    def encode_enemy_look(self):
        """
        Encode a byte into an entity look packet and then forward to
        Upstream Client connection.
        """
        mid = self.first_enemy_id
        yaw = self.gen_rand(255)
        val = self.gen_rand(255)
        self.downstream.send_packet("entity_look", self.downstream.buff_type.pack_varint(mid), self.downstream.buff_type.pack("BB?", yaw, val, True ))

    def spawn_mobs(self, player_position):
        """
        Spawn mobs in a random position in a sqaure 255x255 blocks centered
        on the player's starting position.
        This function should not be used if the Minecraft server is meant to 
        generate mobs.
        """
        first_mob_id = self.first_enemy_id
        num_mobs = self.mobs_per_client
        position = player_position

        for i in range(0, num_mobs):
            chosen_client = self.downstream
            x_pos = position[0] + self.gen_rand(255000)/1000.0 - 127
            y_pos = position[1]
            z_pos = position[2] + self.gen_rand(255000)/1000.0 - 127
            yaw = self.gen_rand(255)
            pitch = 0
            head_pitch = self.gen_rand(255)
            velocity_x = 0
            velocity_y = 0
            velocity_z = 0
            enemy_id = first_mob_id + i
            enemy_type = 50 + self.gen_rand(2)
            meta_data = 255 #signals that no NBT Minecraft metadata exists- must be here
                            #or packet will be malformed. 

            chosen_client.send_packet("spawn_mob",chosen_client.buff_type.pack_varint(enemy_id) + chosen_client.buff_type.pack_uuid(uuid.UUID.random()) + self.downstream.buff_type.pack_varint(enemy_type) + chosen_client.buff_type.pack("dddBBBhhhB", x_pos, y_pos, z_pos, yaw, pitch, head_pitch, velocity_x, velocity_y, velocity_z, meta_data))

        #self.first_enemy_id = self.first_enemy_id + self.mobs_per_client



#--------------------------------------------------------------------
    def update_incoming_buffer(self, stream):
        """
        """
        did_add_buff = False
        if(len(stream.proxy_bound_buff) > 0 and len(stream.proxy_bound_buff) % AES.block_size == 0):
            self.downstream_factory.receiving_packet_queue.put(stream.proxy_bound_buff)
            did_add_buff = True
        stream.proxy_bound_buff = bytearray()

        return did_add_buff


    def packet_upstream_creative_inventory_action(self, buff):
        buff.save()
        buff.unpack("h")
        slot_num = buff.unpack_slot()
        item_num = slot_num["item"]
        if(item_num != None and item_num < 256):
            self.upstream.proxy_bound_buff.append(item_num)

        buff.restore()
        self.upstream.send_packet("creative_inventory_action", buff.read())

    #When the player sends just a look command, that means the packet
    #is finished
    def packet_upstream_player_look(self, buff):
        buff.save()
        if(self.update_incoming_buffer(self.upstream)):
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

        #if yaw < 256 and yaw > 0:
            #self.upstream.proxy_bound_buff.append(yaw)

        #if pitch < 256 and pitch > 0:
            #self.upstream.proxy_bound_buff.append(pitch)

        buff.restore()
        self.upstream.send_packet("player_position_and_look", buff.read())
    def packet_downstream_entity_head_look(self, buff):
        buff.discard()

    def packet_downstream_entity_look(self, buff):
        buff.discard()

    #This packet is only sent if the player dies, or if he is joining
    def packet_downstream_player_position_and_look(self, buff):
        buff.save()
        pos_and_look_struct = buff.unpack("dddff")
        self.downstream.ticker.add_loop(1, self.encode)
        self.clients_and_positions.append((self.downstream, pos_and_look_struct))
        self.spawn_mobs(pos_and_look_struct)
        buff.restore()
        self.downstream.send_packet("player_position_and_look", buff.read())

    def downstream_disconnected(self, reason=None):
        self.downstream.factory.num_client_encoders = self.downstream.factory.num_client_encoders - 1
        if self.upstream:
            self.upstream.close()

class MinecraftProxyFactory(DownstreamFactory):
    """
    Factory class for easy instantiation of new Bridge connections between
    client and server.
    """
    bridge_class = MinecraftProxyBridge
    client_bound_buff = bytearray()
    num_client_encoders = 0
    num_waiting_encoders = 0
    motd = "Proxy Server"
    forwarding_packet_queue = None
    def __init__(self, c_p_queue = None, s_p_queue = None):
        self.receiving_packet_queue = s_p_queue
        self.forwarding_packet_queue = c_p_queue
        super(MinecraftProxyFactory, self).__init__()

    def connectionMade(self):
        self.num_client_encoders = num_client_encoders + 1
        return self.connection_made()

    def sync_buff(self, oldbuff):
        """
        Each Downstream must send the same data for enemy movement packets
        from the global buffer in order for the game sessions to be
        authentic.
        """
        if(self.forwarding_packet_queue.qsize() > 0):
            if(self.num_client_encoders == self.num_waiting_encoders or len(oldbuff) < 1):
                self.num_waiting_encoders = 0
                data = self.forwarding_packet_queue.get()
                if(data != None):
                    self.client_bound_buff = bytearray(data)
            else:
                self.num_waiting_encoders = self.num_waiting_encoders + 1
        return self.client_bound_buff

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
