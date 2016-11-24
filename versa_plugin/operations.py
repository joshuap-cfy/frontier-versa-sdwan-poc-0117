from cloudify import ctx
from cloudify import exceptions as cfy_exc
from cloudify.decorators import operation
import versa_plugin
from copy import deepcopy

from versa_plugin import with_versa
from versa_plugin import get_mandatory
import versa_plugin.appliance
import versa_plugin.cgnat
import versa_plugin.connectors
import versa_plugin.dhcp
import versa_plugin.firewall
import versa_plugin.networking
import versa_plugin.tasks
import versa_plugin.vpn
import versa_plugin.limits
from versa_plugin.cgnat import AddressRange
from collections import namedtuple

ApplianceContext = namedtuple("ApplianceContext",
                              "client, appliance, organization")


def is_use_existing():
    return ctx.node.properties.get('use_existing')


def reqursive_update(d, u):
    for k, v in u.iteritems():
        if isinstance(v, dict):
            r = reqursive_update(d.get(k, {}), v)
            d[k] = r
        elif isinstance(v, list):
            if isinstance(u[k], list):
                d[k] = d.setdefault(k, []) + u[k]
            else:
                d[k] = d.setdefault(k, []) + [u[k]]
        else:
            d[k] = u[k]
    return d


def _get_node_configuration(key, kwargs):
    value = ctx.node.properties.get(key, {})
    value.update(kwargs.get(key, {}))
    if value:
        return value
    else:
        raise cfy_exc.NonRecoverableError(
            "Configuration parameter {0} is absent".format(key))


@operation
@with_versa
def create_resource_pool(versa, **kwargs):
    if is_use_existing():
        return
    instance = _get_node_configuration('instance', kwargs)
    versa_plugin.connectors.add_resource_pool(versa, instance)


@operation
@with_versa
def delete_resource_pool(versa, **kwargs):
    if is_use_existing():
        return
    instance = _get_node_configuration('instance', kwargs)
    name = get_mandatory(instance, 'name')
    versa_plugin.connectors.delete_resource_pool(versa, name)


@operation
@with_versa
def create_cms_local_organization(versa, **kwargs):
    if is_use_existing():
        return
    organization = _get_node_configuration('organization', kwargs)
    versa_plugin.connectors.add_organization(versa, organization)


@operation
@with_versa
def delete_cms_local_organization(versa, **kwargs):
    if is_use_existing():
        return
    organization = _get_node_configuration('organization', kwargs)
    name = get_mandatory(organization, 'name')
    versa_plugin.connectors.delete_organization(versa, name)


@operation
@with_versa
def create_organization(versa, **kwargs):
    if is_use_existing():
        return
    organization = _get_node_configuration('organization', kwargs)
    versa_plugin.appliance.add_organization(versa, organization)


@operation
@with_versa
def delete_organization(versa, **kwargs):
    if is_use_existing():
        return
    organization = _get_node_configuration('organization', kwargs)
    name = get_mandatory(organization, 'name')
    versa_plugin.appliance.delete_organization(versa, name)


@operation
@with_versa
def create_appliance(versa, **kwargs):
    if is_use_existing():
        return
    device = _get_node_configuration('device', kwargs)
    management_ip = get_mandatory(device, 'mgmt-ip')
    versa_plugin.appliance.wait_for_device(versa, management_ip, ctx)
    task = versa_plugin.appliance.add_appliance(versa, device)
    versa_plugin.tasks.wait_for_task(versa, task, ctx)


@operation
@with_versa
def delete_appliance(versa, **kwargs):
    if is_use_existing():
        return
    device = _get_node_configuration('device', kwargs)
    name = get_mandatory(device, 'name')
    task = versa_plugin.appliance.delete_appliance(versa, name)
    versa_plugin.tasks.wait_for_task(versa, task, ctx)


