#!/bin/bash

#Setup script for Ubuntu 16.04. Runs bridge setup script, installs 
#and runs minecraft server, and starts the bridge node. 

sudo apt-get update

sudo apt install -y openjdk-8-jre-headless git

cd ../..
mkdir minecraft_server
cd minecraft_server

curl -o BuildTools.jar https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar 

sudo git config --global --unset core.autocrlf
sudo java -Xmx1024M -jar BuildTools.jar --rev 1.12.2

mv spigot*.jar spigot.jar

sudo cp ../minecruft/Minecraft_Server/eula.txt .
sudo cp ../minecruft/Minecraft_Server/server.properties .
sudo cp ../minecruft/Minecraft_Server/start_server.sh .

#sudo apt upgrade -y 
#sudo apt autoremove -y
#sudo apt-get remove -y python3

cd /home/vagrant/minecruft
sudo ./setup
