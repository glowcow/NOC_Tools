#!/bin/python3

from main.config import bc
import netsnmp
import re

class snmp:
    com1 = 'holding08'
    com2 = 'engforta'
    def vendor(host):
        oid = 'iso.3.6.1.2.1.1.1.0'
        snmpw = netsnmp.snmpget(oid, Version=2, DestHost=host, Community=snmp.com1, Retries=1, Timeout=250000)
        (out,) = snmpw #tuple to variables
        if out is None:
            snmpw = netsnmp.snmpget(oid, Version=2, DestHost=host, Community=snmp.com2, Retries=1, Timeout=250000)
            (out,) = snmpw
            if out is None:
                return False
            else:
                out = out.decode("ascii")
                fnd = re.search('RouterOS', out)
                if fnd:
                    return 'MikroTik'
                else:
                    return False
        else:
            out = out.decode("ascii")
            fnd = re.search('Huawei', out)
            if fnd:
                return 'Huawei'
            else:
                fnd = re.search('RouterOS', out)
                if fnd:
                    return 'MikroTik'
                else:
                    return False

    def walk(host, oid):
        snmpw = netsnmp.Session(Version=2, DestHost=host, Community=snmp.com1, Retries=1, Timeout=250000)
        snmpw.UseLongNames = 0
        snmpw.UseNumeric = 0
        vars = netsnmp.VarList(oid)
        snmpw.walk(vars)
        out = []
        for item in vars:
            if item.val.decode('ascii') == '1':
                out.append(item.tag)
        if out != []:
            return out