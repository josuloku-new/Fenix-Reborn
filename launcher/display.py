"""Supported video modes and graphics controls shared by settings and native UI."""
RESOLUTIONS={
    '854 × 480 · 480p':'854x480',
    '960 × 540 · 540p':'960x540',
    '1280 × 720 · 720p':'1280x720',
    '1600 × 900 · 900p':'1600x900',
    '1920 × 1080 · 1080p':'1920x1080',
    '2560 × 1440 · 1440p':'2560x1440',
    '3840 × 2160 · 4K':'3840x2160',
}
SCALES={'1× · Menor carga':1,'2× · Más detalle':2,'3× · Mayor carga':3,
        '4× · Experimental':4,'5× · Experimental':5,'6× · 8K desde 720p':6}
REFRESH_RATES={f'{rate} Hz':rate for rate in (30,50,60,75,90,120,144,165,180,200,240)}
ANTIALIASING={'Desactivado':'none','FXAA':'fxaa','FXAA intenso':'fxaa_extreme'}
TEXTURE_FILTERS={'Según el juego':-1,'Desactivado':0,'1×':1,'2×':2,'4×':3,'8×':4,'16×':5}
DEFAULTS=dict(resolution='1280x720',scale=1,refreshRate=60,vsync=True,antialiasing='none',anisotropic=3,showFps=False)
PRESETS={
    'Predeterminado':{k:v for k,v in DEFAULTS.items() if k not in ('showFps','refreshRate')},
    'Rendimiento':dict(resolution='1280x720',scale=1,vsync=True,antialiasing='none',anisotropic=-1),
    'Equilibrado':dict(resolution='1920x1080',scale=1,vsync=True,antialiasing='fxaa',anisotropic=3),
    'Calidad':dict(resolution='1920x1080',scale=2,vsync=True,antialiasing='fxaa',anisotropic=5),
    '8K experimental':dict(resolution='1280x720',scale=6,vsync=True,antialiasing='none',anisotropic=5),
}
