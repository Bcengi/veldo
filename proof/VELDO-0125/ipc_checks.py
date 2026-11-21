#!/usr/bin/env python3
"""Disposable real Linux IPC and 0108 relay check. No SSH or Mac qualification.
Exit 2 means socket creation is unavailable; never replace this row with a fixture.
"""
import json
import tempfile
from pathlib import Path
import checks as T


def main():
    with tempfile.TemporaryDirectory(prefix='v125-ipc-') as directory:
        f = T.Fixture(Path(directory))
        try:
            f.prepare(required=['macos'])
            try:
                f.start(ipc=True)
            except AssertionError as error:
                if 'PermissionError' in str(error) and 'Operation not permitted' in str(error):
                    print(json.dumps(dict(row='native/AC1/linux-ipc', status='not_run', reason='sandbox denies sockets')))
                    return 2
                raise
            client = f.client()
            binding = T.launch(client)
            result = client.result(binding, T.observation(), usage={'tokens': 0}, references={'proof': 'synthetic'})
            assert result['record'] == f.service.get(binding['dispatch_id'])
            assert client.watermark == f.service.watermark()
            assert {r['command']['command']['operation'] for r in client.sent} == set(T.CL.OPERATIONS)
            print(json.dumps(dict(row='native/AC1/linux-ipc', status='observed', watermark=client.watermark)))
            return 0
        finally:
            f.close()


if __name__ == '__main__':
    raise SystemExit(main())
