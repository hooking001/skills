#!/usr/bin/env python3
"""Named SSH masters with a human-owned login terminal; stdlib only."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys


def emit(**values):
    print(json.dumps(values, ensure_ascii=False))


def home():
    path = Path(os.environ.get("SSH_CONNECT_HOME", "~/.ssh/ssh-connect")).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    path.chmod(0o700)
    return path


def load():
    path = home() / "servers.json"
    return json.loads(path.read_text()) if path.exists() else {}


def save(servers):
    path = home() / "servers.json"
    temp = home() / "servers.json.tmp"
    with temp.open("w", encoding="utf-8") as stream:
        os.chmod(temp, 0o600)
        json.dump(servers, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temp.replace(path)


def socket_path(name):
    key = hashlib.sha256(name.encode()).hexdigest()[:16]
    path = str(home() / (key + ".sock"))
    if len(os.fsencode(path)) > 100:
        raise ValueError("Socket path too long; set SSH_CONNECT_HOME to a shorter private directory.")
    return path


def get_server(name):
    servers = load()
    if name not in servers:
        raise ValueError("Unknown server: " + name + "; register it first.")
    return servers[name]


def checked(name, server):
    result = subprocess.run(
        ["ssh", "-S", socket_path(name), "-o", "BatchMode=yes", "-O", "check", server["host"]],
        capture_output=True, text=True, timeout=5,
    )
    return result.returncode == 0


def require_connected(name, server):
    if not checked(name, server):
        raise ValueError("Login required. Run connect and ask the user to authenticate in the login terminal.")


def target_options(server, scp=False):
    options = []
    if server.get("user"):
        options += ["-o", "User=" + server["user"]]
    if server.get("port"):
        options += ["-P" if scp else "-p", str(server["port"])]
    return options


def login_command(name, server):
    command = ["ssh", "-tt", "-M", "-S", socket_path(name),
               "-o", "ControlMaster=yes", "-o", "ControlPersist=no"]
    command += target_options(server)
    if server.get("jump"):
        command += ["-J", server["jump"]]
    return command + [server["host"]]


def shared_options(name):
    # ProxyCommand=false prevents an authentication race from falling back to
    # a new network connection, even if the master dies after the status check.
    return ["-o", "ControlPath=" + socket_path(name), "-o", "ControlMaster=no",
            "-o", "ControlPersist=no", "-o", "BatchMode=yes", "-o", "ProxyCommand=false"]


def launch(name, server, manual=False):
    if checked(name, server):
        emit(status="connected", name=name)
        return
    command = shlex.join(login_command(name, server))
    if manual:
        emit(status="manual_login_required", name=name, login_command=command)
        return
    script = Path(socket_path(name)).with_suffix(".command")
    script.write_text(
        "#!/bin/sh\n"
        + "printf '%s\\n' " + shlex.quote("SSH login: " + name + " — authenticate here; keep this terminal open.") + "\n"
        + command + "\n"
        + "rc=$?\nprintf '\\nSSH closed (exit %s). Press Enter to close.\\n' \"$rc\"\n"
        + "read answer\nexit \"$rc\"\n", encoding="utf-8",
    )
    script.chmod(0o700)
    if sys.platform == "darwin":
        terminal = ["open", "-a", "Terminal", str(script)]
    elif os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        terminal = next((args for exe, args in [
            ("gnome-terminal", ["gnome-terminal", "--", "/bin/sh", str(script)]),
            ("konsole", ["konsole", "-e", "/bin/sh", str(script)]),
            ("xterm", ["xterm", "-e", "/bin/sh", str(script)]),
        ] if shutil.which(exe)), None)
    else:
        terminal = None
    if terminal is None:
        emit(status="manual_login_required", name=name, login_command=command)
        return
    # Popen avoids capturing password prompts or keeping the agent tool blocked.
    try:
        with open(os.devnull, "wb") as null:
            process = subprocess.Popen(terminal, stdin=subprocess.DEVNULL, stdout=null, stderr=null,
                                       start_new_session=True)
        if sys.platform == "darwin" and process.wait(timeout=10) != 0:
            emit(status="manual_login_required", name=name, login_command=command,
                 message="Terminal.app could not be opened. Run login_command in a separate terminal.")
            return
    except (OSError, subprocess.TimeoutExpired) as error:
        emit(status="manual_login_required", name=name, login_command=command, message=str(error))
        return
    emit(status="login_required", name=name, launcher_pid=process.pid, login_command=command,
         message="Authenticate in the opened terminal; then check status. Keep the terminal open.")


def register(args):
    if not args.name.strip() or len(args.name) > 80 or any(ord(c) < 32 for c in args.name):
        raise ValueError("Server name must be 1–80 characters without control characters.")
    for label, value, pattern in [
        ("host", args.host, r"[A-Za-z0-9_.:%\[\]-]+"),
        ("user", args.user, r"[A-Za-z0-9_.-]+"),
        ("jump", args.jump, r"[A-Za-z0-9_.:@,%\[\]-]+"),
    ]:
        if value is not None and (value.startswith("-") or not re.fullmatch(pattern, value)):
            raise ValueError("Invalid " + label)
    if args.port is not None and not 1 <= args.port <= 65535:
        raise ValueError("Port must be 1–65535.")
    if args.workdir is not None and not args.workdir.startswith("/"):
        raise ValueError("Workdir must be an absolute remote path.")
    server = {key: getattr(args, key) for key in ("host", "user", "port", "jump", "workdir")
              if getattr(args, key) is not None}
    servers = load()
    if args.name in servers and servers[args.name] != server:
        if not args.replace:
            raise ValueError("Server already registered differently; use --replace for an intentional update.")
        if checked(args.name, servers[args.name]):
            raise ValueError("Disconnect before replacing a connected server.")
    servers[args.name] = server
    save(servers)
    emit(status="registered", name=args.name, server=server, registry=str(home() / "servers.json"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="action", required=True)
    reg = sub.add_parser("register")
    reg.add_argument("name")
    reg.add_argument("--host", required=True, help="Hostname, IP, or existing ~/.ssh/config alias")
    reg.add_argument("--user")
    reg.add_argument("--port", type=int)
    reg.add_argument("--jump")
    reg.add_argument("--workdir")
    reg.add_argument("--replace", action="store_true")
    sub.add_parser("list")
    for action in ("status", "connect", "disconnect", "remove", "run", "upload", "download"):
        item = sub.add_parser(action)
        item.add_argument("name")
        if action == "connect":
            item.add_argument("--manual", action="store_true")
        if action == "run":
            item.add_argument("--cwd")
            item.add_argument("command", help="One remote bash command string; use -- before it")
        if action in ("upload", "download"):
            item.add_argument("source")
            item.add_argument("destination")
            item.add_argument("--recursive", action="store_true")
    args = parser.parse_args()
    if args.action == "register":
        register(args)
        return 0
    if args.action == "list":
        emit(servers=load())
        return 0
    server = get_server(args.name)
    if args.action == "connect":
        launch(args.name, server, args.manual)
        return 0
    if args.action == "status":
        connected = checked(args.name, server)
        emit(status="connected" if connected else "login_required", name=args.name)
        return 0 if connected else 1
    if args.action == "remove":
        if checked(args.name, server):
            raise ValueError("Disconnect before removing a connected server.")
        servers = load()
        del servers[args.name]
        save(servers)
        emit(status="removed", name=args.name)
        return 0
    require_connected(args.name, server)
    if args.action == "disconnect":
        return subprocess.call(["ssh", "-S", socket_path(args.name), "-O", "exit", server["host"]])
    if args.action == "run":
        cwd = args.cwd or server.get("workdir")
        if cwd is not None and not cwd.startswith("/"):
            raise ValueError("Workdir must be an absolute remote path.")
        body = ("cd -- " + shlex.quote(cwd) + " || exit\n" if cwd else "") + args.command
        command = ["ssh"] + shared_options(args.name) + target_options(server)
        return subprocess.call(command + [server["host"], "bash -lc " + shlex.quote(body)])
    remote = args.destination if args.action == "upload" else args.source
    if not remote.startswith("/") or "\n" in remote or "\r" in remote:
        raise ValueError("Transfer remote path must be absolute and contain no newlines.")
    host = server["host"]
    if ":" in host and not host.startswith("["):
        host = "[" + host + "]"
    remote_spec = host + ":" + remote
    local = str(Path(args.source if args.action == "upload" else args.destination).expanduser().resolve())
    command = ["scp"] + shared_options(args.name) + target_options(server, scp=True)
    if args.recursive:
        command += ["-r"]
    paths = [local, remote_spec] if args.action == "upload" else [remote_spec, local]
    return subprocess.call(command + paths)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (ValueError, OSError, subprocess.TimeoutExpired) as error:
        emit(status="error", message=str(error))
        sys.exit(1)
