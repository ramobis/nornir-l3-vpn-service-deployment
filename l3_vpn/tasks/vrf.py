import helpers as hlp

from nornir.core.task import Task, Result
from nornir_napalm.plugins.tasks import napalm_get
from nornir_napalm.plugins.tasks import napalm_configure
from nornir_jinja2.plugins.tasks import template_file


def configure_vrf(task: Task) -> Result:
    getters = ["interfaces_ip", "network_instances"]
    result = napalm_get(task, getters)
    loopback_ip = list(
        result.result["interfaces_ip"][task.host.defaults.data.get("primary_loopback")][
            "ipv4"
        ].keys()
    )[0]

    configured_vrfs = result.result["network_instances"].keys()
    specified_vrfs = task.host.defaults.data.get("system_vrfs") + list(
        task.host.data["host_service_data"].keys()
    )
    obsolete_vrfs = hlp.get_obsolete_vrfs(configured_vrfs, specified_vrfs)
    missing_vrfs = hlp.get_missing_vrfs(configured_vrfs, specified_vrfs)

    task.run(task=remove_obsolete_vrf, obsolete_vrfs=obsolete_vrfs)
    task.run(
        task=create_missing_vrf, missing_vrfs=missing_vrfs, loopback_ip=loopback_ip
    )

    return result


def remove_obsolete_vrf(task: Task, obsolete_vrfs: list[str]) -> Result:
    commands = "\n".join([f"no vrf definition {vrf}" for vrf in obsolete_vrfs])
    if len(commands) > 0:
        return napalm_configure(task=task, configuration=commands, replace=False)


def create_missing_vrf(task: Task, missing_vrfs: list[str], loopback_ip: str) -> Result:
    if len(missing_vrfs) == 0:
        return
    service_data = task.host.get("global_service_data")
    commands = template_file(
        task=task,
        template="vrf_config.j2",
        path="templates/",
        missing_vrfs=missing_vrfs,
        service_data=service_data,
        loopback_ip=loopback_ip,
    ).result

    return napalm_configure(task=task, configuration=commands, replace=False)
