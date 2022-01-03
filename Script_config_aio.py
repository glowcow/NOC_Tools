#!/bin/python3

from main.ssh import ssh
from main.sql import pgsql
from main.telnet import telnet
from main.snmp import snmp
from main.log import log
from ipaddress import IPv4Network
from simple_term_menu import TerminalMenu
from  main.config import radctl, mik_acc, mgmt, cts_var, bc
import time
import re
import random
import secrets

def l2vpn_config():
    print(f'{bc.CYAN}{"="*25} Start configuration L2VPN {"="*25}{bc.ENDC}')
    s1 = ssh.init(mgmt.bsr01, radctl.username, radctl.password, 1)
    s2 = ssh.init(mgmt.bsr02, radctl.username, radctl.password, 1)
    pw = input('Номер полукольца BSA [500-999]:')
    vpls = input('Номер VPLS на BSR:')
    vlan = input('Клиентский VLAN:')
    rate = input('Скорость канала (Мб/с):')
    print(f'{bc.CYAN}{"="*32} Checking... {"="*32}{bc.ENDC}')
    if pgsql.read(f"SELECT id FROM l2vpn_token WHERE pw = '{pw}' and vpls = '{vpls}'"):
        print(f'{bc.RED}[!]{bc.ENDC} Такое L2VPN включение уже настроенно!')
        return False
    a_bsa = pgsql.read(f"SELECT active_bsa FROM rings WHERE pw_ring = '{pw}'")[0]
    b_bsa = pgsql.read(f"SELECT backup_bsa FROM rings WHERE pw_ring = '{pw}'")[0]
    a_bsa_base = pgsql.read(f"SELECT ip_base FROM bsa WHERE bsa = '{a_bsa}'")[0]
    b_bsa_base = pgsql.read(f"SELECT ip_base FROM bsa WHERE bsa = '{b_bsa}'")[0]
    a_bsa_140 = pgsql.read(f"SELECT ip_vprn140 FROM bsa WHERE bsa = '{a_bsa}'")[0]
    b_bsa_140 = pgsql.read(f"SELECT ip_vprn140 FROM bsa WHERE bsa = '{b_bsa}'")[0]
    a_bsa_s = snmp.vendor(a_bsa_140)
    b_bsa_s = snmp.vendor(b_bsa_140)
    cmd_mtu = (f'show service id {vpls} sdp detail | match SdpOperMTU')
    for a in ssh.invoke(cmd_mtu, s1).split('\n'):
        if not re.findall('MinReqd', a):
            mtu = False
        else:
            mtu = a.split()[3]
            break

    if not mtu or not a_bsa_s or not b_bsa_s:
        return False

    print(f'Полукольцо: {pw} / SDP-3{pw}')
    print(f'Номер VPLS: {vpls}')
    print(f'Клиентский VLAN: {vlan}')
    print(f'Скорость канала: {rate} Mb/s')
    print(f'MTU в VPLS на BSR: {mtu} byte')
    if a_bsa_base == b_bsa_base:
        print(f'{bc.GREEN}|{a_bsa_s} BSA-{a_bsa}|{bc.ENDC}')
        print(f'IP адрес Base BSA: {a_bsa_base}')
        print(f'IP адрес VPRN140 BSA: {a_bsa_140}')
    else:
        print(f'Основная{bc.GREEN}|{a_bsa_s} BSA-{a_bsa}|{bc.ENDC} <===> {bc.GREEN}|BSA-{b_bsa} {b_bsa_s}|{bc.ENDC}Резервная')
        print(f'IP адрес Base основной BSA: {a_bsa_base}')
        print(f'IP адрес Base резервной BSA: {b_bsa_base}')
        print(f'IP адрес VPRN140 основной BSA: {a_bsa_140}')
        print(f'IP адрес VPRN140 резервной BSA: {b_bsa_140}')
    
    slct = input('Начинаем конфигурацию? (y/n):')
    if slct != 'y':
        print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted!')
        ssh.close(s1)
        ssh.close(s2)
        return False
    #Backup BSA exists
    if a_bsa_base != b_bsa_base:
        # Configure active side
        if a_bsa_s == 'Huawei':
            # Connect to bsr01
            print(f'Настраиваю на BSR01...')
            cmd1 = (f'configure service vpls {vpls}\nendpoint "BSA{a_bsa}-BSA{b_bsa}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.2\nexit\nexit\nspoke-sdp 3{pw}:{vpls} endpoint "BSA{a_bsa}-BSA{b_bsa}" create\nno shutdown\nexit\n')
            result1 = ssh.invoke(cmd1, s1)
            log.write(result1, 2)
            print(f'Готово')
            # Connect to active BSA
            print(f'Настраиваю на основной BSA{a_bsa} {a_bsa_s}...')
            cmd2 = (f'system-view\nvsi {vpls}\ndescription BSA{a_bsa}-BSA{b_bsa}\npwsignal ldp\nvsi-id {vpls}\npeer 10.6.200.1 upe\npeer {b_bsa_base} upe\nquit\nmtu {mtu}\nencapsulation ethernet\nignore-ac-state\nquit\n')+'\n'
            result2 = telnet.huawei(cmd2, a_bsa_140, radctl.username, radctl.password)
            log.write(result2, 2)
            print(f'Готово')
        elif a_bsa_s == 'MikroTik':
            # Connect to bsr01
            print(f'Настраиваю на BSR01...')
            cmd3 = (f'configure service vpls {vpls}\nendpoint "BSA{a_bsa}-BSA{b_bsa}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.2\nexit\nexit\nspoke-sdp 3{pw}:{vpls} create\nno shutdown\nexit\n')
            result1 = ssh.invoke(cmd3, s1)
            log.write(result1, 2)
            print(f'Готово')
            # Connect to active BSA
            print(f'Настраиваю на основной BSA{a_bsa} {a_bsa_s}...')
            cmd4 = (f'/interface vpls add advertised-l2mtu={mtu} cisco-style=yes cisco-style-id={vpls} disabled=no l2mtu=1600 name=h-vpls{vpls} remote-peer=10.6.200.1\n/interface bridge add mtu=1500 name=Bridge_vpls{vpls} protocol-mode=none\n/interface bridge port add bridge=Bridge_vpls{vpls} interface=h-vpls{vpls}\n')+'\n'
            s_4 = ssh.init(a_bsa_140, mik_acc.username_m, mik_acc.password_m, 2)
            if s_4:
                result2 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            else:
                s_4 = ssh.init(a_bsa_140, mik_acc.username_m, mik_acc.password_m2, 2)
                result2 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            log.write(result2, 2)
            print(f'Готово')
        else:
            print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted, wrong BSA HW!')
        # Configure backup side
        if b_bsa_s == 'Huawei':
            # Connect to bsr02
            print(f'Настраиваю на BSR02...')
            cmd1 = (f'configure service vpls {vpls}\nendpoint "BSA{a_bsa}-BSA{b_bsa}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.1\nexit\nexit\nspoke-sdp 3{pw}:{vpls} endpoint "BSA{a_bsa}-BSA{b_bsa}" create\nno shutdown\nexit\n')
            result1 = ssh.invoke(cmd1, s2)
            log.write(result1, 2)
            print(f'Готово')
            # Connect to backup BSA
            print(f'Настраиваю на резервной BSA{b_bsa} {b_bsa_s}...')
            cmd2 = (f'system-view\nvsi {vpls}\ndescription BSA{a_bsa}-BSA{b_bsa}\npwsignal ldp\nvsi-id {vpls}\npeer 10.6.200.2 upe\npeer {a_bsa_base} upe\nquit\nmtu {mtu}\nencapsulation ethernet\nignore-ac-state\nquit\n')+'\n'
            result2 = telnet.huawei(cmd2, b_bsa_140, radctl.username, radctl.password)
            log.write(result2, 2)
            print(f'Готово')
        elif b_bsa_s == 'MikroTik':
            # Connect to bsr02
            print(f'Настраиваю на BSR02...')
            cmd3 = (f'configure service vpls {vpls}\nendpoint "BSA{a_bsa}-BSA{b_bsa}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.1\nexit\nexit\nspoke-sdp 3{pw}:{vpls} create\nno shutdown\nexit\n')
            result1 = ssh.invoke(cmd3, s2)
            log.write(result1, 2)
            print(f'Готово')
            # Connect to backup BSA
            print(f'Настраиваю на резервной BSA{b_bsa} {b_bsa_s}...')
            cmd4 = (f'/interface vpls add advertised-l2mtu={mtu} cisco-style=yes cisco-style-id={vpls} disabled=no l2mtu=1600 name=h-vpls{vpls} remote-peer=10.6.200.2\n/interface bridge add mtu=1500 name=Bridge_vpls{vpls} protocol-mode=none\n/interface bridge port add bridge=Bridge_vpls{vpls} interface=h-vpls{vpls}\n')+'\n'
            s_4 = ssh.init(b_bsa_140, mik_acc.username_m, mik_acc.password_m, 2)
            if s_4:
                result2 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            else:
                s_4 = ssh.init(b_bsa_140, mik_acc.username_m, mik_acc.password_m2, 2)
                result2 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            log.write(result2, 2)
            print(f'Готово')
        else:
            print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted, wrong BSA HW!')
    #No Backup BSA
    else:
        if a_bsa_s == 'Huawei':
            # Connect to bsr01
            print(f'Настраиваю на BSR01...')
            cmd1 = (f'configure service vpls {vpls}\nendpoint "BSA{a_bsa}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.2\nexit\nexit\nspoke-sdp 3{pw}:{vpls} endpoint "BSA{a_bsa}" create\nno shutdown\nexit\n')
            result1 = ssh.invoke(cmd1, s1)
            log.write(result1, 2)
            print(f'Готово')
            # Connect to BSA
            print(f'Настраиваю BSA{a_bsa} {a_bsa_s}...')
            cmd2 = (f'system-view\nvsi {vpls}\ndescription BSA{a_bsa}\npwsignal ldp\nvsi-id {vpls}\npeer 10.6.200.1 upe\npeer 10.6.200.2 upe\nquit\nmtu {mtu}\nencapsulation ethernet\nignore-ac-state\nquit\n')+'\n'
            result2 = telnet.huawei(cmd2, a_bsa_140, radctl.username, radctl.password)
            log.write(result2, 2)
            print(f'Готово')
        elif a_bsa_s == 'MikroTik':
            # Connect to bsr01
            print(f'Настраиваю на BSR01...')
            cmd3 = (f'configure service vpls {vpls}\nendpoint "BSA{a_bsa}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.2\nexit\nexit\nspoke-sdp 3{pw}:{vpls} create\nno shutdown\nexit\n')
            result1 = ssh.invoke(cmd3, s1)
            log.write(result1, 2)
            print(f'Готово')
            # Connect to BSA
            print(f'Настраиваю BSA{a_bsa} {a_bsa_s}...')
            cmd4 = (f'/interface vpls add advertised-l2mtu={mtu} cisco-style=yes cisco-style-id={vpls} disabled=no l2mtu=1600 name=h-vpls{vpls} remote-peer=10.6.200.1\n/interface bridge add mtu=1500 name=Bridge_vpls{vpls} protocol-mode=none\n/interface bridge port add bridge=Bridge_vpls{vpls} interface=h-vpls{vpls}\n')+'\n'
            s_4 = ssh.init(a_bsa_140, mik_acc.username_m, mik_acc.password_m, 2)
            if s_4:
                result2 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            else:
                s_4 = ssh.init(a_bsa_140, mik_acc.username_m, mik_acc.password_m2, 2)
                result2 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            log.write(result2, 2)
            print(f'Готово')
        else:
            print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted, wrong BSA HW!')
        # Configure backup side
        if a_bsa_s == 'Huawei':
            # Connect to bsr02
            print(f'Настраиваю на BSR02...')
            cmd1 = (f'configure service vpls {vpls}\nendpoint "BSA{a_bsa}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.1\nexit\nexit\nspoke-sdp 3{pw}:{vpls} endpoint "BSA{a_bsa}" create\nno shutdown\nexit\n')
            result02 = ssh.invoke(cmd1, s2)
            log.write(result02, 2)
            print(f'Готово')
        elif a_bsa_s == 'MikroTik':
            # Connect to bsr02
            print(f'Настраиваю на BSR02...')
            cmd3 = (f'configure service vpls {vpls}\nendpoint "BSA{a_bsa}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.1\nexit\nexit\nspoke-sdp 3{pw}:{vpls} create\nno shutdown\nexit\n')
            result02 = ssh.invoke(cmd3, s2)
            log.write(result02, 2)
            print(f'Готово')
        else:
            print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted, wrong BSA HW!')

    pgsql.write(f"insert into l2vpn_token values ('{pw}', '{vpls}', '{vlan}', '{rate}')")
    conf_id = pgsql.read(f"SELECT id FROM l2vpn_token ORDER BY date DESC LIMIT 1")[0]
    print(f'{bc.CYAN}{"="*34} ALL DONE {"="*33}\n{"="*19} Configuration session ID: {conf_id} {"="*19}{bc.ENDC}')
    ssh.close(s1)
    ssh.close(s2)

