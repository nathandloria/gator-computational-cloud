"""This file contains the TestGccEc2 class."""
# pylint: disable=E0401
import os
import time
from os.path import dirname, join

import pytest
from botocore.exceptions import ClientError
from dotenv import load_dotenv

from gcc_exec.gcc_ec2 import GccEc2


class TestGccEc2:
    """This class contains methods to test the GccEc2 class."""

    env_path = join(dirname(__file__), ".env")

    if os.path.isfile(env_path):
        load_dotenv()

    __gcc_ec2_obj = GccEc2(
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )

    def test_create_key_pair(self):
        """This method ensures key pairs are created properly."""
        response = self.__gcc_ec2_obj.create_key_pair("test_create_key_pair")

        pytest.key_pair_name = response["KeyName"]

        assert isinstance(response, dict)
        assert response["KeyPairId"] is not None

    def test_create_security_group(self):
        """This method ensures security groups are created properly."""
        response = self.__gcc_ec2_obj.create_security_group(
            "test_create_security_group"
        )

        pytest.security_group_id = response["GroupId"]

        assert isinstance(response, dict)
        assert response["GroupId"] is not None

    def test_create_instance(self):
        """This method ensures instances are created properly."""
        response = self.__gcc_ec2_obj.create_instance(
            pytest.key_pair_name, pytest.security_group_id
        )

        pytest.instance_id = response["Instances"][0]["InstanceId"]

        assert isinstance(response, dict)
        assert response["Instances"][0]["InstanceId"] is not None

    def test_terminate_instance(self):
        """This method ensures instances are terminated properly."""
        response = self.__gcc_ec2_obj.terminate_instance(pytest.instance_id)

        assert isinstance(response, dict)
        assert response["TerminatingInstances"][0]["InstanceId"] == pytest.instance_id

    def test_delete_key_pair(self):
        """This method ensures key pairs are deleted properly."""
        response = self.__gcc_ec2_obj.delete_key_pair(pytest.key_pair_name)

        assert isinstance(response, dict)
        assert response["ResponseMetadata"] is not None

    def test_delete_security_group(self):
        """This method ensures security groups are deleted properly."""
        while True:
            try:
                response = self.__gcc_ec2_obj.delete_security_group(
                    pytest.security_group_id
                )
                break
            except ClientError:
                time.sleep(10)

        assert isinstance(response, dict)
        assert response["ResponseMetadata"] is not None
