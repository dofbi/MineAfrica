# Minecruft: A Minecraft Protocol Proxy

A protocol proxy based PT that transforms traffic into Minecraft Traffic. 

## Installation 

This code base currently is designed for linux systems. For best results, perform this installation on an Ubuntu Host running Ubuntu 16.04. 

First clone this project

Install VirtualBox and Vagrant

https://www.vagrantup.com/downloads.html

https://www.virtualbox.org/wiki/Linux_Downloads

Then navigate within the Minecruft Repo to Minecraft_Server

cd ./Minecraft_Server

and then with your favorite text editor, open Vagrantfile. 

Edit the first two IP addresses to match your LAN's subnet. 
(Static IPs are necessary - hosting the server with a dynamic IP sometimes
causes connection problems with Vagrant.)

Then run vagrant up. 
(While running vagrant up, you will have to seclect a physical network interface that your computer is using.
Select the one that your LAN is using. To check the names of the interfaces run the command "ip a")

Running "vagrant up" will take some time. This command sets up two virtual machines that run the PT proxy and PT client respectively. 

cd ..

## Running the Proxy and Client

In the Minecruft/Minecraft_Server Directory Tab open four terminal windows or tabs. Run these four commands (one in each terminal). 
vagrant ssh Bridge
vagrant ssh Bridge
vagrant ssh Client
vagrant ssh Client

(OR just open the machines using virtualbox and use a tool like screen - the default usernames are "vagrant", and the default passwords are "vagrant" on both machines.) 

In one of the vagrant ssh Bridge sessions goto the /minecruft/Minecruft_Proxy folder and 
run: sudo ./Minecruft_Main.py server $MINECRAFT_SERVER_IP $MINECRAFT_SERVER_PORT 9004

This will start the Proxy Server for Minecruft

In the other vagrant ssh Bridge session run: (you may have to install iperf)
iperf -s -p 9004

Then in` one of the vagrant ssh Client sessions goto the /minecruft/Minecruft_Proxy folder and 
run: sudo ./Minecruft_Main.py server $MINECRAFT_SERVER_IP $MINECRAFT_SERVER_PORT 9004
sudo ./Minecruft_Main.py client $VAGRANT_PROXY_IP 25565 9004

and in the other vagrant ssh Client session, run 
iperf -n 10k -c 127.0.0.1 -p 9004
#iperf generates traffic for the PT to sniff, forward, and inject

###To install the custom Minecraft_Server on your network (Only one per LAN is needed , so skip this step if one is already running) 
Navigate to the Minecruft/Minecraft_Server directory. 
run vagrant ssh Bridge

navigate to minecruft/Minecraft_Server. cd minecruft/Minecraft_Server
and run ./setup_bridge.sh 

#Running the minecraft server (only one per LAN is needed)
If the minecraft server is already installed using the setup_bridge.sh script then just run these commands after running 
vagrant ssh Bridge, or opening the machine in virtualbox. 

cd ~/minecraft_server 
and then run 
sudo ./start_server.sh