def l2vpn_remove():
    print(f'{bc.CYAN}{"="*28} Start remove L2VPN {"="*29}{bc.ENDC}')
    s1 = ssh.init(mgmt.bsr01, radctl.username, radctl.password, 1)
    s2 = ssh.init(mgmt.bsr02, radctl.username, radctl.password, 1)
    conf_id = input('Введите ID включения: ')
    print(f'{bc.CYAN}{"="*32} Checking... {"="*32}{bc.ENDC}')
    pw = pgsql.read(f"SELECT pw FROM l2vpn_token WHERE id = '{conf_id}'")[0]
    if not re.findall(r'\b\d{3}\b', str(pw)):
        print(f'{bc.RED}[!]{bc.ENDC} Неверный ID включения L2VPN Радио!')
        ssh.close(s1)
        ssh.close(s2)
        return False
    vpls = pgsql.read(f"SELECT vpls FROM l2vpn_token WHERE id = '{conf_id}'")[0]
    vlan = pgsql.read(f"SELECT vlan FROM l2vpn_token WHERE id = '{conf_id}'")[0]
    rate = pgsql.read(f"SELECT rate FROM l2vpn_token WHERE id = '{conf_id}'")[0]
    a_bsa = pgsql.read(f"SELECT active_bsa FROM rings WHERE pw_ring = '{pw}'")[0]
    b_bsa = pgsql.read(f"SELECT backup_bsa FROM rings WHERE pw_ring = '{pw}'")[0]
    a_bsa_base = pgsql.read(f"SELECT ip_base FROM bsa WHERE bsa = '{a_bsa}'")[0]
    b_bsa_base = pgsql.read(f"SELECT ip_base FROM bsa WHERE bsa = '{b_bsa}'")[0]
    a_bsa_140 = pgsql.read(f"SELECT ip_vprn140 FROM bsa WHERE bsa = '{a_bsa}'")[0]
    b_bsa_140 = pgsql.read(f"SELECT ip_vprn140 FROM bsa WHERE bsa = '{b_bsa}'")[0]
    a_bsa_s = snmp.vendor(a_bsa_140)
    b_bsa_s = snmp.vendor(b_bsa_140)
    if not a_bsa_s or not b_bsa_s:
        return False
    print(f'Полукольцо: {pw} / SDP-3{pw}')
    print(f'Номер VPLS: {vpls}')
    print(f'Клиентский VLAN: {vlan}')
    print(f'Скорость канала: {rate} Mb/s')
    #print(f'MTU в VPLS на BSR: {mtu} byte')

    if a_bsa_base == b_bsa_base:
        print(f'{bc.GREEN}|{a_bsa_s} BSA-{a_bsa}|{bc.ENDC}')
        print(f'IP адрес Base BSA: {a_bsa_base}')
        print(f'IP адрес VPRN140 BSA: {a_bsa_140}')
    else:
        print(f'Основная{bc.GREEN}|{a_bsa_s} BSA-{a_bsa}|{bc.ENDC} <===> {bc.GREEN}|BSA-{b_bsa} {b_bsa_s}|{bc.ENDC}Резервная')
        print(f'IP адрес Base основной BSA: {a_bsa_base}')
        print(f'IP адрес Base резервной BSA: {b_bsa_base}')
        print(f'IP адрес VPRN140 основной BSA: {a_bsa_140}')
        print(f'IP адрес VPRN140 резервной BSA: {b_bsa_140}')
    
    slct = input('Начинаем удаление? (y/n):')
    if slct != 'y':
        print(f'{bc.RED}[!]{bc.ENDC} Remove aborted!')
        ssh.close(s1)
        ssh.close(s2)
        return False
    #Backup BSA exists
    if a_bsa_base != b_bsa_base:
        #Connect to bsr01/bsr02
        print(f'Удаляю на BSR01 и BSR02...')
        cmd1 = (f'configure service vpls {vpls}\nspoke-sdp 3{pw}:{vpls} shutdown\nno spoke-sdp 3{pw}:{vpls}\nendpoint "BSA{a_bsa}-BSA{b_bsa}" mc-endpoint {vpls}{vlan} no mc-ep-peer\nendpoint "BSA{a_bsa}-BSA{b_bsa}" no mc-endpoint\nno endpoint "BSA{a_bsa}-BSA{b_bsa}"\nexit\n')
        result01 = ssh.invoke(cmd1, s1)
        log.write(result01, 2)
        result02 = ssh.invoke(cmd1, s2)
        log.write(result02, 2)
        print(f'Готово')
        # Configure active side
        if a_bsa_s == 'Huawei':
            # Connect to active BSA
            print(f'Удаляю на основной BSA{a_bsa} {a_bsa_s}...')
            cmd2 = (f'system-view\nundo vsi {vpls}\nY\nquit\n')+'\n'
            result1 = telnet.huawei(cmd2, a_bsa_140, radctl.username, radctl.password)
            log.write(result1, 2)
            print(f'Готово')
        elif a_bsa_s == 'MikroTik':
            # Connect to active BSA
            print(f'Удаляю на основной BSA{a_bsa} {a_bsa_s}...')
            cmd4 = (f'/interface bridge port remove [find interface=h-vpls{vpls}]\n/interface bridge remove [find name=Bridge_vpls{vpls}]\n/interface vpls remove [find cisco-style-id={vpls}]\n')+'\n'
            s_4 = ssh.init(a_bsa_140, mik_acc.username_m, mik_acc.password_m, 2)
            if s_4:
                result2 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            else:
                s_4 = ssh.init(a_bsa_140, mik_acc.username_m, mik_acc.password_m2, 2)
                result2 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            log.write(result2, 2)
            print(f'Готово')
        else:
            print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted, wrong BSA HW!')
        # Configure backup side
        if b_bsa_s == 'Huawei':
            # Connect to backup BSA
            print(f'Удаляю на резервной BSA{b_bsa} {b_bsa_s}...')
            cmd2 = (f'system-view\nundo vsi {vpls}\nY\nquit\n')+'\n'
            result11 = telnet.huawei(cmd2, b_bsa_140, radctl.username, radctl.password)
            log.write(result11, 2)
            print(f'Готово')
        elif b_bsa_s == 'MikroTik':
            # Connect to backup BSA
            print(f'Удаляю на резервной BSA{b_bsa} {b_bsa_s}...')
            cmd4 = (f'/interface bridge port remove [find interface=h-vpls{vpls}]\n/interface bridge remove [find name=Bridge_vpls{vpls}]\n/interface vpls remove [find cisco-style-id={vpls}]\n')+'\n'
            s_4 = ssh.init(b_bsa_140, mik_acc.username_m, mik_acc.password_m, 2)
            if s_4:
                result11 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            else:
                s_4 = ssh.init(b_bsa_140, mik_acc.username_m, mik_acc.password_m2, 2)
                result11 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            log.write(result11, 2)
            print(f'Готово')
        else:
            print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted, wrong BSA HW!')
    #No Backup BSA
    else:
        #Connect to bsr01/bsr02
        print(f'Удаляю на BSR01 и BSR02...')
        cmd1 = (f'configure service vpls {vpls}\nspoke-sdp 3{pw}:{vpls} shutdown\nno spoke-sdp 3{pw}:{vpls}\nendpoint "BSA{a_bsa}" mc-endpoint {vpls}{vlan} no mc-ep-peer\nendpoint "BSA{a_bsa}" no mc-endpoint\nno endpoint "BSA{a_bsa}"\nexit\n')
        result01 = ssh.invoke(cmd1, s1)
        log.write(result01, 2)
        result02 = ssh.invoke(cmd1, s2)
        log.write(result02, 2)
        print(f'Готово')
        if a_bsa_s == 'Huawei':
            # Connect to BSA
            print(f'Удаляю на BSA{a_bsa} {a_bsa_s}...')
            cmd2 = (f'system-view\nundo vsi {vpls}\nY\nquit\n')+'\n'
            result1 = telnet.huawei(cmd2, a_bsa_140, radctl.username, radctl.password)
            log.write(result1, 2)
            print(f'Готово')
        elif a_bsa_s == 'MikroTik':
            # Connect to BSA
            print(f'Удаляю на BSA{a_bsa} {a_bsa_s}...')
            cmd4 = (f'/interface bridge port remove [find interface=h-vpls{vpls}]\n/interface bridge remove [find name=Bridge_vpls{vpls}]\n/interface vpls remove [find cisco-style-id={vpls}]\n')+'\n'
            s_4 = ssh.init(a_bsa_140, mik_acc.username_m, mik_acc.password_m, 2)
            if s_4:
                result1 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            else:
                s_4 = ssh.init(a_bsa_140, mik_acc.username_m, mik_acc.password_m2, 2)
                result1 = ssh.exec(cmd4, s_4)
                ssh.close(s_4)
            log.write(result1, 2)
            print(f'Готово')
        else:
            print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted, wrong BSA HW!')

    pgsql.write(f"DELETE FROM l2vpn_token WHERE id = '{conf_id}'")
    print(f'{bc.CYAN}{"="*34} ALL DONE {"="*33}{bc.ENDC}')
    ssh.close(s1)
    ssh.close(s2)