@operation
@with_versa
def associate_organization(versa, **kwargs):
    if is_use_existing():
        return
    organization = _get_node_configuration('organization', kwargs)
    appliance = get_mandatory(organization, 'appliance')
    net_info = get_mandatory(organization, 'networking-info')
    for net in net_info:
        interface = get_mandatory(get_mandatory(net, 'network-info'),
                                  'parent-interface')
        versa_plugin.networking.create_interface(versa, appliance,
                                                 interface)
    task = versa_plugin.appliance.associate_organization(versa,
                                                         organization)
    versa_plugin.tasks.wait_for_task(versa, task, ctx)


@operation
@with_versa
def create_router(versa, **kwargs):
    if is_use_existing():
        return
    router = _get_node_configuration('router', kwargs)
    if versa_plugin.networking.is_router_exists(versa, router):
        raise cfy_exc.NonRecoverableError("Router exists")
    versa_plugin.networking.create_virtual_router(versa, router)


@operation
@with_versa
def delete_router(versa, **kwargs):
    if is_use_existing():
        return
    router = _get_node_configuration('router', kwargs)
    router_name = router['name']
    if versa_plugin.networking.is_router_exists(versa, router_name):
        versa_plugin.networking.delete_virtual_router(versa, router_name)


@operation
@with_versa
def insert_to_router(versa, **kwargs):
    if is_use_existing():
        return
    router = _get_node_configuration('router', kwargs)
    router_name = router['name']
    networks = ctx.node.properties.get('networks', [])
    for net_name in networks:
        versa_plugin.networking.add_network_to_router(
            versa, router_name, net_name)


@operation
@with_versa
def delete_from_router(versa, **kwargs):
    if is_use_existing():
        return
    networks = ctx.node.properties.get('networks', [])
    router_name = ctx.node.properties['name']
    for net_name in networks:
        versa_plugin.networking.delete_network_from_router(
            versa, router_name, net_name)


@operation
@with_versa
def create_cgnat(versa, **kwargs):
    if is_use_existing():
        return
    pool = ctx.node.properties['pool']
    pool_name = pool['name']
    ranges = [AddressRange(r['name'], r['low'], r['hight'])
              for r in pool['ranges']]
    routing_instance = pool['routing_instance']
    provider_org = pool['provider_org']
    versa_plugin.cgnat.create_pool(versa,
                                   pool_name,
                                   ranges, routing_instance,
                                   provider_org)
    rule = ctx.node.properties['rule']
    rule_name = rule['name']
    source_addresses = rule['addresses']
    versa_plugin.cgnat.create_rule(versa,
                                   rule_name,
                                   source_addresses, pool_name)


@operation
@with_versa
def delete_cgnat(versa, **kwargs):
    if is_use_existing():
        return
    pool = ctx.node.properties['pool']
    pool_name = pool['name']
    rule = ctx.node.properties['rule']
    rule_name = rule['name']
    versa_plugin.cgnat.delete_rule(versa,
                                   rule_name)
    versa_plugin.cgnat.delete_pool(versa,
                                   pool_name)


@operation
@with_versa
def create_zone(versa, **kwargs):
    if is_use_existing():
        return
    zone = ctx.node.properties['zone']
    zone_name = zone['name']
    zone_exsists = versa_plugin.networking.get_zone(versa, zone_name)
    if zone_exsists:
        raise cfy_exc.NonRecoverableError(
            "Zone '{}' exsists".format(zone_name))
    versa_plugin.networking.create_zone(versa, zone)


@operation
@with_versa
def insert_to_zone(versa, **kwargs):
    if is_use_existing():
        return
    zone = ctx.node.properties['zone']
    zone_name = zone['name']
    zone_exsists = versa_plugin.networking.get_zone(versa,
                                                    zone_name)
    if zone_exsists:
        ctx.instance.runtime_properties[zone_name] = deepcopy(zone_exsists)
        new_zone = reqursive_update(zone_exsists, zone)
        versa_plugin.networking.update_zone(versa, new_zone)


