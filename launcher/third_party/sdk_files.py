"""Read Windows SDK MSI databases and unpack CAB files without installation.

Original integration by JoSuLoku, 2026. No MSI custom actions, registration,
administrator installer or unrelated SDK utilities are executed.
"""
import ctypes
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

REQUIRED_MSIS = {
    'Universal CRT Headers Libraries and Sources-x86_en-us.msi',
    'Windows SDK Desktop Headers x64-x86_en-us.msi',
    'Windows SDK Desktop Headers x86-x86_en-us.msi',
    'Windows SDK Desktop Libs x64-x86_en-us.msi',
    'Windows SDK for Windows Store Apps Headers-x86_en-us.msi',
    'Windows SDK for Windows Store Apps Headers OnecoreUap-x86_en-us.msi',
    'Windows SDK OnecoreUap Headers x86-x86_en-us.msi',
    'Windows SDK for Windows Store Apps Libs-x86_en-us.msi',
}

# Release x64 build only. This list matches the SDK/SDL link interface and the
# CMake Windows platform defaults; the integration tests link the actual game.
SDK_LIBRARIES = {name+'.lib' for name in (
    'kernel32','user32','gdi32','winmm','imm32','ole32','oleaut32','version',
    'uuid','advapi32','setupapi','shell32','hid','dinput8','dxgi','dxguid',
    'winspool','comdlg32','ucrt','onecore')}
CRT_LIBRARIES = {'msvcrt.lib','msvcprt.lib','vcruntime.lib','oldnames.lib'}
RELEASE_DLLS = {name+'.dll' for name in (
    'msvcp140','msvcp140_1','msvcp140_2','msvcp140_atomic_wait',
    'msvcp140_codecvt_ids','vcruntime140','vcruntime140_1',
    'vcruntime140_threads','concrt140')}

def keep_vsix_member(name):
    parts=tuple(p.lower() for p in name.replace('\\','/').split('/'))
    filename=parts[-1]
    if 'vc' not in parts:return False
    if 'include' in parts:return True
    if 'onecore' in parts and 'x64' in parts and filename in CRT_LIBRARIES:return True
    return 'redist' in parts and 'x64' in parts and filename in RELEASE_DLLS

def keep_sdk_file(relative):
    parts=tuple(p.lower() for p in relative.parts)
    if any(p in ('arm','arm64','arm64ec','x86','cppwinrt') for p in parts):return False
    if 'include' in parts:return True
    return 'lib' in parts and relative.name.lower() in SDK_LIBRARIES

def rows(path,query):
    msi=ctypes.WinDLL('msi',use_last_error=True)
    handle=ctypes.c_uint();view=ctypes.c_uint()
    msi.MsiOpenDatabaseW.argtypes=[ctypes.c_wchar_p,ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint)]
    msi.MsiDatabaseOpenViewW.argtypes=[ctypes.c_uint,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint)]
    msi.MsiViewExecute.argtypes=[ctypes.c_uint,ctypes.c_uint]
    msi.MsiViewFetch.argtypes=[ctypes.c_uint,ctypes.POINTER(ctypes.c_uint)]
    msi.MsiRecordGetFieldCount.argtypes=[ctypes.c_uint]
    msi.MsiRecordGetStringW.argtypes=[ctypes.c_uint,ctypes.c_uint,ctypes.c_wchar_p,ctypes.POINTER(ctypes.c_uint)]
    msi.MsiCloseHandle.argtypes=[ctypes.c_uint]
    def checked(code):
        if code:raise RuntimeError(f'No se pudo leer el MSI ({code}): {path.name}')
    checked(msi.MsiOpenDatabaseW(str(path),None,ctypes.byref(handle)))
    try:
        checked(msi.MsiDatabaseOpenViewW(handle,query,ctypes.byref(view)));checked(msi.MsiViewExecute(view,0))
        result=[]
        while True:
            record=ctypes.c_uint();code=msi.MsiViewFetch(view,ctypes.byref(record))
            if code==259:break
            checked(code)
            try:
                row=[]
                for index in range(1,msi.MsiRecordGetFieldCount(record)+1):
                    length=ctypes.c_uint(0);code=msi.MsiRecordGetStringW(record,index,None,ctypes.byref(length))
                    if code not in (0,234):checked(code)
                    text=ctypes.create_unicode_buffer(length.value+1);length.value+=1
                    checked(msi.MsiRecordGetStringW(record,index,text,ctypes.byref(length)));row.append(text.value)
                result.append(row)
            finally:msi.MsiCloseHandle(record)
        return result
    finally:
        if view.value:msi.MsiCloseHandle(view)
        msi.MsiCloseHandle(handle)

def plan(path,destination):
    path=Path(path);destination=Path(destination).resolve()
    directories={r[0]:(r[1],r[2]) for r in rows(path,'SELECT `Directory`, `Directory_Parent`, `DefaultDir` FROM `Directory`')}
    components={r[0]:r[1] for r in rows(path,'SELECT `Component`, `Directory_` FROM `Component`')}
    files=rows(path,'SELECT `File`, `Component_`, `FileName`, `Sequence` FROM `File`')
    media=sorted((int(r[0]),r[1]) for r in rows(path,'SELECT `LastSequence`, `Cabinet` FROM `Media`') if r[1])
    resolved={}
    def directory(key):
        if key in resolved:return resolved[key]
        parent,raw=directories[key];name=raw.split(':',1)[0].split('|')[-1]
        result=directory(parent) if parent else destination
        if name not in ('.','SourceDir','TARGETDIR',''):result=result/name
        result=result.resolve()
        if not result.is_relative_to(destination):raise ValueError('Ruta no válida en los datos del SDK.')
        resolved[key]=result;return result
    result=[]
    for key,component,name,sequence in files:
        target=(directory(components[component])/name.split('|')[-1]).resolve()
        if not target.is_relative_to(destination):raise ValueError('Nombre no válido en los datos del SDK.')
        if not keep_sdk_file(target.relative_to(destination)):continue
        cabinet=next((cab for end,cab in media if int(sequence)<=end),None)
        if not cabinet:raise ValueError('No se encontró el CAB para '+name)
        if cabinet.startswith('#'):raise ValueError('Este SDK usa un CAB integrado no admitido: '+cabinet)
        result.append((key,target,cabinet))
    return result

def required_cabinets(path):
    return {cabinet for _,_,cabinet in plan(path,Path(path).parent/'sdk-target')}

def extract(path,destination,cabinet_directory,sevenzip):
    destination=Path(destination).resolve();cabinet_directory=Path(cabinet_directory)
    with tempfile.TemporaryDirectory(prefix='sdk-cabs-',dir=destination.parent) as temporary:
        expanded={}
        for key,target,cabinet in plan(path,destination):
            if cabinet not in expanded:
                source=cabinet_directory/cabinet
                if not source.is_file():raise FileNotFoundError(source)
                folder=Path(temporary)/str(len(expanded));folder.mkdir()
                subprocess.run([str(sevenzip),'x',str(source),'-o'+str(folder),'-y'],stdout=subprocess.DEVNULL,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                expanded[cabinet]={f.name.casefold():f for f in folder.rglob('*') if f.is_file()}
            source=expanded[cabinet].get(key.casefold())
            if source is None:raise ValueError('Falta un archivo del SDK: '+key)
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
