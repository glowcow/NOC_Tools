#!/bin/python3

from main.ssh import ssh
from main.sql import pgsql
from main.telnet import telnet
from main.log import log
from main.tg_api import tg_msg
from main.snmp import snmp
from main.config import radctl, mik_acc, bc
from multiprocessing import Pool
import time, re

def bsa_backup(host):
    date = time.strftime('%d-%b-%Y')
    if re.findall(r'[0-9]+(?:\.[0-9]+){3}', host):
        bsa = (pgsql.read(f"SELECT bsa FROM bsa WHERE ip_vprn140 = '{host}'"))[0]
        bsa_type = snmp.vendor(host)
        if bsa_type != False:
            if bsa_type == 'Huawei':
                cmd_h = (f'save\ny\nsave config.cfg\ny\ntftp 176.213.132.105 vpn-instance MGMT put flash:/config.cfg /Backup/BSA/{date}_BSA-{bsa}.cfg\n')
                result = telnet.huawei(cmd_h, host, radctl.username, radctl.password)
                if result != False:
                    if re.findall('TFTP: Uploading the file successfully.', result):
                        print(f'{bc.CYAN}{host}|BSA{bsa} - {bsa_type} - Backup complete!{bc.ENDC}')
                    else:
                        print(f'{bc.RED}{host}|BSA{bsa} - {bsa_type} - Backup error!{bc.ENDC}')
                        return (f'{host}|BSA{bsa} - {bsa_type} - Backup error!')
                else:
                    print(f'{bc.RED}{host}|BSA{bsa} - {bsa_type} - Telnet Error!{bc.ENDC}')
                    return (f'{host}|BSA{bsa} - {bsa_type} - Telnet Error!')
            elif bsa_type == 'MikroTik':
                cmd_m = (f'/export file=exportfile_script.rsc;\n:delay 5;\n/tool fetch address=10.77.177.1 src-path=exportfile_script.rsc mode=ftp upload=yes user=ftp_mikr pass=polinom1 dst-path="Backup/BSA/{date}_BSA-{bsa}.rsc";\n:delay 2;\n')
                s = ssh.init(host, mik_acc.username_m, mik_acc.password_m, 2)
                if s != False:
                    result = ssh.exec(cmd_m, s)
                    if re.findall('status: finished', result):
                        print(f'{host}|BSA{bsa} - {bsa_type} - Backup complete!')
                    else:
                        print(f'{bc.RED}{host}|BSA{bsa} - {bsa_type} - Backup error!{bc.ENDC}')
                        return (f'{host}|BSA{bsa} - {bsa_type} - Backup error!')
                    ssh.close(s)
                else:
                    s = ssh.init(host, mik_acc.username_m, mik_acc.password_m2, 2)
                    if s != False:
                        result = ssh.exec(cmd_m, s)
                        if re.findall('status: finished', result):
                            print(f'{host}|BSA{bsa} - {bsa_type} - Backup complete!')
                        else:
                            print(f'{bc.RED}{host}|BSA{bsa} - {bsa_type} - Backup error!{bc.ENDC}')
                            return (f'{host}|BSA{bsa} - {bsa_type} - Backup error!')
                        ssh.close(s)
                    else:
                        print(f'{bc.RED}{host}|BSA{bsa} - {bsa_type} - SSH Error!{bc.ENDC}')
                        return (f'{host}|BSA{bsa} - {bsa_type} - SSH Error!')
        else:
            print(f'{bc.RED}{host}|BSA{bsa} - SNMP Error!{bc.ENDC}')
            return (f'{host}|BSA{bsa} - SNMP Error!')

def main():
    bsa_list = pgsql.read(f'SELECT ip_vprn140 FROM bsa')
    pool = Pool(64)
    err_list_bsa = pool.map(bsa_backup, bsa_list)
    err_list = list(filter(bool,(err_list_bsa)))
    if len(err_list) != 0:
        msg = "\n".join(err_list)
        log.write(msg, 3)
        tg_msg.send('-1001301855627', '====== #backup_script_2 💾======', f'<code>{msg}</code>')

if __name__ == "__main__":
    main()