def vpls_create(vpls_type, bsr01, bsr02):
    s1 = ssh.init(bsr01, radctl.username, radctl.password, 1)
    s2 = ssh.init(bsr02, radctl.username, radctl.password, 1)
    if vpls_type == 1 and s1 != False and s2 != False:
        mtu = input('Введите значение MTU[1514-9194]:')
        vpls_all = []
        check_1 = (f'show service fdb-info | match "Service Id" | match expression "[5][6-9][0-9][0-9][0-9]"')
        for each in ssh.invoke(check_1, s1).split():
            fnd = re.findall(r'\b\d{5}\b', each)
            if fnd:
                vpls_all.append(int(each))
        vpls_free = sorted(set(range(vpls_all[0], vpls_all[-1])) - set(vpls_all))
        if len(vpls_free) != 0:
            new_vpls = random.choice(vpls_free)
            print(f'Количество пропущенных VPLS: {bc.CYAN}{len(vpls_free)}{bc.ENDC}\nДля настройки будет взят VPLS: {bc.GREEN}{new_vpls}{bc.ENDC}')
            check_2 = (f'show service fdb-info | match "Service Id" | match {new_vpls}')
            fnd = re.findall('Mac Move', ssh.invoke(check_2, s1))
            if fnd:
                print(f'{bc.RED}[!]{bc.ENDC} VPLS {new_vpls} уже существует!')
                return False
            else:
                slct = input(f'VPLS {bc.GREEN}{new_vpls}{bc.ENDC} свободен, начинаем настройку? (y/n):')
                if slct != 'y':
                    return False
                else:
                    print(f'Настраиваю на BSR01...')
                    cmd1 = (f'configure service vpls {new_vpls} create customer 1\ndescription "CREATED_BY_SCRIPT"\nservice-mtu {mtu}\nmesh-sdp 12:{new_vpls} create\nno shutdown\nexit\nno shutdown\nexit\n')
                    result1 = ssh.invoke(cmd1, s1)
                    log.write(result1, 2)
                    print(f'Готово')
                    print(f'Настраиваю на BSR02...')
                    cmd2 = (f'configure service vpls {new_vpls} create customer 1\ndescription "CREATED_BY_SCRIPT"\nservice-mtu {mtu}\nmesh-sdp 21:{new_vpls} create\nno shutdown\nexit\nno shutdown\nexit\n')
                    result2 = ssh.invoke(cmd2, s2)
                    log.write(result2, 2)
                    print(f'Готово')
                    ssh.close(s1)
                    ssh.close(s2)
                    return True
        else:
            new_vpls = vpls_all[-1]+1
            check_2 = (f'show service fdb-info | match "Service Id" | match {new_vpls}')
            fnd = re.findall('Mac Move', ssh.invoke(check_2, s1))
            if fnd:
                print(f'{bc.RED}[!]{bc.ENDC} VPLS {new_vpls} уже существует!')
                return False
            else:
                slct = input(f'VPLS {bc.GREEN}{new_vpls}{bc.ENDC} свободен, начинаем настройку? (y/n):')
                if slct != 'y':
                    return False
                else:
                    print(f'Настраиваю на BSR01...')
                    cmd1 = (f'configure service vpls {new_vpls} create customer 1\ndescription "CREATED_BY_SCRIPT"\nservice-mtu {mtu}\nmesh-sdp 12:{new_vpls} create\nno shutdown\nexit\nno shutdown\nexit\n')
                    result1 = ssh.invoke(cmd1, s1)
                    log.write(result1, 2)
                    print(f'Готово')
                    print(f'Настраиваю на BSR02...')
                    cmd2 = (f'configure service vpls {new_vpls} create customer 1\ndescription "CREATED_BY_SCRIPT"\nservice-mtu {mtu}\nmesh-sdp 21:{new_vpls} create\nno shutdown\nexit\nno shutdown\nexit\n')
                    result2 = ssh.invoke(cmd2, s2)
                    log.write(result2, 2)
                    print(f'Готово')
                    ssh.close(s1)
                    ssh.close(s2)
                    return True
    elif vpls_type == 2 and s1 != False and s2 != False:
        new_vpls = input('Введите вторую часть выделенного Route Target:')
        mtu = input('Введите значение MTU[1514-9194]:')
        fnd = re.findall(r'^2\d{4}$', new_vpls)
        if fnd:
            check_1 = (f'show service fdb-info | match "Service Id" | match {new_vpls}')
            fnd = re.findall('Mac Move', ssh.invoke(check_1, s1))
            if fnd:
                print(f'{bc.RED}[!]{bc.ENDC} VPLS {new_vpls} уже существует!')
                return False
            else:
                slct = input(f'VPLS {bc.GREEN}{new_vpls}{bc.ENDC} свободен, начинаем настройку? (y/n):')
                if slct != 'y':
                    return False
                else:
                    print(f'Настраиваю на BSR01...')
                    cmd1 = (f'configure service vpls {new_vpls} create customer 1\ndescription "CREATED_BY_SCRIPT"\nservice-mtu {mtu}\nsplit-horizon-group "SDP" create\nexit\nbgp\nroute-distinguisher 2002:{new_vpls}\nroute-target export target:9049:{new_vpls} import target:9049:{new_vpls}\npw-template-binding 1 split-horizon-group "SDP"\nmonitor-oper-group "VRRP-3"\nexit\nexit\nbgp-vpls\nmax-ve-id 128\nve-name "bsr"\nve-id 1\nexit\nno shutdown\nexit\nmesh-sdp 12:{new_vpls} create\nno shutdown\nexit\nno shutdown\nexit\n')
                    result1 = ssh.invoke(cmd1, s1)
                    log.write(result1, 2)
                    print(f'Готово')
                    print(f'Настраиваю на BSR02...')
                    cmd2 = (f'configure service vpls {new_vpls} create customer 1\ndescription "CREATED_BY_SCRIPT"\nservice-mtu {mtu}\nsplit-horizon-group "SDP" create\nexit\nbgp\nroute-distinguisher 2002:{new_vpls}\nroute-target export target:9049:{new_vpls} import target:9049:{new_vpls}\npw-template-binding 1 split-horizon-group "SDP"\nmonitor-oper-group "VRRP-3"\nexit\nexit\nbgp-vpls\nmax-ve-id 128\nve-name "bsr"\nve-id 1\nexit\nno shutdown\nexit\nmesh-sdp 21:{new_vpls} create\nno shutdown\nexit\nno shutdown\nexit\n')
                    result2 = ssh.invoke(cmd2, s2)
                    log.write(result2, 2)
                    print(f'Готово')
                    ssh.close(s1)
                    ssh.close(s2)
                    return True
        else:
            print(f'{bc.RED}[!]{bc.ENDC} Неверный номер Route Target!')
            vpls_create(2, bsr01, bsr02)

