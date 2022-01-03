#!/bin/python3

from main.ssh import ssh
from main.sql import pgsql
from main.telnet import telnet
from main.log import log
from main.config import radctl, mgmt, bc
from main.templates import rsdp_pw_tmp, sdp_tmp, pw_tmp, operg_tmp, gi_tmp, vpls_tmp, sap_tmp
from ipaddress import IPv4Network
from simple_term_menu import TerminalMenu
import re, time, random

def db_query(mode):
    if mode == 0:
        mku = input('Введите номер MKU: ')
        ip_base = input('Введите IP Base: ')
        ip_100 = input('Введите IP VPRN 100: ')
        ip_140 = input('Введите IP VPRN 140 (если отсутвует введите --): ')
        ip_r1 = input('Введите IP r1.BS/TP-Link (если отсутвует введите --): ')
        loc = input('Введите адрес из КРУС/EQM: ')
        mku_chck = pgsql.read(f"SELECT EXISTS (SELECT * FROM bsa where bsa = '{mku}')")[0]
        if mku_chck == True:
            print(f'{bc.RED}MKU-{mku} уже существует!{bc.ENDC}')
        elif mku_chck == False:
            slct = input(f'Новая MKU: {bc.CYAN}MKU-{mku}{bc.ENDC}\nIP Base: {bc.GREEN}{ip_base}{bc.ENDC}\nIP VPRN 100: {bc.GREEN}{ip_100}{bc.ENDC}\nIP VPRN 140: {bc.GREEN}{ip_140}{bc.ENDC}\nIP r1.BS/TP-Link: {bc.GREEN}{ip_r1}{bc.ENDC}\nАдрес: {bc.GREEN}{loc}{bc.ENDC}{bc.BOLD}\n\nДобавляем?(y/n){bc.ENDC}')
            if slct == 'y':
                cmd = f"insert into bsa values ('{mku}', '{ip_base}', '{ip_100}', '{ip_140}', '{ip_r1}', '{loc}')"
                pgsql.write(cmd)
                print(f'{bc.GREEN}[!]{bc.ENDC}==Данные записаны в БД!==')
                log.write(f'==Данные записаны в БД!==\n{cmd}', 1)
                return True
            else:
                return False

    elif mode == 1:
        mku = input('Введите номер MKU: ')
        mku_chck = (pgsql.read(f"SELECT EXISTS (SELECT * FROM bsa where bsa = '{mku}')"))[0]
        if mku_chck == False:
            print(f'{bc.RED}MKU-{mku} не существует!{bc.ENDC}')
        else:
            ip_base,ip_100,ip_140,ip_r1,loc = pgsql.read(f"select ip_base, ip_vprn100, ip_vprn140, arp_r1_bs, location from bsa where bsa = '{mku}'")
            slct = input(f'MKU: {bc.CYAN}MKU-{mku}{bc.ENDC}\nIP Base: {bc.GREEN}{ip_base}{bc.ENDC}\nIP VPRN 100: {bc.GREEN}{ip_100}{bc.ENDC}\nIP VPRN 140: {bc.GREEN}{ip_140}{bc.ENDC}\nIP r1.BS: {bc.GREEN}{ip_r1}{bc.ENDC}\nАдрес: {bc.GREEN}{loc}{bc.ENDC}{bc.BOLD}\n\nУдаляем?(y/n){bc.ENDC}')
            if slct == 'y':
                cmd = f"delete from bsa where bsa = '{mku}'"
                pgsql.write(cmd)
                print(f'{bc.RED}[!]{bc.ENDC} == Данные удалены из БД ==')
                log.write(f'==Данные удалены из БД!==\n{cmd}', 1)
                return True
            else:
                return False

    elif mode == 2:
        ring = input('Введите номер пары MKU: ')
        ring_chck = (pgsql.read(f"SELECT EXISTS (SELECT * FROM mku_ring where mku_ring = {ring})"))[0]
        if ring_chck == False:
            print(f'{bc.RED}Пара SDP-5{ring} не существует!{bc.ENDC}')
        else:
            a_bsa,b_bsa = pgsql.read(f"select active_mku, backup_mku from mku_ring where mku_ring = {ring}")
            slct = input(f'Пара {bc.CYAN}SDP-5{ring}{bc.ENDC}\nАктивная {bc.GREEN}MKU-{a_bsa}{bc.ENDC}\nРезервная {bc.GREEN}MKU-{b_bsa}{bc.ENDC}\n\n{bc.BOLD}Удаляем?(y/n){bc.ENDC}')
            if slct == 'y':
                cmd = f"delete from mku_ring where mku_ring = {ring}"
                pgsql.write(cmd)
                print(f'{bc.RED}[!]{bc.ENDC} == Данные удалены из БД ==')
                log.write(f'==Данные удалены из БД!==\n{cmd}', 1)
                return True
            else:
                return False

    elif mode == 3:
        ring = input('Введите номер полуколца(пары BSA/PW): ')
        ring_chck = (pgsql.read(f"SELECT EXISTS (SELECT * FROM rings where pw_ring = {ring})"))[0]
        if ring_chck == False:
            print(f'{bc.RED}Полуколцо PW-{ring} не существует!{bc.ENDC}')
        else:
            a_bsa,b_bsa = pgsql.read(f"select active_bsa, backup_bsa from rings where pw_ring = {ring}")
            slct = input(f'Полуколцо {bc.CYAN}PW-{ring}{bc.ENDC}\nАктивная {bc.GREEN}BSA-{a_bsa}{bc.ENDC}\nРезервная {bc.GREEN}BSA-{b_bsa}{bc.ENDC}\n\n{bc.BOLD}Удаляем?(y/n){bc.ENDC}')
            if slct == 'y':
                cmd = f"delete from rings where pw_ring = {ring}"
                pgsql.write(cmd)
                print(f'{bc.RED}[!]{bc.ENDC} == Данные удалены из БД ==')
                log.write(f'==Данные удалены из БД!==\n{cmd}', 1)
                return True
            else:
                return False

