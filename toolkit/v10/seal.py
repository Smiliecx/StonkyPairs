#!/usr/bin/env python3
"""seal.py -- toolkit v7.1 sealed (encrypted-at-rest) store for orchestrator-only files (spec Rule O-1).
openssl enc -aes-256-cbc -pbkdf2. Passphrase from env PP (drawn with `secrets`, never written to disk).
Store directory from env SEAL_DIR (default ./sealed).

  python3 seal.py write NAME FILE | cat NAME | ls"""
import os, subprocess, sys

SEALED = os.environ.get("SEAL_DIR") or os.path.join(os.getcwd(), "sealed")


def _pp():
    pp = os.environ.get("PP")
    if not pp:
        raise SystemExit("PP not set")
    return pp


def write(name, data):
    if isinstance(data, str):
        data = data.encode("utf-8")
    os.makedirs(SEALED, exist_ok=True)
    out = os.path.join(SEALED, name + ".enc")
    subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-salt", "-pass", "env:PP", "-out", out],
                   input=data, check=True, env=dict(os.environ, PP=_pp()))
    return out


def read(name, text=True):
    path = os.path.join(SEALED, name + ".enc")
    r = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-pass", "env:PP", "-in", path],
                       capture_output=True, check=True, env=dict(os.environ, PP=_pp()))
    return r.stdout.decode("utf-8") if text else r.stdout


def exists(name):
    return os.path.exists(os.path.join(SEALED, name + ".enc"))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "write":
        write(sys.argv[2], open(sys.argv[3], "rb").read())
    elif cmd == "cat":
        sys.stdout.write(read(sys.argv[2]))
    elif cmd == "ls":
        print("\n".join(sorted(os.listdir(SEALED))))
