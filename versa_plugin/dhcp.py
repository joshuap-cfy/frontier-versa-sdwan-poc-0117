import json
from versa_plugin.versaclient import JSON
from requests import codes


def create_options_profile(client, appliance, org_name, name, domain, servers):
    url = ' /api/config/devices/device/{}'\
        '/config/orgs/org-services/{}'\
        '/dhcp/dhcp4-options-profiles'.format(appliance, org_name)
    data = {
        "dhcp4-options-profile": {
            "name": name,
            "domain-name": domain,
            "dns-server": servers,
            "custom-options": {"custom-dhcp-option": []}}}
    client.post(url, json.dumps(data), JSON, codes.created)


def create_lease_profile(client, appliance, org_name, name):
    url = ' /api/config/devices/device/{}'\
        '/config/orgs/org-services/{}'\
        '/dhcp/dhcp4-lease-profiles'.format(appliance, org_name)
    data = {
        "dhcp4-lease-profile": {
            "name": name,
            "valid-lifetime": "3600",
            "renew-timer": "900",
            "rebind-timer": "2800",
            "log-utilization": False}}
    client.post(url, json.dumps(data), JSON, codes.created)


def create_pool(client, appliance, org_name, pool_name, mask,
                range_name, begin_address, end_address):
    url = ' /api/config/devices/device/{}'\
        '/config/orgs/org-services/{}'\
        '/dhcp/dhcp4-dynamic-pools'.format(appliance, org_name)
    data = {
        "dhcp4-dynamic-pool": {
            "name": pool_name,
            "subnet-mask": mask,
            "address-pools": {
                "dhcp4-address-pool-info": [{
                    "name": range_name,
                    "pool": {
                        "ipv4-range": {
                            "begin-address": begin_address,
                            "end-address": end_address}}}]},
            "exclude-addresses": {"dhcp4-address-pool-info": []}}}
    client.post(url, json.dumps(data), JSON, codes.created)


def create_server(client, appliance, org_name, server_name,
                  lease_profile, options_profile, networks, pool):
    url = ' /api/config/devices/device/{}'\
        '/config/orgs/org-services/{}/dhcp/'\
        '/dhcp4-server-and-relay/service-profiles'.format(appliance, org_name)
    data = {
        "dhcp4-service-profile": {
            "name": server_name,
            "lease-profile": lease_profile,
            "options-profile": options_profile,
            "dhcp-request-match": {
                "networks": networks},
            "dhcp-service-type": {
                "service-type": {
                    "allocate-address": {
                        "dynamic": pool}}},
            "dhcp-log-settings": {
                "log-new-allocations": True,
                "log-renewals": False}}}
    client.post(url, json.dumps(data), JSON, codes.created)