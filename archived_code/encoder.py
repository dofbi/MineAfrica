#!/usr/bin/env python3

## \package encoder
#  \brief Decoding and encoding functionality for protocols
#  \author Jon Oakley
#  \date 06/22/2017
#
#  These classes allow data to be encoded an decoded as a given protocol.
#  All elements of the protocol are maintained, mainly timing and payload
#  values.

import random, string
from Crypto.Cipher import AES
import base64
import os
from os import walk
import math
import binascii
from scapy.all import *
import re
import sys
import struct
import linecache
import datetime
import crc16

## Encode data into the payload for any given protocol
class AESEncoder():
    ## Construct the encoder
    #
    # \param field_dir Directory where the field data are stored
    # \param keyfile The AES public/private keypair
    # \param aes_chunk_size The size of the data after encryption
    def __init__(self,field_dir,keyfile,aes_chunk_size):
        ## The size of each block
        self.aes_encrypted_block_size = aes_chunk_size
        ## The size of each AES chunk (minus seq num size)
        self.aes_chunk_size = aes_chunk_size - 4

        with open(keyfile,'rb') as f:
            ## AES key data
            self.aes_key = f.read()

        ## The AES cipher
        self.cipher = self.create_cipher()

        # get the number of bits that can be encoded in the protocol
        # payload and leave 8 bits for the sequence number
        ## Number of data bits per protocol payload

		#pass in the size instead
        self.binary_chunk_size = self.proto.get_total_size() - 8

        print("Encoder Initialized")

    ## Create a new AES cipher
    def create_cipher(self):
        return AES.new(self.aes_key,AES.MODE_ECB)

    ## Encode data into the protocol payload
    #
    # \param data Binary data to be encoded
    # \return A list of payloads (in reverse order) that can be sent over the network
    def encode(self,data):
        # Breaks the data into chunks to be encrypted
        raw_chunks = self.chunk_raw_data(data)

        # Encrypts each chunk
        encrypted_chunks = [self.encrypt(chunk) for chunk in raw_chunks]

        return encrypted_chunks

    ## Convert data into chunks for encryption
    #
    # \param data Binary data to be chunked
    # \return A list of the chunks
    #
    # There should be an overall length, and sequence numbers
    def chunk_raw_data(self,data):
        # Convert the length of the data into four bytes of data
        # represented as a binary string
        data = self.int_to_bytes(len(data)) + data

        # Break data up into chunks of `aes_chunk_size' - 1
        # The -1 accounts for the sequence numbers
        regex = re.compile('.{1,'+str(self.aes_chunk_size)+'}',re.DOTALL)

        # prepend the sequence number to each chunk
        chunks = []
        idx = 0
        for chunk in regex.findall(data):
            chunks.append(struct.pack('>I',idx) + chunk)
            idx += 1

        return chunks

    ## Encrypt each block
    
    # \param block Block of data to encrypt
    # \return Encrypted block
    #
    # Add padding if necessary
    def encrypt(self,block):

        # Calculate number of bytes to pad
        num_pads = (self.aes_encrypted_block_size) - len(block)

        # Pad with random data
        padding = os.urandom(num_pads)
        # append padding
        block = block + padding
        # encrypt and return the result
        return self.cipher.encrypt(block)

    ## Convert an integer into bytes
    #
    # \param integer An integer
    # \return Bytes:
    def int_to_bytes(self, integer):
        return struct.pack('i',integer)

    ## Convert data to binary
    #
    # \param data Binary data to be converted 
    # \return A string of '1's and '0's
    def to_binary(self,data):
        binary = ''
        for byte in data:
            binary += '{:08b}'.format(ord(byte))

        return binary

    ## Convert the binary chunks to payload sized chunks
    #
    # \param chunk String of '1's and '0's to be chunk'd
    # \return A string of '1's and '0's that will fit into a given payload with a sequence number prepended.
    def binary_chunk_to_payload_chunks(self,chunk):
        # Create chunks of the appropriate size
        regex = re.compile('.{1,'+str(self.binary_chunk_size)+'}',re.DOTALL)
        payload_chunks = regex.findall(chunk)

        # prepend sequence numbers
        seq_num = 0
        sequenced_chunks = []
        for proto_chunk in payload_chunks:
            sequenced_chunks.append(self.to_binary(chr(seq_num)) + proto_chunk)
            seq_num = seq_num + 1

        return sequenced_chunks

