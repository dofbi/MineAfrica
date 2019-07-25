#!/bin/bash

#Setup script for Ubuntu 16.04. Runs bridge setup script, installs 
#and runs minecraft server, and starts the bridge node. 

sudo apt-get update

cd /home/vagrant/minecruft
sudo ./setup

sudo apt install -y openjdk-8-jre-headless git

cd Minecraft_Server

curl -o BuildTools.jar https://hub.spigotmc.org/jenkins/job/BuildTools/lastSuccessfulBuild/artifact/target/BuildTools.jar 

sudo git config --global --unset core.autocrlf
sudo java -Xmx1024M -jar BuildTools.jar --rev 1.12.2

mv spigot*.jar spigot.jar

java -Xms1G -Xmx1G -XX:+UseConcMarkSweepGC -jar spigot.jar
