"""A second installed API process, reporting identity-only wakes to its parent."""
import importlib.util
import json
import sys

spec = importlib.util.spec_from_file_location('installed_api', sys.argv[1])
client = importlib.util.module_from_spec(spec)
spec.loader.exec_module(client)
opened = client.open_api(sys.argv[2])
original = opened.api.deliver_record


def deliver(hint):
    print(json.dumps(hint), flush=True)
    return original(hint)


opened.api.deliver_record = deliver
print(json.dumps({'ready': True}), flush=True)
try:
    sys.stdin.read()
finally:
    opened.close()
