#!/bin/bash

#sudo iptables --flush
#sudo iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP
#sudo iptables -L

xterm -hold -e bash -c "../Minecruft_Proxy/Minecruft_Main.py server 192.168.56.103 12347" &
xterm -hold -e bash -c "sleep 10s; ../Minecruft_Proxy/Minecruft_Main.py CLIENT 127.0.0.1 12346" &
xterm -hold -e bash -c "sleep 15s; ./python_server.py 12346" &
xterm -hold -e bash -c "sleep 20s; ./client_test.py" &
wait



