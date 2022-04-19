#!/bin/python3

from  main.config import bc
import jinja2

class ja2:
    def cfg_render(fname, **data):
        try:
            env = jinja2.Environment(loader=jinja2.FileSystemLoader('templates'))
            t = env.get_template(fname)
            cfg = t.render(data)
        except jinja2.exceptions.TemplateNotFound as e:
            print(f'{bc.RED}[!]{bc.ENDC} Template file {e} not found')
            return False
        except ValueError as e:
            print(f'{bc.RED}[!]{bc.ENDC} {e}')
            return False
        else:
            return cfg