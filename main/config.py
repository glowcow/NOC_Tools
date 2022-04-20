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
    prim_com = ''
    old_com = ''

class log_var: #path to local log files and they prefix name e.g Jan-2022_{fname}
    path = '/FILE_SERVER/LOG/Script/'
    fname1 = 'noc-config.log' #prefix name for NOC_config log file
    fname2 = 'svc-config.log' #prefix name for SVC_config log file
    fname3 = 'nd-backup.log' #prefix name for nd_backup log file

class radctl: #RADIUS rw user, all values must be encoded in base64
    username = ''
    password = ''

class mik_acc: #mikrotik router rw user, all values must be encoded in base64
    username_m = ''
    password_m = ''
    password_m2 = ''
    username_cm = ''
    password_cm = ''

class sql_var: #usr_pg & pass_pg must be encoded in base64
    db_pg = ''
    usr_pg = ''
    pass_pg = ''
    host_pg = ''
    port_pg = 5432

class mgmt:
    bsr01 = ''
    bsr02 = ''
    cts01 = ''
    cts02 = ''
    cts03 = ''
    cts04 = ''

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
    bot_token = ''
