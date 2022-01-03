#!/bin/python3

import psycopg2
import time
import base64
from main.config import sql_var, bc

class pgsql:
    def read(cmd):
        con = psycopg2.connect(database=sql_var.db_pg, user=base64.b64decode(sql_var.usr_pg).decode("ascii"), password=base64.b64decode(sql_var.pass_pg).decode("ascii"), host=sql_var.host_pg, port=sql_var.port_pg)
        cursor = con.cursor()
        cursor.execute(cmd)
        sql_out = list(cursor) #list of tuples
        if len(sql_out) == 0:
            #print(f'{bc.RED}[!]{bc.ENDC} SQL return empty!')
            con.close()
            return sql_out
        else:
            out = []
            for a in sql_out:
                for b in list(a):
                    if type(b) is bool:
                        out.append(b)
                    else:
                        out.append(str(b))
            #print(out)
            return out
            con.close()
    
    def write(cmd):
        con = psycopg2.connect(database=sql_var.db_pg, user=base64.b64decode(sql_var.usr_pg).decode("ascii"), password=base64.b64decode(sql_var.pass_pg).decode("ascii"), host=sql_var.host_pg, port=sql_var.port_pg)
        cursor = con.cursor()
        cursor.execute(cmd)
        con.commit()
        con.close()