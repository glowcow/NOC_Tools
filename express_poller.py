#!/bin/python3

from main.config import bc
from main.sql import pgsql
from main.tg_api import tg_msg
from main.snmp import snmp
from multiprocessing import Pool
import re

def bsa_poller_2(host):
    if re.findall(r'[0-9]+(?:\.[0-9]+){3}', host):
        bsa_name = pgsql.read(f"SELECT bsa FROM bsa WHERE ip_vprn140 = '{host}'")[0]
        if len(pgsql.read(f"SELECT DISTINCT active_bsa FROM rings WHERE active_bsa = '{bsa_name}'")) != 0:
            if len(pgsql.read(f"SELECT DISTINCT backup_bsa FROM rings WHERE backup_bsa = '{bsa_name}'")) != 0:
                bsa_role = 'Active+Backup'
            else:
                bsa_role = 'Active'
        elif len(pgsql.read(f"SELECT DISTINCT active_mku FROM mku_ring WHERE active_mku = '{bsa_name}'")) != 0:
            if len(pgsql.read(f"SELECT DISTINCT backup_mku FROM mku_ring WHERE backup_mku = '{bsa_name}'")) != 0:
                bsa_role = 'Active+Backup'
            else:
                bsa_role = 'Active'
        else:
            bsa_role = 'Backup'
        bsa_type = snmp.vendor(host)
        if bsa_type != False:
            if bsa_type == 'Huawei':
                print(f'{bc.GREEN}{bsa_role} MKU-{bsa_name} - {bsa_type}{bc.ENDC}')
                if bsa_role == 'Active':
                    pgsql.write(f"UPDATE rings SET act_state = 'green', active_type = '{bsa_type}' WHERE active_bsa = '{bsa_name}'")
                elif bsa_role == 'Backup':
                    pgsql.write(f"UPDATE rings SET bkp_state = 'green', backup_type = '{bsa_type}' WHERE backup_bsa = '{bsa_name}'")
                elif bsa_role == 'Active+Backup':
                    pgsql.write(f"UPDATE rings SET bkp_state = 'green', backup_type = '{bsa_type}', act_state = 'green', active_type = '{bsa_type}' WHERE backup_bsa = '{bsa_name}'")
                chk_vsi1 = snmp.walk(host, 'iso.3.6.1.4.1.2011.5.25.119.1.1.5.1.13.3')
                if chk_vsi1 != None:
                    for each in chk_vsi1:
                        oid_res = each.split('.')
                        return (f'{host}|{bsa_role}|MKU-{bsa_name}|VSI-{oid_res[19]}|peer {".".join(oid_res[20:24])}🔻')
                chk_vsi2 = snmp.walk(host, 'iso.3.6.1.4.1.2011.5.25.119.1.1.5.1.13.4')
                if chk_vsi2 != None:
                    for each in chk_vsi2:
                        oid_res = each.split('.')
                        return (f'{host}|{bsa_role}|MKU-{bsa_name}|VSI-{oid_res[20]}|peer {".".join(oid_res[21:25])}🔻')
            elif bsa_type == 'MikroTik':
                print(f'{bc.GREEN}{bsa_role} MKU-{bsa_name} - {bsa_type}{bc.ENDC}')
                if bsa_role == 'Active':
                    pgsql.write(f"UPDATE rings SET act_state = 'green', active_type = '{bsa_type}' WHERE active_bsa = '{bsa_name}'")
                elif bsa_role == 'Backup':
                    pgsql.write(f"UPDATE rings SET bkp_state = 'green', backup_type = '{bsa_type}' WHERE backup_bsa = '{bsa_name}'")
                elif bsa_role == 'Active+Backup':
                    pgsql.write(f"UPDATE rings SET bkp_state = 'green', backup_type = '{bsa_type}', act_state = 'green', active_type = '{bsa_type}' WHERE backup_bsa = '{bsa_name}'")
        else:
            print(f'{bc.RED}{bsa_role} MKU-{bsa_name} - Unreachable!{bc.ENDC}')
            if bsa_role == 'Active':
                pgsql.write(f"UPDATE rings SET act_state = 'red' WHERE active_bsa = '{bsa_name}'")
            elif bsa_role == 'Backup':
                pgsql.write(f"UPDATE rings SET bkp_state = 'red' WHERE backup_bsa = '{bsa_name}'")
            elif bsa_role == 'Active+Backup':
                pgsql.write(f"UPDATE rings SET bkp_state = 'red', act_state = 'red' WHERE backup_bsa = '{bsa_name}'")
            return (f'{host}|{bsa_role}|MKU-{bsa_name}🔻')

mp = Pool(64)
bsa_list = pgsql.read(f'SELECT ip_vprn140 FROM bsa')
err_poller = list(filter(bool,(mp.map(bsa_poller_2, bsa_list))))
bsa_cnt = int((list(pgsql.read(f'SELECT COUNT(*) FROM bsa')))[0])
err_bsa = []
err_vsi = []
err_msg = []

for err in err_poller:
    if re.findall('VSI-', err):
        err_vsi.append(err)
    else:
        err_bsa.append(err)

if len(err_bsa) != 0:
    msg1 = "\n".join(err_bsa)
    err_msg.append(f'<b>Недоступные MKU</b>:\n<code>{msg1}</code>')
    bsa_down = ", ".join(err_bsa)
    pgsql.write(f"INSERT INTO bsa_poller_stat values ('{bsa_cnt}', '{bsa_cnt-(len(err_bsa))}', '{len(err_bsa)}', '{bsa_down}')")
else:
    pgsql.write(f"INSERT INTO bsa_poller_stat values ('{bsa_cnt}', '{bsa_cnt-(len(err_bsa))}', '{len(err_bsa)}', 'All BSA is UP!')")
if len(err_vsi) != 0:
    msg2 = "\n".join(err_vsi)
    err_msg.append(f'<b>Проблемные VSI</b>:\n<code>{msg2}</code>')
if len(err_msg) != 0:
    msg = "\n".join(err_msg)
    tg_msg.send('-1001301855627', '====== #express_poller_2 🚀======', msg)
    print(msg)

pgsql.write(f"DELETE FROM bsa_poller_stat WHERE date < NOW() - INTERVAL '30 days'")