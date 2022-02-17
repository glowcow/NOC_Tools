#!/bin/python3

from main.ssh import ssh
from main.config import radctl, mgmt, bc
import base64, re, time, sys

def mac_flap(vpls, mac, sap, minutes):
    cmd = f'show service id {vpls} fdb detail | match {mac}'
    timeout = time.time() + 60*int(minutes)   # minutes from now
    check = ssh.init(mgmt.bsr01, radctl.username, radctl.password, 1)
    date_s = time.strftime('%d-%b-%Y %H:%M:%S')
    print(f'{bc.GREEN}{date_s}|Search started...{bc.ENDC}')
    while True:
        date = time.strftime('%d-%b-%Y %H:%M:%S')
        if check and time.time() < timeout:
            for each in ssh.invoke(cmd, check).split('\n'):
                if re.findall('L/', each):
                    if not re.findall(sap, each):
                        print(f'{bc.RED}{date}|BSR01 Move-port: {each.split()[2]}{bc.ENDC}')
                    #else:
                    #    print(f'{bc.GREEN}{date}|Move-port on BSR01 not found{bc.ENDC}')
        else:
            ssh.close(check)
            date_f = time.strftime('%d-%b-%Y %H:%M:%S')
            print(f'{bc.GREEN}{date_f}|Search finished{bc.ENDC}')
            return False

def launcher():
    print(f'{bc.BOLD}\nMAC-flapping realtime searching on BSR01{bc.ENDC}\n')
    vpls = input('VPLS service ID:')
    mac = input('Uplink peer MAC:')
    sap = input('Uplink SAP:')
    minutes = input('Timeout in minutes:')
    print(f'{bc.GREEN}\nVPLS: {vpls}\nMAC: {mac}\nSAP: {sap}\nTimeout: {minutes} min.\n{bc.ENDC}')
    slct = input(f'Start searching? (y/n):')
    if slct == 'y':
        mac_flap(vpls, mac, sap, minutes)
    elif slct == 'n':
        sys.exit(f'{bc.CYAN}{"="*34} EXITING {"="*34}{bc.ENDC}')
    else:
        launcher()

if __name__ == "__main__":
    launcher()