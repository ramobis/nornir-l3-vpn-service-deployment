import helpers as hlp

from nornir.core.task import Task, Result
from nornir_napalm.plugins.tasks import napalm_configure
from nornir_jinja2.plugins.tasks import template_file


def configure_bgp_address_family(task: Task) -> Result:
    services = list(task.host.data["host_service_data"].keys())

    if len(services) == 0:
        return

    commands = template_file(
        task=task,
        template="bgp_config.j2",
        path="templates/",
        asn=task.host.defaults.data.get("bgp_asn"),
        services=services,
    ).result

    return napalm_configure(task=task, configuration=commands, replace=False)
