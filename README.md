# AWS Turbolaunch
A quick tool for mounting an AWS instance via SSHFS on a mac, signing in with multi-factor annotation, and starting the instance using the command line tools if it is not already running, all in one very short command

Just configure the top of this python script:

```
AWS_URL = '[ENTER YOUR AWS INSTANCE URL]'
AWS_INSTANCE_ID = '[ENTER YOUR AWS INSTANCE ID]'
```

and run

```
$ chmod +x turbolaunch.py
$ ./turbolaunch.py
```

Add an alias and you'll be running in no time.

## Dependencies

Install using `pip install ...`:

```
awscli
subprocess
pexpect
keyring
getpass
commands
json
```
