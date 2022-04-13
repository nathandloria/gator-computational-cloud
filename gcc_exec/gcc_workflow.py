"""This file contains the GccWorkflow class."""
# pylint: disable=R0914,R0912,R0915,R0902,E0401,R1702
import os
import random
import shutil
import threading
import time
from concurrent.futures.thread import ThreadPoolExecutor
from datetime import datetime
from typing import OrderedDict

import xmltodict
from botocore.exceptions import ClientError
from gcc_drbx import GccDrbx
from gcc_ec2 import GccEc2
from gcc_node import GccNode
from gcc_user import GccUser


class GccWorkflow:
    """This class contains methods to manage a GCC workflow."""

    __workflow_dict = None
    __gcc_user_obj = None
    __gcc_ec2_obj = None
    __gcc_drbx_obj = None
    __gcc_security_group = None
    __gcc_key_pair = None
    __exec_date_time = None
    __tmp_dir = None

    def __init__(self, gcc_user_obj: GccUser, workflow_name: str) -> None:
        """Constructor for a GccWorkflow object."""
        self.__gcc_user_obj = gcc_user_obj
        self.__gcc_ec2_obj = GccEc2(
            self.__gcc_user_obj.get_aws_access_key_id(),
            self.__gcc_user_obj.get_aws_secret_access_key(),
        )
        self.__gcc_drbx_obj = GccDrbx(self.__gcc_user_obj.get_oauth2_refresh_token())
        self.__workflow_dict = {
            "type": 0,
            "plan_raw": {},
            "plan_human_readable": {},
            "nodes": {},
            "name": workflow_name,
            "machines_initialized": None,
        }

    def plan(
        self, available_machines: list = [], xml_specification: str = None
    ) -> list:
        """This method creates an execution plan based on a workflow specification."""
        if xml_specification is None:
            xml_specification = xmltodict.parse(
                self.__gcc_drbx_obj.get_file_contents(
                    f"/{self.__workflow_dict['name']}/spec.xml"
                )
            )

        self.__workflow_dict["type"] = int(xml_specification["workflow"]["@type"])

        used_machines = []
        for node in xml_specification["workflow"]["task"]:
            gcc_node_object = GccNode(node["@id"], self)

            try:
                gcc_node_vm = node["vm"]
            except KeyError:
                gcc_node_vm = None

            node_virtual_machine = None

            if gcc_node_vm is not None:
                vm_ip = gcc_node_vm["#text"]

                try:
                    vm_pem = self.__gcc_drbx_obj.get_file_contents(
                        f"/{self.__workflow_dict['name']}/pem/{gcc_node_vm['@pem']}"
                    ).strip("\n")
                except KeyError:
                    vm_pem = None

                node_virtual_machine = {"ip": vm_ip, "pem": vm_pem, "instance_id": None}

                gcc_node_object.set_node_virtual_machine(node_virtual_machine)

            elif len(available_machines) > 0:
                available_machine = available_machines.pop()

                node_virtual_machine = {
                    "ip": available_machine.machine_ip,
                    "pem": available_machine.machine_pem.strip("\n"),
                    "instance_id": None,
                }

                used_machines.append(available_machine)
                gcc_node_object.set_node_virtual_machine(node_virtual_machine)

            try:
                gcc_node_deps = node["dep"]
            except KeyError:
                gcc_node_deps = None

            if gcc_node_deps is not None:
                if isinstance(gcc_node_deps, str):
                    node_dependencies = gcc_node_object.get_node_dependencies()
                    node_dependency_dict = {None: gcc_node_deps.split(",")}

                    if node_dependencies is None:
                        gcc_node_object.set_node_dependencies([node_dependency_dict])
                    elif isinstance(node_dependencies, list):
                        node_dependencies.append(node_dependency_dict)
                        gcc_node_object.set_node_dependencies(node_dependencies)

                    gcc_node_object.set_node_level(0)

                    try:
                        self.__workflow_dict["plan_raw"][0].append(gcc_node_object)
                        self.__workflow_dict["plan_human_readable"][0].append(
                            gcc_node_object.get_node_id()
                        )
                    except KeyError:
                        self.__workflow_dict["plan_raw"][0] = [gcc_node_object]
                        self.__workflow_dict["plan_human_readable"][0] = [
                            gcc_node_object.get_node_id()
                        ]

                if isinstance(gcc_node_deps, OrderedDict):
                    try:
                        gcc_dep_node_id = gcc_node_deps["@node"]
                    except KeyError:
                        gcc_dep_node_id = None

                    try:
                        gcc_dep_file_dependencies = gcc_node_deps["#text"].split(",")
                    except KeyError:
                        gcc_dep_file_dependencies = None

                    if gcc_dep_node_id is not None:
                        node_dependencies = gcc_node_object.get_node_dependencies()
                        node_dependency_dict = {
                            gcc_dep_node_id: gcc_dep_file_dependencies,
                        }
                        node_dependents = self.__workflow_dict["nodes"][
                            gcc_dep_node_id
                        ].get_node_dependents()
                        node_dependents_dict = {
                            gcc_node_object.get_node_id(): gcc_dep_file_dependencies
                        }

                        if node_dependencies is None:
                            gcc_node_object.set_node_dependencies(
                                [node_dependency_dict]
                            )
                        elif isinstance(node_dependencies, list):
                            node_dependencies.append(node_dependency_dict)
                            gcc_node_object.set_node_dependencies(node_dependencies)

                        if node_dependents is None:
                            self.__workflow_dict["nodes"][
                                gcc_dep_node_id
                            ].set_node_dependents([node_dependents_dict])
                        elif isinstance(node_dependents, list):
                            node_dependents.append(node_dependents_dict)
                            self.__workflow_dict["nodes"][
                                gcc_dep_node_id
                            ].set_node_dependents(node_dependents)

                    try:
                        level = (
                            self.__workflow_dict["nodes"][
                                gcc_dep_node_id
                            ].get_node_level()
                            + 1
                        )
                    except TypeError:
                        level = 0

                    gcc_node_object.set_node_level(level)

                    try:
                        self.__workflow_dict["plan_raw"][level].append(gcc_node_object)
                        self.__workflow_dict["plan_human_readable"][level].append(
                            gcc_node_object.get_node_id()
                        )
                    except KeyError:
                        self.__workflow_dict["plan_raw"][level] = [gcc_node_object]
                        self.__workflow_dict["plan_human_readable"][level] = [
                            gcc_node_object.get_node_id()
                        ]

                elif isinstance(gcc_node_deps, list):
                    max_level = 0

                    for dep in gcc_node_deps:
                        if isinstance(dep, str):
                            node_dependencies = gcc_node_object.get_node_dependencies()
                            node_dependency_dict = {None: dep.split(",")}

                            if node_dependencies is None:
                                gcc_node_object.set_node_dependencies(
                                    [node_dependency_dict]
                                )
                            elif isinstance(node_dependencies, list):
                                node_dependencies.append(node_dependency_dict)
                                gcc_node_object.set_node_dependencies(node_dependencies)

                            level = 0

                            if gcc_node_object.get_node_level() is None:
                                gcc_node_object.set_node_level(0)

                        elif isinstance(dep, OrderedDict):
                            try:
                                gcc_dep_node_id = dep["@node"]
                            except KeyError:
                                gcc_dep_node_id = None

                            try:
                                gcc_dep_file_dependencies = dep["#text"].split(",")
                            except KeyError:
                                gcc_dep_file_dependencies = None

                            if gcc_dep_node_id is not None:
                                node_dependencies = (
                                    gcc_node_object.get_node_dependencies()
                                )
                                node_dependency_dict = {
                                    gcc_dep_node_id: gcc_dep_file_dependencies,
                                }
                                node_dependents = self.__workflow_dict["nodes"][
                                    gcc_dep_node_id
                                ].get_node_dependents()
                                node_dependents_dict = {
                                    gcc_node_object.get_node_id(): gcc_dep_file_dependencies
                                }

                                if node_dependencies is None:
                                    gcc_node_object.set_node_dependencies(
                                        [node_dependency_dict]
                                    )
                                elif isinstance(node_dependencies, list):
                                    node_dependencies.append(node_dependency_dict)
                                    gcc_node_object.set_node_dependencies(
                                        node_dependencies
                                    )

                                if node_dependents is None:
                                    self.__workflow_dict["nodes"][
                                        gcc_dep_node_id
                                    ].set_node_dependents([node_dependents_dict])
                                elif isinstance(node_dependents, list):
                                    node_dependents.append(node_dependents_dict)
                                    self.__workflow_dict["nodes"][
                                        gcc_dep_node_id
                                    ].set_node_dependents(node_dependents)

                            try:
                                level = (
                                    self.__workflow_dict["nodes"][
                                        gcc_dep_node_id
                                    ].get_node_level()
                                    + 1
                                )
                            except TypeError:
                                level = 0

                            if level > max_level:
                                max_level = level

                    gcc_node_object.set_node_level(max_level)

                    try:
                        self.__workflow_dict["plan_raw"][max_level].append(
                            gcc_node_object
                        )
                        self.__workflow_dict["plan_human_readable"][max_level].append(
                            gcc_node_object.get_node_id()
                        )
                    except KeyError:
                        self.__workflow_dict["plan_raw"][max_level] = [gcc_node_object]
                        self.__workflow_dict["plan_human_readable"][max_level] = [
                            gcc_node_object.get_node_id()
                        ]

            else:
                gcc_node_object.set_node_level(0)

                try:
                    self.__workflow_dict["plan_raw"][0].append(gcc_node_object)
                    self.__workflow_dict["plan_human_readable"][0].append(
                        gcc_node_object.get_node_id()
                    )
                except KeyError:
                    self.__workflow_dict["plan_raw"][0] = [gcc_node_object]
                    self.__workflow_dict["plan_human_readable"][0] = [
                        gcc_node_object.get_node_id()
                    ]

            self.__workflow_dict["nodes"][
                gcc_node_object.get_node_id()
            ] = gcc_node_object

        if self.__workflow_dict["type"] == 1:
            self.__workflow_dict["plan_raw"] = dict(
                reversed(list(self.__workflow_dict["plan_raw"].items()))
            )
            self.__workflow_dict["plan_human_readable"] = dict(
                reversed(list(self.__workflow_dict["plan_human_readable"].items()))
            )

        return used_machines

    def get_workflow_dict(self) -> dict:
        """This method returns the __workflow_dict private variable."""
        return self.__workflow_dict

    def get_gcc_key_pair(self) -> dict:
        """This method returns the __gcc_key_pair private variable."""
        return self.__gcc_key_pair

    def get_gcc_security_group(self) -> dict:
        """This method returns the __gcc_security_group private variable."""
        return self.__gcc_security_group

    def get_gcc_ec2_obj(self) -> GccEc2:
        """This method returns the __gcc_ec2_obj private variable."""
        return self.__gcc_ec2_obj

    def configure(self) -> None:
        """Set configuration commands and execute them on a virtual machine."""
        if self.__workflow_dict["type"] == 1:
            for level in self.__workflow_dict["plan_raw"]:
                with ThreadPoolExecutor(
                    max_workers=len(self.__workflow_dict["plan_raw"][level])
                ) as executor:
                    for node in self.__workflow_dict["plan_raw"][level]:
                        executor.submit(node.set_config_commands)
                    executor.shutdown()

        elif self.__workflow_dict["type"] == 0:
            with ThreadPoolExecutor(
                max_workers=len(self.__workflow_dict["nodes"])
            ) as executor:
                for node in self.__workflow_dict["nodes"]:
                    executor.submit(
                        self.__workflow_dict["nodes"][node].set_config_commands
                    )
                executor.shutdown()

        with ThreadPoolExecutor(
            max_workers=len(self.__workflow_dict["nodes"])
        ) as executor:
            for node in self.__workflow_dict["nodes"]:
                executor.submit(self.__workflow_dict["nodes"][node].configure)
            executor.shutdown()

    def initialize(self) -> None:
        """Initialize a virtual machine for a node if needed."""
        self.__exec_date_time = datetime.now().strftime("%m:%d:%Y-%H:%M:%S")
        self.__gcc_drbx_obj.create_folder(
            f"/{self.__workflow_dict['name']}/exec/{self.__exec_date_time}"
        )
        self.__tmp_dir = generate_random_string()

        os.makedirs(f"{os.getcwd()}/tmp/{self.__tmp_dir}", exist_ok=True)

        with ThreadPoolExecutor(
            max_workers=len(self.__workflow_dict["nodes"])
        ) as executor:
            for node in self.__workflow_dict["nodes"]:
                if (
                    self.__workflow_dict["nodes"][node].get_node_virtual_machine()
                    is None
                ):
                    if (
                        self.__gcc_security_group is None
                        and self.__gcc_key_pair is None
                    ):
                        self.__gcc_security_group = (
                            self.__gcc_ec2_obj.create_security_group(self.__tmp_dir)
                        )
                        self.__gcc_key_pair = self.__gcc_ec2_obj.create_key_pair(
                            self.__tmp_dir
                        )
                    executor.submit(self.__workflow_dict["nodes"][node].initialize)
            executor.shutdown()

    def execute(self) -> None:
        """This method executes a node payload on a virtual machine."""
        if self.__workflow_dict["type"] == 1:
            threads = []
            for level in self.__workflow_dict["plan_raw"]:
                for node in self.__workflow_dict["plan_raw"][level]:
                    thread = threading.Thread(target=node.execute)
                    threads.append(thread)
                    thread.start()
                time.sleep(5)
            for thread in threads:
                thread.join()

        elif self.__workflow_dict["type"] == 0:
            for level in self.__workflow_dict["plan_raw"]:
                with ThreadPoolExecutor(
                    max_workers=len(self.__workflow_dict["plan_raw"][level])
                ) as executor:
                    for node in self.__workflow_dict["plan_raw"][level]:
                        executor.submit(node.execute)
                    executor.shutdown()

    def complete(self) -> None:
        """Delete tmp directory and terminate created instances."""
        shutil.rmtree(f"{os.getcwd()}/tmp/{self.__tmp_dir}")

        with ThreadPoolExecutor(
            max_workers=len(self.__workflow_dict["nodes"])
        ) as executor:
            for node in self.__workflow_dict["nodes"]:
                executor.submit(self.__workflow_dict["nodes"][node].terminate)
            executor.shutdown()

        if self.__gcc_key_pair is not None:
            self.__gcc_ec2_obj.delete_key_pair(self.__gcc_key_pair["KeyName"])
        if self.__gcc_security_group is not None:
            while True:
                try:
                    self.__gcc_ec2_obj.delete_security_group(
                        self.__gcc_security_group["GroupId"]
                    )
                    break
                except ClientError:
                    time.sleep(10)

    def get_gcc_user_obj(self) -> GccUser:
        """Return gcc user object."""
        return self.__gcc_user_obj

    def get_exec_date_time(self) -> str:
        """Return execution date and time string."""
        return self.__exec_date_time

    def get_gcc_drbx_obj(self) -> GccDrbx:
        """Return gcc dropbox object."""
        return self.__gcc_drbx_obj

    def get_tmp_dir(self) -> str:
        """Return tmp directory string."""
        return self.__tmp_dir


def generate_random_string() -> str:
    """Generate a random 7 character string."""
    choices = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ-"
    return "".join([random.choice(choices) for _ in range(7)])
