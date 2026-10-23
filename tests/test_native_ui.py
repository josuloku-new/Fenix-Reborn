import json
from pathlib import Path
import tempfile
import tkinter as tk
import unittest
import sys
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
from backend import Backend,XEX_SHA256,AUTHOR
from ui import App
from display import RESOLUTIONS,SCALES

class NativeUiTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.backend=Backend(ROOT,self.root);self.windows=[]
        cooked=self.backend.game/'GearGame/CookedXenon';cooked.mkdir(parents=True)
        xex=self.backend.game/'default.xex';xex.write_bytes(b'fixture')
        for resource in ('esn','int'):
            (cooked/f'Coalesced_{resource}.bin').touch();(cooked/f'GearGame_LOC_{resource.upper()}.xxx').touch()
        stat=xex.stat();(self.backend.local/'game_verified.json').write_text(json.dumps(dict(sha256=XEX_SHA256,size=stat.st_size,mtime_ns=stat.st_mtime_ns)))
    def tearDown(self):
        for app in self.windows:
            if not app.closed:app.destroy()
        self.temp.cleanup()
    def app(self,mode='setup',**kwargs):
        app=App(self.backend,mode,hidden=True,**kwargs);self.windows.append(app);app.update_idletasks();return app
    def texts(self,parent):
        result=[]
        for child in parent.winfo_children():
            try:result.append(str(child.cget('text')))
            except tk.TclError:pass
            result+=self.texts(child)
        return result
    def test_native_wizard_preserves_acceptance_and_shows_progress(self):
        app=self.app();app.step=1;app.render();app.accepted.set(True)
        self.backend.job.update(state='running',phase='dependencies',message='Descargando · 40 / 100 MB',progress=40)
        app.state=self.backend.state();app.render();app.poll();app.update_idletasks()
        self.assertTrue(app.accepted.get());self.assertEqual(str(app.prepare_button.cget('state')),'disabled')
        self.assertEqual(app.progress['value'],40);self.assertIn('40 / 100 MB',app.progress_message.cget('text'))
        self.assertIn(AUTHOR,self.texts(app));self.assertIn('VERSIÓN 0.1',self.texts(app))
        self.assertEqual(app.title(),'Fenix Reborn · Preparación')
        self.assertEqual(app.icon_path,ROOT/'launcher/assets/gow2.ico')
        self.assertIn('FENIX',self.texts(app));self.assertIn('REBORN',self.texts(app))
    def test_native_configuration_preserves_tabs_and_saves_presets(self):
        app=self.app('configure');self.assertEqual(app.back.winfo_manager(),'')
        app.sensitivity.set('2.7');app.aim_sensitivity.set('0.8');app.resolution.set('2560 × 1440 · 1440p');app.render_scale.set('2× · Más detalle');app.mod_vars['unlock_fps'].set(True);app.language.set('English')
        app.show_tab('mods');texts=self.texts(app)
        self.assertEqual(sum(t.startswith('Gracias a ') for t in texts),9)
        self.assertIn('Gracias a illusion y boma',texts)
        self.assertIn('Reducir desenfoque de profundidad',texts);self.assertIn('Desactivar bloom',texts)
        app.mod_vars['no_dof_blur'].set(True);app.mod_vars['no_bloom'].set(True)
        app.show_tab('display');app.show_tab('controls')
        self.assertEqual(app.sensitivity.get(),'2.7');app.go_next();self.assertTrue(app.closed)
        saved=self.backend.settings();self.assertEqual(saved['scale'],2);self.assertEqual(saved['sensitivity'],2.7)
        self.assertEqual(saved['resolution'],'2560x1440')
        self.assertEqual(saved['language'],'en-US');self.assertTrue(saved['mods']['unlock_fps'])
        self.assertTrue(saved['mods']['no_dof_blur']);self.assertTrue(saved['mods']['no_bloom'])
        reopened=self.app('configure');self.assertEqual(reopened.sensitivity.get(),'2.7')
        self.assertEqual(reopened.aim_sensitivity.get(),'0.8')
        self.assertIn('Sensibilidad cámara',self.texts(reopened));self.assertIn('Sensibilidad mira',self.texts(reopened))

    def test_hd_selection_survives_tabs_and_save_and_run(self):
        app=self.app('configure');app.show_tab('mods')
        self.assertIn('Pack HD 2×',self.texts(app));self.assertTrue(app.hd_cleanup.get())
        app.hd_textures.set(True);app.show_tab('controls');app.show_tab('display')
        app.show_tab('mods');self.assertTrue(app.hd_textures.get())
        with patch.object(self.backend,'launch') as launch:
            app.save_and_run();launch.assert_called_once()
        self.assertTrue(self.backend.settings()['hdTextures'])
        reopened=self.app('configure');self.assertTrue(reopened.hd_textures.get())
    def test_wizard_closes_only_when_build_succeeded(self):
        app=self.app();app.step=3;app.render()
        self.backend.job.update(state='error',phase='build',message='Error de prueba')
        app.poll();self.assertFalse(app.closed)
        folder=self.backend.runtime/'bin';folder.mkdir(parents=True)
        for name in ('gow2.exe','rexruntime.dll','rexgpu-xenos.dll'):(folder/name).touch()
        (self.backend.runtime/'local_build.json').write_text(json.dumps(dict(version='0.1',xex_sha256=XEX_SHA256,rebuilt_locally=True)))
        self.backend.job.update(state='done',phase='build',message='Todo listo.',progress=100)
        app.poll();self.assertTrue(app.closed)
    def test_cleanup_defaults_on_and_selection_survives_navigation(self):
        app=self.app();app.step=3;app.render();self.assertTrue(app.cleanup.get())
        self.assertIn('Liberar espacio al terminar',self.texts(app))
        app.cleanup.set(False);app.step=2;app.render();app.step=3;app.render()
        with patch.object(self.backend,'start') as start:
            app.start_job('build');start.assert_called_once_with('build')
        self.assertFalse(self.backend.cleanup_after_build)
        self.backend.job.update(state='running',phase='build');app.state=self.backend.state();app.update_actions()
        self.assertEqual(str(app.cleanup_checkbox.cget('state')),'disabled')
    def test_completed_extraction_resumes_at_compilation(self):
        with patch.object(self.backend,'tools_ready',return_value=True):app=self.app()
        self.assertEqual(app.step,3)
        self.assertEqual(app.title_label.cget('text'),'Prepara tu juego.')
    def test_configurator_exposes_both_save_actions(self):
        app=self.app('configure')
        self.assertEqual(app.next.cget('text'),'Guardar y salir')
        self.assertEqual(app.run_button.cget('text'),'Guardar y ejecutar')
        self.assertEqual(str(app.run_button.cget('state')),'disabled')
        self.assertEqual(str(app.next.cget('state')),'normal')
        self.assertEqual(app.preparation_notice.winfo_manager(),'pack')
        self.assertIn('Falta terminar la preparación del juego.',self.texts(app))
    def test_direct_mouse_setting_and_credits_survive_reopening(self):
        app=self.app('configure');self.assertTrue(app.direct_mouse.get())
        self.assertIn('Gracias a marinesciencedude y Clippy95 · Mousehook',self.texts(app))
        self.assertEqual(str(app.deadzone_entry.cget('state')),'disabled')
        app.direct_mouse.set(False);app.update_mouse_controls()
        self.assertEqual(str(app.deadzone_entry.cget('state')),'normal')
        self.assertTrue(app.save());self.assertFalse(self.app('configure').direct_mouse.get())
    def test_smoothing_toggle_remembers_amount_across_tabs_and_reopening(self):
        app=self.app('configure');self.assertFalse(app.smoothing_enabled.get())
        self.assertEqual(str(app.smoothing_entry.cget('state')),'disabled')
        app.smoothing.set('0');app.smoothing_enabled.set(True);app.toggle_smoothing()
        self.assertEqual(app.smoothing.get(),'2')
        self.assertEqual(str(app.smoothing_entry.cget('state')),'normal')
        app.smoothing.set('7');app.show_tab('mods');app.show_tab('controls')
        self.assertTrue(app.smoothing_enabled.get());self.assertTrue(app.save())
        reopened=self.app('configure');self.assertTrue(reopened.smoothing_enabled.get())
        reopened.smoothing_enabled.set(False);reopened.toggle_smoothing();self.assertTrue(reopened.save())
        again=self.app('configure');self.assertFalse(again.smoothing_enabled.get())
        self.assertEqual(again.smoothing.get(),'7.0')
        again.smoothing_enabled.set(True);again.toggle_smoothing()
        self.assertEqual(again.smoothing.get(),'7.0')
    def test_run_action_enables_when_another_process_finishes_preparation(self):
        app=self.app('configure');app.sensitivity.set('2.8')
        self.assertEqual(str(app.run_button.cget('state')),'disabled')
        folder=self.backend.runtime/'bin';folder.mkdir(parents=True)
        for name in ('gow2.exe','rexruntime.dll','rexgpu-xenos.dll'):(folder/name).touch()
        (self.backend.runtime/'local_build.json').write_text(json.dumps(dict(version='0.1',xex_sha256=XEX_SHA256,rebuilt_locally=True)))
        app.poll();app.update_idletasks()
        self.assertEqual(str(app.run_button.cget('state')),'normal')
        self.assertEqual(app.preparation_notice.winfo_manager(),'')
        self.assertEqual(app.sensitivity.get(),'2.8')
    def test_view_preparation_preserves_configuration(self):
        calls=[]
        def open_setup():calls.append(self.backend.settings()['sensitivity'])
        app=self.app('configure',open_setup=open_setup);app.sensitivity.set('3.1')
        self.assertEqual(app.preparation_button.winfo_manager(),'pack')
        app.preparation_button.invoke()
        self.assertEqual(calls,[3.1]);self.assertTrue(app.closed)
    def test_save_and_run_saves_before_launching(self):
        app=self.app('configure');app.sensitivity.set('3.4');app.mod_vars['no_motion_blur'].set(True)
        def launch():
            saved=self.backend.settings();self.assertEqual(saved['sensitivity'],3.4)
            self.assertTrue(saved['mods']['no_motion_blur'])
        with patch.object(self.backend,'launch',side_effect=launch) as mocked:
            app.save_and_run();mocked.assert_called_once()
        self.assertTrue(app.closed)
    def test_failed_launch_keeps_configurator_open(self):
        app=self.app('configure');app.sensitivity.set('2.5')
        with patch.object(self.backend,'launch',side_effect=RuntimeError('No se pudo iniciar')):app.save_and_run()
        self.assertFalse(app.closed);self.assertEqual(app.status_label.cget('text'),'No se pudo iniciar')
        self.assertEqual(self.backend.settings()['sensitivity'],2.5)
    def test_image_controls_persist_1080p_independently_of_render_scale(self):
        app=self.app('configure',tab='display');texts=self.texts(app)
        for title in ('Perfil gráfico','Resolución de vídeo','Escala de renderizado','Suavizado de bordes','Filtrado de texturas','Sincronización vertical (VSync)','Mostrar contador de FPS','Usar ajustes de rendimiento'):
            self.assertIn(title,texts)
        self.assertIn('1920 × 1080 · 1080p',app.resolutions)
        app.resolution.set('1920 × 1080 · 1080p');app.render_scale.set('1× · Menor carga')
        app.antialiasing.set('FXAA');app.anisotropic.set('16×');app.vsync.set(False);app.show_fps.set(True)
        app.show_tab('mods');app.show_tab('controls');app.show_tab('display');self.assertTrue(app.save())
        settings=self.backend.settings();self.assertEqual(settings['resolution'],'1920x1080');self.assertEqual(settings['scale'],1)
        self.assertEqual(settings['antialiasing'],'fxaa');self.assertEqual(settings['anisotropic'],5)
        self.assertFalse(settings['vsync']);self.assertTrue(settings['showFps'])
        reopened=self.app('configure',tab='display');self.assertEqual(reopened.resolution.get(),'1920 × 1080 · 1080p')
        self.assertEqual(reopened.render_scale.get(),'1× · Menor carga');self.assertTrue(reopened.show_fps.get())
    def test_graphics_presets_keep_controls_language_mods_and_fps_preference(self):
        app=self.app('configure',tab='display');app.sensitivity.set('2.7');app.language.set('English')
        app.mod_vars['unlock_fps'].set(True);app.show_fps.set(True)
        app.apply_graphics_preset('Calidad');self.assertEqual(app.graphics_preset.get(),'Calidad')
        self.assertEqual(app.display_settings()['scale'],2);app.apply_graphics_preset('Rendimiento')
        self.assertEqual(app.graphics_preset.get(),'Rendimiento');self.assertEqual(app.display_settings()['resolution'],'1280x720')
        self.assertEqual(app.display_settings()['scale'],1);self.assertTrue(app.show_fps.get())
        self.assertEqual(app.sensitivity.get(),'2.7');self.assertEqual(app.language.get(),'English');self.assertTrue(app.mod_vars['unlock_fps'].get())
        app.resolution.set('1920 × 1080 · 1080p');self.assertEqual(app.graphics_preset.get(),'Personalizado')
    def test_experimental_8k_and_240hz_survive_tabs_and_reopening(self):
        app=self.app('configure',tab='display');app.refresh_rate.set('240 Hz');app.apply_graphics_preset('8K experimental')
        self.assertEqual(app.refresh_rate.get(),'240 Hz');self.assertEqual(app.display_settings()['scale'],6)
        app.show_tab('controls');app.show_tab('display');self.assertTrue(app.save())
        reopened=self.app('configure',tab='display')
        self.assertEqual(reopened.graphics_preset.get(),'8K experimental');self.assertEqual(reopened.refresh_rate.get(),'240 Hz')

if __name__=='__main__':unittest.main()