def cts_config(cts, subn_pool, eoip_pool, l2tp_lo):
    try:
        s1 = ssh.init(cts, mik_acc.username_cm, mik_acc.password_cm, 2)
        if s1 != False:
            cmd = '/ppp secret print terse\n/interface bridge vlan print terse where dynamic=no\n/interface eoip print terse'
            cpe = input(f'Введите pre-config адрес CPE: ')
            vlan_pool = list(range(110, 4095))
            used_vlan = []
            used_ip = []
            used_eoip = []
            ip_pool = []
            s2 = ssh.init(cpe, mik_acc.username_m, mik_acc.password_m2, 2)
            if s2 != False:
                cpe_query = ssh.exec('/system routerboard print\n/interface ethernet print terse', s2)
                cpe_inf = []
                cpe_eth = []
                for string in cpe_query.split('\n'):
                    if re.findall('model:', string):
                        cpe_inf.append(f'Модель: {string.split(": ")[1]}')
                    if re.findall('serial-number:', string):
                        cpe_inf.append(f'Серийный №: {string.split(": ")[1]}')
                    if re.findall('current-firmware:', string):
                        cpe_inf.append(f'Прошивка: {string.split(": ")[1]}')
                    if re.findall('default-name=ether', string):
                        val = string.split()[0]
                        if string.split()[1] == 'R':
                            state = 'UP'
                        elif string.split()[1] == 'RS':
                            state = 'UP in bridge'
                        elif string.split()[1] == 'S':
                            state = 'DOWN in bridge'
                        else:
                            state = 'DOWN'
                        comment = 'no_comment'
                        for e in string.split():
                            if re.findall('comment=', e):
                                comment = e.split('=')[1]
                            if re.findall(r'^name=', e):
                                eth = e.split('=')[1]
                        cpe_eth.append(f'{val}|{eth}|{comment}|{state}')
                msg1 = "\n".join(cpe_inf)
                msg2 = "\n".join(cpe_eth)
                print(f'\n{bc.BOLD}Информация о CPE:{bc.ENDC}\n{msg1}\nПорты:\n{msg2}\n')
                for subn in subn_pool:
                    for ip in (list(IPv4Network(subn).hosts())):
                        ip_pool.append(str(ip))
                lcl_add_eoip = ip_pool[0]
                query = ssh.exec(cmd, s1)
                for each in query.split():
                    if re.findall('remote-address=', each):
                        used_ip.append(each.split('=')[1])
                    if re.findall('vlan-ids=', each):
                        vlans = each.split('=')[1]
                        if re.findall(',', vlans):
                            for vl in vlans.split(','):
                                used_vlan.append(int(vl))
                        else:
                            used_vlan.append(int(vlans))
                    if re.findall('tunnel-id=', each):
                        used_eoip.append(int(each.split('=')[1]))
                free_ip = list(set(ip_pool) - set(used_ip))
                free_vlan = list(set(vlan_pool) - set(used_vlan))
                free_eoip = list(set(eoip_pool) - set(used_eoip))
                ppp = secrets.token_hex(4)
                mgmt = random.choice(list(set(ip_pool) - set(used_ip)))
                vlan = str(random.choice(list(set(vlan_pool) - set(used_vlan))))
                eoip = str(random.choice(list(set(eoip_pool) - set(used_eoip))))
                if len(free_ip) !=0 and len(free_vlan) !=0 and len(free_eoip) !=0:
                    print(f'{bc.BOLD}Информация о CTS:{bc.ENDC}\nВсего свободных IP/VLAN/EoIP: {bc.CYAN}{len(free_ip)}/{len(free_vlan)}/{len(free_eoip)}{bc.ENDC}\nСвободные для настройки IP и VLAN/EoIP: {bc.GREEN}{mgmt}{bc.ENDC} и {bc.GREEN}{vlan}/{eoip}{bc.ENDC}\nPPP secret: {bc.GREEN}mgmt_{ppp}{bc.ENDC}\n')
                    slct = input(f'Начинаем настройку? (y/n):')
                    if slct != 'y':
                        ssh.close(s1)
                        ssh.close(s2)
                        return False
                    else:
                        desc = input(f'Введите дескрипшн клиента (номер заявки или ID):')
                        cpe_prt = input(f'Укажите номер порта клиента на CPE или оставьте пустым[{cpe_eth[0].split("|")[0]}-{cpe_eth[-1].split("|")[0]}]:')
                        gtw = input(f'Введите IP шлюзa для L2TP (для 192.168.0.1 оставьте пустым):')
                        print(f'Настраиваю на CTS({cts})...')
                        conf_cts = f'/ppp secret add name=mgmt_{ppp} password=pass_{ppp} comment={desc} profile=kombi remote-address={mgmt} service=l2tp\n/interface eoip add !keepalive local-address={lcl_add_eoip} name=eoip-tun{eoip}_{ppp} remote-address={mgmt} tunnel-id={eoip}\n/interface bridge port add bridge=br1 frame-types=admit-only-vlan-tagged horizon=10 interface=eoip-tun{eoip}_{ppp}\n/interface bridge vlan add comment={ppp} bridge=br1 tagged=bon1.L2_UP,eoip-tun{eoip}_{ppp} vlan-ids={vlan}\n'
                        result1 = ssh.exec(conf_cts, s1)
                        log.write(result1, 2)
                        if gtw == '' :
                            if cpe_prt != '' :
                                conf_cpe = f'/interface bridge add frame-types=admit-only-untagged-and-priority-tagged mtu=1500 name=br_{ppp} protocol-mode=none vlan-filtering=yes\n/interface eoip add !keepalive local-address={mgmt} name=eoip-tun{eoip}_{ppp} remote-address={lcl_add_eoip} tunnel-id={eoip}\n/interface l2tp-client add comment={desc} allow=mschap2 connect-to={l2tp_lo} disabled=no keepalive-timeout=30 name=l2tp-out-{ppp} password=pass_{ppp} profile=default user=mgmt_{ppp}\n/interface bridge port add bridge=br_{ppp} interface=eoip-tun{eoip}_{ppp}\n/interface bridge port add bridge=br_{ppp} frame-types=admit-only-untagged-and-priority-tagged interface={cpe_eth[int(cpe_prt)].split("|")[1]} pvid={vlan}\n/interface bridge vlan add bridge=br_{ppp} tagged=eoip-tun{eoip}_{ppp} vlan-ids={vlan}\n/ip route add comment=for_CTS_L2TP distance=5 dst-address={l2tp_lo} gateway=192.168.0.1\n'
                            else:
                                conf_cpe = f'/interface bridge add frame-types=admit-only-untagged-and-priority-tagged mtu=1500 name=br_{ppp} protocol-mode=none vlan-filtering=yes\n/interface eoip add !keepalive local-address={mgmt} name=eoip-tun{eoip}_{ppp} remote-address={lcl_add_eoip} tunnel-id={eoip}\n/interface l2tp-client add comment={desc} allow=mschap2 connect-to={l2tp_lo} disabled=no keepalive-timeout=30 name=l2tp-out-{ppp} password=pass_{ppp} profile=default user=mgmt_{ppp}\n/interface bridge port add bridge=br_{ppp} interface=eoip-tun{eoip}_{ppp}\n/interface bridge vlan add bridge=br_{ppp} tagged=eoip-tun{eoip}_{ppp} vlan-ids={vlan}\n/ip route add comment=for_CTS_L2TP distance=5 dst-address={l2tp_lo} gateway=192.168.0.1\n'
                        else:
                            if cpe_prt != '' :
                                conf_cpe = f'/interface bridge add frame-types=admit-only-untagged-and-priority-tagged mtu=1500 name=br_{ppp} protocol-mode=none vlan-filtering=yes\n/interface eoip add !keepalive local-address={mgmt} name=eoip-tun{eoip}_{ppp} remote-address={lcl_add_eoip} tunnel-id={eoip}\n/interface l2tp-client add comment={desc} allow=mschap2 connect-to={l2tp_lo} disabled=no keepalive-timeout=30 name=l2tp-out-{ppp} password=pass_{ppp} profile=default user=mgmt_{ppp}\n/interface bridge port add bridge=br_{ppp} interface=eoip-tun{eoip}_{ppp}\n/interface bridge port add bridge=br_{ppp} frame-types=admit-only-untagged-and-priority-tagged interface={cpe_eth[int(cpe_prt)].split("|")[1]} pvid={vlan}\n/interface bridge vlan add bridge=br_{ppp} tagged=eoip-tun{eoip}_{ppp} vlan-ids={vlan}\n/ip route add comment=for_CTS_L2TP distance=5 dst-address={l2tp_lo} gateway={gtw}\n'
                            else:
                                conf_cpe = f'/interface bridge add frame-types=admit-only-untagged-and-priority-tagged mtu=1500 name=br_{ppp} protocol-mode=none vlan-filtering=yes\n/interface eoip add !keepalive local-address={mgmt} name=eoip-tun{eoip}_{ppp} remote-address={lcl_add_eoip} tunnel-id={eoip}\n/interface l2tp-client add comment={desc} allow=mschap2 connect-to={l2tp_lo} disabled=no keepalive-timeout=30 name=l2tp-out-{ppp} password=pass_{ppp} profile=default user=mgmt_{ppp}\n/interface bridge port add bridge=br_{ppp} interface=eoip-tun{eoip}_{ppp}\n/interface bridge vlan add bridge=br_{ppp} tagged=eoip-tun{eoip}_{ppp} vlan-ids={vlan}\n/ip route add comment=for_CTS_L2TP distance=5 dst-address={l2tp_lo} gateway={gtw}\n'
                        print(f'Настраиваю на CPE({cpe})...')
                        result2 = ssh.exec(conf_cpe, s2)
                        log.write(result2, 2)
                        print(f'{bc.BOLD}{"="*5} Готово! {"="*5}{bc.ENDC}')
                        pgsql.write(f"insert into cts_token values ('{ppp}', '{desc}', '{mgmt}', '{eoip}', '{vlan}')")
                        ssh.close(s1)
                        ssh.close(s2)
                        return True
                else:
                    print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Недоступны необходимые ресурсы на CTS({cts})\n')
                    return False
            else:
                print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Проблема с SSH на CPE({cpe})\n')
                return False
        else:
            print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Проблема с SSH на CTS({cts})\n')
            return False
    except IndexError:
        print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Число вне доступного диапазона [{cpe_eth[0].split("|")[0]}-{cpe_eth[-1].split("|")[0]}]\n')
        return False 
    except ValueError:
        print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Некорректно настроены VLAN на CTS или неверно указано число\n')
        return False    

