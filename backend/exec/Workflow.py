import random
import shutil
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime

import xmltodict
from botocore.exceptions import ClientError
from xmltodict import OrderedDict

from . import Drbx, Ec2, Node, User


class Workflow:
    def __init__(self, user: User, workflow_name: str, temp_dir: str):
        self.user = user
        self.workflow_name = workflow_name
        self.temp_dir = temp_dir
        self.ec2 = Ec2.Ec2(user.aws_access_key_id, user.aws_secret_access_key)
        self.drbx = Drbx.Drbx(
            user.drbx_refresh_token, user.drbx_app_key, user.drbx_app_secret
        )
        self.nodes = []
        self.nodes_dict = {}
        self.security_group = None
        self.key_pair = None
        self.exec_date_time = None
        self.gcc_vms = 0
        self.type = 0

        self.time_to_init = 0
        self.time_to_config = 0
        self.time_to_execute = 0

    def plan(self, available_machines):
        used_machines = []
        workflow_dict = xmltodict.parse(
            self.drbx.get_file_contents(f"/{self.workflow_name}/spec.xml")
        )
        plan = {}

        try:
            self.type = int(workflow_dict["workflow"]["@type"])
        except KeyError:
            pass
        for x in workflow_dict["workflow"]["task"]:
            try:
                __node_dependencies__ = x["dep"]
            except KeyError:
                __node_dependencies__ = None
            try:
                __node_vm__ = x["vm"]
            except KeyError:
                __node_vm__ = None
            node_dependencies = {}
            node_id = x["@id"]
            if __node_dependencies__ is not None:
                if type(__node_dependencies__) == str:
                    node_dependencies[None] = __node_dependencies__
                elif type(__node_dependencies__) == OrderedDict:
                    node_dependencies[
                        __node_dependencies__["@node"]
                    ] = __node_dependencies__["#text"]
                elif type(__node_dependencies__) == list:
                    for y in __node_dependencies__:
                        if type(y) == str:
                            node_dependencies[None] = y
                        elif type(y) == OrderedDict:
                            node_dependencies[dict(y)["@node"]] = dict(y)["#text"]
                elif __node_dependencies__ is None:
                    node_dependencies = None
            node = Node.Node(self, node_id, node_dependencies)
            if __node_vm__ is not None:
                if __node_vm__["@pem"] is not None:
                    node.pem = self.drbx.get_file_contents(
                        f"/{self.workflow_name}/pem/{__node_vm__['@pem']}"
                    ).strip("\n")
                if __node_vm__["#text"] is not None:
                    node.ip = __node_vm__["#text"]
                node.gcc_vm = False
            elif len(available_machines) > 0:
                machine = available_machines[len(available_machines) - 1]
                if machine.pem is not None:
                    node.pem = machine.pem.strip("\n")
                if machine.ip is not None:
                    node.ip = machine.ip
                used_machines.append(available_machines.pop())
                node.gcc_vm = False
            else:
                self.gcc_vms += 1

            self.nodes.append(node)
            self.nodes_dict[node.node_id] = node

        done_ct = 0

        while done_ct < len(self.nodes):
            done_ct = 0
            for node in self.nodes:
                if node.level == 0:
                    __max__ = 0
                    if len(node.node_dependencies.keys()) > 0:
                        for dependency in node.node_dependencies.keys():
                            if dependency is not None:
                                dep = [
                                    d for d in self.nodes if d.node_id == dependency
                                ][0]
                                if dep.level > __max__:
                                    __max__ = dep.level + 1
                            else:
                                if 1 > __max__:
                                    __max__ = 1
                    else:
                        if 1 > __max__:
                            __max__ = 1

                    try:
                        plan[__max__].append(node)
                    except KeyError:
                        plan[__max__] = [node]
                    node.level = __max__
                else:
                    done_ct += 1

        for lev in plan:
            for node in plan[lev]:
                for dep in node.node_dependencies:
                    if dep is not None:
                        self.nodes_dict[dep].node_dependents[
                            node.node_id
                        ] = node.node_dependencies[dep]

        return plan, used_machines

    def initialize(self):
        self.exec_date_time = datetime.now().strftime("%m:%d:%Y-%H:%M:%S")
        self.drbx.create_folder(f"/{self.workflow_name}/exec/{self.exec_date_time}")

        if self.gcc_vms > 0:
            self.security_group = self.ec2.create_security_group(gen_string())
            self.key_pair = self.ec2.create_key_pair(gen_string())

        with ThreadPoolExecutor(max_workers=len(self.nodes)) as executor:
            for node in self.nodes:
                executor.submit(node.initialize)
            executor.shutdown()

    def configure(self, plan):
        if self.type == 0:
            with ThreadPoolExecutor(max_workers=len(self.nodes)) as executor:
                for node in self.nodes:
                    executor.submit(node.set_configure_commands)
                executor.shutdown()

        elif self.type == 1:
            plan = dict(reversed(list(plan.items())))

            for level in plan:
                with ThreadPoolExecutor(max_workers=len(plan[level])) as executor:
                    for node in plan[level]:
                        executor.submit(node.set_configure_commands)
                    executor.shutdown()

        with ThreadPoolExecutor(max_workers=len(self.nodes)) as executor:
            for node in self.nodes:
                executor.submit(node.configure)
            executor.shutdown()

    def execute(self, plan: dict):
        if self.type == 0:
            for level in plan:
                with ThreadPoolExecutor(max_workers=len(plan[level])) as executor:
                    for node in plan[level]:
                        executor.submit(node.execute)
                    executor.shutdown()

        if self.type == 1:
            plan = dict(reversed(list(plan.items())))
            threads = []
            for level in plan:
                for node in plan[level]:
                    t = threading.Thread(target=node.execute)
                    threads.append(t)
                    t.start()
                time.sleep(5)
            for t in threads:
                t.join()

    def complete(self):
        self.drbx.upload_file(
            f"/home/ubuntu/gcc/gcc_web/tmp/{self.temp_dir}/stats.txt",
            f"/{self.workflow_name}/exec/{self.exec_date_time}/stats.txt",
        )
        shutil.rmtree(f"/home/ubuntu/gcc/gcc_web/tmp/{self.temp_dir}")

        with ThreadPoolExecutor(max_workers=len(self.nodes)) as executor:
            for node in self.nodes:
                executor.submit(node.terminate)
            executor.shutdown()

        if self.key_pair is not None:
            self.ec2.delete_key_pair(self.key_pair["KeyName"])
        if self.security_group is not None:
            while True:
                try:
                    self.ec2.delete_security_group(self.security_group["GroupId"])
                    break
                except ClientError:
                    time.sleep(10)


def gen_string():
    choices = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-"
    return "".join([random.choice(choices) for _ in range(7)])
