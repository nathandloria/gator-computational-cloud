import io
import os

import dropbox


class Drbx:
    def __init__(
        self, drbx_refresh_token: str, drbx_app_key: str, drbx_app_secret: str
    ):
        """Initialize an instance of the Drbx class."""
        self.drbx_refresh_token = drbx_refresh_token
        self.drbx_app_key = drbx_app_key
        self.drbx_app_secret = drbx_app_secret
        self.drbx = dropbox.Dropbox(
            oauth2_refresh_token=self.drbx_refresh_token,
            app_key=self.drbx_app_key,
            app_secret=self.drbx_app_secret,
        )

    def upload_file(self, local_file_path: str, drbx_file_path: str):
        """Upload file to Dropbox using the Dropbox API."""
        chunk_size = 4 * 1024 * 1024
        file_size = os.path.getsize(local_file_path)

        with open(local_file_path, "rb") as f:
            if file_size <= chunk_size:
                self.drbx.files_upload(
                    f.read(), drbx_file_path, mode=dropbox.files.WriteMode("overwrite")
                )
            else:
                upload_session_start_result = self.drbx.files_upload_session_start(
                    f.read(chunk_size)
                )
                cursor = dropbox.files.UploadSessionCursor(
                    session_id=upload_session_start_result.session_id, offset=f.tell()
                )
                commit = dropbox.files.CommitInfo(path=drbx_file_path)
                while f.tell() < file_size:
                    if (file_size - f.tell()) <= chunk_size:
                        self.drbx.files_upload_session_finish(
                            f.read(chunk_size), cursor, commit
                        )
                    else:
                        self.drbx.files_upload_session_append_v2(
                            f.read(chunk_size), cursor
                        )
                        cursor.offset = f.tell()

    def get_file_contents(self, drbx_file_path: str):
        """Get the contents of a file stored in Dropbox as a String."""
        _, result = self.drbx.files_download(drbx_file_path)
        with io.BytesIO(result.content) as stream:
            return stream.read().decode()

    def get_file_link(self, drbx_file_path: str):
        """Get the download link of a file stored in Dropbox as a String."""
        result = self.drbx.files_get_temporary_link(drbx_file_path)
        return result.link

    def create_folder(self, drbx_folder_path: str):
        """Create a folder in Dropbox."""
        self.drbx.files_create_folder_v2(drbx_folder_path)

    def list_files(self, drbx_folder_path: str):
        """List the files in a certain directory in Dropbox."""
        result = self.drbx.files_list_folder(drbx_folder_path)
        return [f.name for f in result.entries]