def cts_remove(cts):
    mgmt = input('Введите MGMT IP адрес CPE (q-выход):')
    if re.findall(r'[0-9]+(?:\.[0-9]+){3}', mgmt):
        cmd = f'/ppp secret print terse where remote-address="{mgmt}"'
        s1 = ssh.init(cts, mik_acc.username_cm, mik_acc.password_cm, 2)
        if s1 != False:
            query = ssh.exec(cmd, s1)
            if re.findall(r'mgmt_[a-f0-9]{8}', query):
                for each in query.split():
                    if re.findall(r'mgmt_[a-f0-9]{8}', each): 
                        ppp = each.split('_')[1]
                        break
            else:
                print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! MGMT IP не найден или неверный username ppp secret.\n')
                return False
            print(f'PPP найден: {bc.GREEN}mgmt_{ppp}{bc.ENDC}')
            slct = input(f'Начинаем удаление? (y/n):')
            if slct != 'y':
                return False
            else:
                print(f'Удаляю на CTS({cts})...')
                conf = f'interface bridge vlan remove [find comment="{ppp}"]\n/interface bridge port remove [find interface~"{ppp}"]\n/interface eoip remove [find name~"{ppp}"]\n/ppp secret remove [find name~"{ppp}"]'
                result1 = ssh.exec(conf, s1)
                log.write(result1, 2)
                print(f'{bc.BOLD}{"="*5} Готово! {"="*5}{bc.ENDC}')
                pgsql.write(f"DELETE FROM cts_token WHERE token = '{ppp}'")
                ssh.close(s1)
                return True
        else:
            print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Проблема с SSH на CTS.({cts})\n')
            return False
    else:
        print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Некорректное значение MGMT IP.\n')
        return False

