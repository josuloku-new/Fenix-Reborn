"""Native Windows application: preparation, configuration, and direct play."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parent))
from backend import Backend,AUTHOR,VERSION,MODS
from entrypoints import install_entrypoints,finish_preparation
from processes import spawn_external
from branding import NAME,SETUP_NAME

def main():
    parser=argparse.ArgumentParser();modes=parser.add_mutually_exclusive_group()
    modes.add_argument('--configure',action='store_true');modes.add_argument('--play',action='store_true')
    parser.add_argument('--tab',choices=('controls','display','mods'),default='controls')
    parser.add_argument('--self-test',type=Path);parser.add_argument('--ui-self-test',type=Path)
    parser.add_argument('--handoff-self-test',type=Path,help=argparse.SUPPRESS)
    parser.add_argument('--wait-for-bundle',type=Path,help=argparse.SUPPRESS)
    args=parser.parse_args();root=Path(getattr(sys,'_MEIPASS',Path(__file__).resolve().parent.parent))
    workspace=Path(os.environ.get('FENIX_REBORN_WORKSPACE',Path(sys.executable).parent)) if getattr(sys,'frozen',False) else root
    mode='play' if args.play else 'configure' if args.configure else 'setup'
    if args.handoff_self_test:
        spawn_external([str(workspace/SETUP_NAME),'--self-test',str(args.handoff_self_test),'--wait-for-bundle',str(root)],local=workspace/'.local',cwd=workspace)
        return
    if args.self_test:
        import tempfile,time
        deadline=time.monotonic()+15
        while args.wait_for_bundle and args.wait_for_bundle.exists() and time.monotonic()<deadline:time.sleep(.1)
        args.self_test.write_text(json.dumps(dict(version=VERSION,author=AUTHOR,mode=mode,native_ui=True,web=False,workspace=str(workspace),bundle=str(root),temporary=tempfile.gettempdir(),independent_bundle=root!=args.wait_for_bundle,parent_bundle_removed=not args.wait_for_bundle or not args.wait_for_bundle.exists(),native_source=(root/'native/src/main.cpp').is_file(),game_included=bool(list(root.rglob('*.xex'))),runtime_included=bool(list(root.rglob('gow2.exe'))))),'utf-8');return
    backend=Backend(root,workspace)
    if mode=='play':
        try:backend.launch()
        except Exception as exc:
            if os.name=='nt':ctypes.windll.user32.MessageBoxW(None,str(exc),NAME,0x10)
            else:raise
        return
    from ui import App
    if os.name=='nt':ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('JoSuLoku.FenixReborn.'+mode)
    if args.ui_self_test:
        from display import SCALES,REFRESH_RATES,PRESETS
        app=App(backend,mode,hidden=True,tab=args.tab);app.update_idletasks()
        args.ui_self_test.write_text(json.dumps(dict(native_ui=True,mode=mode,tab=app.tab,title=app.title(),version=VERSION,author=AUTHOR,language_count=len(app.languages),icon=app.icon_path.name,cleanup_default=app.cleanup.get(),save_actions=[app.next.cget('text'),app.run_button.cget('text')] if app.run_button else [],run_enabled=app.run_button.instate(['!disabled']) if app.run_button else False,preparation_notice=bool(app.preparation_notice.winfo_manager()),mouse_settings=dict(camera=float(app.sensitivity.get()),aim=float(app.aim_sensitivity.get()),smoothing=float(app.smoothing.get()),smoothing_enabled=app.smoothing_enabled.get(),direct=app.direct_mouse.get()),mods=[dict(key=m['key'],title=m['title'],authors=m['authors'],enabled=app.mod_vars[m['key']].get()) for m in MODS],display_settings=app.display_settings(),video_modes=list(app.resolutions.values()),render_scales=list(SCALES.values()),refresh_rates=list(REFRESH_RATES.values()),graphics_presets=list(PRESETS),required_size=[app.winfo_reqwidth(),app.winfo_reqheight()])),'utf-8')
        report=json.loads(args.ui_self_test.read_text('utf-8'))
        report['texture_pack']={**app.state['texturePack'],'enabled':app.hd_textures.get(),'cleanup_default':app.hd_cleanup.get()}
        args.ui_self_test.write_text(json.dumps(report),'utf-8')
        app.destroy();return
    mutex=None;session=workspace/('.local/config-session.json' if mode=='configure' else '.local/session.json')
    if os.name=='nt':
        from ctypes import wintypes
        kernel=ctypes.windll.kernel32;kernel.CreateMutexW.argtypes=[ctypes.c_void_p,wintypes.BOOL,wintypes.LPCWSTR];kernel.CreateMutexW.restype=wintypes.HANDLE
        name='Local\\JoSuLokuFenixReborn-'+hashlib.sha256((str(workspace).casefold()+mode).encode()).hexdigest()[:20]
        mutex=kernel.CreateMutexW(None,False,name)
        if kernel.GetLastError()==183:
            try:
                existing=json.loads(session.read_text('utf-8'));hwnd=existing['hwnd'];pid=wintypes.DWORD()
                user=ctypes.windll.user32;user.GetWindowThreadProcessId.argtypes=[wintypes.HWND,ctypes.POINTER(wintypes.DWORD)]
                user.GetWindowThreadProcessId(hwnd,ctypes.byref(pid))
                if pid.value==existing['pid']:
                    user.ShowWindow.argtypes=[wintypes.HWND,ctypes.c_int];user.SetForegroundWindow.argtypes=[wintypes.HWND]
                    user.ShowWindow(hwnd,9);user.SetForegroundWindow(hwnd)
            except (OSError,ValueError,KeyError):pass
            kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle(mutex);return
    try:
        if getattr(sys,'frozen',False) or backend.tools_ready():install_entrypoints(backend)
        if backend.runtime_ready() and backend.game_ready():
            finish_preparation(backend)
            if mode=='setup':return
        def open_setup():
            command=[str(workspace/SETUP_NAME)] if getattr(sys,'frozen',False) else [sys.executable,str(root/'launcher/app.py')]
            spawn_external(command,local=backend.local,cwd=workspace)
        app=App(backend,mode,open_setup=open_setup,tab=args.tab);app.update_idletasks()
        hwnd=app.winfo_id()
        if os.name=='nt':
            user=ctypes.windll.user32;user.GetParent.argtypes=[wintypes.HWND];user.GetParent.restype=wintypes.HWND
            hwnd=user.GetParent(hwnd) or hwnd
            try:
                dark=ctypes.c_int(1);ctypes.windll.dwmapi.DwmSetWindowAttribute(wintypes.HWND(hwnd),20,ctypes.byref(dark),ctypes.sizeof(dark))
            except (AttributeError,OSError):pass
        session.parent.mkdir(parents=True,exist_ok=True);session.write_text(json.dumps(dict(pid=os.getpid(),hwnd=hwnd,mode=mode)),'utf-8')
        app.mainloop()
    finally:
        try:
            if json.loads(session.read_text('utf-8')).get('pid')==os.getpid():session.unlink()
        except (OSError,ValueError):pass
        if mutex:
            kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle(mutex)

if __name__=='__main__':main()
