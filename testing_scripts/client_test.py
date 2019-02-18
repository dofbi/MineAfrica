#!/usr/bin/python3          

import socket               # Import socket module
import multiprocessing
from scapy.all import *
from Crypto.Cipher import AES
from Crypto.Util import Padding

def filter_packets(incoming_tcp_q,duplicate_packets):
	def send_filtered_packets(packet):
		data = str(packet['TCP'])
		print(data)
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


def encrypt_load(message, key):
	cryptr = AES.new(b"passwordpassword", AES.MODE_ECB)
	cipher_str = cryptr.encrypt(message)
	return cipher_str

def decrypt_load(cipher_str, key): 
	cryptr = AES.new(b"passwordpassword", AES.MODE_ECB)
	message = Padding.unpad(cryptr.decrypt(cipher_str), AES.block_size)
	return message

#ports = "12345"
#queue = multiprocessing.Queue()
#direction = "src" 

#receive_tcp_data(ports, direction, queue); 

s = socket.socket()         # Create a socket object
host = "127.0.0.1" # Get local machine name
port = 12346                # Reserve a port for your service.

s.connect((host, port))
print(decrypt_load(s.recv(1024), "bal"))
s.send(b"You are welcome")
s.close()              