def l2vpn_guts(mode, bsr01, bsr02):
    s1 = ssh.init(bsr01, radctl.username, radctl.password, 1)
    s2 = ssh.init(bsr02, radctl.username, radctl.password, 1)
    if s1 != False and s2 != False:
        if mode == 0:
            ring = input('Номер пары MKU [100-499]:')
            sdp = f'5{ring}'
            vpls = input('Номер VPLS на BSR:')
            vlan = input('Клиентский VLAN:')
            rate = input('Скорость канала (Мб/с):')
            print(f'{bc.CYAN}{"="*32} Checking... {"="*32}{bc.ENDC}')
            if pgsql.read(f"SELECT id FROM l2vpn_token WHERE pw = '{sdp}' and vpls = '{vpls}'"):
                print(f'{bc.RED}[!]{bc.ENDC} Такое L2VPN включение уже настроенно!')
                return False
            mku = pgsql.read(f"select active_mku, backup_mku from mku_ring where mku_ring = {ring}")
            if mku:
                a_mku, b_mku = mku
                a_mku_ip = pgsql.read(f"select ip_vprn100 from bsa where bsa = '{a_mku}'")[0]
                b_mku_ip = pgsql.read(f"select ip_vprn100 from bsa where bsa = '{b_mku}'")[0]
                a_mku_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{a_mku}'")[0]
                b_mku_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{b_mku}'")[0]
            cmd_mtu = (f'show service id {vpls} sdp detail | match SdpOperMTU')
            for a in ssh.invoke(cmd_mtu, s1).split('\n'):
                if not re.findall('MinReqd', a):
                    mtu = False
                else:
                    mtu = a.split()[3]
                    break
            if not mtu:
                return False
            else:
                print(f'SDP: {sdp}')
                print(f'Номер VPLS: {vpls}')
                print(f'Клиентский VLAN: {vlan}')
                print(f'Скорость канала: {rate} Mb/s')
                print(f'MTU в VPLS на BSR: {mtu} byte')
                if a_mku_ipb == b_mku_ipb:
                    print(f'{bc.GREEN}|MKU-{a_mku}|{bc.ENDC}')
                    print(f'IP адрес Base MKU: {a_mku_ipb}')
                    print(f'IP адрес VPRN140 MKU: {a_mku_ip}')
                else:
                    print(f'Основная{bc.GREEN}|MKU-{a_mku}|{bc.ENDC} <===> {bc.GREEN}|MKU-{b_mku}|{bc.ENDC}Резервная')
                    print(f'IP адрес Base основной MKU: {a_mku_ipb}')
                    print(f'IP адрес Base резервной MKU: {b_mku_ipb}')
                    print(f'IP адрес VPRN100 основной MKU: {a_mku_ip}')
                    print(f'IP адрес VPRN100 резервной MKU: {b_mku_ip}')
                
                slct = input('Начинаем конфигурацию? (y/n):')
                if slct != 'y':
                    print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted!')
                    ssh.close(s1)
                    ssh.close(s2)
                    return False
                #Backup MKU exists
                if a_mku_ipb != b_mku_ipb:
                    # Configure active side
                    # Connect to bsr01
                    print(f'Настраиваю на BSR01...')
                    cmd1 = (f'configure service vpls {vpls}\nendpoint "MKU{a_mku}-MKU{b_mku}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.2\nexit\nexit\nspoke-sdp {sdp}:{vpls} endpoint "MKU{a_mku}-MKU{b_mku}" create\nno shutdown\nexit\n')
                    result1 = ssh.invoke(cmd1, s1)
                    log.write(result1, 2)
                    print(f'Готово')
                    # Connect to active MKU
                    print(f'Настраиваю на основной MKU{a_mku}...')
                    cmd2 = (f'system-view\nvsi {vpls}\ndescription L2VPN_MKU{a_mku}-MKU{b_mku}\npwsignal ldp\nvsi-id {vpls}\npeer 10.6.200.1 upe\npeer {b_mku_ipb} upe\nquit\nmtu {mtu}\nencapsulation ethernet\nignore-ac-state\nquit\n')+'\n'
                    result2 = telnet.huawei(cmd2, a_mku_ip, radctl.username, radctl.password)
                    log.write(result2, 2)
                    print(f'Готово')
                    # Configure backup side
                    # Connect to bsr02
                    print(f'Настраиваю на BSR02...')
                    cmd1 = (f'configure service vpls {vpls}\nendpoint "MKU{a_mku}-MKU{b_mku}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.1\nexit\nexit\nspoke-sdp {sdp}:{vpls} endpoint "MKU{a_mku}-MKU{b_mku}" create\nno shutdown\nexit\n')
                    result1 = ssh.invoke(cmd1, s2)
                    log.write(result1, 2)
                    print(f'Готово')
                    # Connect to backup MKU
                    print(f'Настраиваю на резервной MKU{b_mku}...')
                    cmd2 = (f'system-view\nvsi {vpls}\ndescription L2VPN_MKU{a_mku}-MKU{b_mku}\npwsignal ldp\nvsi-id {vpls}\npeer 10.6.200.2 upe\npeer {a_mku_ipb} upe\nquit\nmtu {mtu}\nencapsulation ethernet\nignore-ac-state\nquit\n')+'\n'
                    result2 = telnet.huawei(cmd2, b_mku_ip, radctl.username, radctl.password)
                    log.write(result2, 2)
                    print(f'Готово')
                #No Backup MKU
                else:
                    # Connect to bsr01
                    print(f'Настраиваю на BSR01...')
                    cmd1 = (f'configure service vpls {vpls}\nendpoint "MKU{a_mku}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.2\nexit\nexit\nspoke-sdp {sdp}:{vpls} endpoint "MKU{a_mku}" create\nno shutdown\nexit\n')
                    result1 = ssh.invoke(cmd1, s1)
                    log.write(result1, 2)
                    print(f'Готово')
                    # Connect to MKU
                    print(f'Настраиваю MKU{a_mku}...')
                    cmd2 = (f'system-view\nvsi {vpls}\ndescription L2VPN_MKU{a_mku}\npwsignal ldp\nvsi-id {vpls}\npeer 10.6.200.1 upe\npeer 10.6.200.2 upe\nquit\nmtu {mtu}\nencapsulation ethernet\nignore-ac-state\nquit\n')+'\n'
                    result2 = telnet.huawei(cmd2, a_mku_ip, radctl.username, radctl.password)
                    log.write(result2, 2)
                    print(f'Готово')
                    # Configure backup side
                    # Connect to bsr02
                    print(f'Настраиваю на BSR02...')
                    cmd1 = (f'configure service vpls {vpls}\nendpoint "MKU{a_mku}" create\nno suppress-standby-signaling\nmc-endpoint {vpls}{vlan}\nmc-ep-peer 10.6.200.1\nexit\nexit\nspoke-sdp {sdp}:{vpls} endpoint "MKU{a_mku}" create\nno shutdown\nexit\n')
                    result02 = ssh.invoke(cmd1, s2)
                    log.write(result02, 2)
                    print(f'Готово')
                pgsql.write(f"insert into l2vpn_token values ('{sdp}', '{vpls}', '{vlan}', '{rate}')")
                conf_id = pgsql.read(f"SELECT id FROM l2vpn_token ORDER BY date DESC LIMIT 1")[0]
                print(f'{bc.CYAN}{"="*34} ALL DONE {"="*33}\n{"="*19} Configuration session ID: {conf_id} {"="*19}{bc.ENDC}')
                ssh.close(s1)
                ssh.close(s2)
                return True
        elif mode == 1:
            conf_id = input('Введите ID включения: ')
            print(f'{bc.CYAN}{"="*32} Checking... {"="*32}{bc.ENDC}')
            sdp = int(pgsql.read(f"SELECT pw FROM l2vpn_token WHERE id = '{conf_id}'")[0])
            ring = sdp-5000
            if not re.findall(r'\b\d{4}\b', str(sdp)):
                print(f'{bc.RED}[!]{bc.ENDC} Неверный ID включения L2VPN ГУТС!')
                ssh.close(s1)
                ssh.close(s2)
                return False
            vpls = pgsql.read(f"SELECT vpls FROM l2vpn_token WHERE id = '{conf_id}'")[0]
            vlan = pgsql.read(f"SELECT vlan FROM l2vpn_token WHERE id = '{conf_id}'")[0]
            rate = pgsql.read(f"SELECT rate FROM l2vpn_token WHERE id = '{conf_id}'")[0]
            mku = pgsql.read(f"select active_mku, backup_mku from mku_ring where mku_ring = {ring}")
            if mku:
                a_mku, b_mku = mku
                a_mku_ip = pgsql.read(f"select ip_vprn100 from bsa where bsa = '{a_mku}'")[0]
                b_mku_ip = pgsql.read(f"select ip_vprn100 from bsa where bsa = '{b_mku}'")[0]
                a_mku_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{a_mku}'")[0]
                b_mku_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{b_mku}'")[0]
            print(f'SDP: {sdp}')
            print(f'Номер VPLS: {vpls}')
            print(f'Клиентский VLAN: {vlan}')
            print(f'Скорость канала: {rate} Mb/s')
            if a_mku_ipb == b_mku_ipb:
                print(f'{bc.GREEN}|MKU-{a_mku}|{bc.ENDC}')
                print(f'IP адрес Base MKU: {a_mku_ipb}')
                print(f'IP адрес VPRN100 MKU: {a_mku_ip}')
            else:
                print(f'Основная{bc.GREEN}|MKU-{a_mku}|{bc.ENDC} <===> {bc.GREEN}|MKU-{b_mku}|{bc.ENDC}Резервная')
                print(f'IP адрес Base основной MKU: {a_mku_ipb}')
                print(f'IP адрес Base резервной MKU: {b_mku_ipb}')
                print(f'IP адрес VPRN100 основной MKU: {a_mku_ip}')
                print(f'IP адрес VPRN100 резервной MKU: {b_mku_ip}')
            
            slct = input('Начинаем удаление? (y/n):')
            if slct != 'y':
                print(f'{bc.RED}[!]{bc.ENDC} Remove aborted!')
                ssh.close(s1)
                ssh.close(s2)
                return False
            #Backup MKU exists
            if a_mku_ipb != b_mku_ipb:
                #Connect to bsr01/bsr02
                print(f'Удаляю на BSR01 и BSR02...')
                cmd1 = (f'configure service vpls {vpls}\nspoke-sdp {sdp}:{vpls} shutdown\nno spoke-sdp {sdp}:{vpls}\nendpoint "MKU{a_mku}-MKU{b_mku}" mc-endpoint {vpls}{vlan} no mc-ep-peer\nendpoint "MKU{a_mku}-MKU{b_mku}" no mc-endpoint\nno endpoint "MKU{a_mku}-MKU{b_mku}"\nexit\n')
                result01 = ssh.invoke(cmd1, s1)
                log.write(result01, 2)
                result02 = ssh.invoke(cmd1, s2)
                log.write(result02, 2)
                print(f'Готово')
                # Configure active side
                # Connect to active MKU
                print(f'Удаляю на основной MKU{a_mku}...')
                cmd2 = (f'system-view\nundo vsi {vpls}\nY\nquit\n')+'\n'
                result1 = telnet.huawei(cmd2, a_mku_ip, radctl.username, radctl.password)
                log.write(result1, 2)
                print(f'Готово')
                # Configure backup side
                # Connect to backup MKU
                print(f'Удаляю на резервной MKU{b_mku}...')
                result11 = telnet.huawei(cmd2, b_mku_ip, radctl.username, radctl.password)
                log.write(result11, 2)
                print(f'Готово')
            #No Backup MKU
            else:
                #Connect to bsr01/bsr02
                print(f'Удаляю на BSR01 и BSR02...')
                cmd1 = (f'configure service vpls {vpls}\nspoke-sdp {sdp}:{vpls} shutdown\nno spoke-sdp {sdp}:{vpls}\nendpoint "MKU{a_mku}" mc-endpoint {vpls}{vlan} no mc-ep-peer\nendpoint "MKU{a_mku}" no mc-endpoint\nno endpoint "MKU{a_mku}"\nexit\n')
                result01 = ssh.invoke(cmd1, s1)
                log.write(result01, 2)
                result02 = ssh.invoke(cmd1, s2)
                log.write(result02, 2)
                print(f'Готово')
                # Connect to MKU
                print(f'Удаляю на MKU{a_mku}...')
                cmd2 = (f'system-view\nundo vsi {vpls}\nY\nquit\n')+'\n'
                result1 = telnet.huawei(cmd2, a_mku_ip, radctl.username, radctl.password)
                log.write(result1, 2)
                print(f'Готово')
            pgsql.write(f"DELETE FROM l2vpn_token WHERE id = '{conf_id}'")
            print(f'{bc.CYAN}{"="*34} ALL DONE {"="*33}{bc.ENDC}')
            ssh.close(s1)
            ssh.close(s2)
            return True
    else:
        print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Проблема с SSH на BSR.\n')
        return False

