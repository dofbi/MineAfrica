#!/usr/bin/python3
import argparse
import multiprocessing

#Minecraft Bot Libraries - Twisted does the event handling
from twisted.internet import reactor, defer
from quarry.net.client import ClientFactory, SpawningClientProtocol
from quarry.net.auth import ProfileCLI
from MinecraftClientEncoder import MinecraftEncoderFactory
from MinecraftProxyEncoder import MinecraftProxyFactory

# Import socket module
from Crypto.Cipher import AES
from Crypto import Util

#Scapy does the packet sniffing
from scapy.all import sniff, send, TCP, L3RawSocket, IP

def filter_packets(incoming_tcp_q, duplicate_packets):
    """
    Function for filtering out nonTCP packets and saving the TCP packets into the
    incoming_tcp_q.
    """
    def send_filtered_packets(packet):
        data = packet['TCP']
        if not data in duplicate_packets:
            incoming_tcp_q.put(data)
            duplicate_packets.append(data)
        else:
            duplicate_packets.remove(data)
    return send_filtered_packets

def receive_tcp_data(tcp_port, direction, incoming_tcp_q):
    """
    This is a function for sending packets from the host.

    Sniffs all packets of localhost that have ports with the value tcp_port traveling
    either from src or dst using the direction variable.

    direction: src or dst
    tcp_port: String resembling TCP ports such as 9000, 20, 80
    incoming_tcp_q: Queue for saving incoming packets
    """
    port_str_lst = []
    for port in tcp_port.split(','):
        port_str_lst.append('tcp ' + direction + ' port ' +  port)
    port_str = ' or '.join(port_str_lst)

    duplicate_packets = []
    filt = "host 127.0.0.1 and ( " + port_str + " )"
    sniff(filter=filt, prn=filter_packets(incoming_tcp_q, duplicate_packets), iface="lo")

def encrypt_tcp_data(incoming_tcp_q, encrypt_tcp_q, direction):
    """
    This is a function for sending packets from the host.

    Removes packets from incoming_tcp_q, encrypts them with AES_ECB, and then stores the
    encrypted packets into the encrypt_tcp_q.
    """
    while True:
        if incoming_tcp_q.qsize() > 0:
            raw_data = incoming_tcp_q.get()
            padded_block = Util.Padding.pad(bytes(raw_data), AES.block_size)
            encrypt_blocks = encrypt_load(padded_block)
            encrypt_tcp_q.put(bytearray(encrypt_blocks))
            encrypt_tcp_q.put(None)

def decrypt_enc_data(decrypt_tcp_q, response_q):
    """
    This is a function for receiving packets on the host.

    Removes packets from decrypt_tcp_q, decrypts them with AES_ECB, and then stores the
    encrypted packets into the reponse_q.
    """
    while True:
        enc_pack = decrypt_tcp_q.get()
        if enc_pack != None and len(enc_pack) > 0:
            decrypted_pack = decrypt_load(enc_pack)
            unpadded_pack = Util.Padding.unpad(decrypted_pack, AES.block_size)
            response_q.put(bytes(unpadded_pack))

@defer.inlineCallbacks #Needed due to twisted's event handling
def runargs(args, encrypt_tcp_q, decrypt_tcp_q):
    """
    Creates a Minecraft Client Bot, and connects to the Minecraft proxy.
    This assumes that the Minecraft Proxy is already running on another machine.
    """
    profile = yield ProfileCLI.make_profile(args)
    factory = MinecraftEncoderFactory(profile, encrypt_tcp_q, decrypt_tcp_q)
    factory.connect(args.host, args.port)

def client_forward_packet(encrypt_tcp_q, decrypt_tcp_q, forward_addr):
    """
    Starts twisted's event listener for sending and recieving minecraft packets,
    and sets up the client bot to connect to the proper host machine using the
    runargs function. Also passes the encrypt_tcp_q (for forwarding encrypted
    packets) and the decrypt_tcp_q (for receiving encrypted packets) to the
    minecraft client encoder object.
    """
    parser = ProfileCLI.make_parser()
    parser.add_argument("host")
    parser.add_argument("-p", "--port", default=25565, type=int)

    #Later take input and/or pick from a name in a database
    myarr = [forward_addr, "--offline-name", "Notch"]
    args = parser.parse_args(myarr)
    runargs(args, encrypt_tcp_q, decrypt_tcp_q)
    reactor.run()

