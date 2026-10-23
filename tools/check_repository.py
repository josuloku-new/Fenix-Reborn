"""Audit sources without a game image or development SDK."""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys
root=Path(__file__).resolve().parents[1]
try:
    git_root=Path(subprocess.check_output(['git','-C',str(root),'rev-parse','--show-toplevel'],stderr=subprocess.DEVNULL).decode().strip()).resolve()
except (OSError,subprocess.CalledProcessError):git_root=None
if git_root==root:
    tracked=subprocess.check_output(['git','-C',str(root),'ls-files','-z']).decode('utf-8').split('\0')
else:
    # A publication snapshot has no .git and may sit under another checkout.
    # Audit its complete contents rather than silently inspecting its parent.
    tracked=[p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()]
bad=[]
for name in filter(None,tracked):
    path=root/name
    if re.search(r'(?i)(\.(iso|xex|bik|xxx|dds|tfc|tga|upk|exe|dll|obj|lib|pdb|zip|7z|dmp|log)$|(^|/)(\.local|generated|out|dist|__pycache__)/)',name):bad.append(name)
    if path.suffix=='.py':ast.parse(path.read_text('utf-8'),filename=name)
    if path.suffix=='.json':json.loads(path.read_text('utf-8'))
if bad:raise SystemExit('Files that must remain local: '+', '.join(bad))
subprocess.run([sys.executable,'-m','unittest','discover','-s',str(root/'tests'),'-v'],cwd=root,env={**os.environ,'PYTHONDONTWRITEBYTECODE':'1'},check=True)
print(f'Source audit passed: {len(list(filter(None,tracked)))} tracked files; no game or local binaries.')