def rsdp_pw_create(bsr01, bsr02):
    s1 = ssh.init(bsr01, radctl.username, radctl.password, 1)
    s2 = ssh.init(bsr02, radctl.username, radctl.password, 1)
    if s1 != False and s2 != False:
        sdp_used = []
        sdp_all = range(3500, 3999)
        check = ssh.invoke('show service sdp | match TLDP | match expression "[3][5-9][0-9][0-9]"', s1).split('\n')
        for a in check:
            if re.findall('MPLS', a):
                b = int(a.split()[0])
                sdp_used.append(b)
        sdp = str(sorted(set(sdp_all)-set(sdp_used))[0])
        ring = sdp[1:]
        a_bsa = input('Введите номер активной BSA: ')
        b_bsa = input('Введите номер резервной BSA: ')
        bin_port1 = input('Введите номер LAG для SDP binding BSR01: ')
        bin_port2 = input('Введите номер LAG для SDP binding BSR02: ')
        ring_chck = (pgsql.read(f"SELECT EXISTS (SELECT * FROM rings where pw_ring = {ring})"))[0]
        a_bsa_chck = (pgsql.read(f"SELECT EXISTS (SELECT * FROM bsa WHERE bsa = '{a_bsa}')"))[0]
        b_bsa_chck = (pgsql.read(f"SELECT EXISTS (SELECT * FROM bsa WHERE bsa = '{b_bsa}')"))[0]
        if ring_chck == True:
            print(f'{bc.RED}Пара BSA {ring} уже существует!{bc.ENDC}')
            return False
        elif ring_chck == False:
            if a_bsa_chck == False:
                print(f'{bc.RED}Активная BSA-{a_bsa} не существует!{bc.ENDC}')
                return False
            elif a_bsa_chck == True:
                if a_bsa == b_bsa:
                    pg = f"insert into rings values ('{ring}', 'red', '{a_bsa}', 'HZ', 'red', '{b_bsa}', 'HZ', 'No Backup BSA')"
                elif b_bsa_chck == False:
                    print(f'{bc.RED}Резервная BSA-{b_bsa} не существует!{bc.ENDC}')
                    return False
                elif b_bsa_chck == True:
                    pg = f"insert into rings values ('{ring}', 'red', '{a_bsa}', 'HZ', 'red', '{b_bsa}', 'HZ', 'none')"
        a_bsa_ip = pgsql.read(f"select ip_vprn100 from bsa where bsa = '{a_bsa}'")[0]
        b_bsa_ip = pgsql.read(f"select ip_vprn100 from bsa where bsa = '{b_bsa}'")[0]
        a_bsa_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{a_bsa}'")[0]
        b_bsa_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{b_bsa}'")[0]
        print(f'\nНовая SDP: {bc.CYAN}SDP-3{ring}{bc.ENDC}\nНовый PW порт (полукольцо): {bc.GREEN}{ring}{bc.ENDC}\nBSR01 - Активная {bc.GREEN}BSA-{a_bsa}{bc.ENDC}|{a_bsa_ip}\nBSR02 - Резервная {bc.GREEN}BSA-{b_bsa}{bc.ENDC}|{b_bsa_ip}\nBinding port BSR01: LAG-{bin_port1}\nBinding port BSR02: LAG-{bin_port2}\n\n{bc.RED}!!! ТОЛЬКО ДЛЯ BSA HUAWEI !!!{bc.ENDC}')
        cmd = rsdp_pw_tmp(sdp, ring, a_bsa, b_bsa, a_bsa_ipb, b_bsa_ipb, bin_port1, bin_port2)
        slct = input(f'\n{bc.BOLD}Начинаем настройку? (y/n):{bc.ENDC}')
        if slct == 'y':
            pgsql.write(pg)
            print(f'{bc.GREEN}[!]{bc.ENDC} == Данные записаны в БД ==')
            result01 = ssh.invoke(cmd.sdp_bsr01, s1)
            result1 = ssh.invoke(cmd.pw_bsr01, s1)
            print(f'{bc.GREEN}[!]{bc.ENDC} == На BSR01 настроено ==')
            result02 = ssh.invoke(cmd.sdp_bsr02, s2)
            result2 = ssh.invoke(cmd.pw_bsr02, s2)
            print(f'{bc.GREEN}[!]{bc.ENDC} == На BSR02 настроено ==')
            log.write(f'==Данные записаны в БД!==\n{pg}\n{result01}\n{result1}\n{result02}\n{result2}', 1)
            if a_bsa == b_bsa:
                result_aa = telnet.huawei(cmd.bsa_aa, a_bsa_ip, radctl.username, radctl.password)
                print(f'{bc.GREEN}[!]{bc.ENDC} == На BSA-{a_bsa} настроено ==')
                log.write(result_aa, 1)
            else:
                result_a = telnet.huawei(cmd.bsa_a, a_bsa_ip, radctl.username, radctl.password)
                print(f'{bc.GREEN}[!]{bc.ENDC} == На BSA-{a_bsa} настроено ==')
                result_b = telnet.huawei(cmd.bsa_b, b_bsa_ip, radctl.username, radctl.password)
                print(f'{bc.GREEN}[!]{bc.ENDC} == На BSA-{b_bsa} настроено ==')
                log.write(f'{result_a}\n{result_b}', 1)
            ssh.close(s1)
            ssh.close(s2)
        elif slct != 'y':
            print(f'{bc.RED}[!]{bc.ENDC} == Выход ==')
            ssh.close(s1)
            ssh.close(s2)
            return False
    else:
        print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Невозможно подключится к BSR.\n')
        return False

