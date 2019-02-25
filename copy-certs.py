#!/usr/bin/env python2
####################################################################
# Script     : copy-certs.py
# Author     : Jon Oakley
# Date       : 06/22/2017
# Description: This file remotely initiates the bootstrap process on
#   the server. After the server has retrieve all the certs, the
#   client copies over the file chunks, coalesces them, and cleans
#   up.
####################################################################
import subprocess,time,os,sys

FILES = ['cached-certs','cached-microdesc-consensus','cached-microdescs.new']

if __name__ == "__main__":
    if not len(sys.argv) == 5:
        print 'Usage: copy-certs.py username dest-ip local-port proxy-outgoing-port'
        sys.exit()
    else:
        username = sys.argv[1]
        dest_ip = sys.argv[2]
        local_port = sys.argv[3]
        proxy_port = sys.argv[4]


    #Start Proxy
    pt_proc = subprocess.Popen(['sudo','./Minecruft_Proxy/Minecruft_Main.py', 'client', dest_ip, local_port],stdout=subprocess.PIPE)

    print 'Started'

    #Wait for proxy to finish startup
    l = pt_proc.stdout.readline()
    while not "Done" in l:
        l = pt_proc.stdout.readline()
        #print l
        time.sleep(0.1)

    print 'Initialized'

    #Run bootstrap script through ssh
    proc = subprocess.Popen(['ssh', '-p', local_port, username + '@127.0.0.1','"bootstrap.py"'],stdout=subprocess.PIPE)
    #print `proc.communicate()`
    proc.wait()
    print 'Bootstrap Finished'

    #Remove old tmp files (if applicable)
    proc = subprocess.Popen('rm -rf tmp',shell=True,stdout=subprocess.PIPE)
    #print `proc.communicate()`
    proc.wait()

    #Create new folder for temp files
    proc = subprocess.Popen('mkdir -p tmp',shell=True,stdout=subprocess.PIPE)
    #print `proc.communicate()`
    proc.wait()

    #Copy cert files through proxy (no proxy used for testing purposes)
    proc = subprocess.Popen(['scp', '-P', local_port, username+'@127.0.0.1:tmp/*', 'tmp/'],stdout=subprocess.PIPE)
    #proc = subprocess.Popen(['scp', '-P', local_port, username+'@host2:tmp/*', 'tmp/'],stdout=subprocess.PIPE)
    #print `proc.communicate()`
    proc.wait()
    print 'Copied'

    #Kill proxy
    os.system("sudo kill -INT %d"%(pt_proc.pid))
    print 'Exited'

    #Coalesce and copy files
    for f in FILES:
        proc = subprocess.Popen('cat tmp/' + f + '* > tmp/' + f, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        #print `proc.communicate()`
        proc.wait()
        print 'Coalesced'

        proc = subprocess.Popen('cp tmp/' + f + ' /tmp/tor/' + f, shell=True, stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        proc.wait()
        #print `proc.communicate()`

    #Remove files
    proc = subprocess.Popen('rm -rf tmp', shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    #print `proc.communicate()`
    proc.wait()

    print 'Done'