@operation
@with_versa
def delete_zone(versa, **kwargs):
    if is_use_existing():
        return
    zone = ctx.node.properties['zone']
    zone_name = zone['name']
    versa_plugin.networking.delete_zone(versa, zone_name)


@operation
@with_versa
def delete_from_zone(versa, **kwargs):
    if is_use_existing():
        return
    zone = ctx.node.properties['zone']
    zone_name = zone['name']
    old_zone = ctx.instance.runtime_properties.get(zone_name, None)
    if old_zone:
        versa_plugin.networking.update_zone(versa, old_zone)


@operation
@with_versa
def create_firewall_policy(versa, **kwargs):
    if is_use_existing():
        return
    policy = ctx.node.properties['policy']
    versa_plugin.firewall.add_policy(versa, policy)


@operation
@with_versa
def delete_firewall_policy(versa, **kwargs):
    if is_use_existing():
        return
    policy = ctx.node.properties['policy']
    versa_plugin.firewall.delete_policy(versa, policy['name'])


@operation
@with_versa
def create_firewall_rules(versa, **kwargs):
    if is_use_existing():
        return
    policy_name = ctx.node.properties['policy_name']
    rules = ctx.node.properties['rules']
    ctx.instance.runtime_properties['rules'] = {}
    ctx.instance.runtime_properties['appliance'] = versa.appliance
    ctx.instance.runtime_properties['org'] = versa.organization
    ctx.instance.runtime_properties['policy'] = policy_name
    for rule in rules:
        name = rule['name']
        ctx.instance.runtime_properties['rules'][name] = rule
        versa_plugin.firewall.add_rule(versa, policy_name, rule)


@operation
@with_versa
def update_firewall_rule(versa, **kwargs):
    rule = kwargs.get('rule')
    if not rule:
        return
    name = rule.get('name')
    if not name:
        ctx.logger.info("Key 'name' in rule is absent.")
        return
    old_rule = ctx.instance.runtime_properties['rules'].get(name)
    if not old_rule:
        ctx.logger.info("Rule: '{}' not found.".format(name))
        return
    reqursive_update(rule, old_rule)
    policy_name = ctx.instance.runtime_properties['policy']
    versa_plugin.firewall.update_rule(versa, policy_name, rule)


@operation
@with_versa
def get_firewall_rule(versa, **kwargs):
    name = kwargs.get('name')
    if not name:
        ctx.logger.info("Key 'name' is absent.")
        return
    policy_name = ctx.instance.runtime_properties['policy']
    rule = versa_plugin.firewall.get_rule(versa, policy_name, name)
    ctx.logger.info("Rule '{} is: {}".format(name, rule))


@operation
@with_versa
def delete_firewall_rules(versa, **kwargs):
    if is_use_existing():
        return
    policy_name = ctx.node.properties['policy_name']
    rules = ctx.node.properties['rules']
    for rule in rules:
        versa_plugin.firewall.delete_rule(versa, policy_name, rule['name'])


@operation
@with_versa
def create_url_filters(versa, **kwargs):
    url_filters = ctx.node.properties['filters']
    for url_filter in url_filters:
        ctx.logger.info("Filter: {}".format(url_filter))
        versa_plugin.firewall.add_url_filter(versa, url_filter)


@operation
@with_versa
def delete_url_filters(versa, **kwargs):
    url_filters = ctx.node.properties['filters']
    for url_filter in url_filters:
        ctx.logger.info("Filter: {}".format(url_filter))
        versa_plugin.firewall.delete_url_filter(versa, url_filter)


@operation
@with_versa
def create_dhcp_profile(versa, **kwargs):
    if is_use_existing():
        return
    profile_name = ctx.node.properties['profile_name']
    if versa_plugin.limits.is_dhcp_profile_exists(versa,
                                                  profile_name):
        raise cfy_exc.NonRecoverableError("Dhcp profile exists")
    versa_plugin.limits.create_dhcp_profile(versa, profile_name)


