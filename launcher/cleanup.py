"""Remove only preparation folders after a verified successful local build."""
import json
from pathlib import Path
import shutil

def release_preparation_files(backend):
    if not backend.runtime_ready() or not backend.game_ready():
        raise ValueError('La limpieza requiere que el juego esté preparado correctamente.')
    if backend.local.is_symlink() or backend.local.is_junction():
        raise ValueError('No se limpiará una carpeta local redirigida a otra ubicación.')
    base=backend.local.resolve()
    candidates=[base/name for name in ('downloads','tools','build')]
    for pattern in ('unpack-*','extraction-*'):candidates+=list(base.glob(pattern))
    removed=[];skipped=[]
    for target in candidates:
        # Never follow directory links/junctions or touch another workspace.
        if target.is_symlink() or target.is_junction() or target.resolve().parent!=base:
            skipped.append(target.name);continue
        if not target.is_dir():continue
        backend.report('Liberando espacio · '+target.name)
        try:shutil.rmtree(target);removed.append(target.name)
        except OSError:skipped.append(target.name)
    temporary=base/'temp/work'
    if temporary.is_dir() and not temporary.is_symlink() and not temporary.is_junction() and temporary.resolve()==base/'temp/work':
        try:shutil.rmtree(temporary);removed.append('temp/work')
        except OSError:skipped.append('temp/work')
    report=dict(removed=removed,skipped=skipped)
    log=base/'logs/cleanup.json';log.parent.mkdir(parents=True,exist_ok=True)
    log.write_text(json.dumps(report,ensure_ascii=False,indent=2),'utf-8')
    return report
