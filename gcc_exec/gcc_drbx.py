"""This file contains the GccDrbx class."""

import io
import os
from os.path import dirname, join

import dropbox
from dotenv import load_dotenv
from dropbox import files


class GccDrbx:
    """This class contains methods to interface with Dropbox."""

    __drbx = None
    __drbx_app_key = None
    __drbx_app_secret = None

    def __init__(self, oauth2_refresh_token: str) -> None:
        """Constructor method for a GccDrbx object."""
        env_path = join(dirname(__file__), ".env")

        if os.path.isfile(env_path):
            load_dotenv()

        self.__drbx_app_key = os.environ.get("DRBX_APP_KEY")
        self.__drbx_app_secret = os.environ.get("DRBX_APP_SECRET")

        self.__drbx = dropbox.Dropbox(
            oauth2_refresh_token=oauth2_refresh_token,
            app_key=self.__drbx_app_key,
            app_secret=self.__drbx_app_secret,
        )

    def upload_file(
        self, local_file_path: str, drbx_file_path: str
    ) -> files.FileMetadata:
        """Upload file to Dropbox using the Dropbox API."""
        chunk_size = 4 * 1024 * 1024
        file_size = os.path.getsize(local_file_path)

        with open(local_file_path, "rb") as out_file:
            if file_size <= chunk_size:
                response = self.__drbx.files_upload(
                    out_file.read(),
                    drbx_file_path,
                    mode=dropbox.files.WriteMode("overwrite"),
                )
            else:
                upload_session_start_result = self.__drbx.files_upload_session_start(
                    out_file.read(chunk_size)
                )
                cursor = dropbox.files.UploadSessionCursor(
                    session_id=upload_session_start_result.session_id,
                    offset=out_file.tell(),
                )
                commit = dropbox.files.CommitInfo(path=drbx_file_path)
                while out_file.tell() < file_size:
                    if (file_size - out_file.tell()) <= chunk_size:
                        response = self.__drbx.files_upload_session_finish(
                            out_file.read(chunk_size), cursor, commit
                        )
                    else:
                        self.__drbx.files_upload_session_append_v2(
                            out_file.read(chunk_size), cursor
                        )
                        cursor.offset = out_file.tell()
        return response

    def get_file_contents(self, drbx_file_path: str) -> str:
        """Get the contents of a file stored in Dropbox as a String."""
        _, result = self.__drbx.files_download(drbx_file_path)
        with io.BytesIO(result.content) as stream:
            return stream.read().decode()

    def get_file_link(self, drbx_file_path: str) -> str:
        """Get the download link of a file stored in Dropbox as a String."""
        response = self.__drbx.files_get_temporary_link(drbx_file_path)
        return response.link

    def create_folder(self, drbx_folder_path: str) -> files.FolderMetadata:
        """Create a folder in Dropbox."""
        response = self.__drbx.files_create_folder_v2(drbx_folder_path)
        return response

    def list_files(self, drbx_folder_path: str) -> list:
        """List the files in a certain directory in Dropbox."""
        result = self.__drbx.files_list_folder(drbx_folder_path)
        return [f.name for f in result.entries]

    def delete(self, drbx_path: str) -> files.DeleteResult:
        """Delete an object that is stored in Dropbox."""
        result = self.__drbx.files_delete_v2(drbx_path)
        return result

    def get_drbx_app_key(self) -> str:
        """Return the dropbox app key."""
        return self.__drbx_app_key

    def get_drbx_app_secret(self) -> str:
        """Return the dropbox app secret."""
        return self.__drbx_app_secret
