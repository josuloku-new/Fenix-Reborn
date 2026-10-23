"""Preparation and settings, using only Python's standard library.

Tools are prepared locally; game data comes from the user's ISO.
"""
from __future__ import annotations
import ctypes
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import threading
import time
import urllib.request
from urllib.parse import urlsplit
import uuid
import zipfile
from processes import spawn_external
from display import DEFAULTS as DISPLAY_DEFAULTS,RESOLUTIONS,SCALES,REFRESH_RATES,ANTIALIASING,TEXTURE_FILTERS

from branding import VERSION,AUTHOR
XEX_SHA256 = 'c110e168abd4518c510f8358723343e129aed17eea73fe12010b8a0cd0a73bb8'
LANGUAGES = [
    ('es-ES', 'Español de España', 'ESN', 5, 31),
    ('en-US', 'English', 'INT', 1, 103),
    ('it-IT', 'Italiano', 'ITA', 6, 50),
    ('ko-KR', '한국어', 'KOR', 7, 56),
    ('zh-TW', '繁體中文', 'CHT', 8, 101),
    ('es-MX', 'Español latinoamericano', 'ESM', 5, 71),
    ('fr-FR', 'Français', 'FRA', 4, 34), ('de-DE', 'Deutsch', 'DEU', 3, 24),
    ('ja-JP', '日本語', 'JPN', 2, 53), ('zh-CN', '简体中文', 'CHS', 10, 20),
    ('pl-PL', 'Polski', 'POL', 11, 82), ('ru-RU', 'Русский', 'RUS', 12, 88),
]
MODS = [
    dict(key='unlock_fps', title='Desbloquear FPS', detail='Experimental: intenta alcanzar 60 FPS.', authors='illusion y boma', default=False),
    dict(key='lighting', title='Corregir iluminación', detail='Reduce sombras negras y errores de iluminación.', authors='illusion y boma', default=True),
    dict(key='no_ao', title='Desactivar oclusión ambiental', detail='Reduce manchas en las sombras.', authors='illusion', default=True),
    dict(key='no_motion_blur', title='Desactivar desenfoque', detail='Imagen más nítida al girar la cámara.', authors='illusion', default=False),
    dict(key='no_lens_flares', title='Desactivar destellos', detail='Útil si las luces atraviesan paredes.', authors='boma', default=False),
    dict(key='texture_streaming', title='Carga de texturas', detail='Carga más texturas; consume más memoria.', authors='boma', default=False),
    dict(key='no_dof_blur', title='Reducir desenfoque de profundidad', detail='Experimental: reduce el desenfoque gaussiano según la escena.', authors='boma', default=False),
    dict(key='no_bloom', title='Desactivar bloom', detail='Experimental: desactiva el resplandor; el cambio depende de la escena.', authors='boma', default=False),
]
BINDINGS = [
 ('lstick_up','Mover adelante','W'),('lstick_down','Mover atrás','S'),
 ('lstick_left','Mover izquierda','A'),('lstick_right','Mover derecha','D'),
 ('a','Aceptar / cobertura / correr','Space'),('b','Volver / cuerpo a cuerpo','V,Backspace'),
 ('x','Interactuar','E'),('y','Punto de interés','Q'),
 ('left_trigger','Apuntar','RMB'),('right_trigger','Disparar','LMB'),
 ('left_shoulder','Objetivos','Tab'),('right_shoulder','Recargar','R'),
 ('start','Pausa / inicio','Return'),('back','Volver','Escape'),
 ('lstick_press','Pulsar stick izquierdo','C'),('rstick_press','Pulsar stick derecho','F'),
 ('dpad_up','Cruceta arriba','1'),('dpad_down','Cruceta abajo','2'),
 ('dpad_left','Cruceta izquierda','3'),('dpad_right','Cruceta derecha','4'),
 ('rstick_up','Cámara arriba','Up'),('rstick_down','Cámara abajo','Down'),
 ('rstick_left','Cámara izquierda','Left'),('rstick_right','Cámara derecha','Right'),
]

def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''): h.update(block)
    return h.hexdigest()

def extract_zip(archive: Path, destination: Path, limit=3*1024**3):
    """Reject traversal, links and oversized downloads before extracting."""
    base = destination.resolve()
    with zipfile.ZipFile(archive) as z:
        if sum(i.file_size for i in z.infolist()) > limit:
            raise ValueError('El paquete supera el tamaño permitido.')
        for entry in z.infolist():
            target = (base / entry.filename.replace('\\', '/')).resolve()
            if not target.is_relative_to(base) or ':' in entry.filename:
                raise ValueError('Ruta no válida en el paquete descargado.')
            if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                raise ValueError('El paquete contiene enlaces no admitidos.')
        z.extractall(base)

