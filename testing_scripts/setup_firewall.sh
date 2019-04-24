sudo iptables -I INPUT -m tcp -p tcp --dport 22565 -j ACCEPT
sudo iptables -I INPUT -m tcp -p tcp --dport 9001 -j ACCEPT
sudo iptables -I INPUT -m tcp -p tcp --dport 9003 -j ACCEPT
sudo iptables -A OUTPUT -p tcp --tcp-flags RST RST -j DROP

