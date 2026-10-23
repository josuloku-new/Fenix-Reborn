"""Native Tk windows for preparation and persistent game configuration."""
import copy
import os
import tkinter as tk
from tkinter import ttk,filedialog
from backend import BINDINGS,MODS,AUTHOR,VERSION
from display import RESOLUTIONS,SCALES,REFRESH_RATES,ANTIALIASING,TEXTURE_FILTERS,PRESETS
from branding import NAME,SETUP_NAME,ICON_NAME

BG='#101217';PANEL='#1b1e26';SIDE='#15181f';TEXT='#f0eee8';MUTED='#a4a9b5';RED='#d33441'

class App(tk.Tk):
    def __init__(self,backend,mode='setup',*,hidden=False,open_setup=None,tab='controls'):
        super().__init__()
        if hidden:self.withdraw()
        self.backend=backend;self.mode=mode;self.open_setup=open_setup;self.closed=False
        self.step=0;self.tab=tab;self.previous=None;self.state=backend.state()
        self.previous=(self.state['toolsReady'],self.state['gameReady'],self.state['runtimeReady'])
        if mode=='setup' and self.state['toolsReady']:self.step=3 if self.state['gameReady'] else 2
        self.edit=copy.deepcopy(backend.settings());self.accepted=tk.BooleanVar(self,False)
        self.cleanup=tk.BooleanVar(self,backend.cleanup_after_build)
        self.iso=tk.StringVar(self,backend.selected_iso);self.status=tk.StringVar(self,'')
        self.title(NAME+' · '+('Configuración' if mode=='configure' else 'Preparación'))
        self.icon_path=backend.root/'launcher/assets'/ICON_NAME
        self.iconbitmap(default=str(self.icon_path))
        self.geometry('1180x820');self.minsize(980,680);self.configure(bg=BG)
        self.option_add('*Font',('Segoe UI',10));self.option_add('*TCombobox*Listbox.background',PANEL)
        self.option_add('*TCombobox*Listbox.foreground',TEXT)
        self.protocol('WM_DELETE_WINDOW',self.close)
        style=ttk.Style(self);style.theme_use('clam')
        style.configure('.',background=BG,foreground=TEXT,font=('Segoe UI',10))
        style.configure('TFrame',background=BG);style.configure('TLabel',background=BG,foreground=TEXT)
        style.configure('TButton',padding=(18,11),background='#292e39',foreground=TEXT,borderwidth=0)
        style.map('TButton',background=[('active','#3b4251'),('disabled','#20242c')],foreground=[('disabled','#747b88')])
        style.configure('Primary.TButton',background=RED,foreground='white')
        style.map('Primary.TButton',background=[('active','#ec4655'),('disabled','#602b34')])
        style.configure('TEntry',fieldbackground='#0e1117',foreground=TEXT,insertcolor=TEXT,padding=7)
        style.configure('TCombobox',fieldbackground=PANEL,foreground=TEXT,arrowcolor=TEXT,padding=7)
        style.map('TCombobox',fieldbackground=[('readonly',PANEL)],foreground=[('readonly',TEXT)])
        style.configure('TSpinbox',fieldbackground=PANEL,foreground=TEXT,arrowcolor=TEXT,padding=6)
        style.configure('TCheckbutton',background=BG,foreground=TEXT,indicatorcolor='#343b48',padding=4)
        style.map('TCheckbutton',background=[('active',BG)],indicatorcolor=[('selected',RED)])
        style.configure('Horizontal.TProgressbar',background=RED,troughcolor='#2c313d',borderwidth=0)
        self.grid_rowconfigure(0,weight=1);self.grid_columnconfigure(1,weight=1)
        self.sidebar=tk.Frame(self,bg=SIDE,width=260);self.sidebar.grid(row=0,column=0,sticky='nsew');self.sidebar.grid_propagate(False)
        self.label(self.sidebar,'RECOMPILACIÓN ESTÁTICA',fg=RED,bg=SIDE,font=('Segoe UI',9,'bold')).pack(anchor='w',padx=26,pady=(32,20))
        self.label(self.sidebar,'FENIX',bg=SIDE,font=('Segoe UI',34,'bold')).pack(anchor='w',padx=24)
        self.label(self.sidebar,'REBORN',fg=RED,bg=SIDE,font=('Segoe UI',27,'bold')).pack(anchor='w',padx=26)
        self.label(self.sidebar,'VERSIÓN '+VERSION,bg=SIDE,fg=MUTED,font=('Segoe UI',9)).pack(anchor='w',padx=28,pady=(12,28))
        self.side_nav=tk.Frame(self.sidebar,bg=SIDE);self.side_nav.pack(fill='x',padx=18)
        self.label(self.sidebar,AUTHOR,bg=SIDE,font=('Segoe UI',10)).pack(side='bottom',anchor='w',padx=27,pady=28)
        self.label(self.sidebar,'☠',bg=SIDE,fg='#87313f',font=('Segoe UI Symbol',98)).pack(expand=True)
        self.main=tk.Frame(self,bg=BG);self.main.grid(row=0,column=1,sticky='nsew',padx=34,pady=28)
        self.main.grid_columnconfigure(0,weight=1);self.main.grid_rowconfigure(1,weight=1)
        self.heading=tk.Frame(self.main,bg=BG);self.heading.grid(row=0,column=0,sticky='ew')
        self.stage=self.label(self.heading,'',fg=RED,font=('Segoe UI',9,'bold'));self.stage.pack(anchor='w')
        self.title_label=self.label(self.heading,'',font=('Segoe UI',31,'bold'));self.title_label.pack(anchor='w',pady=(18,10))
        self.lead=self.label(self.heading,'',fg=MUTED,wraplength=750);self.lead.pack(anchor='w',pady=(0,20))
        self.preparation_notice=tk.Frame(self.heading,bg=PANEL,padx=16,pady=12)
        preparation_text=tk.Frame(self.preparation_notice,bg=PANEL);preparation_text.pack(side='left',fill='x',expand=True)
        self.label(preparation_text,'Falta terminar la preparación del juego.',bg=PANEL,fg='#e4a0aa',font=('Segoe UI',11,'bold')).pack(anchor='w')
        self.label(preparation_text,'«Guardar y ejecutar» se activará al terminar.',bg=PANEL,wraplength=460,justify='left').pack(anchor='w',pady=(5,0))
        self.preparation_button=ttk.Button(self.preparation_notice,text='Ver preparación',command=self.open_preparation)
        if self.open_setup:self.preparation_button.pack(side='right',padx=(14,0))
        self.body=tk.Frame(self.main,bg=BG);self.body.grid(row=1,column=0,sticky='nsew')
        self.progress_frame=tk.Frame(self.main,bg=PANEL,padx=18,pady=14);self.progress_frame.grid(row=2,column=0,sticky='ew',pady=(12,8))
        self.progress_title=self.label(self.progress_frame,'',bg=PANEL,fg=RED,font=('Segoe UI',10,'bold'));self.progress_title.pack(anchor='w')
        self.progress_message=self.label(self.progress_frame,'',bg=PANEL,wraplength=720,justify='left');self.progress_message.pack(anchor='w',pady=(6,10))
        self.progress=ttk.Progressbar(self.progress_frame,mode='determinate');self.progress.pack(fill='x')
        self.progress_frame.grid_remove();self.indeterminate=False
        self.status_label=self.label(self.main,'',fg=MUTED,wraplength=750,justify='left');self.status_label.grid(row=3,column=0,sticky='ew',pady=(8,4))
        self.actions=tk.Frame(self.main,bg=BG);self.actions.grid(row=4,column=0,sticky='ew',pady=(12,0))
        self.back=ttk.Button(self.actions,text='← Atrás',command=self.go_back);self.back.pack(side='left')
        self.next=ttk.Button(self.actions,text='Comenzar →',style='Primary.TButton',command=self.go_next);self.next.pack(side='right')
        self.run_button=None
        if self.mode=='configure':
            self.next.configure(style='TButton')
            self.run_button=ttk.Button(self.actions,text='Guardar y ejecutar',style='Primary.TButton',command=self.save_and_run)
            self.run_button.pack(side='right',padx=(0,12))
        self.accepted.trace_add('write',lambda *_:self.update_actions())
        self.variables={};self.binding_vars={k:tk.StringVar(self,self.edit['bindings'][k]) for k,_,_ in BINDINGS}
        self.mod_vars={m['key']:tk.BooleanVar(self,self.edit['mods'][m['key']]) for m in MODS}
        self.hd_textures=tk.BooleanVar(self,self.edit['hdTextures'])
        self.hd_cleanup=tk.BooleanVar(self,True)
        self.texture_job_done=False
        self.mode_var=tk.StringVar(self,'Mando' if self.edit['inputMode']=='pad' else 'Teclado + ratón')
        self.direct_mouse=tk.BooleanVar(self,self.edit['directMouse'])
        self.smoothing_enabled=tk.BooleanVar(self,self.edit['smoothingEnabled'])
        self.sensitivity=tk.StringVar(self,str(self.edit['sensitivity']));self.aim_sensitivity=tk.StringVar(self,str(self.edit['aimSensitivity']));self.smoothing=tk.StringVar(self,str(self.edit['smoothing']));self.deadzone=tk.StringVar(self,str(self.edit['deadzone']))
        self.resolutions=RESOLUTIONS
        self.resolution=tk.StringVar(self,next(k for k,v in RESOLUTIONS.items() if v==self.edit['resolution']))
        self.render_scale=tk.StringVar(self,next(k for k,v in SCALES.items() if v==self.edit['scale']))
        self.refresh_rate=tk.StringVar(self,next(k for k,v in REFRESH_RATES.items() if v==self.edit['refreshRate']))
        self.antialiasing=tk.StringVar(self,next(k for k,v in ANTIALIASING.items() if v==self.edit['antialiasing']))
        self.anisotropic=tk.StringVar(self,next(k for k,v in TEXTURE_FILTERS.items() if v==self.edit['anisotropic']))
        self.vsync=tk.BooleanVar(self,self.edit['vsync']);self.show_fps=tk.BooleanVar(self,self.edit['showFps'])
        self.graphics_preset=tk.StringVar(self,'Personalizado')
        for variable in (self.resolution,self.render_scale,self.antialiasing,self.anisotropic,self.vsync):
            variable.trace_add('write',lambda *_:self.update_graphics_preset())
        self.update_graphics_preset()
        self.languages={l['label']:l['code'] for l in self.state['languages']}
        self.language=tk.StringVar(self,next((k for k,v in self.languages.items() if v==self.edit['language']),''))
        self.render();self.poll_timer=self.after(300,self.poll)
        self.bind('<MouseWheel>',self.scroll_bindings)

    def label(self,parent,text,**kwargs):
        return tk.Label(parent,text=text,bg=kwargs.pop('bg',BG),fg=kwargs.pop('fg',TEXT),**kwargs)

    def busy(self):return self.state['job']['state']=='running'

    def render(self):
        if self.mode=='configure' and not (self.state['gameReady'] and self.state['runtimeReady']):
            self.preparation_notice.pack(fill='x',pady=(0,16))
        else:self.preparation_notice.pack_forget()
        for widget in self.body.winfo_children():widget.destroy()
        for widget in self.side_nav.winfo_children():widget.destroy()
        if self.mode=='configure':
            self.stage.configure(text='CONFIGURACIÓN');self.title_label.configure(text='A tu medida.')
            self.lead.configure(text='Los cambios se aplican al iniciar el juego.')
            if not (self.state['gameReady'] and self.state['runtimeReady']):self.lead.configure(text='Termina la preparación en '+SETUP_NAME+'.')
            for key,title in (('controls','Controles'),('display','Imagen'),('mods','Mods')):
                button=tk.Button(self.side_nav,text=title,command=lambda k=key:self.show_tab(k),bg='#38252f' if self.tab==key else SIDE,fg=TEXT,activebackground=PANEL,activeforeground=TEXT,bd=0,anchor='w',padx=15,pady=13)
                button.pack(fill='x',pady=3)
            self.back.pack_forget()
            if not self.state['gameReady']:
                self.label(self.body,'Prepara el juego para configurar sus ajustes.',fg=MUTED).pack(anchor='w',pady=20)
            else:self.render_configuration()
        else:
            titles=['Bienvenida','Herramientas','Tu ISO','Preparar juego']
            self.stage.configure(text=f'PREPARACIÓN / {self.step+1:02} DE 04')
            for i,title in enumerate(titles):
                self.label(self.side_nav,f'{i+1:02}   {title}',bg='#38252f' if i==self.step else SIDE,fg=TEXT if i==self.step else MUTED,anchor='w',padx=13,pady=13).pack(fill='x',pady=3)
            [self.welcome,self.tools,self.iso_page,self.build_page][self.step]()
        self.update_actions()

    def welcome(self):
        self.title_label.configure(text='Vuelve a la lucha.');self.lead.configure(text='Prepara tu juego, paso a paso.')
        for title,text in [('01  Prepara tu equipo','Descarga y preparación.'),('02  Selecciona tu ISO','Elige tu copia del juego.'),('03  Entra en combate','Acceso al juego y configurador independiente.')]:
            card=tk.Frame(self.body,bg=PANEL,padx=23,pady=19);card.pack(fill='x',pady=7)
            self.label(card,title,bg=PANEL,font=('Segoe UI',14,'bold')).pack(anchor='w')
            self.label(card,text,bg=PANEL,fg=MUTED).pack(anchor='w',pady=(7,0))

    def tools(self):
        self.title_label.configure(text='Prepara tu equipo.');self.lead.configure(text='Prepara los archivos necesarios para continuar.')
        for title,ready in [('Preparación del juego',self.state['toolsReady']),('Extracción de ISO',self.state['extractorReady'])]:
            row=tk.Frame(self.body,bg=PANEL,padx=20,pady=20);row.pack(fill='x',pady=5)
            self.label(row,title,bg=PANEL,font=('Segoe UI',12,'bold')).pack(side='left')
            self.label(row,'PREPARADO' if ready else 'PENDIENTE',bg=PANEL,fg='#a4c9ac' if ready else MUTED).pack(side='right')
        ttk.Checkbutton(self.body,text='He leído y acepto las condiciones de Microsoft.',variable=self.accepted).pack(anchor='w',pady=(23,0))
        link=self.label(self.body,'Leer condiciones',fg='#e4a0aa',cursor='hand2');link.pack(anchor='w',padx=28,pady=(0,12));link.bind('<Button-1>',lambda _:os.startfile('https://go.microsoft.com/fwlink/?LinkId=2327714'))
        self.prepare_button=ttk.Button(self.body,text='Descargar y preparar',style='Primary.TButton',command=lambda:self.start_job('dependencies'));self.prepare_button.pack(anchor='w',pady=10)

    def iso_page(self):
        self.title_label.configure(text='Selecciona tu ISO.');self.lead.configure(text='Elige una ISO compatible con Fenix Reborn.')
        row=tk.Frame(self.body,bg=BG);row.pack(fill='x',pady=(8,15));row.columnconfigure(0,weight=1)
        ttk.Entry(row,textvariable=self.iso,state='readonly').grid(row=0,column=0,sticky='ew',padx=(0,10))
        self.select_button=ttk.Button(row,text='Seleccionar ISO…',command=self.select_iso);self.select_button.grid(row=0,column=1)
        self.label(self.body,'Datos verificados.' if self.state['gameReady'] else 'Necesitarás al menos 30 GB libres.',fg=MUTED).pack(anchor='w',pady=14)
        self.extract_button=ttk.Button(self.body,text='Extraer y verificar',style='Primary.TButton',command=lambda:self.start_job('extract'));self.extract_button.pack(anchor='w',pady=10)

    def build_page(self):
        self.title_label.configure(text='Prepara tu juego.');self.lead.configure(text='Este paso puede tardar varios minutos.')
        self.cleanup_checkbox=ttk.Checkbutton(self.body,text='Liberar espacio al terminar',variable=self.cleanup)
        self.cleanup_checkbox.pack(anchor='w',pady=(16,4))
        self.label(self.body,'Elimina descargas y herramientas de preparación. Conserva el juego, tus ajustes y partidas.',fg=MUTED,wraplength=700,justify='left').pack(anchor='w',padx=28,pady=(0,14))
        self.build_button=ttk.Button(self.body,text='Preparar juego',style='Primary.TButton',command=lambda:self.start_job('build'));self.build_button.pack(anchor='w',pady=14)

    def select_iso(self):
        selected=filedialog.askopenfilename(parent=self,title='Selecciona tu ISO',filetypes=[('Imagen Xbox 360','*.iso')])
        if selected:self.backend.selected_iso=selected;self.iso.set(selected);self.update_actions()

    def start_job(self,action):
        try:
            if action=='dependencies':self.backend.license_accepted=self.accepted.get()
            if action=='build':self.backend.cleanup_after_build=self.cleanup.get()
            self.backend.start(action);self.state=self.backend.state();self.update_actions()
        except Exception as exc:self.show_error(exc)

    def show_tab(self,key):self.tab=key;self.render()

    def render_configuration(self):
        language_row=tk.Frame(self.body,bg=BG);language_row.pack(fill='x',pady=(0,20))
        self.label(language_row,'Idioma · audio y subtítulos',fg=MUTED).pack(side='left')
        ttk.Combobox(language_row,textvariable=self.language,values=list(self.languages),state='readonly',width=24).pack(side='right')
        panel=tk.Frame(self.body,bg=BG);panel.pack(fill='both',expand=True)
        if self.tab=='controls':self.controls(panel)
        elif self.tab=='display':self.display_controls(panel)
        else:
            self.mods_canvas=tk.Canvas(panel,bg=BG,highlightthickness=0,height=340)
            self.mods_canvas.pack(side='left',fill='both',expand=True)
            bar=ttk.Scrollbar(panel,command=self.mods_canvas.yview);bar.pack(side='right',fill='y')
            self.mods_canvas.configure(yscrollcommand=bar.set)
            cards=tk.Frame(self.mods_canvas,bg=BG);window=self.mods_canvas.create_window((0,0),window=cards,anchor='nw')
            cards.bind('<Configure>',lambda _:self.mods_canvas.configure(scrollregion=self.mods_canvas.bbox('all')))
            self.mods_canvas.bind('<Configure>',lambda event:self.mods_canvas.itemconfigure(window,width=event.width))
            cards.grid_columnconfigure(0,weight=1);cards.grid_columnconfigure(1,weight=1)
            for i,mod in enumerate(MODS):
                card=tk.Frame(cards,bg=PANEL,padx=14,pady=12);card.grid(row=i//2,column=i%2,sticky='nsew',padx=5,pady=5)
                ttk.Checkbutton(card,text=mod['title'],variable=self.mod_vars[mod['key']]).pack(anchor='w')
                self.label(card,mod['detail'],bg=PANEL,fg=MUTED,wraplength=300,justify='left').pack(anchor='w',padx=4,pady=(7,9))
                self.label(card,'Gracias a '+mod['authors'],bg=PANEL,fg='#e4a0aa',font=('Segoe UI',9)).pack(anchor='w',padx=4)
            hd=self.state.get('texturePack',dict(ready=False,count=0,loader=False))
            card=tk.Frame(cards,bg=PANEL,padx=14,pady=14)
            card.grid(row=(len(MODS)+1)//2,column=0,columnspan=2,sticky='ew',padx=5,pady=8)
            ttk.Checkbutton(card,text='Pack HD 2×',variable=self.hd_textures,
                state='normal' if hd['ready'] else 'disabled').pack(anchor='w')
            self.label(card,'Personajes, armas, objetos y zona inicial del hospital. Reescalado por IA de tu copia del juego.',
                bg=PANEL,fg=MUTED,wraplength=660,justify='left').pack(anchor='w',pady=(5,8))
            self.label(card,f"{hd['count']} texturas preparadas" if hd['count'] else 'Todavía sin preparar',bg=PANEL,fg=TEXT).pack(anchor='w')
            self.hd_prepare=ttk.Button(card,text='Preparar pack HD (2×)',command=self.prepare_texture_pack)
            self.hd_prepare.pack(anchor='w',pady=(10,5))
            ttk.Checkbutton(card,text='Eliminar los archivos de preparación al terminar',variable=self.hd_cleanup).pack(anchor='w')
            self.label(card,'Gracias a Gildor, nihui / Kai Zhang (SRMD), Microsoft / DirectXTex, ReXGlue y FaliGame (referencia).',
                bg=PANEL,fg='#e4a0aa',wraplength=660,justify='left',font=('Segoe UI',9)).pack(anchor='w',pady=(8,0))
        self.reset_button=ttk.Button(self.body,text='Restablecer',command=self.reset);self.reset_button.pack(anchor='w',pady=(16,4))

    def display_controls(self,parent):
        self.label(parent,'Pantalla completa · siempre activa',fg=MUTED).pack(anchor='w',pady=(0,10))
        fields=tk.Frame(parent,bg=BG);fields.pack(fill='x')
        fields.columnconfigure(0,weight=1);fields.columnconfigure(1,weight=1)
        for i,(title,variable,values) in enumerate((
          ('Perfil gráfico',self.graphics_preset,[*PRESETS,'Personalizado']),('Frecuencia del juego',self.refresh_rate,REFRESH_RATES),
          ('Resolución de vídeo',self.resolution,RESOLUTIONS),('Escala de renderizado',self.render_scale,SCALES),
          ('Suavizado de bordes',self.antialiasing,ANTIALIASING),('Filtrado de texturas',self.anisotropic,TEXTURE_FILTERS))):
            cell=tk.Frame(fields,bg=BG);cell.grid(row=i//2,column=i%2,sticky='ew',padx=(0,16),pady=(0,12))
            self.label(cell,title,fg=MUTED).pack(anchor='w',pady=(0,7))
            combo=ttk.Combobox(cell,textvariable=variable,values=list(values),state='readonly',width=28);combo.pack(fill='x')
            if variable is self.graphics_preset:combo.bind('<<ComboboxSelected>>',lambda _:self.apply_graphics_preset())
        ttk.Checkbutton(fields,text='Sincronización vertical (VSync)',variable=self.vsync).grid(row=3,column=0,sticky='w',pady=8)
        ttk.Checkbutton(fields,text='Mostrar contador de FPS',variable=self.show_fps).grid(row=3,column=1,sticky='w',pady=8)
        self.label(parent,'8K: supermuestreo 6× desde 720p, con mucha carga de GPU. Los Hz del monitor se ajustan en Windows; 240 Hz no garantiza 240 FPS.',fg=MUTED,wraplength=700,justify='left').pack(anchor='w',pady=(10,8))
        ttk.Button(parent,text='Usar ajustes de rendimiento',command=lambda:self.apply_graphics_preset('Rendimiento')).pack(anchor='w')

    def display_settings(self):
        return dict(resolution=RESOLUTIONS[self.resolution.get()],scale=SCALES[self.render_scale.get()],refreshRate=REFRESH_RATES[self.refresh_rate.get()],
          antialiasing=ANTIALIASING[self.antialiasing.get()],anisotropic=TEXTURE_FILTERS[self.anisotropic.get()],
          vsync=self.vsync.get(),showFps=self.show_fps.get())

    def update_graphics_preset(self):
        current=self.display_settings()
        self.graphics_preset.set(next((name for name,settings in PRESETS.items() if all(current[k]==v for k,v in settings.items())),'Personalizado'))

    def apply_graphics_preset(self,name=None):
        values=PRESETS.get(name or self.graphics_preset.get())
        if values:self.set_display_settings(values)

    def set_display_settings(self,values):
        for variable,mapping,key in ((self.resolution,RESOLUTIONS,'resolution'),(self.render_scale,SCALES,'scale'),
          (self.antialiasing,ANTIALIASING,'antialiasing'),(self.anisotropic,TEXTURE_FILTERS,'anisotropic')):
            variable.set(next(label for label,value in mapping.items() if value==values[key]))
        self.vsync.set(values['vsync'])
        if 'refreshRate' in values:self.refresh_rate.set(next(k for k,v in REFRESH_RATES.items() if v==values['refreshRate']))
        if 'showFps' in values:self.show_fps.set(values['showFps'])
        self.update_graphics_preset()

    def controls(self,parent):
        row=tk.Frame(parent,bg=BG);row.pack(fill='x',pady=(0,15))
        self.label(row,'Dispositivo',fg=MUTED).pack(side='left')
        combo=ttk.Combobox(row,textvariable=self.mode_var,values=['Teclado + ratón','Mando'],state='readonly',width=24);combo.pack(side='right');combo.bind('<<ComboboxSelected>>',lambda _:self.update_mouse_controls())
        direct=ttk.Checkbutton(parent,text='Ratón directo a la cámara',variable=self.direct_mouse,command=self.update_mouse_controls);direct.pack(anchor='w',pady=(0,5))
        self.label(parent,'Gracias a marinesciencedude y Clippy95 · Mousehook',fg=MUTED,font=('Segoe UI',9)).pack(anchor='w',pady=(0,12))
        fields=tk.Frame(parent,bg=BG);fields.pack(fill='x',pady=(0,15));self.mouse_widgets=[direct]
        for i,(title,var,lo,hi,inc) in enumerate([('Sensibilidad cámara',self.sensitivity,.01,10,.1),('Sensibilidad mira',self.aim_sensitivity,.01,10,.05),('Suavizado (ms)',self.smoothing,0,30,1),('Zona muerta',self.deadzone,0,16000,500)]):
            fields.columnconfigure(i,weight=1);cell=tk.Frame(fields,bg=BG);cell.grid(row=0,column=i,sticky='ew',padx=(0,15))
            if var is self.smoothing:
                toggle=ttk.Checkbutton(cell,text='Suavizado (ms)',variable=self.smoothing_enabled,command=self.toggle_smoothing)
                toggle.pack(anchor='w',pady=(0,7));self.mouse_widgets.append(toggle)
            else:self.label(cell,title,fg=MUTED).pack(anchor='w',pady=(0,7))
            entry=ttk.Spinbox(cell,textvariable=var,from_=lo,to=hi,increment=inc,width=12);entry.pack(fill='x');self.mouse_widgets.append(entry)
            if var is self.deadzone:self.deadzone_entry=entry
            if var is self.smoothing:self.smoothing_entry=entry
        scroll=tk.Frame(parent,bg=BG);scroll.pack(fill='both',expand=True)
        self.bindings_canvas=tk.Canvas(scroll,bg=BG,highlightthickness=0,height=280);self.bindings_canvas.pack(side='left',fill='both',expand=True)
        bar=ttk.Scrollbar(scroll,command=self.bindings_canvas.yview);bar.pack(side='right',fill='y');self.bindings_canvas.configure(yscrollcommand=bar.set)
        form=tk.Frame(self.bindings_canvas,bg=BG);window=self.bindings_canvas.create_window((0,0),window=form,anchor='nw')
        form.bind('<Configure>',lambda _:self.bindings_canvas.configure(scrollregion=self.bindings_canvas.bbox('all')))
        self.bindings_canvas.bind('<Configure>',lambda event:self.bindings_canvas.itemconfigure(window,width=event.width))
        form.columnconfigure(0,weight=1);form.columnconfigure(1,weight=1)
        for i,(key,title,_) in enumerate(BINDINGS):
            cell=tk.Frame(form,bg=BG);cell.grid(row=i//2,column=i%2,sticky='ew',padx=(0,15),pady=4)
            self.label(cell,title,font=('Segoe UI',9)).pack(side='left')
            entry=ttk.Entry(cell,textvariable=self.binding_vars[key],width=12);entry.pack(side='right');self.mouse_widgets.append(entry)
        self.label(parent,'Separa teclas alternativas con una coma. F1, F3, F4 y F7 están reservadas.',fg=MUTED,font=('Segoe UI',9)).pack(anchor='w',pady=(10,0))
        self.update_mouse_controls()

    def update_mouse_controls(self):
        state='disabled' if self.mode_var.get()=='Mando' else 'normal'
        for widget in self.mouse_widgets:widget.configure(state=state)
        self.deadzone_entry.configure(state='disabled' if self.direct_mouse.get() else state)
        self.smoothing_entry.configure(state=state if self.smoothing_enabled.get() else 'disabled')

    def toggle_smoothing(self):
        if self.smoothing_enabled.get():
            try:valid=float(self.smoothing.get())>0
            except ValueError:valid=False
            if not valid:self.smoothing.set('2')
        self.update_mouse_controls()

    def scroll_bindings(self,event):
        for name in ('bindings_canvas','mods_canvas'):
            canvas=getattr(self,name,None)
            if canvas is not None and canvas.winfo_exists() and str(event.widget).startswith(str(canvas)):
                canvas.yview_scroll(-int(event.delta/120),'units');return

    def save(self):
        try:
            data=copy.deepcopy(self.edit);data.update(language=self.languages.get(self.language.get(),''),inputMode='pad' if self.mode_var.get()=='Mando' else 'keyboard_mouse',directMouse=self.direct_mouse.get(),sensitivity=float(self.sensitivity.get()),aimSensitivity=float(self.aim_sensitivity.get()),smoothing=float(self.smoothing.get()),smoothingEnabled=self.smoothing_enabled.get(),hdTextures=self.hd_textures.get(),deadzone=float(self.deadzone.get()),**self.display_settings(),bindings={k:v.get() for k,v in self.binding_vars.items()},mods={k:v.get() for k,v in self.mod_vars.items()})
            self.backend.save_settings(data);self.edit=data;return True
        except Exception as exc:self.show_error(exc);return False

    def reset(self):
        data=self.backend.defaults();self.edit=data;self.mode_var.set('Teclado + ratón')
        self.direct_mouse.set(data['directMouse'])
        self.smoothing_enabled.set(data['smoothingEnabled'])
        self.hd_textures.set(data['hdTextures'])
        for var,key in [(self.sensitivity,'sensitivity'),(self.aim_sensitivity,'aimSensitivity'),(self.smoothing,'smoothing'),(self.deadzone,'deadzone')]:var.set(str(data[key]))
        self.set_display_settings(data)
        self.language.set(next((k for k,v in self.languages.items() if v==data['language']),''))
        for k,var in self.binding_vars.items():var.set(data['bindings'][k])
        for k,var in self.mod_vars.items():var.set(data['mods'][k])
        self.render()

    def update_actions(self):
        if self.mode=='setup' and self.step==3 and hasattr(self,'cleanup_checkbox') and self.cleanup_checkbox.winfo_exists():
            self.cleanup_checkbox.configure(state='disabled' if self.busy() else 'normal')
        busy=self.busy()
        hd_button=getattr(self,'hd_prepare',None)
        if hd_button is not None and hd_button.winfo_exists():
            hd_button.configure(state='normal' if self.state['runtimeReady'] and not busy and not self.state['playing'] else 'disabled')
        if self.mode=='configure':
            self.next.configure(text='Guardar y salir',state='normal' if self.state['gameReady'] and not busy else 'disabled')
            self.run_button.configure(state='normal' if self.state['gameReady'] and self.state['runtimeReady'] and not self.state['playing'] and not busy else 'disabled')
            return
        allowed=[True,self.state['toolsReady'],self.state['gameReady'],self.state['runtimeReady']]
        self.back.configure(state='normal' if self.step and not busy else 'disabled')
        self.next.configure(text='Comenzar →' if self.step==0 else 'Finalizar' if self.step==3 else 'Continuar →',state='normal' if allowed[self.step] and not busy else 'disabled')
        for name,enabled in [('prepare_button',self.accepted.get()),('select_button',True),('extract_button',bool(self.iso.get()) and not self.state['gameReady']),('build_button',self.state['toolsReady'] and self.state['gameReady'])]:
            button=getattr(self,name,None)
            if button is not None and button.winfo_exists():button.configure(state='normal' if enabled and not busy else 'disabled')

    def go_back(self):
        if not self.busy() and self.step:self.step-=1;self.status_label.configure(text='');self.render()

    def go_next(self):
        if self.mode=='configure':
            if self.save():self.close()
        elif self.step==3:
            try:
                from entrypoints import finish_preparation
                finish_preparation(self.backend);self.close()
            except Exception as exc:self.show_error(exc)
        else:self.step+=1;self.status_label.configure(text='');self.render()

    def save_and_run(self):
        if not self.save():return
        try:self.backend.launch();self.close()
        except Exception as exc:self.show_error(exc)

    def prepare_texture_pack(self):
        if not self.save():return
        try:
            self.backend.texture_cleanup=self.hd_cleanup.get()
            self.texture_job_done=False
            self.backend.start('texture_pack');self.state=self.backend.state();self.update_actions()
        except Exception as exc:self.show_error(exc)

    def open_preparation(self):
        if not self.open_setup:return
        if self.mode=='configure' and self.state['gameReady'] and not self.save():return
        self.open_setup();self.close()

    def show_error(self,exc):self.status_label.configure(text=str(exc),fg='#ff8994')

    def poll(self):
        if self.closed:return
        self.state=self.backend.state();job=self.state['job']
        if job['phase']=='texture_pack' and job['state']=='done' and not self.texture_job_done:
            self.texture_job_done=True;self.hd_textures.set(self.state['settings']['hdTextures'])
            self.edit=copy.deepcopy(self.state['settings']);self.status_label.configure(text='Pack HD listo.',fg=TEXT);self.render()
        if self.mode=='setup' and job['phase']=='build' and job['state']=='done' and self.state['runtimeReady']:self.close();return
        readiness=(self.state['toolsReady'],self.state['gameReady'],self.state['runtimeReady'])
        if self.previous is not None and readiness!=self.previous:
            if self.mode=='configure' and not self.languages and self.state['languages']:
                self.languages={l['label']:l['code'] for l in self.state['languages']}
                code=self.state['settings']['language'];self.language.set(next((k for k,v in self.languages.items() if v==code),next(iter(self.languages))))
            self.render()
        self.previous=readiness
        if job['state'] in ('running','error'):
            self.progress_frame.grid();value=job['progress']
            self.progress_title.configure(text='PREPARACIÓN INTERRUMPIDA' if job['state']=='error' else 'EN CURSO'+(f' · {value:.0f}%' if value is not None else ''))
            self.progress_message.configure(text=job['message'],fg='#ff8994' if job['state']=='error' else TEXT)
            if value is None and job['state']=='running':
                if not self.indeterminate:self.progress.configure(mode='indeterminate');self.progress.start(12);self.indeterminate=True
            else:
                self.progress.stop();self.indeterminate=False;self.progress.configure(mode='determinate',value=value or 0)
        else:self.progress_frame.grid_remove()
        self.update_actions();self.poll_timer=self.after(500,self.poll)

    def close(self):
        if self.busy():self.show_error('Espera a que termine la operación en curso.');return
        self.closed=True;self.destroy()

    def destroy(self):
        self.closed=True
        if getattr(self,'poll_timer',None):
            self.after_cancel(self.poll_timer);self.poll_timer=None
        super().destroy()
