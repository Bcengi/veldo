import importlib.util, json, os, pathlib, re, subprocess, sys, tempfile, time
ROOT = pathlib.Path.cwd()
def load(path):
 s=importlib.util.spec_from_file_location(path.stem,path); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
if len(sys.argv)>1:
 job=json.loads(pathlib.Path(sys.argv[1]).read_text())
 audit=open(sys.argv[2], 'w')
 def hook(event,args):
  if event=='open' and isinstance(args[0],str):
   p=pathlib.Path(args[0]).absolute()
   if p.is_relative_to(ROOT): audit.write(json.dumps(str(p))+ '\n'); audit.flush()
 sys.addaudithook(hook)
 sys.path.insert(0,str(ROOT/'scripts'))
 gate=load(ROOT/'scripts/check_gate_mutations.py')
 print(json.dumps(gate.worker(job)))
else:
 gate=load(ROOT/'scripts/check_gate_mutations.py'); cases=gate.inventory(ROOT)
 groups={}
 for c in cases:
  if c['driver']==gate.DRIVERS[0]: groups.setdefault((c['suite'],c['module']),c)
 saved=ROOT/'proof/VELDO-0207/fan-in.json'
 if saved.exists():
  registry={c['identity']:c for c in cases}
  sample=[registry[r['identity']] for r in json.loads(saved.read_text())['cases']]
 else:
  values=[groups[k] for k in sorted(groups)]; sample=[values[round(i*(len(values)-1)/24)] for i in range(25)]
  sample += [c for c in cases if c['driver']==gate.DRIVERS[1]]
 report={'schema':'veldo.case-read-measurement/v1','method':'baseline only; Python open audit plus strace -f -e trace=file -yy; sequential single cases','cases':[]}
 out=ROOT/'proof/VELDO-0207'; out.mkdir(exist_ok=True)
 for c in sample:
  with tempfile.TemporaryDirectory(prefix='reuse-trace-') as tmp:
   t=pathlib.Path(tmp); (t/'job').write_text(json.dumps({'case':c,'mode':'baseline'}))
   start=time.monotonic()
   with open(t/'stdout','w') as stdout, open(t/'stderr','w') as stderr:
    try:
     p=subprocess.Popen(['strace','-f','-yy','-e','trace=file','-o',str(t/'trace'),sys.executable,'-B',__file__,str(t/'job'),str(t/'audit')],env=gate.fixed_env(t),stdout=stdout,stderr=stderr,start_new_session=True)
     try:
      rc=p.wait(timeout=90)
     except subprocess.TimeoutExpired: rc=124
     finally:
      import signal
      try: os.killpg(p.pid,signal.SIGKILL)
      except ProcessLookupError: pass
      p.wait()
    except OSError: rc=125
   paths=set()
   for line in (t/'audit').read_text().splitlines():
    try: paths.add(json.loads(line))
    except ValueError: pass
   for match in re.finditer(re.escape(str(ROOT))+r'[^"<>\n]*',(t/'trace').read_text()): paths.add(match.group())
   files=sorted(str(pathlib.Path(p).relative_to(ROOT)) for p in paths if pathlib.Path(p).is_file() and '.git' not in pathlib.Path(p).relative_to(ROOT).parts and '__pycache__' not in pathlib.Path(p).parts)
   row={'identity':c['identity'],'suite':c['suite'],'module':c['module'],'driver':c['driver'],'seconds':round(time.monotonic()-start,3),'exit':rc,'files':files,'count':len(files)}
   try: row['failed_rows']=json.loads((t/'stdout').read_text())['observation']['failed_rows']
   except (ValueError,KeyError): row['error']=(t/'stderr').read_text()[-1000:]
   report['cases'].append(row); (out/'fan-in.json').write_text(json.dumps(report,indent=2)+'\n')
   print(c['identity'],row['count'],rc, flush=True)
