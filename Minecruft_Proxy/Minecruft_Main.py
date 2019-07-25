#!/usr/bin/python3

import argparse
import io
import os

#Minecraft Bot Libraries - Twisted does the event handling
from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ClientEndpoint
from quarry.net.client import ClientFactory, SpawningClientProtocol
from quarry.net.auth import ProfileCLI
from MinecraftClientEncoder import MinecraftEncoderFactory
from MinecraftProxyEncoder import MinecraftProxyFactory

# Import socket module
import socket
import multiprocessing
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto import Util
from Crypto.PublicKey import RSA

#Scapy does the packet sniffing
from scapy.all import *

def filter_packets(incoming_tcp_q,duplicate_packets):
	def send_filtered_packets(packet):
		data = packet['TCP']
		if not data in duplicate_packets:
			incoming_tcp_q.put(data)
			duplicate_packets.append(data)
		else:
			duplicate_packets.remove(data)
	return send_filtered_packets

def receive_tcp_data(tcp_port, direction, incoming_tcp_q):
	port_str_lst = []
	for p in tcp_port.split(','):
		port_str_lst.append('tcp ' + direction + ' port ' +  p)
	port_str = ' or '.join(port_str_lst)

	duplicate_packets = []
	filt = "host 127.0.0.1 and ( " + port_str + " )"
	sniff(filter=filt,prn=filter_packets(incoming_tcp_q,duplicate_packets),iface="lo")

def encrypt_tcp_data(incoming_tcp_q, enc_tcp_q, direction):
	while True:
		if(incoming_tcp_q.qsize() > 0 ):
			raw_data = incoming_tcp_q.get()
			padded_block = Util.Padding.pad(bytes(raw_data), AES.block_size)
			encrypt_blocks = encrypt_load(padded_block)
			enc_tcp_q.put(bytearray(encrypt_blocks))
			enc_tcp_q.put(None)

#Reform AES blocks back into packets
def decrypt_enc_data(enc_response_q, response_q): 
	while True:
		enc_pack = enc_response_q.get()	
		if (enc_pack != None and len(enc_pack) > 0):
			decrypted_pack = decrypt_load(enc_pack)
			unpadded_pack = Util.Padding.unpad(decrypted_pack, AES.block_size)
			response_q.put(bytes(unpadded_pack))
				
@defer.inlineCallbacks
def runargs(args, enc_packet_q, response_packet_q):
	profile = yield ProfileCLI.make_profile(args)
	factory = MinecraftEncoderFactory(profile, enc_packet_q, response_packet_q)
	factory.connect(args.host, args.port)

def client_forward_packet(enc_packet_q, response_packet_q, forward_addr): 
	parser = ProfileCLI.make_parser()
	parser.add_argument("host")
	parser.add_argument("-p", "--port", default=25565, type=int)
	
	#Later take input and/or pick from a name in a database
	myarr = [forward_addr, "--offline-name", "Notch"]
	args = parser.parse_args(myarr)
	runargs(args, enc_packet_q, response_packet_q)
	reactor.run()

def proxy_forward_packet(enc_packet_q, response_packet_q, minecraft_server_addr, minecraft_server_port, listen_addr, listen_port): 
	factory = MinecraftProxyFactory(enc_packet_q, response_packet_q)
	factory.online_mode = False
	factory.force_protocol_version = 340
	factory.connect_host = minecraft_server_addr
	factory.connect_port = minecraft_server_port
	factory.listen(listen_addr, listen_port)
	reactor.run()

def send_tcp_data(decrypt_q, direction):
	sock = L3RawSocket(iface="lo")
	while 1:
		if decrypt_q.qsize() > 0:
			b_pkt = decrypt_q.get()
			pkt = TCP(b_pkt)
			tcp  = IP(dst='127.0.0.1')/pkt['TCP']

			del tcp['TCP'].chksum
			sock.send(tcp)


def encrypt_load(message, key=None):
	cryptr = AES.new(b"passwordpassword", AES.MODE_ECB)
	cipher_str = cryptr.encrypt(message)
	return cipher_str

def decrypt_load(cipher_str, key=None): 
	cryptr = AES.new(b"passwordpassword", AES.MODE_ECB)
	message = cryptr.decrypt(cipher_str)
	return message

if __name__ == '__main__':
	#Use sys later to take command line arguments
	#generate_nonce(16)
	#me_key = generate_rsa(2048)
	#print(me_key)
	#val = encrypt_rsa(me_key, b"hello")
	#print(val)
	#print(decrypt_rsa(me_key, val))
    
	parser = argparse.ArgumentParser()
	parser.add_argument("mode", help="Client|Server")
	parser.add_argument("dest_ip", help="The destination ip for the Proxy server if in Client mode, or the destination ip for the actual Minecraft Server in Server mode")
	parser.add_argument("fwd_ports", help="Comma delineated list of ports on which to listen. For example, 80,441")
	parser.add_argument("--dest-port", help=" The default is the Minecraft Server Default port 25565.")
	
	pargs = parser.parse_args()
	print(pargs)

	ports = pargs.fwd_ports
	dest_port = 25565 
	dest_ip = pargs.dest_ip	#"192.168.56.102"
	sniffed_packets_queue = multiprocessing.Queue()
	encrypt_queue = multiprocessing.Queue()
	decrypt_queue = multiprocessing.Queue()
	response_queue = multiprocessing.Queue()
	fte_func_args = ()
	packetFlag = True

	fwd_addr = (dest_ip, dest_port)

	if(pargs.mode.upper() == "CLIENT"): 
		direction = "dst"
		forward_packet = client_forward_packet
		fte_func_args = (encrypt_queue, decrypt_queue, dest_ip)
	elif(pargs.mode.upper() == "SERVER"): 
		direction = "src"
		forward_packet = proxy_forward_packet
		fte_func_args = (encrypt_queue, decrypt_queue, dest_ip, dest_port, "0.0.0.0", 25565)
	else: 
		exit()
	
	try:
		print("Done")
		incoming_tcp_proc = multiprocessing.Process(target = receive_tcp_data, args=(ports, direction, sniffed_packets_queue))
		prelim_encrypt_packets = multiprocessing.Process(target = encrypt_tcp_data, args=(sniffed_packets_queue, encrypt_queue, direction))
		send_fte_packet = multiprocessing.Process(target = forward_packet, args=fte_func_args)
		decrypt_received_packets = multiprocessing.Process(target=decrypt_enc_data, args=(decrypt_queue, response_queue))
		forward_received_packets = multiprocessing.Process(target=send_tcp_data, args=(response_queue, direction))

		incoming_tcp_proc.start()
		prelim_encrypt_packets.start()
		send_fte_packet.start()
		decrypt_received_packets.start()
		forward_received_packets.start()

		incoming_tcp_proc.join()
		prelim_encrypt_packets.join()
		send_fte_packet.join()
		decrypt_received_packets.join()
		forward_received_packets.join()

	except KeyboardInterrupt: 
		print("Keyboard Interrupt - Stopping server")
		incoming_tcp_proc.terminate()
		send_fte_packet.terminate()

#s = socket.socket()         # Create a socket object
#host = socket.gethostname() # Get local machine name
#port = 12345                # Reserve a port for your service.

#s.connect((host, port))
#print decrypt_load(s.recv(1024), "bal")
#s.send("You are welcome")
#s.close()              
