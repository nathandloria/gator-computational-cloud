"""This file contains the TestGccDrbx class."""

import os
from os.path import dirname, join

from dotenv import load_dotenv
from dropbox.files import CreateFolderResult, DeleteResult, FileMetadata, FolderMetadata

from gcc_exec.gcc_drbx import GccDrbx


class TestGccDrbx:
    """This class contains methods to test the GccDrbx class."""

    env_path = join(dirname(__file__), ".env")

    if os.path.isfile(env_path):
        load_dotenv()

    __gcc_drbx_obj = GccDrbx(
        oauth2_refresh_token=os.environ.get("OAUTH2_REFRESH_TOKEN")
    )
    __drbx_folder_path = "/.test_gcc_drbx"
    __drbx_file_path = f"{__drbx_folder_path}/test_gcc_drbx.txt"

    def test_create_folder(self):
        """This method ensures folders are created properly."""
        response = self.__gcc_drbx_obj.create_folder(self.__drbx_folder_path)

        assert isinstance(response, CreateFolderResult)
        assert isinstance(response.metadata, FolderMetadata)
        assert response.metadata.path_lower == self.__drbx_folder_path

    def test_upload_file(self):
        """This method ensures files are uploaded properly."""
        local_file_path = join(dirname(__file__), "data/upload/test_gcc_drbx.txt")

        response = self.__gcc_drbx_obj.upload_file(
            local_file_path, self.__drbx_file_path
        )

        assert isinstance(response, FileMetadata)
        assert response.path_lower == self.__drbx_file_path

    def test_get_file_contents(self):
        """This method ensures file contents are retrieved properly."""
        response = self.__gcc_drbx_obj.get_file_contents(self.__drbx_file_path)

        assert isinstance(response, str)
        assert len(response.splitlines()) > 0

    def test_get_file_link(self):
        """This method ensures file links are retrieved properly."""
        response = self.__gcc_drbx_obj.get_file_link(self.__drbx_file_path)

        assert isinstance(response, str)
        assert "https://" in response and "dl.dropboxusercontent.com" in response

    def test_delete(self):
        """This method ensures objects are deleted properly."""
        response = self.__gcc_drbx_obj.delete(self.__drbx_folder_path)

        assert isinstance(response, DeleteResult)
        assert response.metadata.path_lower == self.__drbx_folder_path