def sdp_pw_create(mode, bsr01, bsr02):
    s1 = ssh.init(bsr01, radctl.username, radctl.password, 1)
    s2 = ssh.init(bsr02, radctl.username, radctl.password, 1)
    if s1 != False and s2 != False:
        if mode == 0:
            sdp_used = []
            sdp_all = range(5100, 5999)
            check = ssh.invoke('show service sdp | match TLDP | match expression "[5][1-9][0-9][0-9]"', s1).split('\n')
            for a in check:
                if re.findall('MPLS', a):
                    b = int(a.split()[0])
                    sdp_used.append(b)
            sdp = str(sorted(set(sdp_all)-set(sdp_used))[0])
            ring = sdp[1:]
            a_mku = input('Введите номер активной MKU: ')
            b_mku = input('Введите номер резервной MKU: ')
            bin_port1 = input('Введите номер LAG для SDP binding BSR01: ')
            bin_port2 = input('Введите номер LAG для SDP binding BSR02: ')
            ring_chck = (pgsql.read(f"SELECT EXISTS (SELECT * FROM mku_ring where mku_ring = {ring})"))[0]
            a_mku_chck = (pgsql.read(f"SELECT EXISTS (SELECT * FROM bsa WHERE bsa = '{a_mku}')"))[0]
            b_mku_chck = (pgsql.read(f"SELECT EXISTS (SELECT * FROM bsa WHERE bsa = '{b_mku}')"))[0]
            if ring_chck == True:
                print(f'{bc.RED}Пара MKU {ring} уже существует!{bc.ENDC}')
                return False
            elif ring_chck == False:
                if a_mku_chck == False:
                    print(f'{bc.RED}Активная MKU-{a_mku} не существует!{bc.ENDC}')
                    return False
                elif a_mku_chck == True:
                    if a_mku == b_mku:
                        pg = f"insert into mku_ring values ('{ring}', '{a_mku}', '{b_mku}', 'No Backup MKU')"
                    elif b_mku_chck == False:
                        print(f'{bc.RED}Резервная MKU-{b_mku} не существует!{bc.ENDC}')
                        return False
                    elif b_mku_chck == True:
                        pg = f"insert into mku_ring values ('{ring}', '{a_mku}', '{b_mku}', 'none')"
            a_mku_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{a_mku}'")[0]
            b_mku_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{b_mku}'")[0]
            print(f'\nНовая пара: {bc.CYAN}SDP-5{ring}{bc.ENDC}\nBSR01 - Активная {bc.GREEN}MKU-{a_mku}{bc.ENDC}|{a_mku_ipb}\nBSR02 - Резервная {bc.GREEN}MKU-{b_mku}{bc.ENDC}|{b_mku_ipb}\nBinding port BSR01: LAG-{bin_port1}\nBinding port BSR02: LAG-{bin_port2}')
            cmd = sdp_tmp(sdp, a_mku, b_mku, a_mku_ipb, b_mku_ipb, bin_port1, bin_port2)
            slct = input(f'\n{bc.BOLD}Начинаем настройку? (y/n):{bc.ENDC}')
            if slct == 'y':
                pgsql.write(pg)
                print(f'{bc.GREEN}[!]{bc.ENDC} == Данные записаны в БД ==')
                result1 = ssh.invoke(cmd.bsr01, s1)
                print(f'{bc.GREEN}[!]{bc.ENDC} == На BSR01 настроено ==')
                result2 = ssh.invoke(cmd.bsr02, s2)
                print(f'{bc.GREEN}[!]{bc.ENDC} == На BSR02 настроено ==')
                log.write(f'==Данные записаны в БД!==\n{pg}\n{result1}\n{result2}', 1)
                ssh.close(s1)
                ssh.close(s2)
            elif slct != 'y':
                print(f'{bc.RED}[!]{bc.ENDC} == Выход ==')
                ssh.close(s1)
                ssh.close(s2)
                return False
        elif mode == 1:
            ring = input('Введите номер пары MKU: ')
            sdp = f'5{ring}'
            pw_used = []
            pw_all = range(int(f'{ring}01'), int(f'{ring}99'))
            a_mku, b_mku = pgsql.read(f"select active_mku, backup_mku from mku_ring where mku_ring = {ring}")
            a_mku_ip = pgsql.read(f"select ip_vprn100 from bsa where bsa = '{a_mku}'")[0]
            b_mku_ip = pgsql.read(f"select ip_vprn100 from bsa where bsa = '{b_mku}'")[0]
            a_mku_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{a_mku}'")[0]
            b_mku_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{b_mku}'")[0]
            check = ssh.invoke(f'show service sdp {sdp} pw-port', s1).split('\n')
            for a in check:
                if re.findall('dot1q', a):
                    b = int(a.split()[0])
                    pw_used.append(b)
            pw = str(sorted(set(pw_all)-set(pw_used))[0])
            cmd = pw_tmp(sdp, pw, a_mku, b_mku, a_mku_ipb, b_mku_ipb)
            print(f'\nПара MKU: {bc.CYAN}SDP-5{ring}{bc.ENDC}\nBSR01 - Активная {bc.GREEN}MKU-{a_mku}{bc.ENDC}|{a_mku_ip}|{a_mku_ipb}\nBSR02 - Резервная {bc.GREEN}MKU-{b_mku}{bc.ENDC}|{b_mku_ip}|{b_mku_ipb}\nPW порт: {bc.GREEN}{pw}{bc.ENDC}')
            slct = input(f'\n{bc.BOLD}Начинаем настройку? (y/n):{bc.ENDC}')
            if slct == 'y':
                result1 = ssh.invoke(cmd.bsr01, s1)
                print(f'{bc.GREEN}[!]{bc.ENDC} == На BSR01 настроено ==')
                result2 = ssh.invoke(cmd.bsr02, s2)
                print(f'{bc.GREEN}[!]{bc.ENDC} == На BSR02 настроено ==')
                log.write(f'{result1}\n{result2}', 1)
                if a_mku == b_mku:
                    result_aa = telnet.huawei(cmd.mku_aa, a_mku_ip, radctl.username, radctl.password)
                    print(f'{bc.GREEN}[!]{bc.ENDC} == На MKU-{a_mku} настроено ==')
                    log.write(result_aa, 1)
                else:
                    result_a = telnet.huawei(cmd.mku_a, a_mku_ip, radctl.username, radctl.password)
                    print(f'{bc.GREEN}[!]{bc.ENDC} == На MKU-{a_mku} настроено ==')
                    result_b = telnet.huawei(cmd.mku_b, b_mku_ip, radctl.username, radctl.password)
                    print(f'{bc.GREEN}[!]{bc.ENDC} == На MKU-{b_mku} настроено ==')
                    log.write(f'{result_a}\n{result_b}', 1)
                ssh.close(s1)
                ssh.close(s2)
            elif slct != 'y':
                print(f'{bc.RED}[!]{bc.ENDC} == Выход ==')
                ssh.close(s1)
                ssh.close(s2)
                return False
        ssh.close(s1)
        ssh.close(s2)
    else:
        print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Невозможно подключится к BSR.\n')
        return False