def select_iso() -> str:
    if os.name != 'nt': raise RuntimeError('La selección de ISO requiere Windows.')
    from ctypes import wintypes as w
    class OPENFILENAME(ctypes.Structure):
        _fields_ = [('lStructSize',w.DWORD),('hwndOwner',w.HWND),('hInstance',w.HINSTANCE),
          ('lpstrFilter',w.LPCWSTR),('lpstrCustomFilter',w.LPWSTR),('nMaxCustFilter',w.DWORD),
          ('nFilterIndex',w.DWORD),('lpstrFile',w.LPWSTR),('nMaxFile',w.DWORD),
          ('lpstrFileTitle',w.LPWSTR),('nMaxFileTitle',w.DWORD),('lpstrInitialDir',w.LPCWSTR),
          ('lpstrTitle',w.LPCWSTR),('Flags',w.DWORD),('nFileOffset',w.WORD),
          ('nFileExtension',w.WORD),('lpstrDefExt',w.LPCWSTR),('lCustData',ctypes.c_ssize_t),
          ('lpfnHook',ctypes.c_void_p),('lpTemplateName',w.LPCWSTR),('pvReserved',ctypes.c_void_p),
          ('dwReserved',w.DWORD),('FlagsEx',w.DWORD)]
    buffer = ctypes.create_unicode_buffer(32768)
    data = OPENFILENAME(); data.lStructSize=ctypes.sizeof(data)
    ctypes.windll.user32.GetForegroundWindow.restype=w.HWND
    data.hwndOwner=ctypes.windll.user32.GetForegroundWindow()
    data.lpstrFilter='Imagen Xbox 360 (*.iso)\0*.iso\0\0'
    data.lpstrFile=ctypes.cast(buffer,w.LPWSTR); data.nMaxFile=len(buffer)
    data.lpstrTitle='Selecciona tu ISO compatible';data.Flags=0x00080000|0x00001000|0x00000800|0x8
    if ctypes.windll.comdlg32.GetOpenFileNameW(ctypes.byref(data)): return buffer.value
    error=ctypes.windll.comdlg32.CommDlgExtendedError()
    if error: raise RuntimeError(f'No se pudo abrir el selector de ISO ({error}).')
    return ''

