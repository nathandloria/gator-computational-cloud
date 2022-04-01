class User:
    def __init__(
        self,
        drbx_refresh_token: str,
        drbx_app_key: str,
        drbx_app_secret: str,
        aws_access_key_id: str,
        aws_secret_access_key: str,
    ):
        """Initialize an instance of the User class. Used to store a user's credentials."""
        self.drbx_refresh_token = drbx_refresh_token
        self.drbx_app_key = drbx_app_key
        self.drbx_app_secret = drbx_app_secret
        self.aws_access_key_id = aws_access_key_id
        self.aws_secret_access_key = aws_secret_access_key