def oper_create(bsr01, bsr02):
    s1 = ssh.init(bsr01, radctl.username, radctl.password, 1)
    s2 = ssh.init(bsr02, radctl.username, radctl.password, 1)
    if s1 != False and s2 != False:
        a_snet = []
        u_snet1 = []
        u_sdp1 = []
        u_snet2 = []
        u_sdp2 = []
        sdp = input('Введите номер SDP: ')
        ring = sdp[1:]
        if re.findall(r'\b[5]\d{3}\b', sdp):
            mku = pgsql.read(f"select active_mku, backup_mku from mku_ring where mku_ring = {ring}")
        elif re.findall(r'\b[3]\d{3}\b', sdp):
            mku = pgsql.read(f"select active_bsa, backup_bsa from rings where pw_ring = {ring}")
        else:
            print(f'{bc.RED}[!]{bc.ENDC} Неверный номер SDP: {sdp}')
            ssh.close(s1)
            ssh.close(s2)
            return False
        check = (f'show router 3 route-table')
        for a in ssh.invoke(check, s1).split('\n'):
            if re.findall(f'10.0', a):
                u_snet1.append(a.split()[0])
            if re.findall(f'SDP-', a):
                u_sdp1.append(a.split()[0])
        for b in ssh.invoke(check, s2).split('\n'):
            if re.findall(f'10.0', b):
                u_snet2.append(b.split()[0])
            if re.findall(f'SDP-', b):
                u_sdp2.append(b.split()[0])
        for c in (list(IPv4Network('10.0.0.0/19').subnets(new_prefix=29))):
            a_snet.append(str(c))
        snet1 = sorted(set(a_snet)-set(u_snet1))
        snet2 = sorted(set(a_snet)-set(u_snet2))
        snet = str(sorted(set(snet1)&set(snet2))[0])
        ip_pool = []
        for ip in (list(IPv4Network(snet).hosts())):
                    ip_pool.append(str(ip))
        if mku:
            a_mku, b_mku = mku
            a_mku_ip = pgsql.read(f"select ip_vprn100 from bsa where bsa = '{a_mku}'")[0]
            b_mku_ip = pgsql.read(f"select ip_vprn100 from bsa where bsa = '{b_mku}'")[0]
            a_mku_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{a_mku}'")[0]
            b_mku_ipb = pgsql.read(f"select ip_base from bsa where bsa = '{b_mku}'")[0]
            if f'SDP-{sdp}' not in u_sdp1:
                cmd = operg_tmp(sdp, ip_pool, a_mku, b_mku, a_mku_ipb, b_mku_ipb)
                print(f'\nSDP: {bc.CYAN}SDP-{sdp}{bc.ENDC}\nСледующая подсеть: {snet}\nBSR01 VRRP IP: {bc.GREEN}{ip_pool[-1]}{bc.ENDC}\nBSR02 VRRP IP: {bc.GREEN}{ip_pool[-2]}{bc.ENDC}\nBSR01 - Активная {bc.GREEN}MKU-{a_mku}{bc.ENDC}|{a_mku_ip}|{a_mku_ipb}\nBSR02 - Резервная {bc.GREEN}MKU-{b_mku}{bc.ENDC}|{b_mku_ip}|{b_mku_ipb}\n')
                slct = input(f'\n{bc.BOLD}Начинаем настройку? (y/n):{bc.ENDC}')
                if slct == 'y':
                    result1 = ssh.invoke(cmd.bsr01, s1)
                    print(f'{bc.GREEN}[!]{bc.ENDC} == На BSR01 настроено ==')
                    result2 = ssh.invoke(cmd.bsr02, s2)
                    print(f'{bc.GREEN}[!]{bc.ENDC} == На BSR02 настроено ==')
                    log.write(f'{result1}\n{result2}', 1)
                    if a_mku == b_mku:
                        result_aa = telnet.huawei(cmd.mku_aa, a_mku_ip, radctl.username, radctl.password)
                        print(f'{bc.GREEN}[!]{bc.ENDC} == На MKU-{a_mku} настроено ==')
                        log.write(result_aa, 1)
                    else:
                        result_a = telnet.huawei(cmd.mku_a, a_mku_ip, radctl.username, radctl.password)
                        print(f'{bc.GREEN}[!]{bc.ENDC} == На MKU-{a_mku} настроено ==')
                        result_b = telnet.huawei(cmd.mku_b, b_mku_ip, radctl.username, radctl.password)
                        print(f'{bc.GREEN}[!]{bc.ENDC} == На MKU-{b_mku} настроено ==')
                        log.write(f'{result_a}\n{result_b}', 1)
                    ssh.close(s1)
                    ssh.close(s2)
                    return True
                elif slct != 'y':
                    print(f'{bc.RED}[!]{bc.ENDC} == Выход ==')
                    ssh.close(s1)
                    ssh.close(s2)
                    return False
            else:
                print(f'{bc.RED}[!]{bc.ENDC} Для данной SDP-{sdp} уже есть опергруппа!')
                ssh.close(s1)
                ssh.close(s2)
                return False
        else:
            print(f'{bc.RED}[!]{bc.ENDC} Полукольцо {ring} не найдено!')
            ssh.close(s1)
            ssh.close(s2)
            return False
    else:
        print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Невозможно подключится к BSR.\n')
        return False

