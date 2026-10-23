"""Small native EXEs select play/configuration modes of the Python application."""
from pathlib import Path
import shutil

from branding import PLAY_NAME,CONFIG_NAME,ICON_NAME

def build_entrypoints(backend,destination):
    from toolchain import run,environment
    from icons import embed_icon
    destination=Path(destination);destination.mkdir(parents=True,exist_ok=True)
    tools=backend.local/'tools';env=environment(backend)
    for name,configure in ((PLAY_NAME,False),(CONFIG_NAME,True)):
        obj=destination.parent/(destination.name+('-configure.obj' if configure else '-play.obj'))
        args=[tools/'llvm/bin/clang-cl.exe','/nologo','/utf-8','/O2','/GS-','/Zl','/clang:-fno-builtin','/c',backend.root/'launcher/native/entrypoint.cpp','/Fo:'+str(obj)]
        if configure:args.append('/DFENIX_CONFIGURE')
        run(backend,args,env=env,phase='Creando accesos del juego')
        run(backend,[tools/'llvm/bin/lld-link.exe',obj,'/nodefaultlib','kernel32.lib','user32.lib','/subsystem:windows','/entry:Start','/machine:x64','/out:'+str(destination/name)],env=env,phase='Creando accesos del juego')
        embed_icon(destination/name,backend.root/'launcher/assets'/ICON_NAME)
    return destination

def install_entrypoints(backend,*,config_only=False):
    bundled=backend.root/'launcher/entrypoints'
    names=(CONFIG_NAME,) if config_only else (PLAY_NAME,CONFIG_NAME)
    if not all((bundled/name).is_file() for name in names):
        # Source execution uses the same portable compiler already prepared for
        # the game. Frozen releases contain these tiny application helpers.
        if config_only:return
        bundled=build_entrypoints(backend,backend.local/'build/entrypoints')
    for name in names:
        target=backend.local.parent/name;source=bundled/name
        if target.exists() and target.read_bytes()==source.read_bytes():continue
        stage=target.with_suffix('.new');shutil.copy2(source,stage);stage.replace(target)

def finish_preparation(backend):
    if not backend.runtime_ready() or not backend.game_ready():raise ValueError('El juego todavía no está preparado.')
    if not backend.settings_path.exists():backend.save_settings(backend.defaults())
    install_entrypoints(backend)
