"""Build the assistant EXE; never bundle a recompiled game executable."""
from pathlib import Path
import argparse
import hashlib
import subprocess
import sys

def build_bootstrap(backend,core,work,output):
    from toolchain import environment,run
    from icons import embed_icon
    from branding import SETUP_NAME,ICON_NAME
    work.mkdir(parents=True,exist_ok=True);output.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(core.read_bytes()).hexdigest()[:20]
    (work/'bootstrap_config.h').write_text('static const WCHAR CoreDirectory[] = L".local\\\\app\\\\'+digest+'";\n','utf-8')
    resource=work/'payload.rc';resource.write_text('100 RCDATA "'+core.resolve().as_posix()+'"\n','utf-8')
    tools=backend.local/'tools';env=environment(backend);obj=work/'bootstrap.obj';res=work/'payload.res'
    run(backend,[tools/'llvm/bin/llvm-rc.exe','/fo',res,resource],env=env,phase='Empaquetando aplicación')
    run(backend,[tools/'llvm/bin/clang-cl.exe','/nologo','/utf-8','/O2','/GS-','/Zl','/clang:-fno-builtin','/c',backend.root/'launcher/native/bootstrap.cpp','/I'+str(work),'/Fo:'+str(obj)],env=env,phase='Empaquetando aplicación')
    target=output/SETUP_NAME
    run(backend,[tools/'llvm/bin/lld-link.exe',obj,res,'/nodefaultlib','kernel32.lib','user32.lib','/subsystem:windows','/entry:Start','/machine:x64','/out:'+str(target)],env=env,phase='Empaquetando aplicación')
    embed_icon(target,backend.root/'launcher/assets'/ICON_NAME)
    return target

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--work',type=Path,required=True);parser.add_argument('--output',type=Path);parser.add_argument('--toolchain-workspace',type=Path)
    args=parser.parse_args();root=Path(__file__).resolve().parent.parent
    args.work.mkdir(parents=True,exist_ok=True)
    sys.path.insert(0,str(root/'launcher'))
    from backend import Backend
    from entrypoints import build_entrypoints
    from branding import CORE_NAME,ICON_NAME
    backend=Backend(root,args.toolchain_workspace)
    entrypoints=build_entrypoints(backend,args.work/'entrypoints')
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onefile','--windowed',
      '--name',Path(CORE_NAME).stem,'--runtime-tmpdir','.local/temp/app','--distpath',str(args.work/'core'),'--workpath',str(args.work/'build'),
      '--specpath',str(args.work),'--paths',str(root/'launcher')]
    command+=['--icon',str(root/'launcher/assets'/ICON_NAME)]
    command+=['--add-data',str(entrypoints)+';launcher/entrypoints']
    for name in ('launcher/third_party','launcher/native','launcher/assets','native','licenses'):
        directory=root/name
        if name=='native' and ((directory/'generated').exists() or (directory/'out').exists()):
            raise SystemExit('Remove local generated/build data from the native source tree before packaging.')
        command+=['--add-data',str(directory)+';'+name]
    for name in ('LICENSE','CREDITOS.md'):
        command+=['--add-data',str(root/name)+';.']
    command+=['--add-data',str(root/'launcher/dependencies.json')+';launcher',str(root/'launcher/app.py')]
    subprocess.run(command,cwd=root,check=True)
    build_bootstrap(backend,args.work/'core'/CORE_NAME,args.work/'bootstrap',args.output or root)
if __name__=='__main__':main()
