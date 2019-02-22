#! /usr/bin/python3

from scapy.all import *

newDest = "127.0.0.1"
newPort = 25565
stdTTL = 60

def minecraft_encode(data): 
	newpackets = []; 
	packbyte = bytes(data); 
	payStr = b'0x11' + packbyte[0: 32]; 
	pack = IP(dst=newDest)/TCP(dport=newPort)/payStr
	return pack

pkt = sniff(count=110, filter ="src 192.168.1.71 and dst port 25565 and tcp"); 
if(pkt != None):
    for x in pkt: 
        mestr = bytes(TCP(x).payload)
        print(mestr)
        #print((TCP(x).payload).decode('utf-8'))
        #ar = mestr.split('\'')
        #if len(ar) >= 2:
         #   v = ar[1] 
          #  if len(v) >= 10:
           #     print(v)
           # if n[0] == b'b\'E':    
	#pack = minecraft_encode(pkt[0]); 
    print("")
	#print(pack.summary); 
