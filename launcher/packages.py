"""Files used by the pinned Release toolchain; excludes debug and GUI tools."""
from pathlib import Path
import shutil
from third_party.sdk_files import keep_sdk_file,keep_vsix_member,RELEASE_DLLS

POLICY_VERSION=1
SDK_LIBRARIES={name+'.lib' for name in (
    'aes128','disasm','fmt','libavcodec','libavutil','mspack','o1heap',
    'rexgpu-xenos','rexruntime','SDL3_test','SDL3-static','spdlog','TracyClient','xxhash')}

def keep_tool_file(tool,relative):
    path=Path(relative);parts=path.parts;name=path.name
    if not parts:return False
    if name.lower().startswith(('license','copyright')) or parts[0].lower()=='licenses':return True
    if name.lower().startswith(('msvcp140','vcruntime140','concrt140')) and path.suffix.lower()=='.dll':return name.lower() in RELEASE_DLLS
    if tool=='cmake':
        return (parts[0]=='bin' and (name in ('cmake.exe','cmcldeps.exe') or name.lower() in RELEASE_DLLS)) or (parts[0]=='share' and any(p in ('Modules','Templates') for p in parts))
    if tool=='sdk':
        if name.endswith(('-debug.cmake','-relwithdebinfo.cmake')):return False
        if parts[0] in ('include','cmake','share'):return True
        if parts[0]=='lib':return 'cmake' in parts or name in SDK_LIBRARIES
        return parts[0]=='bin' and (name in ('rexglue.exe','rexruntime.dll','rexgpu-xenos.dll','TracyClient.dll') or name.lower() in RELEASE_DLLS)
    if tool=='windows':
        if parts[0]=='Windows Kits':return keep_sdk_file(path)
        return keep_vsix_member(path.as_posix())
    if tool=='llvm':
        if name=='.complete':return True
        return (parts[0]=='bin' and (name in ('clang-cl.exe','lld-link.exe','llvm-lib.exe','llvm-rc.exe','llvm-mt.exe') or name.lower() in RELEASE_DLLS)) or (parts[:2]==('lib','clang') and ('include' in parts or name=='clang_rt.builtins-x86_64.lib'))
    return True

def trim_tool(root,tool):
    """Only called on generated tool folders, never on game/user directories."""
    root=Path(root).resolve();removed=0
    for file in root.rglob('*'):
        if file.is_file() and not keep_tool_file(tool,file.relative_to(root)):
            if not file.resolve().is_relative_to(root):raise ValueError('Ruta no válida en las herramientas.')
            removed+=file.stat().st_size;file.unlink()
    for folder in sorted((p for p in root.rglob('*') if p.is_dir()),key=lambda p:len(p.parts),reverse=True):
        if not any(folder.iterdir()):folder.rmdir()
    return removed

def copy_tool(source,destination,tool):
    source=Path(source);destination=Path(destination)
    for file in source.rglob('*'):
        if file.is_file() and keep_tool_file(tool,file.relative_to(source)):
            target=destination/file.relative_to(source);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(file,target)
