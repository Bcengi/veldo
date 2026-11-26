import base64
from pathlib import Path
import subprocess
root=Path.cwd()
source=(root/'proof/VELDO-0368/round3/measure-landlock.py').read_bytes()
code="from pathlib import Path;import base64,runpy;p=Path('.local/0368/round3/measure-landlock.py');p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(base64.b64decode("+repr(base64.b64encode(source).decode())+"));runpy.run_path(str(p),run_name='__main__')"
args=['/home/dmitry/projects/myday/scripts/remote_run.sh','--fetch','.local/0368/round3/landlock.json','--out',str(root/'proof/VELDO-0368/round3'),'pc1',str(root),'f345e09b6','--','/usr/bin/python3','-B','-c',code]
status = subprocess.call(args)
if status == 0:
    out = root / 'proof/VELDO-0368/round3'
    fetched = out / '.local/0368/round3/landlock.json'
    (out / 'landlock.json').write_bytes(fetched.read_bytes())
    fetched.unlink()
    for directory in (fetched.parent, fetched.parent.parent, fetched.parent.parent.parent):
        directory.rmdir()
raise SystemExit(status)