def gi_create(mode, bsr01, bsr02):
    s1 = ssh.init(bsr01, radctl.username, radctl.password, 1)
    s2 = ssh.init(bsr02, radctl.username, radctl.password, 1)
    if s1 != False and s2 != False:
        pw = input('Введите номер PW: ')
        pw_check = ssh.invoke(f'show pw-port {pw}', s1)
        if re.findall('PW Port Information', pw_check):
            srrp_all = range(9990001, 9999999)
            srrp_used = []
            mpsap_all = range(4074, 4094)
            mpsap_used = []
            for a in ssh.invoke('show srrp | match expression "[9][9][9][0-9][0-9][0-9][0-9]"', s1).split('\n'):
                if re.findall(' Up ', a):
                    srrp_used.append(int(a.split()[0]))
            for b in ssh.invoke(f'show service sap-using | match -{pw}', s1).split('\n'):
                if re.findall(f'pw-{pw}:', b):
                    if re.findall(']', b):
                        sap = ((b.split()[0]).split(':')[1])[:-1]
                    else:
                        sap = (b.split()[0]).split(':')[1]
                    if sap != '*':
                        mpsap_used.append(int(sap))
            srrp = str(sorted(set(srrp_all)-set(srrp_used))[0])
            mpsap = str(sorted(set(mpsap_all)-set(mpsap_used))[0])
            cmd = gi_tmp(pw, srrp, mpsap)
            if mode == 0:
                gi_check = ssh.invoke(f'show router 100 interface "CCTV" detail | match "PW-{pw}"\n', s1)
                if not re.findall('VPRN G', gi_check):
                    print(f'\nPW: {bc.GREEN}{pw}{bc.ENDC}\nSRRP: {bc.GREEN}{srrp}{bc.ENDC}\nmessage-path: {bc.GREEN}pw-{pw}:{mpsap}{bc.ENDC}\nГрупповой интерфейс: {bc.GREEN}group-interface "CCTV-PW-{pw}"{bc.ENDC}')
                    slct = input(f'\n{bc.BOLD}Начинаем настройку? (y/n):{bc.ENDC}')
                    if slct == 'y':
                        result1 = ssh.invoke(cmd.cctv_bsr01, s1)
                        print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR01 настроено ==')
                        result2 = ssh.invoke(cmd.cctv_bsr02, s2)
                        print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR02 настроено ==')
                        log.write(f'{result1}\n{result2}', 1)
                        ssh.close(s1)
                        ssh.close(s2)
                        return True
                    elif slct != 'y':
                        print(f'{bc.RED}[!]{bc.ENDC} == Выход ==')
                        ssh.close(s1)
                        ssh.close(s2)
                        return False
                else:
                    print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Для PW-{pw} уже существует групповой интерфейс в subscriber-interface CCTV!\n')
                    ssh.close(s1)
                    ssh.close(s2)
                    return False
            elif mode == 1:
                gi_check = ssh.invoke(f'show router 100 interface "IPoE" detail | match "PW-{pw}"\n', s1)
                if not re.findall('VPRN G', gi_check):
                    print(f'\nPW: {bc.GREEN}{pw}{bc.ENDC}\nSRRP: {bc.GREEN}{srrp}{bc.ENDC}\nmessage-path: {bc.GREEN}pw-{pw}:{mpsap}{bc.ENDC}\nГрупповой интерфейс: {bc.GREEN}group-interface "IPOE-PW-{pw}"{bc.ENDC}')
                    slct = input(f'\n{bc.BOLD}Начинаем настройку? (y/n):{bc.ENDC}')
                    if slct == 'y':
                        result1 = ssh.invoke(cmd.ipoe_bsr01, s1)
                        print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR01 настроено ==')
                        result2 = ssh.invoke(cmd.ipoe_bsr02, s2)
                        print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR02 настроено ==')
                        log.write(f'{result1}\n{result2}', 1)
                        ssh.close(s1)
                        ssh.close(s2)
                        return True
                    elif slct != 'y':
                        print(f'{bc.RED}[!]{bc.ENDC} == Выход ==')
                        ssh.close(s1)
                        ssh.close(s2)
                        return False
            elif mode == 2:
                gi_check = ssh.invoke(f'show router 100 interface "SUB-DEFAULT" detail | match "PW-{pw}"\n', s1)
                if not re.findall('VPRN G', gi_check):
                    print(f'\nPW: {bc.GREEN}{pw}{bc.ENDC}\nSRRP: {bc.GREEN}{srrp}{bc.ENDC}\nmessage-path: {bc.GREEN}pw-{pw}:{mpsap}{bc.ENDC}\nГрупповой интерфейс: {bc.GREEN}group-interface "DEFAULT-PW-{pw}"{bc.ENDC}')
                    slct = input(f'\n{bc.BOLD}Начинаем настройку? (y/n):{bc.ENDC}')
                    if slct == 'y':
                        result1 = ssh.invoke(cmd.sdef_bsr01, s1)
                        print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR01 настроено ==')
                        result2 = ssh.invoke(cmd.sdef_bsr02, s2)
                        print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR02 настроено ==')
                        log.write(f'{result1}\n{result2}', 1)
                        ssh.close(s1)
                        ssh.close(s2)
                        print(f'{bc.GREEN}[!]{bc.ENDC}Не забываем добавить в АРМ:{bc.CYAN} Отчеты > Тех Сопровождение > Суффиксы Балансирования{bc.ENDC}')
                        return True
                    elif slct != 'y':
                        print(f'{bc.RED}[!]{bc.ENDC} == Выход ==')
                        ssh.close(s1)
                        ssh.close(s2)
                        return False
                else:
                    print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Для PW-{pw} уже существует групповой интерфейс в subscriber-interface SUB-DEFAULT!\n')
                    ssh.close(s1)
                    ssh.close(s2)
                    return False
            elif mode == 3:
                gi_check = ssh.invoke(f'show router 140 interface "ACCESS-ENFORTA" detail | match "PW-{pw}"\n', s1)
                if not re.findall('VPRN G', gi_check):
                    print(f'\nPW: {bc.GREEN}{pw}{bc.ENDC}\nSRRP: {bc.GREEN}{srrp}{bc.ENDC}\nmessage-path: {bc.GREEN}pw-{pw}:{mpsap}{bc.ENDC}\nГрупповой интерфейс: {bc.GREEN}group-interface "ENFORTA-PW-{pw}"{bc.ENDC}')
                    slct = input(f'\n{bc.BOLD}Начинаем настройку? (y/n):{bc.ENDC}')
                    if slct == 'y':
                        result1 = ssh.invoke(cmd.aenf_bsr01, s1)
                        print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR01 настроено ==')
                        result2 = ssh.invoke(cmd.aenf_bsr02, s2)
                        print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR02 настроено ==')
                        log.write(f'{result1}\n{result2}', 1)
                        ssh.close(s1)
                        ssh.close(s2)
                        return True
                    elif slct != 'y':
                        print(f'{bc.RED}[!]{bc.ENDC} == Выход ==')
                        ssh.close(s1)
                        ssh.close(s2)
                        return False
                else:
                    print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Для PW-{pw} уже существует групповой интерфейс в subscriber-interface ACCESS-ENFORTA!\n')
                    ssh.close(s1)
                    ssh.close(s2)
                    return False
        elif re.findall('not found', pw_check):
            print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! PW порт не сущеcтвует!\n')
            ssh.close(s1)
            ssh.close(s2)
            return False
    else:
        print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Невозможно подключится к BSR.\n')
        return False

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
                cmd = vpls_tmp(new_vpls, mtu)
                slct = input(f'VPLS {bc.GREEN}{new_vpls}{bc.ENDC} свободен, начинаем настройку? (y/n):')
                if slct != 'y':
                    return False
                else:
                    print(f'Настраиваю на BSR01...')
                    result1 = ssh.invoke(cmd.bs_bsr01, s1)
                    log.write(result1, 1)
                    print(f'Готово')
                    print(f'Настраиваю на BSR02...')
                    result2 = ssh.invoke(cmd.bs_bsr02, s2)
                    log.write(result2, 1)
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
                cmd = vpls_tmp(new_vpls, mtu)
                slct = input(f'VPLS {bc.GREEN}{new_vpls}{bc.ENDC} свободен, начинаем настройку? (y/n):')
                if slct != 'y':
                    return False
                else:
                    print(f'Настраиваю на BSR01...')
                    result1 = ssh.invoke(cmd.bs_bsr01, s1)
                    log.write(result1, 1)
                    print(f'Готово')
                    print(f'Настраиваю на BSR02...')
                    result2 = ssh.invoke(cmd.bs_bsr02, s2)
                    log.write(result2, 1)
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
                cmd = vpls_tmp(new_vpls, mtu)
                slct = input(f'VPLS {bc.GREEN}{new_vpls}{bc.ENDC} свободен, начинаем настройку? (y/n):')
                if slct != 'y':
                    return False
                else:
                    print(f'Настраиваю на BSR01...')
                    result1 = ssh.invoke(cmd.rt_bsr01, s1)
                    log.write(result1, 1)
                    print(f'Готово')
                    print(f'Настраиваю на BSR02...')
                    result2 = ssh.invoke(cmd.rt_bsr02, s2)
                    log.write(result2, 1)
                    print(f'Готово')
                    ssh.close(s1)
                    ssh.close(s2)
                    return True
        else:
            print(f'{bc.RED}[!]{bc.ENDC} Неверный номер Route Target!')
            return False