## Decode a given protocol
class Decoder():
    ## Construct a protocol decoder
    #
    # \param field_dir Directory where the field data are stored
    # \param keyfile The AES private/public keypair
    # \param aes_chunk_size The size of the AES block after encryption
    def __init__(self,field_dir,keyfile,aes_chunk_size):
        ## The size of the AES block after encryption
        self.aes_encrypted_block_size = aes_chunk_size
        ## Size of AES accounting for the sequence number
        self.aes_chunk_size = aes_chunk_size - 1

        with open(keyfile,'rb') as f:
            ## AES key data
            self.aes_key = f.read()

        ## AES cipher
        self.cipher = self.create_cipher()
        ## NTP protocol
        self.proto = Protocol(field_dir,True)

        # get the number of bits that can be encoded in the protocol
        # payload and leave 8 bits for the sequence number
        ## Number of data bits per protocol payload

		#Pass in the size instead
        self.binary_chunk_size = self.proto.get_total_size() - 8

        # Session Variables
        self.reset()

        print("Decoder Initialized")

    ## Create a new AES cipher
    def create_cipher(self):
        return AES.new(self.aes_key,AES.MODE_ECB)

    ## Called whenever a malformed packet is received or it's time to process a new packet
    def reset(self):
        ## The current AES chunk sequence number
        self.aes_chunk_seq = 0
        ## The current payload sequence number
        self.proto_chunk_seq = 0
        ## Data in the AES chunk
        self.aes_chunk_data = ''
        ## Data in the binary chunk
        self.binary_chunk = ''
        ## The length of the packet
        self.packet_len = 0
        ## Data in the packet
        self.packet_data = ''

    ## Decode the payload of a given protocol
    #
    # \param payload The binary payload of a protocol
    # \return The original data that were sent
    def decode(self,payload):
        # map the bytes to a binary string
        payload_seq,data = self.proto.unmap_data(payload)

        # Remove the 8-bit sequence number
        #payload_seq = int(decoded_ntp_chunk[:8],2)
        #data = decoded_ntp_chunk[8:]

        if payload_seq == None:
            return None

        # Check to see if the payload seq number is in order
        if not payload_seq == self.proto_chunk_seq:
            self.reset()
            return None
        else:
            self.proto_chunk_seq += 1

        # append the new binary data to the existing binary data
        self.binary_chunk += data

        # Check to see if all the data for one AES block has arrived
        # There should be 64B/AES block, therefore, 512 bits
        if len(self.binary_chunk) >= self.aes_encrypted_block_size*8:
            # Reset the payload sequence number
            self.proto_chunk_seq = 0
            # Convert the binary string to a byte string
            # Note that random data was sent in order to fill the last payload
            # this data is removed here
            encrypted_data = self.binary_to_str(self.binary_chunk[:self.aes_encrypted_block_size*8])
            # Reset the incoming binary data
            self.binary_chunk = ''
            # Decrypt the data
            decrypted_data = self.decrypt(encrypted_data)
            # Set the AES sequence number
            aes_seq = struct.unpack('>I',decrypted_data[:4])[0]
            data = decrypted_data[4:]

            # Check to see if the AES chunk is valid
            if not aes_seq == self.aes_chunk_seq:
                self.reset()
                return None
            else:
                self.aes_chunk_seq += 1

            # Parse the length of the packet
            if aes_seq == 0:
                self.packet_len = self.bytes_to_int(data[:4])
                #print(self.packet_len
                data = data[4:]

            # Store the packet data
            self.packet_data += data

            # Check to see if all the packet data has arrived
            if len(self.packet_data) >= self.packet_len:
                # Extra data may have been added to fill the last
                # AES block.  This data is removed here
                packet = self.packet_data[:self.packet_len]
                self.reset()
                return packet

        return None

    ## Decrypt an AES block
    #
    # \param block Data to decrypt
    # \return Unencrypted data
    def decrypt(self,block):
        return self.cipher.decrypt(block)

    ## Convert a byte-string to integers
    #
    # \param byte_data A single byte
    # \return An integer
    def bytes_to_int(self, byte_data):
        return struct.unpack('i',byte_data)[0]

    ## Converts a binary-string to a byte-string
    #
    # \param binary_string A string of '1's and '0's
    # \return Binary data
    def binary_to_str(self, binary_string):
        byte_arr = re.findall('.{8}',binary_string)
        data = ''
        for b in byte_arr:
            data += chr(int(b,2))

        return data

if __name__ == '__main__':
    # AES Parameters
    aes_chunk_size = 64
    keyfile = 'aes_key'

    field_dir = 'fields/'

    payload = os.urandom(10000)
    syn_pkt = TCP(sport=45678,dport=6006,flags='S')
    payload_pkt = TCP(sport=45678,dport=6006)/payload
    b_payload_pkt = str(payload_pkt)
    #print(`b_payload_pkt`
    b_syn_pkt = str(syn_pkt)

    enc = Encoder(field_dir,keyfile,aes_chunk_size)
    dec = Decoder(field_dir,keyfile,aes_chunk_size)

    # random.seed(100)
    placeholder = enc.encode_placeholder()
    # proxy_pkt = IP(dst='10.0.0.1')/UDP(sport=12345,dport=4713)/placeholder
    # send(proxy_pkt)
    #syn_pkt.show()
    #payload_pkt.show()
    #payloads = enc.encode(b_syn_pkt)
    #start = datetime.datetime.now()
    payloads = enc.encode(b_payload_pkt)
    #print("enc: " + `datetime.datetime.now() - start`

    #payloads.insert(random.randint(1,len(payloads)-1),placeholder)
    #print(`payloads`
    payloads.reverse()
    for p in payloads:
        #start = datetime.datetime.now()
        decoded_packet = dec.decode(p)
        #print(`datetime.datetime.now() - start`
        if not decoded_packet == None:
            print(decoded_packet)
            #pass

    if decoded_packet == b_syn_pkt:
        print("Match Syn!")
        decoded_syn_pkt = TCP(decoded_packet)
        decoded_syn_pkt.show()

    if decoded_packet == b_payload_pkt:
        print("Match Payload!")
        decoded_payload_pkt = TCP(decoded_packet)
        decoded_payload_pkt.show()

    elif decoded_packet:
        for idx,b in enumerate(b_payload_pkt):
            print(idx + ": " + decoded_packet[idx] + " <--> " + b_payload_pkt[idx])

    else:
        print('NoneType Returned.  Bad.')
