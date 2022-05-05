# NOC tools and configuration scripts
## Table of contents
* [General info](#general-info)
* [Technologies](#technologies)
* [Setup](#setup)

## General info
This project was created to automate the daily routine tasks for network engineers.
* ```SVC_config.py``` - Tools for service activation department. Makes new or remove old entire configuration from network devices. Uses various patterns in ```main/templates.py``` for it.
* ```NOC_config.py``` - Same as above, but for NOC department. Makes or remove configuration on core network devices, in depend on current state.
* ```Check-mac-flap.py``` - Running in real time (specified in menu), this tool helps detect L2 loop sources(SAP, Spoke-SDP, BGP-VPLS) in large VPLS on Nokia BSR.

## Technologies
Project is created with:
* PostgreSQL 13
* multiprocess 0.70.12.2
* jinja2 2.11.3
* paramiko 2.10.3
* psycopg2 2.9.1
* python3_netsnmp 1.1a1
* simple_term_menu 1.4.1

## Setup
To run this project git clone it locally, install required packages via PIP ```pip3 install -r requirements.txt```.
If needed change variables in ```main/config.py```. For some definitions in scripts postgresql database must be configured.
