# Nornir L3-VPN Service Deployment

## Description

At the OST Eastern Switzerland University of Applied Sciences as part of the Network Automation course we were given the task to fully automate the deployment of L3-VPN services declaratively defined in a YAML file on a given service provider network topology using Nornir.

Given the service definition the Nornir

- Create dedicated VRF for each service
- Remove VRFs for services which are not required anymore
- Configure the BGP L3-VPN address family for each service VRF
- Configure interfaces for both single and multi homed routers
- Configure HSRP
- Remove all services in case an empty service definition is given (requires user confirmation)

## Visuals

Link to demonstration video: [https://www.youtube.com/watch?v=GxoJ0eT5u1c](https://www.youtube.com/watch?v=GxoJ0eT5u1c)

## Installation

To run the ansible playbook setup_customer_service.yaml the following dependencies need to be installed using pip.

- nornir
- nornir_napalm
- nornir_utils
- nornir_rich
- nornir_jinja2
- ipaddress

To not messup with your python installation on your host system consider creating a dedicated virtual environment using the command:

```sh
python3 -m venv venv
```

And activate the virtual environment using the command:

```sh
source venv/bin/activate
```

Now install the requirements using pip.
As the requirements are listed in the requirements.txt file you may install the dependencies with the command:

```sh
pip install -r requirements.txt
```

## Configuration

The required configuration to run the automation tasks specified in this project are related to the inventory.

### Defaults

In the _defaults.yaml_ file the following variables need to be specified.

- **service_file:** Path to yaml file containing the service defintions
- **bgp_asn:** BGP autonomous system number of the iBGP domain in the service porvider network
- **system_vrfs:** The VRFs present on the system and which should not be touched by any automation steps
- **primary_loopback:**S Interface used to establish iBGP peerings

### Hosts

Specify your hosts in the _hosts.yaml_ file.
A sample host definition may look like the following.

```yaml
edge-01.lab:
  hostname: 10.8.34.3
  groups:
    - cisco
    - site-A
  data:
    hsrp:
      vip_offset: 1
      priority: 10
```

The values specified for hsrp are only required for multihomed devices.

- **vip_offset:** Specifies the offset to the HSRP virtual IP address of the IP address to be configured on the target interface (e.g. VIP: 192.168.1.1 and Offset: 3 => IP: 192.168.1.4). **Two routers at the same multihomed site are not allowed to specifiy the same offset otherwise there will be an IP address conflict.**
- **priority:** Specifies the HSRP priority of the host. **Two routers at the same multihomed site should specify distinct priorities otherwise the active standby election is based on the physical address of the devices.**

### Groups

There are two types of groups.
The **cisco** group is used to specify information applicable on all cisco routers such as the username, platform and connection plugin specific parameters.
The other groups are **site-specific** and are used to indicate whether a site is multi-homed or single homed.

### Connection Plugin

As connection Plugin napalm is used and the configuration is part of the **cisco** group.
The napalm connection plugin uses netmiko as backend to connect to the devices via SSH.
The netmiko backend can be configured by the specification of values under **extras/optional_args**.

The following parameters are set:

- Unsupported ciphers are disabled
- The path to the SSH private key is specified
- The path to the SSH config file is specified
- The boolean flag is set to use SSH key authentication

```yaml
cisco:
  username: cisco
  platform: ios
  connection_options:
    napalm:
      extras:
        optional_args:
          disabled_algorithms: { "pubkeys": ["rsa-sha2-256","rsa-sha2-512"]}
          key_file: /home/boss/.ssh/id_rsa
          ssh_config_file: /home/boss/.ssh/config
          use_keys: True
```

### SSH Client

On the SSH client generate an SSH private key.

```sh
ssh-keygen -t rsa -b 2048
```

Add **Host** entry to SSH config file.
In this case the IP address is used to connect to the network devices so a wildcard IP address is used to match the destination addresses.

```
Host 10.8.*
    User cisco
    PubkeyAcceptedKeyTypes=+ssh-rsa
    HostKeyAlgorithms=+ssh-rsa
    IdentityFile /home/boss/.ssh/id_rsa
```

### SSH Server

Each cisco router needs to be configured as SSH server using the same parameters to accept connections from the netmiko plugin triggered by napalm.

Use the following command to display the public key with a line length of maximum 72 characters.

```sh
fold -b -w 72 /path/to/ssh/public/key
```

Run the commands below on all target cisco routers.

```
ip ssh version 2
ip ssh pubkey-chain
  username cisco
   key-string
ssh-rsa <output of the fold command>

ip ssh server algorithm authentication publickey
no ip ssh server algorithm authentication password
no ip ssh server algorithm authentication keyboard
```

## Usage

```
Usage: main.py [OPTIONS]                                                                                                                                                              
                                                                                                                                                                                       
╭─ Options ───────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --dry-run    --no-dry-run      [default: dry-run]                                                                                                                                   │
│ --verbose    --no-verbose      [default: no-verbose]                                                                                                                                │
│ --help                         Show this message and exit.                                                                                                                          │
╰─────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

In order to configure L3-VPN services with the automation tool provided in this project please first make sure that you defined the services in the corresponding yaml file.

### Specify services

Services can be specified in the following format:

```yaml
services:
  - name: "CustA"
    id: 10
    description: "Customer A"
    route_import:
      - "10:0"
    route_export:
      - "10:0"
    sites:
        site-A:
            interfaces:
            - name: "GigabitEthernet4.10"
              ip: "192.168.1.1 255.255.255.0"
        site-B:
            interfaces:
            - name: "GigabitEthernet4"
              ip: "192.168.2.1 255.255.255.0"
```

By default the services defintion is loaded from the file services.yaml located in the root directory of this project.

The location of the file can be specified in the defaults using the service_file variable.

### Run Nornir Application

The Nornir application can be executed using:

```bash
python3 l3_vpn/main.py --no-dry-run
```

## Important Datastructures

The datastructure below maps customer VRF names to static/global service information.

```python
{
    "CustA": {
        "id": 10,
        "description": "Customer A",
        "route_import": ["10:0"],
        "route_export": ["10:0"],
    },
    "CustB": {
        "id": 20,
        "description": "Customer B",
        "route_import": ["20:0"],
        "route_export": ["20:0"],
    },
}
```

The datastructure below maps customer VRF names to dynamic/host specific service information.
Currently it is just the required interface configuration.
The example below is the configuration for routers located at site-A for both services CustA and CustB.

```python
{
    "CustA": {
        "interfaces": [
            {"name": "GigabitEthernet4.10", "ip": "192.168.1.1 255.255.255.0"}
        ]
    },
    "CustB": {
        "interfaces": [
            {"name": "GigabitEthernet4.20", "ip": "192.168.21.2 255.255.255.0"}
        ]
    },
}
```

## Project status

There will be no further development work on this project after the submission deadline on 19th of April 2024.
