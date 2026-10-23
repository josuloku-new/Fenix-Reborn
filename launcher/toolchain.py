"""Portable Clang + Windows libraries; no VS installer, IDE or MSBuild.

Microsoft components are downloaded on the user's machine, after the license
checkbox is accepted. They are never bundled into the source repository.
"""
from pathlib import Path
import json
import os
import re
import shutil
import subprocess
import sys
import uuid
from packages import trim_tool,POLICY_VERSION
from third_party.sdk_files import RELEASE_DLLS
from processes import spawn_external

def run(backend,args,*,cwd=None,env=None,phase=''):
    logs=backend.local/'logs';logs.mkdir(parents=True,exist_ok=True)
    log=logs/'preparation.log'
    backend.report(phase or 'Ejecutando herramientas locales…')
    totals=0;downloaded={}
    with log.open('a',encoding='utf-8') as output:
        child_env=(env or os.environ).copy();child_env['PYTHONUNBUFFERED']='1';child_env['PYTHONIOENCODING']='utf-8'
        process=spawn_external([str(a) for a in args],local=backend.local,cwd=cwd,env=child_env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for line in process.stdout:
            output.write(line);output.flush()
            if line.startswith('GOW2_PROGRESS '):
                try:
                    event=json.loads(line[len('GOW2_PROGRESS '):])
                    if event['kind']=='total':totals=event['bytes'];downloaded={}
                    elif event['kind']=='download':
                        downloaded[event['file']]=event['done'];done=sum(downloaded.values())
                        backend.report(f"Descargando Windows / C++ · {done/1024**2:.1f} / {totals/1024**2:.1f} MB · {Path(event['file']).name}",min(100,round(done*100/totals,1)) if totals else None)
                    elif event['kind']=='extract':backend.report('Preparando Windows / C++ · '+event['file'])
                except (ValueError,KeyError,TypeError):pass
            elif match:=re.match(r'\[(\d+)/(\d+)\]',line):
                backend.report(f"{phase} · {match[1]} / {match[2]} tareas",round(int(match[1])*100/int(match[2]),1))
        process.stdout.close();result=process.wait()
    if result:raise RuntimeError(f'{phase or "La operación"} ha fallado (código {result}). Registro: {log}')
    return log

def install(backend):
    from backend import extract_zip
    root=backend.local/'tools';root.mkdir(parents=True,exist_ok=True)
    config=backend.manifest
    for key,expected in [('python','python.exe'),('cmake','bin/cmake.exe'),('ninja','ninja.exe'),('sdk','bin/rexglue.exe')]:
        target=root/key
        if (target/expected).is_file():continue
        archive=backend.download(config[key]);stage=root/('unpack-'+uuid.uuid4().hex)
        backend.report('Preparando '+config[key]['label']+'…');extract_zip(archive,stage,limit=8*1024**3)
        if key=='cmake':source=next(stage.glob('cmake-*'))
        elif key=='sdk':source=next(stage.rglob('rexglue.exe')).parent.parent
        else:source=stage
        if target.exists():raise ValueError(f'Hay una preparación parcial en {target}. No se sobrescribirá.')
        trim_tool(source,key);source.rename(target)
        if stage.exists():shutil.rmtree(stage)
    if not (root/'llvm/.complete').is_file():
        seven=root/'sevenzip'
        if not list(seven.rglob('7z.exe')):
            # Extract the SFX archive with 7zr; never execute an installer.
            # This also avoids MSI's fragile TARGETDIR quoting (error 1639).
            bootstrap=backend.download(config['sevenzip_bootstrap'])
            archive=backend.download(config['sevenzip']);seven.mkdir(exist_ok=True)
            run(backend,[bootstrap,'x',archive,'-o'+str(seven),'-y'],phase='Preparando extractor de herramientas')
        executable=next(seven.rglob('7z.exe'))
        archive=backend.download(config['llvm']);target=root/'llvm';target.mkdir(exist_ok=True)
        run(backend,[executable,'x',archive,'-o'+str(target),'-y','bin/clang-cl.exe','bin/lld-link.exe','bin/llvm-lib.exe','bin/llvm-rc.exe','bin/llvm-mt.exe','lib/clang/*/include/*','lib/clang/*/lib/windows/clang_rt.builtins-x86_64.lib','LICENSE.TXT'],phase='Preparando compilador')
        if not all((target/'bin'/name).is_file() for name in ('clang-cl.exe','lld-link.exe','llvm-lib.exe','llvm-rc.exe','llvm-mt.exe')):raise ValueError('El paquete LLVM está incompleto.')
        (target/'.complete').write_text(config['llvm']['sha256'],'ascii')
    msvc=root/'windows'
    try:environment(backend);windows_complete=True
    except ValueError:windows_complete=False
    if not windows_complete:
        helper=backend.root/'launcher/third_party/vsdownload.py'
        args=[root/'python/python.exe',helper,'--major','18','--accept-license','--dest',msvc,'--cache',backend.local/'downloads/windows',
          '--architecture','x64','--host-arch','x64','--with-default','no','--with-msvc','no','--with-sdk','yes',
          '--sdk-version','10.0.26100','--with-workload','no','--with-asan','no','--with-atl','no','--with-dia','no',
          '--with-msbuild','no','--with-devcmd','no','--skip-patch',
          'Microsoft.VC.14.50.18.0.CRT.Headers','Microsoft.VC.14.50.18.0.CRT.x64.OneCore.Desktop','Microsoft.VisualCpp.CRT.Redist.X64']
        helper_env=os.environ.copy();helper_env['GOW2_SEVENZIP']=str(next((root/'sevenzip').rglob('7z.exe')))
        run(backend,args,env=helper_env,phase='Preparando archivos de Windows')
    # Validate paths rather than treating a partial folder as an installed SDK.
    environment(backend)
    marker=root/'minimal-policy.json'
    if not marker.exists() or json.loads(marker.read_text('utf-8')).get('version')!=POLICY_VERSION:
        backend.report('Ajustando las herramientas…')
        removed=sum(trim_tool(root/key,key) for key in ('windows','cmake','sdk','llvm','ninja','python','sevenzip'))
        environment(backend)
        marker.write_text(json.dumps(dict(version=POLICY_VERSION,removed_bytes=removed)),'utf-8')
    # Fresh Windows machines may not have the VC runtime installed. Keep it
    # app-local beside tools, rather than requiring a system redistributable.
    for dll in runtime_dlls(root):
        for consumer in (root/'sdk/bin',root/'llvm/bin',root/'cmake/bin',root/'ninja'):
            shutil.copy2(dll,consumer/dll.name)

def runtime_dlls(tools):
    folder=tools/'windows/VC/Redist'
    return [f for f in folder.rglob('*.dll') if f.name.lower() in RELEASE_DLLS and any(part.lower()=='x64' for part in f.parts)] if folder.exists() else []

def environment(backend):
    tools=backend.local/'tools';windows=tools/'windows'
    crt=sorted(windows.glob('VC/Tools/MSVC/*'))
    sdk=windows/'Windows Kits/10'
    versions=sorted((sdk/'Include').glob('*')) if (sdk/'Include').exists() else []
    if not crt or not versions:raise ValueError('Faltan las cabeceras y bibliotecas de Windows/C++. Prepara las herramientas.')
    crt=crt[-1];version=versions[-1].name
    include=[crt/'include',sdk/'Include'/version/'ucrt',sdk/'Include'/version/'shared',sdk/'Include'/version/'um',sdk/'Include'/version/'winrt']
    lib=[crt/'lib/onecore/x64',sdk/'Lib'/version/'ucrt/x64',sdk/'Lib'/version/'um/x64']
    if not all(p.is_dir() for p in include+lib):raise ValueError('La preparación de Windows/C++ está incompleta.')
    essential=[crt/'include/vector',crt/'lib/onecore/x64/oldnames.lib',crt/'lib/onecore/x64/msvcrt.lib',sdk/'Include'/version/'shared/winapifamily.h',sdk/'Include'/version/'um/Windows.h',sdk/'Lib'/version/'um/x64/kernel32.lib']
    if not all(p.is_file() for p in essential):raise ValueError('Faltan archivos de Windows/C++. Vuelve a preparar las herramientas para completar la descarga.')
    env=os.environ.copy()
    # Explicit local paths prevent accidentally relying on a VS installation.
    env['INCLUDE']=';'.join(str(p) for p in include);env['LIB']=';'.join(str(p) for p in lib)
    system=Path(os.environ.get('SystemRoot','C:/Windows'))
    env['PATH']=';'.join(str(p) for p in [tools/'llvm/bin',tools/'ninja',tools/'cmake/bin',tools/'python',tools/'sdk/bin',system/'System32',system])
    env['GOW2_XEX_PATH']=str(backend.game/'default.xex')
    return env

def build(backend):
    if not backend.game_ready():raise ValueError('Extrae y verifica la ISO antes de reconstruir el juego.')
    backend.verify_game(backend.game)
    env=environment(backend);tools=backend.local/'tools'
    project=backend.local/'build/native'
    if not project.exists():shutil.copytree(backend.root/'native',project,ignore=shutil.ignore_patterns('generated','out','__pycache__'))
    manifest=project/'gow2_manifest.toml';text=manifest.read_text('utf-8')
    text=re.sub(r'^game_root\s*=.*$', 'game_root = '+json.dumps(backend.game.as_posix()),text,flags=re.M)
    text=re.sub(r'^file_path\s*=.*$', 'file_path = '+json.dumps((backend.game/'default.xex').as_posix()),text,flags=re.M)
    manifest.write_text(text,'utf-8')
    log=run(backend,[tools/'sdk/bin/rexglue.exe','codegen',manifest],cwd=project,env=env,phase='Analizando el juego')
    if re.search(r'Unresolved (conditional branch|function|b target)|Jump target .* unresolved',log.read_text('utf-8',errors='replace')):raise ValueError('El análisis contiene saltos sin resolver. Consulta el registro.')
    output=project/'out/ninja'
    args=[tools/'cmake/bin/cmake.exe','-S',project,'-B',output,'-G','Ninja','-DCMAKE_BUILD_TYPE=Release',
      '-DCMAKE_TRY_COMPILE_CONFIGURATION=Release','-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreadedDLL',
      '-DCMAKE_CXX_COMPILER='+(tools/'llvm/bin/clang-cl.exe').as_posix(),'-DCMAKE_LINKER='+(tools/'llvm/bin/lld-link.exe').as_posix(),
      '-DCMAKE_RC_COMPILER='+(tools/'llvm/bin/llvm-rc.exe').as_posix(),'-DCMAKE_MT='+(tools/'llvm/bin/llvm-mt.exe').as_posix(),
      '-DCMAKE_MAKE_PROGRAM='+(tools/'ninja/ninja.exe').as_posix(),'-DCMAKE_PREFIX_PATH='+(tools/'sdk').as_posix(),
      '-DPython3_EXECUTABLE='+(tools/'python/python.exe').as_posix()]
    run(backend,args,cwd=project,env=env,phase='Preparando el juego')
    # Limit memory pressure from the large generated translation units.
    jobs=max(1,min(4,(os.cpu_count() or 2)//2))
    run(backend,[tools/'cmake/bin/cmake.exe','--build',output,'--target','gow2','--parallel',str(jobs)],cwd=project,env=env,phase='Preparando el juego')
    executable=next(output.rglob('gow2.exe'),None)
    if executable is None:raise ValueError('La compilación no produjo gow2.exe.')
    destination=backend.runtime/'bin';destination.mkdir(parents=True,exist_ok=True)
    shutil.copy2(executable,destination/'gow2.exe')
    from icons import embed_icon
    from branding import ICON_NAME
    embed_icon(destination/'gow2.exe',backend.root/'launcher/assets'/ICON_NAME)
    for name in ('rexruntime.dll','rexgpu-xenos.dll'):
        source=next((tools/'sdk/bin').rglob(name),None)
        if source is None:raise ValueError('Falta '+name+' en el SDK.')
        shutil.copy2(source,destination/name)
    for file in runtime_dlls(tools):shutil.copy2(file,destination/file.name)
    from texture_pack import build_plugin
    build_plugin(backend)
    for source,label in ((tools/'sdk/licenses','sdk'),(backend.root/'licenses','project')):
        if source.exists():shutil.copytree(source,backend.runtime/'licenses'/label,dirs_exist_ok=True)
    from backend import VERSION, XEX_SHA256, file_hash
    (backend.runtime/'local_build.json').write_text(json.dumps(dict(version=VERSION,xex_sha256=XEX_SHA256,exe_sha256=file_hash(destination/'gow2.exe'),rebuilt_locally=True),indent=2),'utf-8')
