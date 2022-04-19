#!/bin/python3
#configuration sample templates for various hardware.
class rsdp_pw_tmp():
    def __init__(self, sdp, ring, a_bsa, b_bsa, a_bsa_ipb, b_bsa_ipb, bin_port1, bin_port2):
        self.sdp_bsr01 = f'configure service sdp {sdp} mpls create \ndescription "TLDP-TO-BSA-{a_bsa}"\nfar-end {a_bsa_ipb}\nldp\nadv-mtu-override\nkeep-alive\nshutdown\nexit\nbinding\nport lag-{bin_port1}\nexit\nno shutdown\nexit all\n'
        self.sdp_bsr02 = f'configure service sdp {sdp} mpls create \ndescription "TLDP-TO-BSA-{b_bsa}"\nfar-end {b_bsa_ipb}\nldp\nadv-mtu-override\nkeep-alive\nshutdown\nexit\nbinding\nport lag-{bin_port2}\nexit\nno shutdown\nexit all\n'
        self.pw_bsr01 = f'configure pw-port {ring} create\ndescription "BSA-{a_bsa}_SDP-{sdp}_RING-{ring}"\nexit all\nconfigure redundancy multi-chassis peer 10.6.200.2 sync\nport pw-{ring} sync-tag "PW{ring}" create\nexit all\nconfigure service sdp {sdp} \nbinding\npw-port {ring} vc-id {ring} create\nvc-type vlan\nvlan-vc-tag {ring}\nno shutdown\nexit all\n'
        self.pw_bsr02 = f'configure pw-port {ring} create\ndescription "BSA-{b_bsa}_SDP-{sdp}_RING-{ring}"\nexit all\nconfigure redundancy multi-chassis peer 10.6.200.1 sync\nport pw-{ring} sync-tag "PW{ring}" create\nexit all\nconfigure service sdp {sdp} \nbinding\npw-port {ring} vc-id {ring} create\nvc-type vlan\nvlan-vc-tag {ring}\nno shutdown\nexit all\n'
        self.bsa_aa = f'system-view\nvsi {ring}\ndescription SUBSCRIBERS_BSR01-BSR02_RING-{ring}\npwsignal ldp\nvsi-id {ring}\npeer 10.6.200.1 upe\npeer 10.6.200.2 upe\nquit\nmtu 9168\nignore-ac-state\nquit\nquit\nsave\ny\n'
        self.bsa_a = f'system-view\nvsi {ring}\ndescription SUBSCRIBERS_BSR01-BSA{b_bsa}_RING-{ring}\npwsignal ldp\nvsi-id {ring}\npeer 10.6.200.1 upe\npeer {b_bsa_ipb} upe\nquit\nmtu 9168\nignore-ac-state\nquit\nquit\nsave\ny\n'
        self.bsa_b = f'system-view\nvsi {ring}\ndescription SUBSCRIBERS_BSR02-BSA{a_bsa}_RING-{ring}\npwsignal ldp\nvsi-id {ring}\npeer 10.6.200.2 upe\npeer {a_bsa_ipb} upe\nquit\nmtu 9168\nignore-ac-state\nquit\nquit\nsave\ny\n'
