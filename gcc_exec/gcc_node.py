"""This file contains the GccNode class."""
# pylint: disable=C0301,R0914,W0612,R1721,R1702,W1514,R0912
import json
import os
import socket
import time
from io import StringIO
from typing import Any

import paramiko


class GccNode:
    """This class contains methods to configure and execute a node in a workflow."""

    __node_virtual_machine = None
    __node_level = None
    __node_id = None
    __node_dependents = None
    __node_dependencies = None
    __node_config = None
    __gcc_workflow_obj = None

    def __init__(self, node_id: str, gcc_workflow_obj: Any) -> None:
        """Constructor for a GccNode object."""
        self.__node_id = node_id
        self.__gcc_workflow_obj = gcc_workflow_obj

    def set_node_level(self, node_level: int) -> None:
        """This method sets the level of a node in a workflow plan."""
        self.__node_level = node_level

    def get_node_level(self) -> int:
        """This method returns a nodes level."""
        return self.__node_level

    def get_node_id(self) -> str:
        """This method returns a nodes id"""
        return self.__node_id

    def set_node_virtual_machine(self, node_virtual_machine: dict) -> None:
        """This methid sets a nodes virtual machine."""
        self.__node_virtual_machine = node_virtual_machine

    def get_node_virtual_machine(self) -> dict:
        """This methid returns a nodes virtual machine."""
        return self.__node_virtual_machine

    def initialize(self) -> None:
        """This method initializes a nodes virtual machine if needed."""
        security_group = self.__gcc_workflow_obj.get_gcc_security_group()
        key_pair = self.__gcc_workflow_obj.get_gcc_key_pair()
        retry_count = 0

        result = self.__gcc_workflow_obj.get_gcc_ec2_obj().create_instance(
            key_pair["KeyName"], security_group["GroupId"]
        )
        self.__node_virtual_machine = {
            "ip": None,
            "pem": key_pair["KeyMaterial"],
            "instance_id": result["Instances"][0]["InstanceId"],
        }

        instance = self.__gcc_workflow_obj.get_gcc_ec2_obj().get_instance_object(
            self.__node_virtual_machine["instance_id"]
        )
        instance.wait_until_running()

        while retry_count <= 20:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex((instance.public_ip_address, 22))
            if result == 0:
                if instance.public_ip_address is not None:
                    self.__node_virtual_machine["ip"] = instance.public_ip_address
                    break
            else:
                time.sleep(10)

    def set_config_commands(self) -> None:
        """Set the configuration commands for a specific node on it's virtual machine."""
        drbx_node_path = f"/{self.__gcc_workflow_obj.get_workflow_dict()['name']}/nodes/{self.__node_id}.zip"
        drbx_node_link = self.__gcc_workflow_obj.get_gcc_drbx_obj().get_file_link(
            drbx_node_path
        )

        self.__node_config = {
            "config_commands": [
                f"sudo rm -rf /home/ubuntu/{self.__node_id}",
                "sudo apt update -qq",
                "sudo apt update -qq",
                "sudo apt install unzip -y -qq",
                "sudo apt install python3-pip -y -qq",
                "pip3 install rpyc",
                "pip3 install dropbox",
                f"wget {drbx_node_link} -O {self.__node_id}.zip",
                f"unzip {self.__node_id}.zip -d /home/ubuntu",
            ],
            "receiving_ports": None,
            "receiving_args": None,
            "sending_args": None,
            "receiving_args_str": None,
            "sending_args_str": None,
            "dropbox_args_str": None,
        }

        if self.__gcc_workflow_obj.get_workflow_dict()["type"] == 1:
            port = 5001

            if self.__node_dependencies is not None:
                for node_dependency in self.__node_dependencies:
                    receiving_args_dict = {
                        "host": "0.0.0.0",
                        "port": port,
                        "outdir": "data/in",
                    }

                    if self.__node_config["receiving_args"] is None:
                        self.__node_config["receiving_args"] = [receiving_args_dict]
                    elif isinstance(self.__node_config["receiving_args"], list):
                        self.__node_config["receiving_args"].append(receiving_args_dict)

                    if self.__node_config["receiving_ports"] is None:
                        self.__node_config["receiving_ports"] = [port]
                    elif isinstance(self.__node_config["receiving_ports"], list):
                        self.__node_config["receiving_ports"].append(port)

                    port += 1

                    gcc_workflow_name = self.__gcc_workflow_obj.get_workflow_dict()[
                        "name"
                    ]
                    gcc_drbx_obj = self.__gcc_workflow_obj.get_gcc_drbx_obj()

                    for node_id in node_dependency:
                        if node_id is None:
                            for file in node_dependency[node_id]:
                                if file == "*":
                                    for __file__ in gcc_drbx_obj.list_files(
                                        f"/{self.__gcc_workflow_obj.get_workflow_dict()['name']}/data"
                                    ):
                                        self.__node_config["config_commands"].append(
                                            f"wget {gcc_drbx_obj.get_file_link(f'/{gcc_workflow_name}/data/{__file__}')} -O /home/ubuntu/{self.__node_id}/data/in/{__file__}"
                                        )
                                else:
                                    self.__node_config["config_commands"].append(
                                        f"wget {gcc_drbx_obj.get_file_link(f'/{gcc_workflow_name}/data/{file}')} -O /home/ubuntu/{self.__node_id}/data/in/{file}"
                                    )

            if self.__node_dependents is not None:
                for node_dependent in self.__node_dependents:
                    filedictlist = []

                    for node_id in node_dependent:
                        for file in node_dependent[node_id]:
                            filedict = {"filename": file, "filedir": "data/out"}
                            filedictlist.append(filedict)

                        sending_to_node = self.__gcc_workflow_obj.get_workflow_dict()[
                            "nodes"
                        ][node_id]

                        sending_args_dict = {
                            "host": sending_to_node.get_node_virtual_machine()["ip"],
                            "filedictlist": filedictlist,
                            "port": sending_to_node.get_node_config()[
                                "receiving_ports"
                            ].pop(),
                        }

                        if self.__node_config["sending_args"] is None:
                            self.__node_config["sending_args"] = [sending_args_dict]
                        elif isinstance(self.__node_config["sending_args"], list):
                            self.__node_config["sending_args"].append(sending_args_dict)

            if self.__node_config["sending_args"] is None:
                self.__node_config["sending_args_str"] = json.dumps(str([]))
            elif isinstance(self.__node_config["sending_args"], list):
                self.__node_config["sending_args_str"] = json.dumps(
                    str(self.__node_config["sending_args"])
                )

            if self.__node_config["receiving_args"] is None:
                self.__node_config["receiving_args_str"] = json.dumps(str([]))
            elif isinstance(self.__node_config["receiving_args"], list):
                self.__node_config["receiving_args_str"] = json.dumps(
                    str(self.__node_config["receiving_args"])
                )

        uda_dict = {
            "drbx_refresh_token": self.__gcc_workflow_obj.get_gcc_user_obj().get_oauth2_refresh_token(),
            "drbx_app_key": self.__gcc_workflow_obj.get_gcc_drbx_obj().get_drbx_app_key(),
            "drbx_app_secret": self.__gcc_workflow_obj.get_gcc_drbx_obj().get_drbx_app_secret(),
            "local_dir_path": "/data/out",
            "drbx_dir_path": f"/{self.__gcc_workflow_obj.get_workflow_dict()['name']}/exec/{self.__gcc_workflow_obj.get_exec_date_time()}/{self.__node_id}/data/out",
        }
        self.__node_config["dropbox_args_str"] = json.dumps(str(uda_dict))

        self.__node_config["config_commands"] += [
            f"cd {self.__node_id};pip3 install -r requirements.txt",
            "exit",
        ]

    def configure(self) -> None:
        """Execute configuration commands on a virtual machine."""
        keyfile = StringIO(self.__node_virtual_machine["pem"])
        mykey = paramiko.RSAKey.from_private_key(keyfile)
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.__node_virtual_machine["ip"], username="ubuntu", pkey=mykey)

        with open(
            f"{os.getcwd()}/tmp/{self.__gcc_workflow_obj.get_tmp_dir()}/{self.__node_id}_logs.txt",
            "w+",
        ) as log_file:
            for comm in self.__node_config["config_commands"]:
                stdin, stdout, stderr = client.exec_command(comm)

                log_file.write(f"\n[{comm}]\n")
                log_file.writelines([line for line in stdout])

        log_file.close()
        client.close()

    def execute(self) -> None:
        """Execute execution commands on a virtual machine."""
        exec_commands = []

        if self.__gcc_workflow_obj.get_workflow_dict()["type"] == 1:
            exec_commands += [
                f"cd {self.__node_id};chmod +x run.sh;./run.sh {self.__node_config['receiving_args_str']} {self.__node_config['sending_args_str']} {self.__node_config['dropbox_args_str']}",
                "exit",
            ]

        elif self.__gcc_workflow_obj.get_workflow_dict()["type"] == 0:
            gcc_workflow_name = self.__gcc_workflow_obj.get_workflow_dict()["name"]
            gcc_drbx_obj = self.__gcc_workflow_obj.get_gcc_drbx_obj()

            if self.__node_dependencies is not None:
                for node_dependency in self.__node_dependencies:
                    for node_id in node_dependency:
                        if node_id is not None:
                            for file in node_dependency[node_id]:
                                if file == "*":
                                    for __file__ in gcc_drbx_obj.list_files(
                                        f"/{gcc_workflow_name}/exec/{self.__gcc_workflow_obj.get_exec_date_time()}/{node_id}/data/out"
                                    ):
                                        exec_commands.append(
                                            f"wget {gcc_drbx_obj.get_file_link(f'/{gcc_workflow_name}/exec/{self.__gcc_workflow_obj.get_exec_date_time()}/{node_id}/data/out/{__file__}')} -O /home/ubuntu/{self.__node_id}/data/in/{__file__}"
                                        )
                                else:
                                    exec_commands.append(
                                        f"wget {gcc_drbx_obj.get_file_link(f'/{gcc_workflow_name}/exec/{self.__gcc_workflow_obj.get_exec_date_time()}/{node_id}/data/out/{file}')} -O /home/ubuntu/{self.__node_id}/data/in/{file}"
                                    )
                        else:
                            for file in node_dependency[node_id]:
                                if file == "*":
                                    for __file__ in gcc_drbx_obj.list_files(
                                        f"/{gcc_workflow_name}/data"
                                    ):
                                        exec_commands.append(
                                            f"wget {gcc_drbx_obj.get_file_link(f'/{gcc_workflow_name}/data/{__file__}')} -O /home/ubuntu/{self.__node_id}/data/in/{__file__}"
                                        )
                                else:
                                    exec_commands.append(
                                        f"wget {gcc_drbx_obj.get_file_link(f'/{gcc_workflow_name}/data/{file}')} -O /home/ubuntu/{self.__node_id}/data/in/{file}"
                                    )

            exec_commands += [
                f"cd {self.__node_id};chmod +x run.sh;./run.sh {self.__node_config['dropbox_args_str']}",
                "exit",
            ]

        keyfile = StringIO(self.__node_virtual_machine["pem"])
        mykey = paramiko.RSAKey.from_private_key(keyfile)
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.__node_virtual_machine["ip"], username="ubuntu", pkey=mykey)

        with open(
            f"{os.getcwd()}/tmp/{self.__gcc_workflow_obj.get_tmp_dir()}/{self.__node_id}_logs.txt",
            "a+",
        ) as log_file:
            for comm in exec_commands:
                stdin, stdout, stderr = client.exec_command(comm)

                log_file.write(f"\n[{comm}]\n\n")
                log_file.writelines([line for line in stdout])

        log_file.close()
        client.close()

        self.__gcc_workflow_obj.get_gcc_drbx_obj().upload_file(
            f"{os.getcwd()}/tmp/{self.__gcc_workflow_obj.get_tmp_dir()}/{self.__node_id}_logs.txt",
            f"/{self.__gcc_workflow_obj.get_workflow_dict()['name']}/exec/{self.__gcc_workflow_obj.get_exec_date_time()}/{self.__node_id}/{self.__node_id}_logs.txt",
        )

    def terminate(self) -> None:
        """Terminate the virtual machine associated with a node if needed."""
        if self.__node_virtual_machine["instance_id"] is not None:
            self.__gcc_workflow_obj.get_gcc_ec2_obj().terminate_instance(
                self.__node_virtual_machine["instance_id"]
            )

    def set_node_dependencies(self, node_dependencies: list) -> None:
        """Set node dependencies."""
        self.__node_dependencies = node_dependencies

    def get_node_dependencies(self) -> list:
        """Get node dependencies."""
        return self.__node_dependencies

    def set_node_dependents(self, node_dependents: list) -> None:
        """Set node dependents."""
        self.__node_dependents = node_dependents

    def get_node_dependents(self) -> list:
        """Get node dependents."""
        return self.__node_dependents

    def get_node_config(self) -> dict:
        """Get node configuration."""
        return self.__node_config
