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

Edit the first variable's IP address to match your LAN's subnet. 
(Static IPs are necessary - hosting the server with a dynamic IP sometimes
causes connection problems with Vagrant.)

Then run vagrant init and vagrant up. 
(While running vagrant up, you will have to seclect a physical network interface that your computer is using.
Select the one that your LAN is using. To check the names of the interfaces run the command "ip a")

Running "vagrant up" will take some time. This command sets up a virtual machine that runs the PT proxy and Minecraft Server. 

Navigate back 

cd ..

and run "sudo ./setup" to install the necessary files on your host machine. 

## Running

Open antoher terminal tab and navigate to the Minecraft_Server directory in one of them; navigate to Minecruft_Proxy in the other. 

In the Minecraft_Server Directory Tab run 

vagrant ssh

ssh -i .vagrant/machines/default/virtualbox/private-key -D 9003 localhost

This starts a SOCKS proxy on the server.

Then, in the same tab, navigate to the minecraft server using

cd ~/minecraft_server 
and then run 
sudo ./start_server.sh

Then in the other tab run: sudo ./Minecruft_Main.py server 127.0.0.1 25566 9003

This will start the Proxy Server for Minecruft

Then on your host machine navigate to the Minecruft_Proxy folder
cd Minecruft/Minecruft_Proxy
and run the command 

sudo ./Minecruft_Main.py client $VagrantIP 25565 9003

Finally, vagrant ssh using one more terminal and run 
iperf -s -p 9003

and in another terminal on your host; run 
iperf -y C -b 1k -c 127.0.0.1 -p 9003





