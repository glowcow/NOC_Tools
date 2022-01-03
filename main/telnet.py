#!/bin/python3

import base64
import time
import telnetlib
from main.config import bc

class telnet:
    def huawei(cmd, host, username, password):
        try:
            tn = telnetlib.Telnet(host, port = 23, timeout = 5)
            username = base64.b64decode(username).decode("ascii")+'\n'
            password = base64.b64decode(password).decode("ascii")+'\n'
            tn.read_until(b'Username:')
            tn.write(username.encode("ascii"))
            time.sleep(1)
            tn.read_until(b'Password:')
            tn.write(password.encode("ascii"))
            time.sleep(1)
            #print(f'{bc.GREEN}[+]{bc.ENDC} Connection was established successfully to {host}')
            tn.write(cmd.encode("ascii"))
            time.sleep(10)
            out = tn.read_very_eager().decode("ascii")
            tn.close()
            #print(f'{bc.RED}[!]{bc.ENDC} Disconnected from {host}')
            return out
        except:
            print(f'{bc.RED}[!]{bc.ENDC} Unknown Telnet Error on {host}')
            return False