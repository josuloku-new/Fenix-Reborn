"""Independent child processes with all scratch files inside this installation."""
from contextlib import contextmanager
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import subprocess
import sys
import threading

_spawn_lock=threading.Lock()

def child_environment(local,base=None):
    environment=dict(os.environ if base is None else base)
    temporary=Path(local).resolve()/'temp/work';temporary.mkdir(parents=True,exist_ok=True)
    for name in ('TEMP','TMP','TMPDIR'):environment[name]=str(temporary)
    # A restarted onefile application must own its unpacked resources. Otherwise
    # closing its parent removes files from the still-running child instance.
    environment['PYINSTALLER_RESET_ENVIRONMENT']='1'
    return environment

@contextmanager
def independent_dll_search():
    if os.name!='nt' or not getattr(sys,'frozen',False):
        yield;return
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetDllDirectoryW.argtypes=[wintypes.DWORD,wintypes.LPWSTR];kernel.GetDllDirectoryW.restype=wintypes.DWORD
    kernel.SetDllDirectoryW.argtypes=[wintypes.LPCWSTR];kernel.SetDllDirectoryW.restype=wintypes.BOOL
    with _spawn_lock:
        length=kernel.GetDllDirectoryW(0,None);previous=ctypes.create_unicode_buffer(length+1)
        kernel.GetDllDirectoryW(len(previous),previous)
        if not kernel.SetDllDirectoryW(None):raise ctypes.WinError(ctypes.get_last_error())
        try:yield
        finally:kernel.SetDllDirectoryW(previous.value or None)

def spawn_external(args,*,local,env=None,**kwargs):
    environment=child_environment(local,env)
    with independent_dll_search():
        return subprocess.Popen(args,env=environment,**kwargs)
