#!/bin/python3

from main.config import log_var, bc
import os, getpass, time, re

class log:
    usr = os.getlogin()
    usr_eff = getpass.getuser()
    def write(result, mode):
        exec(f'f = log_var.fname{str(mode)}', globals(), locals())
        fn = locals()['f']
        try:
            wr_date = time.strftime('%b-%Y')
            log_date = time.strftime('%d-%b-%Y %H:%M:%S')
            file = open(f'/FILE_SERVER/LOG/Script/{wr_date}_{fn}', 'a')
            file.write(f'{log.usr_eff}({log.usr})|{log_date}|{"="*50}\n')
            if result:
                for each in result.split('\n'):
                    file.write(f'{log.usr_eff}({log.usr})|{log_date}| {each}\n')
            else:
                file.write(f'{log.usr_eff}({log.usr})|{log_date}| {result}\n')
            file.close()
        except PermissionError:
            print(f'{bc.RED}[!]{bc.ENDC} Ошибка открытия файла лога')
    
    def read(mode):
        exec(f'f = log_var.fname{str(mode)}', globals(), locals())
        fn = locals()['f']
        try:
            wr_date = time.strftime('%b-%Y')
            log_date = time.strftime('%d-%b-%Y')
            src = open(f'/FILE_SERVER/LOG/Script/{wr_date}_{fn}', 'r').read().split('\n')
            log_td = []
            for a in src:
                if re.findall(log_date, a):
                    log_td.append(a)
            if len(log_td) != 0 :
                msg = "\n".join(log_td)
                print(f'\n{bc.CYAN}{"="*80}{bc.ENDC}\n{msg}\n{bc.CYAN}{"="*80}{bc.ENDC}\n')
            else:
                print(f'\n{bc.CYAN}{"="*80}{bc.ENDC}\nЗа сегодня лога нет\n{bc.CYAN}{"="*80}{bc.ENDC}\n')
        except FileNotFoundError:
            print(f'{bc.RED}[!]{bc.ENDC} За текущий месяц файла лога нет')
            return False