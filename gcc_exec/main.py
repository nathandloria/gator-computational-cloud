"""This file contains a method to execute a workflow using the cli."""
# pylint: disable=E0401
import sys

from gcc_user import GccUser
from gcc_workflow import GccWorkflow


def main(
    oauth2_refresh_token: str,
    aws_access_key_id: str,
    aws_secret_access_key: str,
    workflow_name: str,
):
    """This method contains code to execute a wofkflow."""
    gcc_user_obj = GccUser(
        oauth2_refresh_token, aws_access_key_id, aws_secret_access_key
    )
    gcc_workflow_obj = GccWorkflow(gcc_user_obj, workflow_name)

    gcc_workflow_obj.plan([])
    gcc_workflow_obj.initialize()
    gcc_workflow_obj.configure()
    gcc_workflow_obj.execute()
    gcc_workflow_obj.complete()


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4])
