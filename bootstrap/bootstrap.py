#!/usr/bin/env python2
####################################################################
# Script     : bootstrap.py
# Author     : Jon Oakley
# Date       : 06/22/2017
# Description: This script downloads the certs required by tor on the
#   server.  After the certs are downloaded, they are split into 1KB
#   chunks so they can be easily copied back to the client.
####################################################################
import subprocess,time

FILES = ['cached-certs','cached-microdesc-consensus','cached-microdescs.new']

if __name__ == "__main__":
    #Cleanup old files
    proc = subprocess.Popen('rm -rf tmp torrc',shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    proc.wait()

    #Create a new torrc config file for this operation
    with open('torrc','w') as f:
        f.write('Nickname PTClient\nClientOnly 1\nDataDirectory ./tmp')

    #Create a new temp directory for the certs
    proc = subprocess.Popen(['mkdir','-p', 'tmp'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    proc.wait()

    #Start Tor
    tor = subprocess.Popen(['tor', '-f', 'torrc'],stdout=subprocess.PIPE,stderr=subprocess.PIPE)

    #Wait for Tor to load
    l = tor.stdout.readline()
    while not "Done" in l:
        time.sleep(0.1)
        #print l
        l = tor.stdout.readline()

    #Stop Tor
    tor.kill()
    #Cleanup torrc
    proc = subprocess.Popen('rm -rf torrc', shell=True, stdout=subprocess.PIPE,stdin=subprocess.PIPE)
    #print `proc.communicate()`

    for f in FILES:
        #Split each of the downloaded files
        proc = subprocess.Popen('split -b 1K -d tmp/' + f + ' tmp/' + f, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #print `proc.communicate()`

        #Remove the original file
        proc = subprocess.Popen('rm -rf tmp/' + f,shell=True,stdout = subprocess.PIPE, stderr=subprocess.PIPE)
        #print `proc.communicate()`

    #Remove unecessary files
    proc = subprocess.Popen('rm -rf tmp/lock tmp/state', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    #print `proc.communicate()`