def proxy_forward_packet(encrypt_tcp_q, decrypt_tcp_q, minecraft_server_addr, minecraft_server_port,
                         listen_addr, listen_port):
    """
    Starts twisted's event listener for sending and recieving minecraft packets,
    and sets up the proxy server which first connects to a Minecraft server set in offline
    mode (TODO: ADD ONLINE SERVER FUNCTIONALITY LATER), and then waits for incoming Minecraft
    Client connections. Also passes the encrypt_tcp_q (for forwarding encrypted
    packets) and the decrypt_tcp_q (for receiving encrypted packets) to the
    minecraftProxyEncoder object.
    """
    factory = MinecraftProxyFactory(encrypt_tcp_q, decrypt_tcp_q)
    factory.online_mode = False
    factory.force_protocol_version = 340
    factory.connect_host = minecraft_server_addr
    factory.connect_port = minecraft_server_port
    factory.listen(listen_addr, listen_port)
    reactor.run()

def inject_tcp_packets(response_q):
    """
    Takes the received unencrypted response_q TCP packets and injects them
    onto the localhost's machine.
    """
    sock = L3RawSocket(iface="lo")
    while 1:
        if response_q.qsize() > 0:
            b_pkt = response_q.get()
            pkt = TCP(b_pkt)
            tcp = IP(dst='127.0.0.1')/pkt['TCP']

            del tcp['TCP'].chksum
            sock.send(tcp)


def encrypt_load(message, key=None):
    """
    Encrypts with AES_ECB using a default password. This is not for security
    it is for creating an even chance of sending binary ones and zeros.
    """
    cryptr = AES.new(b"passwordpassword", AES.MODE_ECB)
    cipher_str = cryptr.encrypt(message)
    return cipher_str

def decrypt_load(cipher_str, key=None):
    """
    Encrypts with AES_ECB using a default password. This is not for security
    it is for creating an even chance of sending binary ones and zeros.
    """
    cryptr = AES.new(b"passwordpassword", AES.MODE_ECB)
    message = cryptr.decrypt(cipher_str)
    return message

if __name__ == '__main__':
    #Parse input arguments, require mode, dest_ip, dest_port, and fwd_ports.
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", help="Client|Server")
    parser.add_argument("dest_ip", help="The destination IP for the Proxy server if"
                        "in Client mode, or the destination IP for the actual Minecraft Server"
                        "in Server mode")
    parser.add_argument("dest_port", help=" The default is the Minecraft Server"
                        "default port 25565.")
    parser.add_argument("fwd_ports", help="Comma delineated list of ports on which to"
                        "listen. For example, 80,441")

    pargs = parser.parse_args()
    print(pargs)

    #Initialize and set important vaiables
    ports = pargs.fwd_ports
    dest_port = int(pargs.dest_port)
    dest_ip = pargs.dest_ip

    #These queues are used throughout the project
    sniffed_packets_queue = multiprocessing.Queue()
    encrypt_queue = multiprocessing.Queue()
    decrypt_queue = multiprocessing.Queue()
    response_queue = multiprocessing.Queue()
    fte_func_args = ()
    packetFlag = True

    fwd_addr = (dest_ip, dest_port)

    #Client and Server specific setup and function choices
    #A Client will run a MinecraftClientEncoder and a Server
    #will run a proxy.
    if pargs.mode.upper() == "CLIENT":
        direction = "dst"
        forward_packet = client_forward_packet
        fte_func_args = (encrypt_queue, decrypt_queue, dest_ip)
    elif pargs.mode.upper() == "SERVER":
        direction = "src"
        forward_packet = proxy_forward_packet
        fte_func_args = (encrypt_queue, decrypt_queue, dest_ip, dest_port, "0.0.0.0", 25565)
    else:
        exit()

    #Start the processes
    try:
        print("Done")
        incoming_tcp_proc = multiprocessing.Process(target=receive_tcp_data, args=
                                                    (ports, direction, sniffed_packets_queue))
        prelim_encrypt_packets = multiprocessing.Process(target = encrypt_tcp_data, args=
                                                         (sniffed_packets_queue, encrypt_queue, direction))
        send_fte_packet = multiprocessing.Process(target = forward_packet, args=fte_func_args)
        decrypt_received_packets = multiprocessing.Process(target=decrypt_enc_data, 
                                                           args=(decrypt_queue, response_queue))
        forward_received_packets = multiprocessing.Process(target=inject_tcp_packets, args=(response_queue,))

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
        prelim_encrypt_packets.terminate()
        send_fte_packet.terminate()
        decrypt_received_packets.terminate()
        forward_received_packets.terminate()
