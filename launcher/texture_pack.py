"""Build a local AI-upscaled BC1 pack from the user's verified game files."""
from pathlib import Path
import json
import os
import re
import shutil
import struct
import subprocess
from urllib.parse import urlsplit
from processes import spawn_external

SOURCES=('GearGame.xxx','SP_Hospital_01.xxx','SP_Hospital_01_S.xxx','SP_Hospital_01_Backdrop.xxx')
MASK64=(1<<64)-1

def bc1_identity(data):
    if len(data)<128 or data[:4]!=b'DDS ' or data[84:88]!=b'DXT1':raise ValueError('Se requiere DDS BC1.')
    height,width=struct.unpack_from('<II',data,12)
    if not width or not height or width>4096 or height>4096:raise ValueError('Dimensiones DDS no válidas.')
    size=((width+3)//4)*((height+3)//4)*8
    if len(data)<128+size:raise ValueError('DDS incompleto.')
    payload=data[128:128+size];fingerprint=14695981039346656037;opaque=True
    for (word,) in struct.iter_unpack('<Q',payload):
        fingerprint=((fingerprint^word)*1099511628211)&MASK64
        c0=word&65535;c1=(word>>16)&65535;indices=word>>32
        if c0<=c1 and indices&(indices>>1)&0x55555555:opaque=False
    return f'{fingerprint:016x}_{width}x{height}',width,height,opaque

def diffuse_name(name):
    return bool(re.search(r'(?i)(?:_D(?:_\d+)?$|diffuse(?:map)?(?:_\w+)?$|_Tex(?:ture)?$)',name)) and not re.search(r'(?i)(normal|mask|specular|emiss|noise|screen|muzzle|gore|blood|hair|water|lightmap|distortion|fx_)',name)

def status(backend):
    folder=backend.local/'mods/textures-hd'
    try:
        manifest=json.loads((folder/'pack.json').read_text('utf-8'))
        entries=manifest['textures']
        count=sum(bool(re.fullmatch(r'[0-9a-f]{16}_\d+x\d+',entry['id'])) and (folder/(entry['id']+'.dds')).is_file() for entry in entries)
        loader=json.loads((backend.runtime/'texture_loader.json').read_text('utf-8')).get('version')==1
        return dict(ready=bool(count) and loader and manifest.get('complete') is True,count=count,loader=loader)
    except (OSError,ValueError,KeyError,TypeError):
        return dict(ready=False,count=0,loader=(backend.runtime/'texture_loader.json').is_file())

def command(backend,args,label,*,cwd=None,progress=None,capture=False):
    log=backend.local/'logs/texture-pack.log';log.parent.mkdir(parents=True,exist_ok=True)
    backend.report(label,progress)
    result=[]
    with log.open('a',encoding='utf-8') as output:
        process=spawn_external([str(a) for a in args],local=backend.local,cwd=cwd or backend.local,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf-8',errors='replace',
            creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        for line in process.stdout:
            output.write(line);output.flush()
            if capture:result.append(line)
        process.stdout.close();code=process.wait()
    if code:raise RuntimeError(f'{label} ha fallado ({code}). Registro: {log}')
    return ''.join(result)

def install_tools(backend):
    from backend import extract_zip
    folder=backend.local/'texture-pack/tools';folder.mkdir(parents=True,exist_ok=True)
    for key,name in (('texture_umodel','umodel.exe'),('texture_texconv','texconv.exe')):
        archive=backend.download(backend.manifest[key]);destination=folder/name
        if not destination.is_file() or destination.read_bytes()!=archive.read_bytes():shutil.copy2(archive,destination)
    if not (folder/'upscaler/srmd-ncnn-vulkan.exe').is_file():
        archive=backend.download(backend.manifest['texture_upscaler'])
        stage=folder/'unpack-upscaler'
        extract_zip(archive,stage,limit=256*1024**2)
        next(stage.rglob('srmd-ncnn-vulkan.exe')).parent.rename(folder/'upscaler')
        if stage.exists():shutil.rmtree(stage)
    return folder

def prepare(backend):
    if not backend.runtime_ready() or not backend.game_ready():raise ValueError('Prepara el juego antes de crear el pack HD.')
    if backend.process is not None and backend.process.poll() is None:raise ValueError('Cierra el juego antes de preparar el pack.')
    if not status(backend)['loader']:raise ValueError('Actualiza la preparación del juego para instalar el cargador de texturas.')
    backend.verify_game(backend.game)
    tools=install_tools(backend);umodel=tools/'umodel.exe';texconv=tools/'texconv.exe'
    source=backend.game/'GearGame/CookedXenon';work=backend.local/'texture-pack/work'
    export=work/'originals';export.mkdir(parents=True,exist_ok=True)
    for package in SOURCES:
        if not (source/package).is_file():continue
        listing=command(backend,[umodel,'-list','-path='+str(source),package],'Leyendo texturas · '+package,capture=True)
        names=sorted({m[1] for m in re.findall(r'\b(Texture2D)\s+(\S+)\s*$',listing,re.M) if diffuse_name(m[1])})
        if names:
            command(backend,[umodel,'-export','-dds','-nooverwrite','-noanim','-nomesh','-nostat',
                '-path='+str(source),'-out='+str(export),package,*['-obj='+name for name in names]],'Extrayendo texturas · '+package)
    textures=[];seen=set()
    for file in export.rglob('*.dds'):
        try:identity,width,height,opaque=bc1_identity(file.read_bytes())
        except ValueError:continue
        if not opaque or min(width,height)<256 or max(width,height)>2048 or identity in seen:continue
        seen.add(identity);textures.append((file,identity,width,height))
    # Marcus and the main characters are prepared first, even when resuming.
    textures.sort(key=lambda item:('marcus' not in item[0].stem.lower(),'cog_dom' not in item[0].stem.lower(),item[0].stem.lower()))
    if not textures:raise ValueError('No se han encontrado texturas de color compatibles en esta copia.')
    folder=backend.local/'mods/textures-hd';folder.mkdir(parents=True,exist_ok=True)
    stage=work/'convert';stage.mkdir(parents=True,exist_ok=True)
    entries=[]
    for index,(original,identity,width,height) in enumerate(textures,1):
        output=folder/(identity+'.dds');label=f'Pack HD · {index}/{len(textures)} · {original.stem}'
        progress=round((index-1)*100/len(textures),1)
        if not output.is_file():
            command(backend,[texconv,'-nologo','-y','-ft','png','-o',stage,original],label,cwd=stage,progress=progress)
            png=stage/(original.stem+'.png');enhanced=stage/(original.stem+'-hd.png')
            command(backend,[tools/'upscaler/srmd-ncnn-vulkan.exe','-i',png,'-o',enhanced,
                '-n','-1','-s','2','-t','128','-j','1:1:1','-m',tools/'upscaler/models-srmd'],
                label+' · mejorando imagen',cwd=tools/'upscaler',progress=progress)
            command(backend,[texconv,'-nologo','-y','-f','BC1_UNORM','-m','0','-w',str(width*2),'-h',str(height*2),
                '-if','FANT','-o',stage,enhanced],label+' · comprimiendo',cwd=stage,progress=progress)
            generated=stage/(enhanced.stem+'.dds')
            _,new_width,new_height,_=bc1_identity(generated.read_bytes())
            if (new_width,new_height)!=(width*2,height*2):raise ValueError('El reescalador no produjo el tamaño esperado.')
            shutil.copy2(generated,output.with_suffix('.new'));output.with_suffix('.new').replace(output)
            for intermediate in (png,enhanced,generated):intermediate.unlink(missing_ok=True)
        entries.append(dict(id=identity,name=original.stem,original=[width,height],replacement=[width*2,height*2]))
        manifest=dict(version=1,name='Fenix Reborn HD 2×',author='By JoSuLoku @2026',complete=index==len(textures),
            method='SRMD 2× → BC1',sources=list(SOURCES),textures=entries)
        temporary=folder/'pack.new';temporary.write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8');temporary.replace(folder/'pack.json')
    if getattr(backend,'texture_cleanup',True):
        base=(backend.local/'texture-pack').resolve()
        for child in ('work','tools'):
            target=base/child
            if target.is_dir() and not target.is_symlink() and not target.is_junction() and target.resolve().parent==base:shutil.rmtree(target)
        for key in ('texture_umodel','texture_texconv','texture_upscaler'):
            item=backend.manifest[key]
            (backend.local/'downloads'/(item['sha256']+Path(urlsplit(item['url']).path).suffix)).unlink(missing_ok=True)
    settings=backend.settings();settings['hdTextures']=True;backend.save_settings(settings)
    backend.report(f'Pack HD listo · {len(entries)} texturas',100)

def build_plugin(backend):
    from backend import extract_zip
    from toolchain import environment,run
    tools=backend.local/'tools';work=backend.local/'build/texture-plugin'
    archive=backend.download(backend.manifest['texture_sdk_source'])
    source=work/'source'
    if not source.exists():extract_zip(archive,source,limit=512*1024**2)
    sdk=next(source.glob('rexglue-sdk-*'))
    patcher=backend.root/'native/texture_pack/patch_sdk.py'
    env=environment(backend)
    run(backend,[tools/'python/python.exe',patcher,sdk],env=env,phase='Preparando texturas nativas')
    out=work/'out'
    run(backend,[tools/'cmake/bin/cmake.exe','-S',backend.root/'native/texture_pack','-B',out,'-G','Ninja',
        '-DCMAKE_BUILD_TYPE=Release','-DCMAKE_C_COMPILER='+str(tools/'llvm/bin/clang-cl.exe'),
        '-DCMAKE_CXX_COMPILER='+str(tools/'llvm/bin/clang-cl.exe'),'-DCMAKE_LINKER='+str(tools/'llvm/bin/lld-link.exe'),
        '-DCMAKE_RC_COMPILER='+str(tools/'llvm/bin/llvm-rc.exe'),'-DCMAKE_MT='+str(tools/'llvm/bin/llvm-mt.exe'),
        '-DCMAKE_MAKE_PROGRAM='+(tools/'ninja/ninja.exe').as_posix(),'-DREXGLUE_ROOT='+sdk.as_posix(),'-DREXGLUE_DIST='+(tools/'sdk').as_posix()],
        env=env,phase='Preparando cargador de texturas')
    run(backend,[tools/'cmake/bin/cmake.exe','--build',out,'--target','rexgpu-xenos','--parallel','4'],env=env,phase='Preparando cargador de texturas')
    destination=backend.runtime/'bin/rexgpu-xenos.dll'
    shutil.copy2(out/'bin/rexgpu-xenos.dll',destination)
    from backend import file_hash
    (backend.runtime/'texture_loader.json').write_text(json.dumps(dict(version=1,sha256=file_hash(destination))),'utf-8')
