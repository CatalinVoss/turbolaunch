#!/usr/bin/env python
# -*- coding: utf-8 -*-
import fnmatch
import os
import re
import sys
from subprocess import Popen, PIPE, STDOUT
import time
import pexpect
import keyring
import getpass
import commands
import json
import time

# Keys for keychain
TOOL_NAME = 'turbolaunch'
MFA_SECRET = 'mfa_secret'
AWS_USER = 'remote_user'
AWS_PASSWORD = 'remote_password'
MOUNT_PATH = 'mount_path'

AWS_URL = '[ENTER YOUR AWS INSTANCE URL]'
AWS_INSTANCE_ID = '[ENTER YOUR AWS INSTANCE ID]'

KILL_SSHFS_CMD = 'killall sshfs 2> /dev/null'

def warn():
    print "  _      _____   ___  _  _______  _______"
    print " | | /| / / _ | / _ \/ |/ /  _/ |/ / ___/"
    print " | |/ |/ / __ |/ , _/    // //    / (_ / "
    print " |__/|__/_/ |_/_/|_/_/|_/___/_/|_/\___/  "
    print "                                         "
    print "DON'T LOG IN THIS WAY UNLESS YOU HAVE FULL DISK ENCRYPTION ENABLED!"

def usage():
    print 'To get set up: ./turbolaunch.py setup'
    print 'To mount and log in: ./turbolaunch.py'
    print 'To mount only: ./turbolaunch.py m'
    print 'To log in with x-window forwarding: ./turbolaunch.py x'
    print 'To show this text: ./turbolaunch.py help'
    print ''
    print 'Dependencies:'
    print '  brew install oath-toolkit'
    print '  pip install keyring'
    print '  pip install pexpect'
    print '  pip install awscli'

def open_mount(mount_path):
    cmd = "osascript -e 'tell application \"Terminal\" to activate' -e 'tell application \"System Events\" to tell process \"Terminal\" to keystroke \"t\" using command down' -e 'tell application \"Terminal\" to do script \"cd "+mount_path+"\" in selected tab of the front window'"
    os.system(cmd)

# Annoys the heck out of the instance until it's running
def start_instance():
    print "Starting AWS instance "+AWS_INSTANCE_ID+"..."
    attempts = 0

    cmd = "aws ec2 start-instances --instance-ids "+AWS_INSTANCE_ID
    while True:
        if attempts > 10:
            print "Failed to start instance within 10 attempts"
            return False
        attempts += 1
        output = commands.getstatusoutput(cmd)[1]
        parse = json.loads(output)
        if parse['StartingInstances'][0]['CurrentState']['Name'] == 'running':
            if attempts == 1:
                print "Was already running..."
            else:
                print "Started successfully..."
            return True
        time.sleep(10) # Give the instance 10 seconds, then ping again


def fill_login(child, code, aws_password):
    child.expect('Verification code: ')
    child.sendline(code)
    child.expect('Password: ')
    child.sendline(aws_password)

def login(option=''):
    # Read credentials from keychain
    mfa_secret= keyring.get_password(TOOL_NAME, MFA_SECRET)
    aws_user = keyring.get_password(TOOL_NAME, AWS_USER)
    aws_password = keyring.get_password(TOOL_NAME, AWS_PASSWORD)

    if not mfa_secret or not aws_user or not aws_password:
        print "We need setup!"
        return setup()

    if not start_instance():
        return

    # Get MFA code
    child = pexpect.spawn('oathtool -b --totp '+mfa_secret)
    code = child.readline()

    if option == '':
        awsml_cmd = 'ssh '+aws_user+'@'+AWS_URL
    elif option == 'm': # mount AND login!
        print "Mounting SSHFS volume..."
        os.system(KILL_SSHFS_CMD)
        mount_path = keyring.get_password(TOOL_NAME, MOUNT_PATH)
        if not mount_path:
            print "We need setup!"
            return setup()
        os.system('mkdir -p '+mount_path)
        os.system('umount -f '+mount_path+' 2> /dev/null')
        # We need to open a bash here at the end of it, because if the script terminates, pexpect kills the child process
        # and SSHFS relies on staying open
        awsml_cmd ='/bin/sh -c \"/usr/local/bin/sshfs '+aws_user+'@'+AWS_URL+':\'/home/'+aws_user+'\' \''+mount_path+'\' -ovolname=awsml; /bin/bash\"'
    elif option == 'x': # x-window forwarding
        awsml_cmd = 'ssh -X '+aws_user+'@'+AWS_URL
    else:
        print 'Option not recognized: '+str(option)

    child = pexpect.spawn(awsml_cmd)
    fill_login(child, code, aws_password)

    # If we mounted the volume, we're now in a bash, so let's use that one to log in as well
    if option == "m":
        child.expect('bash*')
        child.sendline('ssh '+aws_user+'@'+AWS_URL)
        fill_login(child, code, aws_password)
        print "IMPORTANT: To keep SSHFS running, you need to keep this window open. We've conveniently logged you into the instance, so use it as any other ssh window."
        open_mount(mount_path)

    print "Logged into instance"
    child.interact()

    # Kill sshfs when the user terminated the interaction before we quit
    if option == "m":
        os.system(KILL_SSHFS_CMD)

def setup():
    warn()

    mfa_secret = getpass.getpass('Enter your MFA secret: ')
    keyring.set_password(TOOL_NAME, MFA_SECRET, mfa_secret)

    aws_user = getpass.getpass('Enter your AWS username: ')
    keyring.set_password(TOOL_NAME, AWS_USER, aws_user)

    aws_password = getpass.getpass('Enter your AWS password: ')
    keyring.set_password(TOOL_NAME, AWS_PASSWORD, aws_password)

    mount_path = raw_input('Your desired absolute (!) SSHFS mount path: ')
    keyring.set_password(TOOL_NAME, MOUNT_PATH, mount_path)

    print "You are all set up to use turbolaunch!"

    print "HOWEVER, to enable automatic starting of the instance, you need to set up `aws configure` separately."

if __name__ == "__main__":
    if len(sys.argv) == 1:
        # Configure defaults here
        login('')
    elif 'help' in sys.argv[1] or '-h' in sys.argv[1]:
        warn()
        usage()
    elif 'setup' in sys.argv[1]:
        setup()
    else:
        login(sys.argv[1])
