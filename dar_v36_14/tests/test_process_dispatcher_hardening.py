import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dar.boundary import BoundaryDenied
from dar.process_dispatcher import UnixDispatcherServer


class ProcessDispatcherHardeningTests(unittest.TestCase):
    def _server(self, socket_path):
        server = object.__new__(UnixDispatcherServer)
        server.socket_path = str(socket_path)
        return server

    def test_socket_parent_must_be_owned_by_dispatcher_uid(self):
        with tempfile.TemporaryDirectory() as d:
            parent = Path(d) / "sock"
            server = self._server(parent / "dar.sock")
            real_stat = os.stat(parent)
            foreign = type(real_stat)(
                real_stat.st_mode,
                real_stat.st_ino,
                real_stat.st_dev,
                real_stat.st_nlink,
                real_stat.st_uid + 1,
                real_stat.st_gid,
                real_stat.st_size,
                real_stat.st_atime,
                real_stat.st_mtime,
                real_stat.st_ctime,
            )
            with patch("dar.process_dispatcher.os.stat", return_value=foreign):
                with self.assertRaisesRegex(BoundaryDenied, "not owned by dispatcher uid"):
                    server._prepare_socket_parent()

    def test_socket_parent_is_created_for_current_uid(self):
        with tempfile.TemporaryDirectory() as d:
            socket_path = Path(d) / "new-parent" / "dar.sock"
            server = self._server(socket_path)
            parent = server._prepare_socket_parent()
            self.assertEqual(Path(parent), socket_path.parent)
            self.assertEqual(os.stat(parent).st_uid, os.getuid())
            self.assertTrue(os.path.isdir(parent))

    def test_serve_once_binds_generation_and_lock_before_listen(self):
        server = object.__new__(UnixDispatcherServer)
        server.socket_path = "/tmp/dar-test.sock"
        server._daemon_lock_fd = None
        calls = []

        def lock():
            calls.append("lock")

        def bind():
            calls.append("bind")

        def parent():
            calls.append("parent")
            return "/tmp"

        server._acquire_daemon_lock = lock
        server._bind_generation = bind
        server._prepare_socket_parent = parent

        class FakeSocket:
            def __init__(self):
                self.closed = False
            def settimeout(self, value):
                calls.append(("timeout", value))
            def bind(self, path):
                calls.append(("bind_socket", path))
            def listen(self, n):
                calls.append(("listen", n))
            def accept(self):
                raise TimeoutError
            def close(self):
                self.closed = True

        # The production loop uses socket.timeout, so make the fake accept raise it.
        import socket
        class FakeServerSocket(FakeSocket):
            def accept(self):
                raise socket.timeout()

        with patch("dar.process_dispatcher.socket.socket", return_value=FakeServerSocket()):
            with patch("dar.process_dispatcher.os.unlink"):
                with patch.object(server, "_release_daemon_lock", side_effect=lambda: calls.append("release")):
                    # Stop the one-shot server at accept by raising KeyboardInterrupt.
                    def stop_accept():
                        raise KeyboardInterrupt
                    FakeServerSocket.accept = stop_accept
                    with self.assertRaises(KeyboardInterrupt):
                        server.serve_once()

        self.assertEqual(calls[:3], ["lock", "bind", "parent"])


if __name__ == "__main__":
    unittest.main()
