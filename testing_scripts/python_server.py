#!/usr/bin/python3           

import socket               # Import socket module
import sys
from Crypto.Cipher import AES
from Crypto.Util import Padding

def encrypt_load(message, key):
	cryptr = AES.new(b"passwordpassword", AES.MODE_ECB)
	cipher_str = cryptr.encrypt(message)
	return cipher_str

def decypt_load(cipher_str, key): 
	cryptr = AES.new(b"passwordpassword", AES.MODE_ECB)
	message = cryptr.decrypt(cipher_str)
	return message

f = open('my256key.dat', 'r')
key_data = f.read(); 
f.close(); 

s = socket.socket()         # Create a socket object
host = "127.0.0.1" # Get local machine name

print(sys.argv)
port = int(sys.argv[1])                # Reserve a port for your service.
s.bind((host, port))        # Bind to the port

s.listen(5)                 # Now wait for client connection
data = 'thanks friend'
while True:
   c, addr = s.accept()     # Establish connection with client.
   print('Got connection from', addr)
   pay = encrypt_load(Padding.pad(data.encode('utf-8'), AES.block_size), key_data)
   c.send(pay); 
   print(c.recv(1024))
   c.close()                # Close the connection
