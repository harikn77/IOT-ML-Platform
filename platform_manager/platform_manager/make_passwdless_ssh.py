import json
import sys

server_list = sys.argv[1]
servers = json.loads(open(server_list).read())

f = open('make_passwdless.sh', 'w')
f.write('### This file is autogenerated by make_passwdless.py ###\n')

stub = """
#!/bin/sh

set -o errexit
set -o nounset

mkdir -p ~/.ssh
if [ ! -f ~/.ssh/id_rsa ]; then
    ssh-keygen -q -N '' -t rsa -f ~/.ssh/id_rsa
fi

"""

for worker in servers['workers']:
    stub += "sshpass -p " + worker['passwd'] + " ssh-copy-id -o StrictHostKeyChecking=no " + worker['user'] + "@" + worker['ip'] + "\n"

f.write(stub)
f.close()

