import json
import os
import socket
import time
from io import StringIO

import paramiko as paramiko

from . import Workflow


class Node:
    def __init__(self, workflow: Workflow, node_id: str, node_dependencies: dict):
        self.workflow = workflow
        self.node_id = node_id
        self.node_dependencies = node_dependencies
        self.gcc_vm = True
        self.ip = None
        self.pem = None
        self.level = 0
        self.node_dependents = {}
        self.receiving_ports = []
        self.sending_ports = []
        self.ins_id = None
        self.rae = None
        self.sae = None
        self.uda = None
        self.configure_commands = []

    def initialize(self):
        security_group = self.workflow.security_group
        key_pair = self.workflow.key_pair
        retry_count = 0

        if self.gcc_vm:
            result = self.workflow.ec2.create_instance(
                key_pair["KeyName"], security_group["GroupId"]
            )
            self.ins_id = result["Instances"][0]["InstanceId"]

            ins = self.workflow.ec2.ec2_resource.Instance(id=self.ins_id)
            ins.wait_until_running()

            while retry_count <= 20:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((ins.public_ip_address, 22))
                if result == 0:
                    if ins.public_ip_address is not None:
                        self.ip = ins.public_ip_address
                        break
                else:
                    time.sleep(10)
        else:
            while retry_count <= 20:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex((self.ip, 22))
                if result == 0:
                    break
                else:
                    time.sleep(10)

    def set_configure_commands(self):
        if self.workflow.type == 0:
            self.configure_commands += [
                f"sudo rm -rf /home/ubuntu/{self.node_id}",
                "sudo apt update -qq",
                "sudo apt update -qq",
                "sudo apt install unzip -y -qq",
                "sudo apt install python3-pip -y -qq",
                "pip3 install rpyc",
                "pip3 install dropbox",
                f"wget {self.workflow.drbx.get_file_link(f'/{self.workflow.workflow_name}/nodes/{self.node_id}.zip')} -O {self.node_id}.zip",
                f"unzip {self.node_id}.zip -d /home/ubuntu",
            ]

        elif self.workflow.type == 1:
            self.configure_commands += [
                f"sudo rm -rf /home/ubuntu/{self.node_id}",
                "sudo apt update -qq",
                "sudo apt update -qq",
                "sudo apt install unzip -y -qq",
                "sudo apt install python3-pip -y -qq",
                "pip3 install rpyc",
                "pip3 install dropbox",
                f"wget {self.workflow.drbx.get_file_link(f'/{self.workflow.workflow_name}/nodes/{self.node_id}.zip')} -O {self.node_id}.zip",
                f"unzip {self.node_id}.zip -d /home/ubuntu",
            ]

            port = 5001
            receiving_args = []
            sending_args = []

            if self.node_dependencies is not None:
                for node in self.node_dependencies:
                    receiving_args_dict = {}
                    if node is not None:
                        receiving_args_dict["host"] = "0.0.0.0"
                        receiving_args_dict["port"] = port
                        receiving_args_dict["outdir"] = "data/in"
                        receiving_args.append(receiving_args_dict)
                        self.receiving_ports.append(port)
                        port += 1
                    else:
                        for file in self.node_dependencies[node].split(","):
                            if file == "*":
                                for __file__ in self.workflow.drbx.list_files(
                                    f"/{self.workflow.workflow_name}/data"
                                ):
                                    self.configure_commands.append(
                                        f"wget {self.workflow.drbx.get_file_link(f'/{self.workflow.workflow_name}/data/{__file__}')} -O /home/ubuntu/{self.node_id}/data/in/{__file__}"
                                    )
                            else:
                                self.configure_commands.append(
                                    f"wget {self.workflow.drbx.get_file_link(f'/{self.workflow.workflow_name}/data/{file}')} -O /home/ubuntu/{self.node_id}/data/in/{file}"
                                )

                for node in self.node_dependents:
                    sending_args_dict = {}
                    if node is not None:
                        filedictlist = []
                        for file in self.node_dependents[node].split(","):
                            filedict = {"filename": file, "filedir": "data/out"}
                            filedictlist.append(filedict)

                        sending_args_dict["host"] = self.workflow.nodes_dict[node].ip
                        sending_args_dict["filedictlist"] = filedictlist
                        sending_args_dict["port"] = self.workflow.nodes_dict[
                            node
                        ].receiving_ports.pop()
                        sending_args.append(sending_args_dict)

            self.rae = json.dumps(str(receiving_args))
            self.sae = json.dumps(str(sending_args))

        uda_dict = {
            "drbx_refresh_token": self.workflow.user.drbx_refresh_token,
            "drbx_app_key": self.workflow.user.drbx_app_key,
            "drbx_app_secret": self.workflow.user.drbx_app_secret,
            "local_dir_path": "/data/out",
            "drbx_dir_path": f"/{self.workflow.workflow_name}/exec/{self.workflow.exec_date_time}/{self.node_id}/data/out",
        }
        self.uda = json.dumps(str(uda_dict))

        self.configure_commands += [
            f"cd {self.node_id};pip3 install -r requirements.txt",
            "exit",
        ]

    def configure(self):
        key_pair = self.workflow.key_pair

        if self.pem is None:
            self.pem = key_pair["KeyMaterial"]

        keyfile = StringIO(self.pem)
        mykey = paramiko.RSAKey.from_private_key(keyfile)
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.ip, username="ubuntu", pkey=mykey)

        log_file = open(
            f"{os.getcwd()}/tmp/{self.workflow.temp_dir}/{self.node_id}_logs.txt",
            "w+",
        )

        for comm in self.configure_commands:
            stdin, stdout, stderr = client.exec_command(comm)
            log_file.write(f"\n[{comm}]\n")
            log_file.writelines([line for line in stdout])

        log_file.close()
        client.close()

    def execute(self):
        key_pair = self.workflow.key_pair
        commands = []

        if self.workflow.type == 0:
            if self.node_dependencies is not None:
                for node in self.node_dependencies:
                    for file in self.node_dependencies[node].split(","):
                        if node is not None:
                            if file == "*":
                                for __file__ in self.workflow.drbx.list_files(
                                    f"/{self.workflow.workflow_name}/exec/{self.workflow.exec_date_time}/{node}/data/out"
                                ):
                                    commands.append(
                                        f"wget {self.workflow.drbx.get_file_link(f'/{self.workflow.workflow_name}/exec/{self.workflow.exec_date_time}/{node}/data/out/{__file__}')} -O /home/ubuntu/{self.node_id}/data/in/{__file__}"
                                    )
                            else:
                                commands.append(
                                    f"wget {self.workflow.drbx.get_file_link(f'/{self.workflow.workflow_name}/exec/{self.workflow.exec_date_time}/{node}/data/out/{file}')} -O /home/ubuntu/{self.node_id}/data/in/{file}"
                                )
                        else:
                            if file == "*":
                                for __file__ in self.workflow.drbx.list_files(
                                    f"/{self.workflow.workflow_name}/data"
                                ):
                                    commands.append(
                                        f"wget {self.workflow.drbx.get_file_link(f'/{self.workflow.workflow_name}/data/{__file__}')} -O /home/ubuntu/{self.node_id}/data/in/{__file__}"
                                    )
                            else:
                                commands.append(
                                    f"wget {self.workflow.drbx.get_file_link(f'/{self.workflow.workflow_name}/data/{file}')} -O /home/ubuntu/{self.node_id}/data/in/{file}"
                                )

            commands += [
                f"cd {self.node_id};chmod +x run.sh;./run.sh {self.uda}",
                "exit",
            ]

        elif self.workflow.type == 1:
            commands += [
                f"cd {self.node_id};chmod +x run.sh;./run.sh {self.rae} {self.sae} {self.uda}",
                "exit",
            ]

        if self.pem is None:
            self.pem = key_pair["KeyMaterial"]

        keyfile = StringIO(self.pem)
        mykey = paramiko.RSAKey.from_private_key(keyfile)
        client = paramiko.SSHClient()
        client.load_system_host_keys()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(self.ip, username="ubuntu", pkey=mykey)

        log_file = open(
            f"{os.getcwd()}/tmp/{self.workflow.temp_dir}/{self.node_id}_logs.txt",
            "a+",
        )

        for comm in commands:
            stdin, stdout, stderr = client.exec_command(comm)
            log_file.write(f"\n[{comm}]\n")
            log_file.writelines([line for line in stdout])

        log_file.close()
        client.close()

        self.workflow.drbx.upload_file(
            f"{os.getcwd()}/tmp/{self.workflow.temp_dir}/{self.node_id}_logs.txt",
            f"/{self.workflow.workflow_name}/exec/{self.workflow.exec_date_time}/{self.node_id}/{self.node_id}_logs.txt",
        )

    def terminate(self):
        if self.gcc_vm:
            if self.ins_id is not None:
                self.workflow.ec2.terminate_instance(self.ins_id)