@operation
@with_versa
def delete_dhcp_profile(versa, **kwargs):
    if is_use_existing():
        return
    profile_name = ctx.node.properties['profile_name']
    if versa_plugin.limits.is_dhcp_profile_exists(versa,
                                                  profile_name):
        versa_plugin.limits.delete_dhcp_profile(versa,
                                                profile_name)


@operation
@with_versa
def create_dhcp_lease_profile(versa, **kwargs):
    if is_use_existing():
        return
    lease_name = ctx.node.properties['lease_profile']
    versa_plugin.dhcp.create_lease_profile(versa, lease_name)


@operation
@with_versa
def delete_dhcp_lease_profile(versa, **kwargs):
    if is_use_existing():
        return
    lease_name = ctx.node.properties['lease_profile']
    if versa_plugin.dhcp.is_lease_profile_exsists(versa, lease_name):
        versa_plugin.dhcp.delete_lease_profile(versa, lease_name)


@operation
@with_versa
def create_dhcp_options_profile(versa, **kwargs):
    if is_use_existing():
        return
    options_name = ctx.node.properties['name']
    domain = ctx.node.properties['domain']
    servers = ctx.node.properties['servers']
    versa_plugin.dhcp.create_options_profile(versa, options_name,
                                             domain, servers)


@operation
@with_versa
def delete_dhcp_options_profile(versa, **kwargs):
    if is_use_existing():
        return
    options_name = ctx.node.properties['name']
    if versa_plugin.dhcp.is_dhcp_profile_exists(versa, options_name):
        versa_plugin.dhcp.delete_options_profile(versa, options_name)


@operation
@with_versa
def create_dhcp_global_configuration(versa, **kwargs):
    if is_use_existing():
        return
    lease_profile = ctx.node.properties['lease_profile']
    options_profile = ctx.node.properties['options_profile']
    versa_plugin.dhcp.update_global_configuration(versa,
                                                  lease_profile,
                                                  options_profile)


@operation
@with_versa
def delete_dhcp_global_configuration(versa, **kwargs):
    if is_use_existing():
        return
    lease_profile = []
    options_profile = []
    versa_plugin.dhcp.update_global_configuration(versa, lease_profile,
                                                  options_profile)


@operation
@with_versa
def create_dhcp_pool(versa, **kwargs):
    if is_use_existing():
        return
    lease_profile = ctx.node.properties['lease_profile']
    options_profile = ctx.node.properties['options_profile']
    pool_name = ctx.node.properties['name']
    mask = ctx.node.properties['mask']
    range_name = ctx.node.properties['range_name']
    begin_address = ctx.node.properties['begin_address']
    end_address = ctx.node.properties['end_address']
    versa_plugin.dhcp.create_pool(versa,
                                  pool_name, mask, lease_profile,
                                  options_profile,
                                  range_name, begin_address, end_address)


@operation
@with_versa
def delete_dhcp_pool(versa, **kwargs):
    if is_use_existing():
        return
    pool_name = ctx.node.properties['name']
    if versa_plugin.dhcp.is_pool_exists(versa, pool_name):
        versa_plugin.dhcp.delete_pool(versa, pool_name)


@operation
@with_versa
def create_dhcp_server(versa, **kwargs):
    if is_use_existing():
        return
    lease_profile = ctx.node.properties['lease_profile']
    options_profile = ctx.node.properties['options_profile']
    pool_name = ctx.node.properties['pool_name']
    server_name = ctx.node.properties['name']
    networks = ctx.node.properties['networks']
    versa_plugin.dhcp.create_server(versa,
                                    server_name, lease_profile, options_profile,
                                    networks, pool_name)


