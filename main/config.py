#!/bin/python3

class bc: #makes some colors
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    GREEN = '\033[92m'
    RED = '\033[91m'
    BLINK = '\33[5m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

class snmp_com: #primary and old SNMP communities for check network devices, must be encoded in base64
    prim_com = 'aG9sZGluZzA4'
    old_com = 'ZW5nZm9ydGE='

class log_var: #path to local log files and they prefix name e.g Jan-2022_{fname}
    path = '/FILE_SERVER/LOG/Script/'
    fname1 = 'noc-configure.log' #prefix name for NOC_config log file
    fname2 = 'svc-configure.log' #prefix name for SVC_config log file
    fname3 = 'nd-backup.log' #prefix name for nd_backup log file

class radctl: #RADIUS rw user, all values must be encoded in base64
    username = 'Z3V0c2NvbmY='
    password = 'OG5PTklkamNWbw=='

class mik_acc: #mikrotik router rw user, all values must be encoded in base64
    username_m = 'YWRtaW4='
    password_m = 'cG9saW5vbQ=='
    password_m2 = 'ZW5mb3J0aXQ='
    username_cm = 'c2NyaXB0MGNvbmZpZw=='
    password_cm = 'bmJkTVBrbzBwYjVz'

class sql_var: #usr_pg & pass_pg must be encoded in base64
    db_pg = 'pw_rings'
    usr_pg = 'YXV0b19zY3JpcHQ='
    pass_pg = 'd25xSkV5V2tMVld1Wmo0cA=='
    host_pg = 'localhost'
    port_pg = 5432

class mgmt:
    bsr01 = '176.213.132.137'
    bsr02 = '176.213.132.161'
    cts01 = '10.200.88.10'
    cts02 = '10.200.122.1'
    cts03 = '10.200.88.11'
    cts04 = '10.200.122.2'

class cts_var:
    subn_pool_cts01 = ['10.200.96.0/22', '10.200.100.0/23', '10.200.102.0/24']
    eoip_pool_cts01 = list(range(1, 5000))
    l2tp_lo_cts01 = '176.213.132.174'
    subn_pool_cts02 = ['10.200.103.0/24']
    eoip_pool_cts02 = list(range(5001, 10000))
    l2tp_lo_cts02 = '176.213.132.175'
    subn_pool_cts03 = ['10.200.16.0/22', '10.200.20.0/23']
    eoip_pool_cts03 = list(range(10001, 15000))
    l2tp_lo_cts03 = '176.213.132.180'
    subn_pool_cts04 = ['10.200.22.0/23', '10.200.24.0/22']
    eoip_pool_cts04 = list(range(15001, 20000))
    l2tp_lo_cts04 = '176.213.132.183'

class tg_api:
    bot_token = '949226977:AAH-CRfBcEdMHXInVc7XnUkDe-9johPAyDU'