def sap_vp(mode, bsr01, bsr02):
    s1 = ssh.init(bsr01, radctl.username, radctl.password, 1)
    s2 = ssh.init(bsr02, radctl.username, radctl.password, 1)
    if s1 != False and s2 != False:
        if mode == 0:
            sap = input('Введите SAP [lag-x:y.z | pw-x:y]: ')
            ip = input('Введите IP адрес для BSR [х.х.х.х/у]: ')
            sp = input('Введите скорость в Мбит/c: ')
            vprn = input('Введите номер VPRN: ')
            rate = str(int(sp)*1024)
            cmbs = str(int(rate)//8)
            vprn_u = []
            for a in ssh.invoke('show service service-using vprn', s1).split():
                if re.findall(r'\b\d{5}\b', a):
                    vprn_u.append(a)
            if re.findall('Number of SAP', ssh.invoke(f'show service sap-using sap {sap}', s1)):
                print(f'\n{bc.RED}[!]{bc.ENDC} SAP уже используется на BSR!\n')
                ssh.close(s1)
                ssh.close(s2)
                return False
            if vprn not in vprn_u:
                print(f'\n{bc.RED}[!]{bc.ENDC} VPRN не найден на BSR!\n')
                ssh.close(s1)
                ssh.close(s2)
                return False
            if re.findall('lag-', sap):
                ifc = f'VPRN{vprn}_LAG-{(sap.split(":")[0]).split("-")[1]}_{(sap.split(":")[1]).split(".")[0]}-{(sap.split(":")[1]).split(".")[1]}'
            elif re.findall('pw-', sap):
                ifc = f'VPRN{vprn}_PW-{(sap.split(":")[0]).split("-")[1]}_{(sap.split(":")[1])}'
            g = sap.split(':')[0]
            if re.findall('lag', g.split('-')[0]):
                e = g.split('-')[1]
                opg = f'STP-LAG{e}'
            elif re.findall('pw', g.split('-')[0]):
                e = g.split('-')[1]
                if re.findall('1001', e) or re.findall('1002', e):
                    opg = f'SDP-PSW01'
                if re.findall(r'\b\d{5}\b', e):
                    (e)[:3]
                    opg = f'SDP-5{(e)[:3]}'
                else:
                    opg = f'SDP-3{e}'
            if re.findall('Could not find oper-group', ssh.invoke(f'show service oper-group "{opg}"', s1)):
                print(f'\n{bc.RED}[!]{bc.ENDC} Опер-группа не найденa на BSR!\n')
                ssh.close(s1)
                ssh.close(s2)
                return False
            if re.findall('Local   Local', ssh.invoke(f'show router {vprn} route-table {ip} longer', s1)):
                print(f'\n{bc.RED}[!]{bc.ENDC} IP адрес {ip} уже используется в VPRN {vprn}!\n')
                ssh.close(s1)
                ssh.close(s2)
                return False
            print(f'\nVPRN: {bc.GREEN}{vprn}{bc.ENDC}\nИнтерфейс: {bc.GREEN}{ifc}{bc.ENDC}\nIP адрес на BSR: {bc.GREEN}{ip}{bc.ENDC}\nSAP: {bc.GREEN}{sap}{bc.ENDC}\nОпер-группа: {bc.GREEN}{opg}{bc.ENDC}\nСкорость: {bc.GREEN}{sp} Мбит/c{bc.ENDC}')
            slct = input(f'\n{bc.BOLD}Начинаем конфигурацию? (y/n):{bc.ENDC}')
            if slct != 'y':
                print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted!')
                ssh.close(s1)
                ssh.close(s2)
                return False
            else:
                cmd = f'configure service vprn {vprn} interface {ifc} create\ndescription "ADDED_BY_SCRIPT"\nmonitor-oper-group "{opg}"\naddress {ip}\nmac 00:00:5e:00:02:ff\nip-mtu 1500\nsap {sap} create\ningress\nqos 55\nqueue-override\nqueue 1 create\ncbs {cmbs}\nmbs {cmbs} kilobytes\nrate {rate} cir {rate}\nexit\nexit\nexit\negress\nqos 55\nqueue-override\nqueue 1 create\ncbs {cmbs}\nmbs {cmbs} kilobytes\nrate {rate} cir {rate}\nexit\nexit\nexit\nexit\nexit all\n'
                print(f'Настраиваю на BSR01...')
                result1 = ssh.invoke(cmd, s1)
                print(f'Настраиваю на BSR02...')
                result2 = ssh.invoke(cmd, s2)
                print(f'{bc.GREEN}[+]{bc.ENDC} === Готово! ===')
                ssh.close(s1)
                ssh.close(s2)
                log.write(f'{result1}\n{result2}', 2)
                return True
        elif mode == 1:
            sap = input('Введите SAP [lag-x:y.z]: ')
            sp = input('Введите скорость в Мбит/c: ')
            vpls = input('Введите номер VPLS: ')
            rate = str(int(sp)*1024)
            vpls_u = []
            for a in ssh.invoke('show service fdb-info | match "Service Id"', s1).split():
                if re.findall(r'\b\d{5}\b', a):
                    vpls_u.append(a)
            if not re.findall('No Matching Entries', ssh.invoke(f'show service sap-using sap {sap}', s1)):
                print(f'\n{bc.RED}[!]{bc.ENDC} SAP уже используется на BSR!\n')
                ssh.close(s1)
                ssh.close(s2)
                return False
            if vpls not in vpls_u:
                print(f'\n{bc.RED}[!]{bc.ENDC} VPLS не найден на BSR!\n')
                ssh.close(s1)
                ssh.close(s2)
                return False
            print(f'\nVPLS: {bc.GREEN}{vpls}{bc.ENDC}\nSAP: {bc.GREEN}{sap}{bc.ENDC}\nСкорость: {bc.GREEN}{sp} Мбит/c{bc.ENDC}')
            slct = input(f'\n{bc.BOLD}Начинаем конфигурацию? (y/n):{bc.ENDC}')
            if slct != 'y':
                print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted!')
                ssh.close(s1)
                ssh.close(s2)
                return False
            else:
                cmd = f'configure service vpls {vpls}\nsap {sap} create\ndescription "ADDED_BY_SCRIPT"\ningress\nqos 55 multipoint-shared\nqueue-override\nqueue 1 create\nrate {rate} cir {rate}\nexit\nexit\nexit\negress\nqos 55\nqueue-override\nqueue 1 create\nrate {rate} cir {rate}\nexit\nexit\nexit\nno shutdown\nexit\nexit all\n'
                print(f'Настраиваю на BSR01...')
                result1 = ssh.invoke(cmd, s1)
                print(f'Настраиваю на BSR02...')
                result2 = ssh.invoke(cmd, s2)
                print(f'{bc.GREEN}[+]{bc.ENDC} === Готово! ===')
                ssh.close(s1)
                ssh.close(s2)
                log.write(f'{result1}\n{result2}', 2)
                return True
        elif mode == 2:
            ifc = input('Введите интерфейс: ')
            vprn = input('Введите номер VPRN: ')
            if not re.findall('Interfaces :', ssh.invoke(f'show service id {vprn} interface "{ifc}" ', s1)):
                print(f'\n{bc.RED}[!]{bc.ENDC} SAP или VPRN не найден на BSR!\n')
                ssh.close(s1)
                ssh.close(s2)
                return False
            for a in ssh.invoke(f'show service id {vprn} interface "{ifc}" detail', s1).split('\n'):
                if re.findall('SAP Id', a):
                    sap = a.split()[3]
            print(f'\nVPRN: {bc.GREEN}{vprn}{bc.ENDC}\nИнтерфейс: {bc.GREEN}{ifc}{bc.ENDC}\nSAP: {bc.GREEN}{sap}{bc.ENDC}')
            slct = input(f'\n{bc.BOLD}Начинаем удаление? (y/n):{bc.ENDC}')
            if slct != 'y':
                print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted!')
                ssh.close(s1)
                ssh.close(s2)
                return False
            else:
                cmd = f'configure service vprn {vprn}\ninterface "{ifc}"\nsap {sap} shutdown\nno sap {sap}\nshutdown\nexit\nno interface "{ifc}"\nexit all\n'
                print(f'Удаляю на BSR01...')
                result1 = ssh.invoke(cmd, s1)
                print(f'Удаляю на BSR02...')
                result2 = ssh.invoke(cmd, s2)
                print(f'{bc.GREEN}[+]{bc.ENDC} === Готово! ===')
                ssh.close(s1)
                ssh.close(s2)
                log.write(f'{result1}\n{result2}', 2)
                return True
        elif mode == 3:
            sap = input('Введите SAP [lag-x:y.z]: ')
            vpls = input('Введите номер VPLS: ')
            if not re.findall('Service Access Points', ssh.invoke(f'show service id {vpls} sap {sap}', s1)):
                print(f'\n{bc.RED}[!]{bc.ENDC} SAP или VPLS не найден на BSR!\n')
                ssh.close(s1)
                ssh.close(s2)
                return False
            print(f'\nVPLS: {bc.GREEN}{vpls}{bc.ENDC}\nSAP: {bc.GREEN}{sap}{bc.ENDC}')
            slct = input(f'\n{bc.BOLD}Начинаем удаление? (y/n):{bc.ENDC}')
            if slct != 'y':
                print(f'{bc.RED}[!]{bc.ENDC} Configuration aborted!')
                ssh.close(s1)
                ssh.close(s2)
                return False
            else:
                cmd = f'configure service vpls {vpls}\nsap {sap} shutdown\nno sap {sap}\n'
                print(f'Удаляю на BSR01...')
                result1 = ssh.invoke(cmd, s1)
                print(f'Удаляю на BSR02...')
                result2 = ssh.invoke(cmd, s2)
                print(f'{bc.GREEN}[+]{bc.ENDC} === Готово! ===')
                ssh.close(s1)
                ssh.close(s2)
                log.write(f'{result1}\n{result2}', 2)
                return True
    else:
        print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Проблема с SSH на BSR.\n')
        return False

def launcher_2():
    main_menu_title = "\n------------------------------------\nv3.5|06.12.2021|Service configurator\n------------------------------------\n  Главное меню | Что будем делать?\n------------------------------------"
    main_menu_items = ['Конфигурация BSR (vpls, vprn, sap)', 'Конфигурация L2VPN (PW-полукольца)', 'Конфигурация CTS', 'Посмотреть лог за сегодня', 'Выход']
    main_menu_cursor = "> "
    main_menu_cursor_style = ("fg_cyan", "bold")
    main_menu_style = ("bold", "fg_green")
    main_menu_exit = False
    main_menu = TerminalMenu(menu_entries=main_menu_items, title=main_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)

    bsr_menu_title = "\n> Конфигурация BSR\n------------------------------------"
    bsr_menu_items = ['Создание базового VPLS на BSR', 'Создание АРМ МГ VPLS на BSR', 'Добавление/удаление SAP в VPLS или VPRN', 'Назад в главное меню']
    bsr_menu_back = False
    bsr_menu = TerminalMenu(bsr_menu_items, title=bsr_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)

    l2vpn_menu_title = "\n> Конфигурация L2VPN\n------------------------------------"
    l2vpn_menu_items = ['Настройка нового L2VPN (Радио)', 'Настройка нового L2VPN (ГУТС)','Удаление существуещего L2VPN (Радио)', 'Удаление существуещего L2VPN (ГУТС)', 'Назад в главное меню']
    l2vpn_menu_back = False
    l2vpn_menu = TerminalMenu(l2vpn_menu_items, title=l2vpn_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)

    cts_menu_title = "\n> Конфигурация CTS\n------------------------------------"
    cts_menu_items = ['Создание нового включения на CTS', 'Удаление существующего включения на CTS', 'Назад в главное меню']
    cts_menu_back = False
    cts_menu = TerminalMenu(cts_menu_items, title=cts_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)

    cts_s_menu_title = "\n> Конфигурация CTS\n------------------------------------"
    cts_s_menu_items = ['CTS01 - 10.200.88.10', 'CTS02 - 10.200.122.1', 'CTS03 - 10.200.88.11', 'Назад в предыдущее меню']
    cts_s_menu_back = False
    cts_s_menu = TerminalMenu(cts_s_menu_items, title=cts_s_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)

    bsr_sap_menu_title = "\n> Конфигурация BSR\n------------------------------------"
    bsr_sap_menu_items = ['Создать интерфейс и SAP в VPRN', 'Добавить SAP в VPLS', 'Удаление существуещего интерфейса в VPRN', 'Удаление существуещего SAP в VPLS', 'Назад в предыдущее меню']
    bsr_sap_menu_back = False
    bsr_sap_menu = TerminalMenu(bsr_sap_menu_items, title=bsr_sap_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)

    while not main_menu_exit:
        main_sel = main_menu.show()
        if main_sel == 0:
            while not bsr_menu_back:
                bsr_slct = bsr_menu.show()
                if bsr_slct == 0:
                    vpls_create(1, mgmt.bsr01, mgmt.bsr02)
                    time.sleep(2)
                elif bsr_slct == 1:
                    vpls_create(2, mgmt.bsr01, mgmt.bsr02)
                    time.sleep(2)
                elif bsr_slct == 2:
                    while not bsr_sap_menu_back:
                        bsr_sap_slct = bsr_sap_menu.show()
                        if bsr_sap_slct == 0:
                            sap_vp(bsr_sap_slct, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(2)
                        if bsr_sap_slct == 1:
                            sap_vp(bsr_sap_slct, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(2)
                        if bsr_sap_slct == 2:
                            sap_vp(bsr_sap_slct, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(2)
                        if bsr_sap_slct == 3:
                            sap_vp(bsr_sap_slct, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(2)
                        elif bsr_sap_slct == 4:
                            bsr_sap_menu_back = True
                elif bsr_slct == 3:
                    bsr_menu_back = True
            bsr_menu_back = False
        elif main_sel == 1:
            while not l2vpn_menu_back:
                l2vpn_slct = l2vpn_menu.show()
                if l2vpn_slct == 0:
                    l2vpn_config()
                    time.sleep(2)
                elif l2vpn_slct == 1:
                    l2vpn_guts(0, mgmt.bsr01, mgmt.bsr02)
                    time.sleep(2)
                elif l2vpn_slct == 2:
                    l2vpn_remove()
                    time.sleep(2)
                elif l2vpn_slct == 3:
                    l2vpn_guts(1, mgmt.bsr01, mgmt.bsr02)
                    time.sleep(2)
                elif l2vpn_slct == 4:
                    l2vpn_menu_back = True
            l2vpn_menu_back = False
        elif main_sel == 2:
            while not cts_menu_back:
                cts_slct = cts_menu.show()
                if cts_slct == 0:
                    while not cts_s_menu_back:
                        cts_s_slct = cts_s_menu.show()
                        if cts_s_slct == 0:
                            cts_config(mgmt.cts01, cts_var.subn_pool_cts01, cts_var.eoip_pool_cts01, cts_var.l2tp_lo_cts01)
                            time.sleep(2)
                        if cts_s_slct == 1:
                            cts_config(mgmt.cts02, cts_var.subn_pool_cts02, cts_var.eoip_pool_cts02, cts_var.l2tp_lo_cts02)
                            time.sleep(2)
                        if cts_s_slct == 2:
                            cts_config(mgmt.cts03, cts_var.subn_pool_cts03, cts_var.eoip_pool_cts03, cts_var.l2tp_lo_cts03)
                            time.sleep(2)
                        elif cts_s_slct == 3:
                            cts_s_menu_back = True
                    cts_s_menu_back = False
                elif cts_slct == 1:
                    while not cts_s_menu_back:
                        cts_s_slct = cts_s_menu.show()
                        if cts_s_slct == 0:
                            cts_remove(mgmt.cts01)
                            time.sleep(2)
                        if cts_s_slct == 1:
                            cts_remove(mgmt.cts02)
                            time.sleep(2)
                        if cts_s_slct == 2:
                            cts_remove(mgmt.cts03)
                            time.sleep(2)
                        elif cts_s_slct == 3:
                            cts_s_menu_back = True
                    cts_s_menu_back = False
                elif cts_slct == 2:
                    cts_menu_back = True
            cts_menu_back = False
        elif main_sel == 3:
            log.read(2)
            time.sleep(2)
        elif main_sel == 4:
            main_menu_exit = True
            print("=== Выход ===")

launcher_2()