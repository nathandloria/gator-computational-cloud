"""This file contains the SocketService class."""
# pylint: disable=E1136,E0213,R0801,C0415,E1133,R0914,C0103
import rpyc


class SocketService(rpyc.Service):
    """This class contains methods to transfer data between nodes in GCC."""

    def exposed_get_send_files(self):
        """Return send_files method to user."""
        from rpyc.utils.teleportation import export_function

        return export_function(self.send_files)

    def exposed_get_send_files_to_many(self):
        """Return send_files_to_many method to user."""
        from rpyc.utils.teleportation import export_function

        return export_function(self.send_files_to_many)

    def exposed_get_receive_files(self):
        """Return receive_files method to user."""
        from rpyc.utils.teleportation import export_function

        return export_function(self.receive_files)

    def exposed_get_receive_files_from_many(self):
        """Return receive_files_from_many method to user."""
        from rpyc.utils.teleportation import export_function

        return export_function(self.receive_files_from_many)

    def exposed_get_upload_to_dropbox(self):
        """Return upload_to_dropbox method to user."""
        from rpyc.utils.teleportation import export_function

        return export_function(self.upload_to_dropbox)

    def send_files(filedictlist, host, port):
        """Handles the sending of files to one recipient."""
        import os
        import socket
        from pathlib import Path

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))

        for filedict in filedictlist:
            filedir = filedict["filedir"]
            filename = filedict["filename"]
            filepath = Path(f"{filedir}/{filename}")
            if filepath.is_file():
                filesize = os.path.getsize(filepath)

            sock.sendall(filename.encode() + b"\x00")
            sock.sendall(str(filesize).encode() + b"\x00")

            with open(filepath, "rb") as out_file:
                sock.sendall(out_file.read())
                out_file.close()

    def send_files_to_many(argsdictlist):
        """Handles the sending of files to multiple recipients."""
        import os
        import socket
        import threading
        from pathlib import Path

        def _send_files(filedictlist, host, port):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((host, port))

            for filedict in filedictlist:
                filedir = filedict["filedir"]
                filename = filedict["filename"]
                filepath = Path(f"{filedir}/{filename}")
                if filepath.is_file():
                    filesize = os.path.getsize(filepath)

                sock.sendall(filename.encode() + b"\x00")
                sock.sendall(str(filesize).encode() + b"\x00")

                with open(filepath, "rb") as out_file:
                    sock.sendall(out_file.read())
                    out_file.close()

        threads = []
        for argsdict in argsdictlist:
            host = argsdict["host"]
            port = argsdict["port"]
            filedictlist = argsdict["filedictlist"]
            thread = threading.Thread(
                target=_send_files, args=(filedictlist, host, port)
            )
            threads.append(thread)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def receive_files(outdir, host, port):
        """Handles the receiving of files from one sender."""
        import os
        import socket
        from pathlib import Path

        def get_bytes(conn, num, buffer):
            while len(buffer) < num:
                data = conn.recv(1024)
                if not data:
                    data = buffer
                    buffer = b""
                    return data, buffer
                buffer += data
            data, buffer = buffer[:num], buffer[num:]
            return data, buffer

        def get_data(conn, buffer):
            while b"\x00" not in buffer:
                data = conn.recv(1024)
                if not data:
                    return ""
                buffer += data
            data, _, buffer = buffer.partition(b"\x00")
            return data.decode(), buffer

        try:
            os.mkdir(outdir)
        except FileExistsError:
            pass

        sock = socket.socket()
        sock.bind((host, port))
        sock.listen(5)

        conn, addr = sock.accept()
        print(f"accepted connection from {addr}")
        buffer = b""

        while True:
            try:
                filename, buffer = get_data(conn, buffer)
            except ValueError:
                break

            filepath = Path(f"{outdir}/{filename}")
            filesize, buffer = get_data(conn, buffer)
            filesize = int(filesize)

            with open(filepath, "wb") as in_file:
                remaining = filesize
                while remaining:
                    chunksize = 4096 if remaining >= 4096 else remaining
                    chunk, buffer = get_bytes(conn, chunksize, buffer)
                    if not chunk:
                        break
                    in_file.write(chunk)
                    remaining -= len(chunk)
                in_file.close()
        sock.close()

    def receive_files_from_many(argsdictlist):
        """Handles the receiving of files from  many recipients."""
        import os
        import socket
        import threading
        from pathlib import Path

        def _receive_files(outdir, host, port):
            def get_bytes(conn, num, buffer):
                while len(buffer) < num:
                    data = conn.recv(1024)
                    if not data:
                        data = buffer
                        buffer = b""
                        return data, buffer
                    buffer += data
                data, buffer = buffer[:num], buffer[num:]
                return data, buffer

            def get_data(conn, buffer):
                while b"\x00" not in buffer:
                    data = conn.recv(1024)
                    if not data:
                        return ""
                    buffer += data
                data, _, buffer = buffer.partition(b"\x00")
                return data.decode(), buffer

            try:
                os.mkdir(outdir)
            except FileExistsError:
                pass

            sock = socket.socket()
            sock.bind((host, port))
            sock.listen(5)

            conn, addr = sock.accept()
            print(f"accepted connection from {addr}")
            buffer = b""

            while True:
                try:
                    filename, buffer = get_data(conn, buffer)
                except ValueError:
                    break

                filepath = Path(f"{outdir}/{filename}")
                filesize, buffer = get_data(conn, buffer)
                filesize = int(filesize)

                with open(filepath, "wb") as in_file:
                    remaining = filesize
                    while remaining:
                        chunksize = 4096 if remaining >= 4096 else remaining
                        chunk, buffer = get_bytes(conn, chunksize, buffer)
                        if not chunk:
                            break
                        in_file.write(chunk)
                        remaining -= len(chunk)
                    in_file.close()
            sock.close()

        threads = []
        for argsdict in argsdictlist:
            outdir = argsdict["outdir"]
            host = argsdict["host"]
            port = argsdict["port"]
            thread = threading.Thread(target=_receive_files, args=(outdir, host, port))
            threads.append(thread)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

    def upload_to_dropbox(argsdict):
        """Handles the upload of files to Dropbox."""
        import os
        import threading

        import dropbox

        def _upload_file(local_file_path, drbx_file_path, drbx):
            chunk_size = 4 * 1024 * 1024
            file_size = os.path.getsize(local_file_path)

            with open(local_file_path, "rb") as out_file:
                if file_size <= chunk_size:
                    drbx.files_upload(
                        out_file.read(),
                        drbx_file_path,
                        mode=dropbox.files.WriteMode("overwrite"),
                    )
                else:
                    upload_session_start_result = drbx.files_upload_session_start(
                        out_file.read(chunk_size)
                    )
                    cursor = dropbox.files.UploadSessionCursor(
                        session_id=upload_session_start_result.session_id,
                        offset=out_file.tell(),
                    )
                    commit = dropbox.files.CommitInfo(path=drbx_file_path)
                    while out_file.tell() < file_size:
                        if (file_size - out_file.tell()) <= chunk_size:
                            drbx.files_upload_session_finish(
                                out_file.read(chunk_size), cursor, commit
                            )
                        else:
                            drbx.files_upload_session_append_v2(
                                out_file.read(chunk_size), cursor
                            )
                            cursor.offset = out_file.tell()

        drbx_refresh_token = argsdict["drbx_refresh_token"]
        drbx_app_key = argsdict["drbx_app_key"]
        drbx_app_secret = argsdict["drbx_app_secret"]
        drbx = dropbox.Dropbox(
            oauth2_refresh_token=drbx_refresh_token,
            app_key=drbx_app_key,
            app_secret=drbx_app_secret,
        )
        local_dir_path = argsdict["local_dir_path"]
        drbx_dir_path = argsdict["drbx_dir_path"]

        threads = []
        for file in os.listdir(f"{os.getcwd()}{local_dir_path}"):
            thread = threading.Thread(
                target=_upload_file,
                args=(
                    f"{os.getcwd()}{local_dir_path}/{file}",
                    f"{drbx_dir_path}/{file}",
                    drbx,
                ),
            )
            threads.append(thread)
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()


if __name__ == "__main__":
    from rpyc.utils.server import ThreadedServer

    server_thread = ThreadedServer(SocketService, port=18861)
    server_thread.start()
