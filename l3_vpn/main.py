import helpers as hlp
import typer
import logging
from nornir import InitNornir
from nornir.core.task import Task, Result
from nornir_rich.progress_bar import RichProgressBar
from nornir_rich.functions import print_result
from tasks import vrf, bgp, interface


def configure_l3_customer_service(task: Task) -> Result:
    site = hlp.get_site_group_name(task.host.groups)
    task.host.data["host_service_data"] = hlp.get_host_service_data(
        task.host.defaults.data.get("service_file"), site
    )
    task.run(task=vrf.configure_vrf)
    task.run(task=bgp.configure_bgp_address_family)
    task.run(task=interface.configure_interfaces)
    return task.results


def main(dry_run: bool = True, verbose: bool = False):
    nr = InitNornir(config_file="config.yaml", dry_run=dry_run)
    nr.inventory.defaults.data["global_service_data"] = hlp.get_global_service_data(
        nr.inventory.defaults.data.get("service_file")
    )

    if nr.inventory.defaults.data["global_service_data"] == {}:
        answer = input(
            "Please confirm that all L3 VPN services shall be removed [Yes/No]:"
        )
        if answer.lower() in ["y", "yes"]:
            pass
        else:
            return

    nr_with_processors = nr.with_processors([RichProgressBar()])
    result = nr_with_processors.run(task=configure_l3_customer_service)

    log_level = logging.INFO if verbose else logging.ERROR
    print_result(
        result,
        vars=["result", "failed", "diff", "changed", "severity_level"],
        severity_level=log_level,
    )


if __name__ == "__main__":
    typer.run(main)