def sap_vp(mode, bsr01, bsr02):
    s1 = ssh.init(bsr01, radctl.username, radctl.password, 1)
    s2 = ssh.init(bsr02, radctl.username, radctl.password, 1)
    if s1 != False and s2 != False:
        if mode == 0: #add SAP and interface to VPRN
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
                cmd = sap_tmp(mode, vprn, ifc, opg, ip, sap, cmbs, rate)
                print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR01 настроено ==')
                result1 = ssh.invoke(cmd.vprn_add, s1)
                print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR02 настроено ==')
                result2 = ssh.invoke(cmd.vprn_add, s2)
                print(f'{bc.GREEN}[+]{bc.ENDC} === Готово! ===')
                ssh.close(s1)
                ssh.close(s2)
                log.write(f'{result1}\n{result2}', 1)
                return True
        elif mode == 1: #add SAP to VPLS
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
                cmd = sap_tmp(mode, vpls, sap, rate)
                print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR01 настроено ==')
                result1 = ssh.invoke(cmd.vpls_add, s1)
                print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR02 настроено ==')
                result2 = ssh.invoke(cmd.vpls_add, s2)
                print(f'{bc.GREEN}[+]{bc.ENDC} === Готово! ===')
                ssh.close(s1)
                ssh.close(s2)
                log.write(f'{result1}\n{result2}', 1)
                return True
        elif mode == 2: #remove SAP and interface from VPRN
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
                cmd = sap_tmp(mode, vprn, ifc, sap)
                print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR01 удалено ==')
                result1 = ssh.invoke(cmd.vprn_del, s1)
                print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR02 удалено ==')
                result2 = ssh.invoke(cmd.vprn_del, s2)
                print(f'{bc.GREEN}[+]{bc.ENDC} === Готово! ===')
                ssh.close(s1)
                ssh.close(s2)
                log.write(f'{result1}\n{result2}', 1)
                return True
        elif mode == 3: #remove SAP from VPLS
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
                cmd = sap_tmp(mode, vpls, sap)
                print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR01 удалено ==')
                result1 = ssh.invoke(cmd.vpls_del, s1)
                print(f'{bc.GREEN}[+]{bc.ENDC} == На BSR02 удалено ==')
                result2 = ssh.invoke(cmd.vpls_del, s2)
                print(f'{bc.GREEN}[+]{bc.ENDC} === Готово! ===')
                ssh.close(s1)
                ssh.close(s2)
                log.write(f'{result1}\n{result2}', 1)
                return True
    else:
        print(f'\n{bc.RED}[!]{bc.ENDC} ОШИБКА! Проблема с SSH на BSR.\n')
        return False

