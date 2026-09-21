#!/usr/bin/env python3
"""The authority as a REAL child process, for VELDO-0107's rows. Serves one store until told to
stop by the existence of a file, so the suite never leaves a process behind."""
import hashlib
import hmac
import importlib.util as ilu
import json
import os
import sys


def load(name, path):
    spec = ilu.spec_from_file_location(name, path)
    m = ilu.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def main():
    cfg = json.loads(open(sys.argv[1]).read())
    EN = load("v107_enroll", cfg["enrollment_module"])
    CC = load("v107_client", cfg["client_module"])
    key = cfg["key"].encode()

    def verify(payload, signature):
        return hmac.compare_digest("hmac-sha256:" + hmac.new(key, payload, hashlib.sha256).hexdigest(),
                                   signature)

    applied = []

    def apply(command):
        applied.append(command)
        with open(cfg["applied_log"], "a") as fh:
            fh.write(json.dumps(command) + "\n")
        return {"applied": True, "operation": command.get("operation")}

    authority = CC.Authority(cfg["store_uuid"], cfg["domain_uuid"], cfg["store_path"], EN, verify,
                             cfg["host_identity"], apply)
    srv = CC.bind(cfg["address"])
    srv.settimeout(0.25)
    open(cfg["ready_flag"], "w").write("ready\n")
    try:
        CC.serve_forever(srv, authority, until=lambda: os.path.exists(cfg["stop_flag"]))
    finally:
        srv.close()
        try:
            os.unlink(cfg["address"])
        except OSError:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
