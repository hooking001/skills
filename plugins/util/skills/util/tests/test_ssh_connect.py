"""Offline behavioral checks. No real servers, login windows, or user config."""

import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import patch


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ssh_connect.py"
SPEC = importlib.util.spec_from_file_location("ssh_connect", SCRIPT)
ssh = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(ssh)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = patch.dict(os.environ, {"SSH_CONNECT_HOME": str(self.root / "state")})
        self.env.start()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.env.stop)

    def cli(self, *args):
        output = io.StringIO()
        with patch("sys.argv", [str(SCRIPT), *args]), contextlib.redirect_stdout(output):
            code = ssh.main()
        return code, json.loads(output.getvalue()) if output.getvalue() else None

    def register(self, *args):
        return self.cli("register", "개발 서버", "--host", "dev.example", "--user", "id", *args)

    def test_registration_persists_and_is_private(self):
        self.register("--port", "2222", "--jump", "id@bastion", "--workdir", "/home/id/my project")
        _, listing = self.cli("list")
        self.assertEqual(listing["servers"]["개발 서버"]["port"], 2222)
        self.assertEqual(stat.S_IMODE(ssh.home().stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((ssh.home() / "servers.json").stat().st_mode), 0o600)
        self.assertFalse((self.root / ".ssh" / "config").exists())

    def test_existing_ssh_alias_does_not_override_user_or_port(self):
        self.cli("register", "연구", "--host", "research")
        command = ssh.login_command("연구", ssh.get_server("연구"))
        self.assertNotIn("User=", " ".join(command))
        self.assertNotIn("-p", command)
        self.assertEqual(command[-1], "research")

    def test_registration_does_not_overwrite_without_explicit_replace(self):
        self.register()
        with self.assertRaisesRegex(ValueError, "already registered"):
            self.register("--port", "2222")
        with patch.object(ssh, "checked", return_value=True):
            with self.assertRaisesRegex(ValueError, "Disconnect"):
                self.register("--port", "2222", "--replace")
        with patch.object(ssh, "checked", return_value=False):
            self.register("--port", "2222", "--replace")
        self.assertEqual(ssh.get_server("개발 서버")["port"], 2222)

    def test_rejects_option_and_shell_injection_in_connection_fields(self):
        for field, value in [("--host", "-oProxyCommand=id"), ("--host", "a;touch /tmp/bad"),
                             ("--user", "id\nother"), ("--jump", "$(id)")]:
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.cli("register", "bad", "--host", "host", field + "=" + value)

    def test_connected_reuses_master_without_opening_window(self):
        self.register()
        with patch.object(ssh, "checked", return_value=True), patch.object(ssh.subprocess, "Popen") as popen:
            _, result = self.cli("connect", "개발 서버")
        self.assertEqual(result["status"], "connected")
        popen.assert_not_called()

    def test_manual_connection_does_not_authenticate_in_agent(self):
        self.register()
        with patch.object(ssh, "checked", return_value=False), patch.object(ssh.subprocess, "Popen") as popen:
            _, result = self.cli("connect", "개발 서버", "--manual")
        self.assertEqual(result["status"], "manual_login_required")
        self.assertIn("ControlPersist=no", result["login_command"])
        popen.assert_not_called()

    def test_mac_launch_is_an_external_terminal_and_not_connection_success(self):
        self.register()
        with patch.object(ssh, "checked", return_value=False), patch.object(ssh.sys, "platform", "darwin"), \
                patch.object(ssh.subprocess, "Popen") as popen:
            popen.return_value.pid = 123
            popen.return_value.wait.return_value = 0
            _, result = self.cli("connect", "개발 서버")
        self.assertEqual(result["status"], "login_required")
        argv = popen.call_args.args[0]
        self.assertEqual(argv[:3], ["open", "-a", "Terminal"])
        launcher = Path(argv[3])
        self.assertEqual(stat.S_IMODE(launcher.stat().st_mode), 0o700)
        subprocess.run(["/bin/sh", "-n", str(launcher)], check=True)

    def test_terminal_open_failure_provides_manual_login(self):
        self.register()
        with patch.object(ssh, "checked", return_value=False), patch.object(ssh.sys, "platform", "darwin"), \
                patch.object(ssh.subprocess, "Popen", side_effect=OSError("launch denied")):
            _, result = self.cli("connect", "개발 서버")
        self.assertEqual(result["status"], "manual_login_required")
        self.assertIn("ssh", result["login_command"])

    def test_status_and_operations_fail_without_master(self):
        self.register()
        with patch.object(ssh, "checked", return_value=False), patch.object(ssh.subprocess, "call") as call:
            code, result = self.cli("status", "개발 서버")
            self.assertEqual((code, result["status"]), (1, "login_required"))
            for operation in [("run", "개발 서버", "--", "echo hi"),
                              ("upload", "개발 서버", "local", "/tmp/x"),
                              ("download", "개발 서버", "/tmp/x", "local")]:
                with self.assertRaisesRegex(ValueError, "Login required"):
                    self.cli(*operation)
        call.assert_not_called()

    def test_run_preserves_quoting_cwd_and_exit_status(self):
        cwd = self.root / "project with ' quote"
        cwd.mkdir()
        self.register("--workdir", str(cwd))
        with patch.object(ssh, "checked", return_value=True), patch.object(ssh.subprocess, "call", return_value=17) as call:
            code, _ = self.cli("run", "개발 서버", "--", "printf '%s' \"$PWD\"")
        self.assertEqual(code, 17)
        command = call.call_args.args[0]
        self.assertIn("BatchMode=yes", command)
        self.assertIn("ProxyCommand=false", command)
        result = subprocess.run(shlex.split(command[-1]), capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, str(cwd))

    def test_failed_cd_cannot_execute_following_commands(self):
        self.register("--workdir", str(self.root / "missing"))
        with patch.object(ssh, "checked", return_value=True), patch.object(ssh.subprocess, "call", return_value=0) as call:
            self.cli("run", "개발 서버", "--", "true; printf BAD")
        result = subprocess.run(shlex.split(call.call_args.args[0][-1]), capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("BAD", result.stdout)

    def test_download_and_upload_with_spaces(self):
        self.register("--port", "2222")
        with patch.object(ssh, "checked", return_value=True), patch.object(ssh.subprocess, "call", return_value=0) as call:
            self.cli("upload", "개발 서버", "./-local file", "/tmp/my file", "--recursive")
            upload = call.call_args.args[0]
            self.assertEqual(upload[-2:], [str(Path("./-local file").resolve()), "dev.example:/tmp/my file"])
            self.assertIn("-r", upload)
            self.assertIn("-P", upload)
            self.assertIn("ProxyCommand=false", upload)
            self.cli("download", "개발 서버", "/tmp/my file", "./result file")
            download = call.call_args.args[0]
            self.assertEqual(download[-2:], ["dev.example:/tmp/my file", str(Path("./result file").resolve())])
            with self.assertRaisesRegex(ValueError, "absolute"):
                self.cli("upload", "개발 서버", "./local", "relative")

    def test_disconnect_and_remove(self):
        self.register()
        with patch.object(ssh, "checked", return_value=True), patch.object(ssh.subprocess, "call", return_value=0) as call:
            self.cli("disconnect", "개발 서버")
            self.assertIn("exit", call.call_args.args[0])
            with self.assertRaisesRegex(ValueError, "Disconnect"):
                self.cli("remove", "개발 서버")
        with patch.object(ssh, "checked", return_value=False):
            self.cli("remove", "개발 서버")
        self.assertEqual(ssh.load(), {})


if __name__ == "__main__":
    unittest.main()
