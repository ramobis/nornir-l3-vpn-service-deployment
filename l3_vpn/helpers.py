import re
import ipaddress
import yaml
from nornir.core.inventory import ParentGroups, Group
from nornir.core.task import Task


def get_global_service_data(service_file: str) -> dict:
    services = {}
    with open(service_file, "r") as file:
        data = yaml.safe_load(file)

        if data["services"] is None:
            return services

        for service in data["services"]:
            services[service["name"]] = {
                "id": service["id"],
                "description": service["description"],
                "route_import": service["route_import"],
                "route_export": service["route_export"],
            }
    return services


def get_host_service_data(service_file: str, site: str) -> dict:
    services = {}
    with open(service_file, "r") as file:
        data = yaml.safe_load(file)

        if data["services"] is None:
            return services

        for service in data["services"]:
            if service["sites"] is None:
                continue
            if site in service["sites"]:
                services[service["name"]] = service["sites"][site]
    return services


def get_obsolete_vrfs(present_now: list[str], present_after: list[str]) -> list[str]:
    # returns entries in present_now and not in present_after
    return list(set(present_now) - set(present_after))


def get_missing_vrfs(present_now: list[str], present_after: list[str]) -> list[str]:
    # returns entries in present_after and not in present_now
    return list(set(present_after) - set(present_now))


def get_site_group_name(groups: ParentGroups) -> str:
    for g in groups:
        if g.name.startswith("site-"):
            return g.name


def get_site_group(groups: ParentGroups) -> Group:
    for g in groups:
        if g.name.startswith("site-"):
            return g


def increment_ipv4_addr(ip: str, increment: int) -> str:
    return str(ipaddress.ip_address(ip) + increment)


def get_multihomed_interface_configuration_data(task: Task, increment: int) -> dict:
    service_data = task.host.data["host_service_data"]

    if len(service_data) == 0:
        return

    interfaces = {}

    for s_name, s_data in service_data.items():
        interfaces[s_name] = []
        for interface in s_data["interfaces"]:
            addr, mask = interface["ip"].split(" ")[0], interface["ip"].split(" ")[1]
            incremented_addr = increment_ipv4_addr(addr, increment)
            interfaces[s_name].append(
                {
                    "name": interface["name"],
                    "ip": f"{incremented_addr} {mask}",
                    "hsrp_ip": addr,
                }
            )
    return interfaces


def get_subinterfaces_with_no_ip(
    all_interfaces: list[str], interfaces_with_ip: list[str]
) -> list[str]:
    subinterface_regex = r"^GigabitEthernet[0-9]+\.[0-9]+$"
    all_subinterfaces = [
        int_name
        for int_name in all_interfaces
        if re.match(subinterface_regex, int_name)
    ]
    subinterfaces_with_ip = [
        int_name
        for int_name in interfaces_with_ip
        if re.match(subinterface_regex, int_name)
    ]
    return list(set(all_subinterfaces) - set(subinterfaces_with_ip))