def launcher_2():
    main_menu_title = "\n--------------------------------------\nv1.7 | 02.01.2022 | NOC configurator\n--------------------------------------\nГлавное меню | Что будем делать?\n--------------------------------------"
    main_menu_items = ['Конфигурация BSR', 'Конфигурация SDP и PW ГУТС и Радио', 'Работа с SQL', 'Посмотреть лог за сегодня', 'Выход']
    main_menu_cursor = "> "
    main_menu_cursor_style = ("fg_cyan", "bold")
    main_menu_style = ("bold", "fg_green")
    main_menu_exit = False
    main_menu = TerminalMenu(menu_entries=main_menu_items, title=main_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)

    bsr_menu_title = "\n> Конфигурация BSR\n------------------------------------"
    bsr_menu_items = ['Создание oper-group', 'Создание group-interface', 'Создание базового VPLS на BSR', 'Создание АРМ МГ VPLS на BSR', 'Создание/удаление SAP в VPLS или VPRN', 'Назад в главное меню']
    bsr_menu_back = False
    bsr_menu = TerminalMenu(bsr_menu_items, title=bsr_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)
    
    bsr_sap_menu_title = "\n> Конфигурация BSR\n------------------------------------"
    bsr_sap_menu_items = ['Создать интерфейс и SAP в VPRN', 'Добавить SAP в VPLS', 'Удаление существуещего интерфейса в VPRN', 'Удаление существуещего SAP в VPLS', 'Назад в предыдущее меню']
    bsr_sap_menu_back = False
    bsr_sap_menu = TerminalMenu(bsr_sap_menu_items, title=bsr_sap_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)

    gi_bsr_menu_title = "\n>> Создание group-interface\n------------------------------------"
    gi_bsr_menu_items = ['CCTV [VPRN 100]', 'IPoE [VPRN 100]', 'SUB-DEFAULT [VPRN 100]', 'ACCESS-ENFORTA [VPRN 140]', 'Назад в главное меню']
    gi_bsr_menu_back = False
    gi_bsr_menu = TerminalMenu(gi_bsr_menu_items, title=gi_bsr_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)

    sdp_menu_title = "\n> Конфигурация SDP и PW ГУТС и Радио\n------------------------------------"
    sdp_menu_items = ['Создание новой пары и SDP [ГУТС]', 'Добавление PW в сущ. SDP [ГУТС]', 'Создание нового ринга (SDP и PW)[Радио]', 'Назад в главное меню']
    sdp_menu_back = False
    sdp_menu = TerminalMenu(sdp_menu_items, title=sdp_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)

    db_menu_title = "\n> Работа с SQL\n------------------------------------"
    db_menu_items = ['Добавление BSA/MKU', 'УДАЛЕНИЕ BSA/MKU', 'УДАЛЕНИЕ пары MKU [ГУТС]', 'УДАЛЕНИЕ пары BSA [Радио]',  'Назад в главное меню']
    db_menu_back = False
    db_menu = TerminalMenu(db_menu_items, title=db_menu_title, menu_cursor=main_menu_cursor, menu_cursor_style=main_menu_cursor_style, menu_highlight_style=main_menu_style, cycle_cursor=True, clear_screen=False)

    while not main_menu_exit:
        main_sel = main_menu.show()
        if main_sel == 0:
            while not bsr_menu_back:
                bsr_slct = bsr_menu.show()
                if bsr_slct == 0:
                    oper_create(mgmt.bsr01, mgmt.bsr02)
                    time.sleep(1)
                elif bsr_slct == 1:
                    while not gi_bsr_menu_back:
                        gi_bsr_slct = gi_bsr_menu.show()
                        if gi_bsr_slct == 0:
                            gi_create(0, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(1)
                        elif gi_bsr_slct == 1:
                            gi_create(1, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(1)
                        elif gi_bsr_slct == 2:
                            gi_create(2, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(1)
                        elif gi_bsr_slct == 3:
                            gi_create(3, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(1)
                        elif gi_bsr_slct == 4:
                            gi_bsr_menu_back = True
                    gi_bsr_menu_back = False
                elif bsr_slct == 2:
                    vpls_create(1, mgmt.bsr01, mgmt.bsr02)
                    time.sleep(1)
                elif bsr_slct == 3:
                    vpls_create(2, mgmt.bsr01, mgmt.bsr02)
                    time.sleep(1)
                elif bsr_slct == 4:
                    while not bsr_sap_menu_back:
                        bsr_sap_slct = bsr_sap_menu.show()
                        if bsr_sap_slct == 0:
                            sap_vp(0, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(2)
                        if bsr_sap_slct == 1:
                            sap_vp(1, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(2)
                        if bsr_sap_slct == 2:
                            sap_vp(2, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(2)
                        if bsr_sap_slct == 3:
                            sap_vp(3, mgmt.bsr01, mgmt.bsr02)
                            time.sleep(2)
                        elif bsr_sap_slct == 4:
                            bsr_sap_menu_back = True
                    bsr_sap_menu_back = False
                elif bsr_slct == 5:
                    bsr_menu_back = True
            bsr_menu_back = False
        elif main_sel == 1:
            while not sdp_menu_back:
                sdp_slct = sdp_menu.show()
                if sdp_slct == 0:
                    sdp_pw_create(0, mgmt.bsr01, mgmt.bsr02)
                    time.sleep(1)
                elif sdp_slct == 1:
                    sdp_pw_create(1, mgmt.bsr01, mgmt.bsr02)
                    time.sleep(1)
                elif sdp_slct == 2:
                    rsdp_pw_create(mgmt.bsr01, mgmt.bsr02)
                    time.sleep(1)
                elif sdp_slct == 3:
                    sdp_menu_back = True
            sdp_menu_back = False
        elif main_sel == 2:
            while not db_menu_back:
                db_slct = db_menu.show()
                if db_slct == 0:
                    db_query(0)
                    time.sleep(1)
                elif db_slct == 1:
                    db_query(1)
                    time.sleep(1)
                elif db_slct == 2:
                    db_query(2)
                    time.sleep(1)
                elif db_slct == 3:
                    db_query(3)
                    time.sleep(1)
                elif db_slct == 4:
                    db_menu_back = True
            db_menu_back = False
        elif main_sel == 3:
            log.read(1)
            time.sleep(2)
        elif main_sel == 4:
            main_menu_exit = True
            print("=== Выход ===")

launcher_2()