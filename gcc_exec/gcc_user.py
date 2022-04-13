"""This file contains the GccUser class."""


class GccUser:
    """This class contains getter and setter methods for GCC User credentials"""

    __oauth2_refresh_token = None
    __aws_access_key_id = None
    __aws_secret_access_key = None

    def __init__(
        self,
        oauth2_refresh_token: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
    ) -> None:
        """Constructor for a GccUser class object."""
        self.__oauth2_refresh_token = oauth2_refresh_token
        self.__aws_access_key_id = aws_access_key_id
        self.__aws_secret_access_key = aws_secret_access_key

    def get_oauth2_refresh_token(self) -> str:
        """This method returns a users oauth2 refresh token."""
        return self.__oauth2_refresh_token

    def get_aws_access_key_id(self) -> str:
        """This method returns a users aws access key id."""
        return self.__aws_access_key_id

    def get_aws_secret_access_key(self) -> str:
        """This method returns a users aws secret access key."""
        return self.__aws_secret_access_key