class Backend:
    def __init__(self, root: Path, workspace: Path | None = None):
        self.root=root.resolve();self.local=(workspace or self.root).resolve()/'.local'
        self.game=self.local/'game';self.runtime=self.local/'runtime'
        self.settings_path=self.local/'settings.json'
        self.manifest=json.loads((self.root/'launcher/dependencies.json').read_text('utf-8'))
        self.lock=threading.Lock();self.job={'state':'idle','message':'','phase':'','progress':None}
        self.selected_iso=''; self.process=None
        self.license_accepted=False
        self.on_build_complete=None
        self.cleanup_after_build=True
        self.texture_cleanup=True

    def tools_ready(self):
        tools=self.local/'tools'
        if not all((tools/p).is_file() for p in ('sdk/bin/rexglue.exe','llvm/.complete','llvm/bin/clang-cl.exe','llvm/bin/lld-link.exe','llvm/bin/llvm-rc.exe','llvm/bin/llvm-mt.exe','cmake/bin/cmake.exe','ninja/ninja.exe','python/python.exe','extract-xiso.exe')):return False
        from toolchain import environment
        try:environment(self);return True
        except ValueError:return False

    def available_languages(self):
        folder=self.game/'GearGame/CookedXenon'
        if not folder.is_dir(): return []
        names={p.name.casefold() for p in folder.iterdir()}
        return [dict(code=code,label=label) for code,label,res,_,_ in LANGUAGES
            if f'coalesced_{res.lower()}.bin' in names and f'geargame_loc_{res}.xxx'.casefold() in names]

    def game_ready(self):
        # A receipt avoids hashing on every UI poll, but validates the file's
        # size/time against the last complete cryptographic verification.
        xex=self.game/'default.xex';receipt=self.local/'game_verified.json'
        try:
            data=json.loads(receipt.read_text('utf-8'));stat=xex.stat()
            return data=={'sha256':XEX_SHA256,'size':stat.st_size,'mtime_ns':stat.st_mtime_ns} and bool(self.available_languages())
        except (OSError,ValueError): return False

    def verify_game(self, path: Path):
        if file_hash(path/'default.xex')!=XEX_SHA256:
            raise ValueError('Esta versión de la ISO todavía no es compatible con el ejecutable preparado.')

    def runtime_ready(self):
        try:
            receipt=json.loads((self.runtime/'local_build.json').read_text('utf-8'))
        except (OSError,ValueError):return False
        return receipt.get('rebuilt_locally') is True and receipt.get('version')==VERSION and receipt.get('xex_sha256')==XEX_SHA256 and all((self.runtime/'bin'/name).is_file() for name in ('gow2.exe','rexruntime.dll','rexgpu-xenos.dll'))

    def defaults(self):
        languages=self.available_languages()
        return dict(version=3,language=languages[0]['code'] if languages else 'es-ES',inputMode='keyboard_mouse',
          sensitivity=1.0,aimSensitivity=0.65,smoothing=2,smoothingEnabled=False,deadzone=9000,directMouse=True,**DISPLAY_DEFAULTS,
          hdTextures=False,mods={m['key']:m['default'] for m in MODS},bindings={k:v for k,_,v in BINDINGS})

    def settings(self):
        result=self.defaults()
        if self.settings_path.exists():
            stored=json.loads(self.settings_path.read_text('utf-8'));result.update(stored)
            if 'smoothingEnabled' not in stored:result['smoothingEnabled']=result['smoothing']>0
            result['mods']={**self.defaults()['mods'],**stored.get('mods',{})}
        # Version 1 stored only an integer GPU scale with misleading resolution
        # labels. Preserve that scale and its original 720p video mode.
        result['version']=3
        return result

    def save_settings(self, data):
        if data.get('language') not in {l['code'] for l in self.available_languages()}:
            raise ValueError('Selecciona un idioma presente en tu ISO.')
        if data.get('inputMode') not in ('keyboard_mouse','pad'): raise ValueError('Dispositivo no válido.')
        for name,lo,hi in [('sensitivity',.01,10),('aimSensitivity',.01,10),('smoothing',0,30),('deadzone',0,16000),('scale',1,6)]:
            value=data.get(name)
            if isinstance(value,bool) or not isinstance(value,(int,float)) or not lo<=value<=hi:
                raise ValueError(f'Valor no válido: {name}.')
        if type(data['scale']) is not int or data['scale'] not in SCALES.values(): raise ValueError('Escala no válida.')
        if type(data.get('refreshRate')) is not int or data['refreshRate'] not in REFRESH_RATES.values():raise ValueError('Frecuencia no válida.')
        if data.get('resolution') not in RESOLUTIONS.values():raise ValueError('Resolución no válida.')
        if data.get('antialiasing') not in ANTIALIASING.values():raise ValueError('Suavizado de bordes no válido.')
        if type(data.get('anisotropic')) is not int or data['anisotropic'] not in TEXTURE_FILTERS.values():raise ValueError('Filtrado de texturas no válido.')
        for key in ('vsync','showFps','directMouse','smoothingEnabled','hdTextures'):
            if type(data.get(key)) is not bool:raise ValueError('Estado no válido: '+key)
        if data['smoothingEnabled'] and data['smoothing']<=0:
            raise ValueError('Elige un suavizado mayor que 0 ms o desactívalo.')
        for m in MODS:
            if type(data.get('mods',{}).get(m['key'])) is not bool: raise ValueError('Estado de mod no válido.')
        special={'Space','Return','Escape','Backspace','Tab','Up','Down','Left','Right','LMB','RMB','MMB','Delete','Insert','Home','End','PageUp','PageDown'}
        for key,_,_ in BINDINGS:
            value=data.get('bindings',{}).get(key,'')
            if not isinstance(value,str) or not value or len(value)>80: raise ValueError('Asignación de tecla no válida.')
            for alternative in value.split(','):
                parts=alternative.strip().split('+')
                if any(p not in ('Shift','Ctrl','Control','Alt') for p in parts[:-1]) or not (parts[-1] in special or re.fullmatch(r'[A-Z0-9]|F(?:[1-9]|1[0-9]|2[0-4])|Numpad[0-9]',parts[-1])):
                    raise ValueError(f'Tecla no reconocida: {alternative}.')
        clean={k:data[k] for k in self.defaults() if k!='version'};clean['version']=3
        self.local.mkdir(parents=True,exist_ok=True)
        temp=self.settings_path.with_suffix('.tmp');temp.write_text(json.dumps(clean,ensure_ascii=False,indent=2),'utf-8');temp.replace(self.settings_path)

    def state(self):
        with self.lock: job=dict(self.job)
        from texture_pack import status as texture_status
        return dict(version=VERSION,author=AUTHOR,runtimeReady=self.runtime_ready(),toolsReady=self.tools_ready(),gameReady=self.game_ready(),
          extractorReady=(self.local/'tools/extract-xiso.exe').is_file(),languages=self.available_languages(),
          settings=self.settings(),mods=MODS,bindings=[dict(key=k,label=l,default=v) for k,l,v in BINDINGS],
          selectedIso=self.selected_iso,job=job,texturePack=texture_status(self),playing=self.process is not None and self.process.poll() is None)

    def report(self,message,progress=None):
        with self.lock:self.job.update(message=message,progress=progress)

    def start(self,action):
        if action not in ('dependencies','extract','build','texture_pack'): raise ValueError('Operación no válida.')
        if action=='dependencies' and not self.license_accepted:raise ValueError('Lee y acepta las condiciones de las herramientas de Microsoft antes de prepararlas.')
        with self.lock:
            if self.job['state']=='running':raise ValueError('Hay una operación en curso.')
            self.job=dict(state='running',message='Preparando…',phase=action,progress=None)
        def work():
            try:
                getattr(self,action)()
                with self.lock:self.job.update(state='done',message='Todo listo.',progress=100)
                if action=='build' and self.on_build_complete:self.on_build_complete()
            except Exception as exc:
                with self.lock:self.job.update(state='error',message=str(exc),progress=None)
        threading.Thread(target=work,daemon=True).start()

    def download(self,dependency):
        url=dependency.get('url','');sha=dependency.get('sha256','')
        if not re.fullmatch('[a-f0-9]{64}',sha): raise ValueError('Falta la huella de verificación de la herramienta. Usa la release preparada por el autor.')
        cache=self.local/'downloads';cache.mkdir(parents=True,exist_ok=True)
        target=cache/(sha+(Path(urlsplit(url).path).suffix or '.zip'))
        if target.exists() and file_hash(target)==sha:return target
        bundled=self.root/'dist'/dependency.get('bundled','runtime.zip')
        if bundled.is_file():
            if file_hash(bundled)!=sha:raise ValueError('El paquete local no supera la verificación SHA-256.')
            return bundled
        if not url.startswith('https://'):raise ValueError('Falta una dirección HTTPS válida para descargar la herramienta.')
        part=target.with_suffix('.part')
        request=urllib.request.Request(url,headers={'User-Agent':f'FenixReborn/{VERSION}'})
        with urllib.request.urlopen(request,timeout=60) as response,part.open('wb') as f:
            total=int(response.headers.get('Content-Length',0));done=0
            while block:=response.read(1024*1024):
                f.write(block);done+=len(block)
                amount=f'{done/1024**2:.1f} / {total/1024**2:.1f} MB' if total else f'{done/1024**2:.1f} MB'
                self.report('Descargando '+dependency.get('label','dependencias')+' · '+amount,round(done*100/total,1) if total else None)
        if file_hash(part)!=sha:raise ValueError('La descarga no supera la verificación SHA-256. No se ejecutará.')
        part.replace(target);return target

    def dependencies(self):
        from toolchain import install
        install(self)
        if not (self.local/'tools/extract-xiso.exe').is_file():
            archive=self.download(self.manifest['extractor']);temp=self.local/('unpack-'+uuid.uuid4().hex)
            extract_zip(archive,temp)
            binary=next(temp.rglob('extract-xiso.exe'),None)
            if binary is None:raise ValueError('El paquete no contiene el extractor de ISO.')
            shutil.copy2(binary,self.local/'tools/extract-xiso.exe')

    def build(self):
        from toolchain import build
        build(self)
        from entrypoints import finish_preparation
        finish_preparation(self)
        if self.cleanup_after_build:
            from cleanup import release_preparation_files
            release_preparation_files(self)

    def texture_pack(self):
        from texture_pack import prepare
        prepare(self)

    def extract(self):
        if self.game_ready():return
        if not self.tools_ready():
            raise ValueError('Prepara las dependencias antes de extraer la ISO.')
        source=Path(self.selected_iso)
        if not source.is_file() or source.suffix.lower()!='.iso':raise ValueError('Selecciona una ISO existente.')
        if self.game.exists():raise ValueError('Ya hay una carpeta .local/game. No se sobrescribirá.')
        if shutil.disk_usage(self.local).free<30*1024**3:raise ValueError('Se necesitan al menos 30 GB libres para extraer y reconstruir el juego.')
        stage=self.local/('extraction-'+uuid.uuid4().hex);stage.mkdir(parents=True)
        self.report('Extrayendo tu ISO. El original se conserva intacto…')
        logs=self.local/'logs';logs.mkdir(exist_ok=True)
        with (logs/'extraction.log').open('w',encoding='utf-8') as log:
            result=spawn_external([str(self.local/'tools/extract-xiso.exe'),'-s','-d',str(stage),str(source)],local=self.local,cwd=self.local,stdout=log,stderr=subprocess.STDOUT,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0)).wait()
        if result:raise ValueError('La extracción ha fallado. Consulta .local/logs/extraction.log; los datos parciales se conservan aparte.')
        self.report('Verificando la versión y los idiomas…')
        self.verify_game(stage);stage.rename(self.game)
        if not self.available_languages():raise ValueError('No se han encontrado recursos de idioma en la ISO.')
        stat=(self.game/'default.xex').stat()
        (self.local/'game_verified.json').write_text(json.dumps(dict(sha256=XEX_SHA256,size=stat.st_size,mtime_ns=stat.st_mtime_ns)),'utf-8')

    def launch_args(self):
        if not self.game_ready():raise ValueError('Primero extrae y verifica la ISO.')
        s=self.settings();self.save_settings(s)
        locale=next(l for l in LANGUAGES if l[0]==s['language'])
        width,height=s['resolution'].split('x')
        args=['--game_data_root',str(self.game),'--user_data_root',str(self.local/'userdata'),
          '--cache_root',str(self.local/'cache'),'--log_level','info','--input_backend','sdl',
          '--user_language',str(locale[3]),'--user_country',str(locale[4]),'--fullscreen',
          '--window_width',width,'--window_height',height,'--video_mode_width',width,'--video_mode_height',height,
          '--resolution_scale',str(s['scale']),
          '--draw_resolution_scale_x',str(s['scale']),'--draw_resolution_scale_y',str(s['scale']),
          '--video_mode_refresh_rate',str(s['refreshRate']),
          '--swap_post_effect',s['antialiasing'],'--anisotropic_override',str(s['anisotropic']),
          '--'+('' if s['vsync'] else 'no-')+'vsync',
          '--'+('' if s['showFps'] else 'no-')+'gow2_show_fps']
        if s['inputMode']=='keyboard_mouse':
            args+=['--mnk_mode','--mnk_mouse','--mnk_sensitivity',str(s['sensitivity']),
              '--'+('' if s['directMouse'] else 'no-')+'gow2_mouse_direct',
              '--gow2_mouse_aim_sensitivity',str(s['aimSensitivity']),
              '--gow2_mouse_smoothing_ms',str(s['smoothing'] if s['smoothingEnabled'] else 0),'--gow2_mouse_deadzone',str(s['deadzone'])]
            for key,_,_ in BINDINGS:args+=['--keybind_'+key,s['bindings'][key].replace(' ','')]
        else:args+=['--no-mnk_mode','--no-mnk_mouse']
        for mod in MODS:args+=['--'+('' if s['mods'][mod['key']] else 'no-')+'gow2_mod_'+mod['key']]
        return args

    def launch(self):
        if not self.runtime_ready():raise ValueError('El juego todavía no está preparado. Espera a que termine la compilación.')
        if self.process is not None and self.process.poll() is None:raise ValueError('El juego ya está abierto.')
        # The receipt validates polls cheaply; verify original content again at launch.
        self.verify_game(self.game)
        env=os.environ.copy()
        # Only the user's selected local pack reaches the native renderer.
        for key in tuple(env):
            if key.startswith('FENIX_TEXTURE_'):env.pop(key,None)
        if self.settings()['hdTextures']:
            from texture_pack import status as texture_status
            if not texture_status(self)['ready']:raise ValueError('Prepara primero el pack HD desde Mods.')
            env['FENIX_TEXTURE_PACK']=str(self.local/'mods/textures-hd')
        self.process=spawn_external([str(self.runtime/'bin/gow2.exe'),*self.launch_args()],local=self.local,cwd=self.local,env=env)
        def watch():
            process=self.process;code=process.wait()
            if code:
                with self.lock:self.job.update(state='error',message=f'El juego se cerró con código {code}. Los registros están en .local/runtime/bin/logs.')
        threading.Thread(target=watch,daemon=True).start()
