"""Create an audited source snapshot and a separate assistant release asset."""
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]

def digest(file):return hashlib.sha256(file.read_bytes()).hexdigest()

def main():
    destination=ROOT/'SUBIR A GITHUB'
    if destination.is_symlink() or destination.is_junction() or destination.resolve()!=ROOT/'SUBIR A GITHUB':
        raise SystemExit('Unexpected publication destination; nothing removed.')
    private=ROOT/'.local'
    if private.is_symlink() or private.is_junction():raise SystemExit('Refusing a redirected staging directory.')
    assistant=ROOT/'Fenix-Reborn-Setup-0.1.exe'
    if not assistant.is_file():raise SystemExit('Build Fenix-Reborn-Setup-0.1.exe before preparing its release.')
    names=sorted(filter(None,subprocess.check_output(['git','-C',str(ROOT),'ls-files','-z']).decode('utf-8').split('\0')))
    forbidden=re.compile(r'(?i)(\.(iso|xex|bik|xxx|stfs|dds|tfc|tga|upk|exe|dll|obj|lib|pdb|zip|7z|dmp|log|msi|cab|vsix|pyd|pyc)$|(^|/)(\.local|generated|out|dist|__pycache__|SUBIR A GITHUB)/)')
    if not names or any(forbidden.search(name) for name in names):raise SystemExit('The source list contains private/generated files, or is empty.')
    stage=private/('publish-'+uuid.uuid4().hex);repository=stage/'REPOSITORIO';release=stage/'RELEASE'
    repository.mkdir(parents=True);release.mkdir()
    for name in names:
        source=ROOT/name
        if source.is_symlink() or not source.resolve().is_relative_to(ROOT):raise SystemExit('Source outside workspace: '+name)
        target=repository/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
        if digest(source)!=digest(target):raise SystemExit('Source copy mismatch: '+name)
    asset=release/assistant.name;shutil.copy2(assistant,asset)
    if digest(asset)!=digest(assistant):raise SystemExit('Release copy mismatch.')
    temporary=private/'temp/work';temporary.mkdir(parents=True,exist_ok=True)
    test_environment={**os.environ,'PYTHONDONTWRITEBYTECODE':'1','TEMP':str(temporary),'TMP':str(temporary),'TMPDIR':str(temporary)}
    subprocess.run([sys.executable,str(repository/'tools/check_repository.py')],cwd=repository,env=test_environment,check=True)
    actual=sorted(p.relative_to(repository).as_posix() for p in repository.rglob('*') if p.is_file())
    if actual!=names:raise SystemExit('Unexpected files in the source snapshot.')
    (stage/'COMO_SUBIR.txt').write_text(
        'Fenix Reborn 0.1 · By JoSuLoku @2026\n\n'
        '1. REPOSITORIO: sube su contenido como raíz del repositorio de GitHub.\n'
        '   Incluye también .github, .gitignore y .gitattributes.\n'
        '2. RELEASE: en GitHub > Releases crea la versión v0.1 y adjunta\n'
        '   Fenix-Reborn-Setup-0.1.exe como archivo descargable de esa release.\n\n'
        'Nombre del repositorio sugerido: fenix-reborn.\n\n'
        'Los usuarios descargan el asistente EXE desde Releases y seleccionan su ISO.\n'
        'El juego y los datos privados permanecen en la instalación local.\n','utf-8')
    if destination.exists():shutil.rmtree(destination)
    stage.rename(destination)
    print(json.dumps(dict(folder=str(destination),source_files=len(names),source_bytes=sum((destination/'REPOSITORIO'/n).stat().st_size for n in names),release_asset=assistant.name,release_sha256=digest(destination/'RELEASE'/assistant.name)),ensure_ascii=False))

if __name__=='__main__':main()