@operation
@with_versa
def delete_dhcp_server(versa, **kwargs):
    if is_use_existing():
        return
    server_name = ctx.node.properties['name']
    if versa_plugin.dhcp.is_server_exists(versa, server_name):
        versa_plugin.dhcp.delete_server(versa, server_name)


@operation
@with_versa
def create_interface(versa, **kwargs):
    if is_use_existing():
        return
    interface = _get_node_configuration('interface', kwargs)
    versa_plugin.networking.create_interface(versa, interface)


@operation
@with_versa
def delete_interface(versa, **kwargs):
    if is_use_existing():
        return
    interface = _get_node_configuration('interface', kwargs)
    name = interface['name']
    versa_plugin.networking.delete_interface(versa, name)


@operation
@with_versa
def create_network(versa, **kwargs):
    if is_use_existing():
        return
    network = _get_node_configuration('network', kwargs)
    if versa_plugin.networking.is_network_exists(versa, network):
        raise cfy_exc.NonRecoverableError("Network exists")
    versa_plugin.networking.create_network(versa, network)


@operation
@with_versa
def delete_network(versa, **kwargs):
    if is_use_existing():
        return
    network = _get_node_configuration('network', kwargs)
    name = network['name']
    if versa_plugin.networking.is_network_exists(versa,
                                                 name):
        versa_plugin.networking.delete_network(versa, name)


@operation
@with_versa
def insert_to_limits(versa, **kwargs):
    if is_use_existing():
        return
    dhcp_profile = ctx.node.properties.get('dhcp_profile')
    routes = ctx.node.properties.get('routes', [])
    networks = ctx.node.properties.get('networks', [])
    interfaces = ctx.node.properties.get('interfaces', [])
    provider_orgs = ctx.node.properties.get('provider_orgs', [])
    for name in routes:
        versa_plugin.limits.add_routing_instance(versa, name)
    for name in networks:
        versa_plugin.limits.add_traffic_identification_networks(
            versa, name, 'using-networks')
    for name in interfaces:
        versa_plugin.limits.add_traffic_identification_networks(
            versa, name, 'using')
    for name in provider_orgs:
        versa_plugin.limits.add_provider_organization(versa, name)
    if dhcp_profile:
        versa_plugin.limits.insert_dhcp_profile_to_limits(versa,
                                                          dhcp_profile)


@operation
@with_versa
def delete_from_limits(versa, **kwargs):
    if is_use_existing():
        return
    dhcp_profile = ctx.node.properties.get('dhcp_profile')
    routes = ctx.node.properties.get('routes', [])
    networks = ctx.node.properties.get('networks', [])
    interfaces = ctx.node.properties.get('interfaces', [])
    provider_orgs = ctx.node.properties.get('provider_orgs', [])
    for name in routes:
        versa_plugin.limits.delete_routing_instance(versa, name)
    for name in networks:
        versa_plugin.limits.delete_traffic_identification_networks(
            versa, name, 'using-networks')
    for name in interfaces:
        versa_plugin.limits.delete_traffic_identification_networks(
            versa, name, 'using')
    for name in provider_orgs:
        versa_plugin.limits.delete_provider_organization(versa, name)
    if dhcp_profile:
        versa_plugin.limits.delete_dhcp_profile_from_limits(versa,
                                                            dhcp_profile)


@operation
@with_versa
def create_vpn_profile(versa, **kwargs):
    if is_use_existing():
        return
    profile = _get_node_configuration('profile', kwargs)
    name = profile['name']
    if versa_plugin.vpn.is_profile_exists(versa, name):
        raise cfy_exc.NonRecoverableError("VPN profile exists")
    versa_plugin.vpn.create_profile(versa, profile)


@operation
@with_versa
def delete_vpn_profile(versa, **kwargs):
    if is_use_existing():
        return
    profile = _get_node_configuration('profile', kwargs)
    name = profile['name']
    if versa_plugin.vpn.is_profile_exists(versa,
                                          name):
        versa_plugin.vpn.delete_profile(versa, name)
