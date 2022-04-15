"""This file contains the TestGccWorkflow class."""
# pylint: disable=W1514,R0913,E0401
import os
from os.path import dirname, join
from unittest import mock

import pytest
from dotenv import load_dotenv
from gcc_user import GccUser
from gcc_workflow import GccWorkflow


class TestGccWorkflow:
    """This class contains methods to test the GccWorkflow class."""

    env_path = join(dirname(__file__), ".env")

    if os.path.isfile(env_path):
        load_dotenv()

    __gcc_user_obj = GccUser(
        oauth2_refresh_token=os.environ.get("OAUTH2_REFRESH_TOKEN"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )

    @pytest.mark.parametrize(
        "xml_specification_filename,\
            workflow_name,workflow_type,\
                workflow_plan_human_readable,\
                    node_virtual_machines",
        [
            (
                "spec_1.xml",
                "workflow_1",
                0,
                {0: ["n1"], 1: ["n2", "n3"], 2: ["n4"]},
                [None, None, None, None],
            ),
            (
                "spec_2.xml",
                "workflow_2",
                1,
                {2: ["n4"], 1: ["n2", "n3"], 0: ["n1"]},
                [None, None, None, None],
            ),
            (
                "spec_3.xml",
                "workflow_3",
                0,
                {0: ["n1"], 1: ["n2", "n3"], 2: ["n4"]},
                [dict, dict, dict, dict],
            ),
            (
                "spec_4.xml",
                "workflow_4",
                1,
                {2: ["n4"], 1: ["n2", "n3"], 0: ["n1"]},
                [dict, dict, dict, dict],
            ),
        ],
    )
    def test_plan(
        self,
        xml_specification_filename: str,
        workflow_name: str,
        workflow_type: int,
        workflow_plan_human_readable: dict,
        node_virtual_machines: list,
    ):
        """This method ensures workflow plans are generated properly."""
        gcc_workflow_obj = GccWorkflow(
            gcc_user_obj=self.__gcc_user_obj, workflow_name=workflow_name
        )

        with open(
            join(dirname(__file__), f"data/spec/{xml_specification_filename}")
        ) as xml_specification_file:
            xml_specification = xml_specification_file.read()

        gcc_workflow_obj.plan(
            available_machines=[], xml_specification=xml_specification
        )

        workflow_dict = gcc_workflow_obj.get_workflow_dict()

        print(workflow_dict)

        assert workflow_dict["name"] == workflow_name
        assert workflow_dict["type"] == workflow_type
        assert workflow_dict["plan_human_readable"] == workflow_plan_human_readable
        for node in workflow_dict["nodes"]:
            node_virtual_machine = node_virtual_machines.pop()

            if node_virtual_machine is None:
                assert (
                    workflow_dict["nodes"][node].get_node_virtual_machine()
                    == node_virtual_machine
                )
            else:
                assert isinstance(
                    workflow_dict["nodes"][node].get_node_virtual_machine(),
                    node_virtual_machine,
                )

    @mock.patch(
        "gcc_node.GccNode.initialize",
        return_value=None,
    )
    @mock.patch(
        "gcc_ec2.GccEc2.create_key_pair",
        return_value=None,
    )
    @mock.patch(
        "gcc_ec2.GccEc2.create_security_group",
        return_value=None,
    )
    @mock.patch(
        "gcc_drbx.GccDrbx.create_folder",
        return_value=None,
    )
    @mock.patch("os.makedirs", return_value=None)
    @pytest.mark.parametrize(
        "xml_specification_filename,workflow_name,security_group,key_pair",
        [
            (
                "spec_1.xml",
                "workflow_1",
                None,
                None,
            ),
            (
                "spec_2.xml",
                "workflow_2",
                {},
                {},
            ),
        ],
    )
    def test_initialize(
        self,
        mock_makedirs: mock.MagicMock,
        mock_create_folder: mock.MagicMock,
        mock_create_security_group: mock.MagicMock,
        mock_create_key_pair: mock.MagicMock,
        mock_initialize: mock.MagicMock,
        xml_specification_filename: str,
        workflow_name: str,
        security_group: dict,
        key_pair: dict,
    ):
        """This method ensures all nodes have a virtual machine initialized."""
        gcc_workflow_obj = GccWorkflow(
            gcc_user_obj=self.__gcc_user_obj, workflow_name=workflow_name
        )

        with open(
            join(dirname(__file__), f"data/spec/{xml_specification_filename}")
        ) as xml_specification_file:
            xml_specification = xml_specification_file.read()

        gcc_workflow_obj.plan(
            available_machines=[], xml_specification=xml_specification
        )

        gcc_workflow_obj.set_gcc_security_group(security_group)
        gcc_workflow_obj.set_gcc_key_pair(key_pair)

        gcc_workflow_obj.initialize()

        if security_group is None and key_pair is None:
            assert mock_create_key_pair.called
            assert mock_create_security_group.called

        assert mock_initialize.called
        assert mock_create_folder.called
        assert mock_makedirs.called

    @mock.patch(
        "gcc_node.GccNode.set_config_commands",
        return_value=None,
    )
    @mock.patch("gcc_node.GccNode.configure_virtual_machine", return_value=None)
    @pytest.mark.parametrize(
        "xml_specification_filename,workflow_name",
        [
            (
                "spec_3.xml",
                "workflow_3",
            ),
            (
                "spec_4.xml",
                "workflow_4",
            ),
        ],
    )
    def test_configure(
        self,
        mock_configure_virtual_machine: mock.MagicMock,
        mock_set_config_commands: mock.MagicMock,
        xml_specification_filename: str,
        workflow_name: str,
    ):
        """This method ensures all virtual machines are configured."""
        gcc_workflow_obj = GccWorkflow(
            gcc_user_obj=self.__gcc_user_obj, workflow_name=workflow_name
        )

        with open(
            join(dirname(__file__), f"data/spec/{xml_specification_filename}")
        ) as xml_specification_file:
            xml_specification = xml_specification_file.read()

        gcc_workflow_obj.plan(
            available_machines=[], xml_specification=xml_specification
        )

        gcc_workflow_obj.configure()

        assert mock_set_config_commands.called
        assert mock_configure_virtual_machine.called

    @mock.patch(
        "gcc_node.GccNode.execute",
        return_value=None,
    )
    @mock.patch("time.sleep", return_value=None)
    @pytest.mark.parametrize(
        "xml_specification_filename,workflow_name",
        [
            (
                "spec_1.xml",
                "workflow_1",
            ),
            (
                "spec_2.xml",
                "workflow_2",
            ),
            (
                "spec_3.xml",
                "workflow_3",
            ),
            (
                "spec_4.xml",
                "workflow_4",
            ),
        ],
    )
    def test_execute(
        self,
        mock_sleep: mock.MagicMock,
        mock_execute: mock.MagicMock,
        xml_specification_filename: str,
        workflow_name: str,
    ):
        """This method ensures all nodes are executed."""
        gcc_workflow_obj = GccWorkflow(
            gcc_user_obj=self.__gcc_user_obj, workflow_name=workflow_name
        )

        with open(
            join(dirname(__file__), f"data/spec/{xml_specification_filename}")
        ) as xml_specification_file:
            xml_specification = xml_specification_file.read()

        gcc_workflow_obj.plan(
            available_machines=[], xml_specification=xml_specification
        )

        workflow_dict = gcc_workflow_obj.get_workflow_dict()

        gcc_workflow_obj.execute()

        if workflow_dict["type"] == 1:
            assert mock_sleep.called

        assert mock_execute.called

    @mock.patch(
        "gcc_node.GccNode.terminate",
        return_value=None,
    )
    @mock.patch(
        "gcc_ec2.GccEc2.delete_key_pair",
        return_value=None,
    )
    @mock.patch(
        "gcc_ec2.GccEc2.delete_security_group",
        return_value=None,
    )
    @mock.patch("shutil.rmtree", return_value=None)
    @pytest.mark.parametrize(
        "xml_specification_filename,workflow_name,security_group,key_pair",
        [
            (
                "spec_1.xml",
                "workflow_1",
                None,
                None,
            ),
            (
                "spec_2.xml",
                "workflow_2",
                {"GroupId": "group_2"},
                {"KeyName": "key_2"},
            ),
            (
                "spec_3.xml",
                "workflow_3",
                None,
                None,
            ),
            (
                "spec_4.xml",
                "workflow_4",
                {"GroupId": "group_4"},
                {"KeyName": "key_4"},
            ),
        ],
    )
    def test_complete(
        self,
        mock_rmtree: mock.MagicMock,
        mock_delete_security_group: mock.MagicMock,
        mock_delete_key_pair: mock.MagicMock,
        mock_teminate: mock.MagicMock,
        xml_specification_filename: str,
        workflow_name: str,
        security_group: dict,
        key_pair: dict,
    ):
        """This method ensures that a workflow completes correctly."""
        gcc_workflow_obj = GccWorkflow(
            gcc_user_obj=self.__gcc_user_obj, workflow_name=workflow_name
        )

        with open(
            join(dirname(__file__), f"data/spec/{xml_specification_filename}")
        ) as xml_specification_file:
            xml_specification = xml_specification_file.read()

        gcc_workflow_obj.plan(
            available_machines=[], xml_specification=xml_specification
        )

        gcc_workflow_obj.set_gcc_security_group(security_group)
        gcc_workflow_obj.set_gcc_key_pair(key_pair)

        gcc_workflow_obj.complete()

        if security_group is not None and key_pair is not None:
            assert mock_delete_key_pair.called
            assert mock_delete_security_group.called

        assert mock_teminate.called
        assert mock_rmtree.called
