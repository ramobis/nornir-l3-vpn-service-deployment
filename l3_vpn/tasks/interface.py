import helpers as hlp

from nornir.core.task import Task, Result
from nornir_napalm.plugins.tasks import napalm_configure, napalm_get
from nornir_jinja2.plugins.tasks import template_file


def configure_interfaces(task: Task) -> Result:
    site = hlp.get_site_group(task.host.groups)
    if site.data.get("multi_homed"):
        task.run(configure_interfaces_multi_homed)
    else:
        task.run(configure_interfaces_single_homed)
    task.run(delete_unused_subinterfaces)
    return task.results


def configure_interfaces_single_homed(task: Task) -> Result:
    service_data = task.host.data["host_service_data"]

    if len(service_data) == 0:
        return

    commands = ("\n").join(
        [
            template_file(
                task=task,
                template="interface_single_homed_config.j2",
                path="templates/",
                service=service,
                interfaces=service_data[service]["interfaces"],
            ).result
            for service in service_data.keys()
        ]
    )

    return napalm_configure(task=task, configuration=commands, replace=False)


def configure_interfaces_multi_homed(task: Task) -> Result:
    service_data = task.host.data["host_service_data"]

    if len(service_data) == 0:
        return

    hsrp_config = task.host.data.get("hsrp")
    hsrp_priority = hsrp_config["priority"]
    hsrp_vip_offset = hsrp_config["vip_offset"]

    interfaces = hlp.get_multihomed_interface_configuration_data(task, hsrp_vip_offset)

    if interfaces is None:
        return

    commands = ("\n").join(
        [
            template_file(
                task=task,
                template="interface_multi_homed_config.j2",
                path="templates/",
                service=service,
                interfaces=interfaces[service],
                hsrp_priority=hsrp_priority,
            ).result
            for service in service_data.keys()
        ]
    )
    return napalm_configure(task=task, configuration=commands, replace=False)


def delete_unused_subinterfaces(task: Task) -> Result:
    getters = ["interfaces_ip", "interfaces"]
    result = napalm_get(task, getters)

    all_interfaces = list(result.result["interfaces"].keys())
    interfaces_with_ip = list(result.result["interfaces_ip"].keys())

    subinterfaces_with_no_ip = hlp.get_subinterfaces_with_no_ip(
        all_interfaces, interfaces_with_ip
    )

    subinterfaces_to_delete = [
        interface
        for interface in subinterfaces_with_no_ip
        if result.result["interfaces"][interface]["is_up"]
    ]

    if len(subinterfaces_to_delete) == 0:
        return

    commands = ("\n").join(
        [f"no interface {interface}" for interface in subinterfaces_to_delete]
    )
    return napalm_configure(task=task, configuration=commands, replace=False)
