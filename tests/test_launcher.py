import hashlib
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
from backend import Backend,MODS,AUTHOR,extract_zip,XEX_SHA256
from toolchain import runtime_dlls,run,environment
from packages import keep_tool_file,trim_tool
from third_party import sdk_files
from entrypoints import PLAY_NAME,CONFIG_NAME
from cleanup import release_preparation_files
from display import RESOLUTIONS

class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        (self.root/'launcher').mkdir();(self.root/'launcher/dependencies.json').write_bytes((ROOT/'launcher/dependencies.json').read_bytes())
        self.backend=Backend(self.root)
    def tearDown(self):self.temp.cleanup()
    def fake_game(self):
        cooked=self.backend.game/'GearGame/CookedXenon';cooked.mkdir(parents=True)
        (self.backend.game/'default.xex').write_bytes(b'fixture')
        for resource in ('esn','int','ita','kor','cht'):
            (cooked/f'Coalesced_{resource}.bin').touch();(cooked/f'GearGame_LOC_{resource.upper()}.xxx').touch()
        (cooked/'Coalesced_esm.bin').touch()
        stat=(self.backend.game/'default.xex').stat()
        (self.backend.local/'game_verified.json').write_text(json.dumps(dict(sha256=XEX_SHA256,size=stat.st_size,mtime_ns=stat.st_mtime_ns)))
    def test_startup_creates_no_local_data(self):
        state=self.backend.state();self.assertFalse(self.backend.local.exists())
        self.assertFalse(state['runtimeReady']);self.assertFalse(state['gameReady'])
        self.assertEqual((state['author'],state['version']),(AUTHOR,'0.1'))
    def test_settings_and_arguments_roundtrip(self):
        self.fake_game();s=self.backend.defaults();s['mods']['unlock_fps']=True;s['sensitivity']=2.5;s['aimSensitivity']=0.8
        self.backend.save_settings(s);args=self.backend.launch_args()
        self.assertEqual(args[args.index('--user_country')+1],'31')
        self.assertEqual(args[args.index('--user_language')+1],'5')
        self.assertIn('--fullscreen',args);self.assertIn('--vsync',args);self.assertIn('--gow2_mod_unlock_fps',args)
        self.assertEqual(self.backend.settings()['sensitivity'],2.5)
        self.assertEqual(self.backend.settings()['aimSensitivity'],0.8)
        self.assertEqual(args[args.index('--gow2_mouse_aim_sensitivity')+1],'0.8')
        self.assertIn('--gow2_mouse_direct',args)
        self.assertNotIn('es-MX',[l['code'] for l in self.backend.available_languages()])

    def test_hd_pack_reaches_native_process_only_when_selected(self):
        self.fake_game();settings=self.backend.defaults();settings['hdTextures']=True
        self.backend.save_settings(settings)
        folder=self.backend.local/'mods/textures-hd';folder.mkdir(parents=True)
        identity='0123456789abcdef_1024x1024'
        (folder/(identity+'.dds')).touch()
        (folder/'pack.json').write_text(json.dumps(dict(complete=True,textures=[dict(id=identity)])))
        self.backend.runtime.mkdir();(self.backend.runtime/'texture_loader.json').write_text('{"version":1}')
        with patch.object(self.backend,'runtime_ready',return_value=True),patch.object(self.backend,'verify_game'),patch('backend.threading.Thread'),patch('backend.spawn_external') as spawn,patch.dict('os.environ',{'FENIX_TEXTURE_MAGENTA_ALL':'1'}):
            self.backend.launch();env=spawn.call_args.kwargs['env']
            self.assertEqual(env['FENIX_TEXTURE_PACK'],str(folder))
            self.assertNotIn('FENIX_TEXTURE_MAGENTA_ALL',env)
            self.backend.process=None;settings['hdTextures']=False;self.backend.save_settings(settings)
            self.backend.launch();self.assertNotIn('FENIX_TEXTURE_PACK',spawn.call_args.kwargs['env'])
    def test_absent_languages_and_invalid_keys_rejected(self):
        self.fake_game();s=self.backend.defaults();s['language']='es-MX'
        with self.assertRaises(ValueError):self.backend.save_settings(s)
        s['language']='es-ES';s['bindings']['a']='not a key'
        with self.assertRaises(ValueError):self.backend.save_settings(s)
    def test_older_controls_gain_aim_adjustment_without_losing_preferences(self):
        self.fake_game();old=self.backend.defaults();del old['aimSensitivity'];del old['directMouse']
        old.update(sensitivity=2.7,smoothing=0)
        self.backend.settings_path.write_text(json.dumps(old),'utf-8')
        loaded=self.backend.settings()
        self.assertEqual(loaded['aimSensitivity'],0.65)
        self.assertTrue(loaded['directMouse'])
        self.assertEqual(loaded['sensitivity'],2.7);self.assertEqual(loaded['smoothing'],0)
        loaded['aimSensitivity']=float('nan')
        with self.assertRaises(ValueError):self.backend.save_settings(loaded)
    def test_direct_mouse_can_be_disabled_without_changing_other_controls(self):
        self.fake_game();s=self.backend.defaults();s['directMouse']=False
        self.backend.save_settings(s);args=self.backend.launch_args()
        self.assertIn('--no-gow2_mouse_direct',args);self.assertNotIn('--gow2_mouse_direct',args)
        self.assertEqual(self.backend.settings()['aimSensitivity'],0.65)
    def test_smoothing_switch_preserves_amount_and_controls_effective_launch_value(self):
        self.fake_game();s=self.backend.defaults();s.update(smoothing=7,smoothingEnabled=True)
        self.backend.save_settings(s);args=self.backend.launch_args()
        self.assertEqual(args[args.index('--gow2_mouse_smoothing_ms')+1],'7')
        s['smoothingEnabled']=False;self.backend.save_settings(s);args=self.backend.launch_args()
        self.assertEqual(args[args.index('--gow2_mouse_smoothing_ms')+1],'0')
        self.assertEqual(self.backend.settings()['smoothing'],7)
        for value in (0,6):
            old=self.backend.defaults();old.pop('smoothingEnabled');old['smoothing']=value
            self.backend.settings_path.write_text(json.dumps(old),'utf-8')
            restored=self.backend.settings()
            self.assertEqual(restored['smoothingEnabled'],value>0)
            self.assertEqual(restored['smoothing'],value)
    def test_controller_disables_mouse(self):
        self.fake_game();s=self.backend.defaults();s['inputMode']='pad';self.backend.save_settings(s)
        args=self.backend.launch_args();self.assertIn('--no-mnk_mouse',args);self.assertNotIn('--mnk_mouse',args)
    def test_video_modes_and_graphics_options_reach_native_arguments(self):
        self.fake_game()
        for resolution in RESOLUTIONS.values():
            settings=self.backend.defaults();settings.update(resolution=resolution,scale=2,vsync=False,antialiasing='fxaa_extreme',anisotropic=5,showFps=True)
            settings['mods']['unlock_fps']=True;self.backend.save_settings(settings);args=self.backend.launch_args()
            width,height=resolution.split('x')
            for option,value in (('--video_mode_width',width),('--window_width',width),('--video_mode_height',height),('--window_height',height),('--resolution_scale','2'),('--swap_post_effect','fxaa_extreme'),('--anisotropic_override','5')):
                self.assertEqual(args[args.index(option)+1],value)
            self.assertIn('--no-vsync',args);self.assertNotIn('--vsync',args)
            self.assertIn('--gow2_show_fps',args);self.assertIn('--fullscreen',args)
    def test_old_settings_migrate_without_changing_gpu_scale_or_user_presets(self):
        self.fake_game();old=self.backend.defaults()
        for key in ('resolution','refreshRate','vsync','antialiasing','anisotropic','showFps'):old.pop(key)
        old.update(version=1,scale=3,sensitivity=2.9);old['mods']['unlock_fps']=True
        self.backend.settings_path.write_text(json.dumps(old),'utf-8')
        settings=self.backend.settings();self.assertEqual(settings['resolution'],'1280x720')
        self.assertEqual(settings['scale'],3);self.assertEqual(settings['sensitivity'],2.9)
        self.assertTrue(settings['mods']['unlock_fps']);self.assertTrue(settings['vsync'])
        self.assertEqual(settings['version'],3);self.assertEqual(settings['refreshRate'],60);self.assertFalse(settings['showFps'])
        self.backend.save_settings(settings);self.assertEqual(self.backend.settings()['scale'],3)
    def test_invalid_graphics_values_are_rejected(self):
        self.fake_game()
        for key,value in (('resolution','123x456'),('antialiasing','unsupported'),('anisotropic',True),('anisotropic',16),('vsync','yes'),('showFps',1),('refreshRate',241),('refreshRate',True),('scale',6.0),('scale',8)):
            settings=self.backend.defaults();settings[key]=value
            with self.subTest(key=key,value=value):
                with self.assertRaises(ValueError):self.backend.save_settings(settings)
    def test_8k_supersampling_and_240hz_do_not_overflow_guest_video_mode(self):
        from display import PRESETS
        self.fake_game();settings=self.backend.defaults();settings.update(PRESETS['8K experimental'],refreshRate=240)
        settings['mods']['unlock_fps']=True;self.backend.save_settings(settings);args=self.backend.launch_args()
        for option,value in (('--video_mode_width','1280'),('--video_mode_height','720'),('--resolution_scale','6'),('--draw_resolution_scale_x','6'),('--draw_resolution_scale_y','6'),('--video_mode_refresh_rate','240')):
            self.assertEqual(args[args.index(option)+1],value)
        self.assertEqual(1280*settings['scale'],7680);self.assertEqual(720*settings['scale'],4320)
        self.assertEqual(args.count('--video_mode_refresh_rate'),1)
    def test_version_two_settings_keep_graphics_when_refresh_rate_is_added(self):
        self.fake_game();old=self.backend.defaults();old.pop('refreshRate');old.update(version=2,resolution='1920x1080',scale=2)
        self.backend.settings_path.write_text(json.dumps(old),'utf-8');settings=self.backend.settings()
        self.assertEqual((settings['resolution'],settings['scale'],settings['refreshRate']),('1920x1080',2,60))
    def test_changed_xex_invalidates_receipt(self):
        self.fake_game();self.assertTrue(self.backend.game_ready())
        (self.backend.game/'default.xex').write_bytes(b'changed image');self.assertFalse(self.backend.game_ready())
    def test_zip_traversal_rejected(self):
        archive=self.root/'bad.zip'
        with zipfile.ZipFile(archive,'w') as z:z.writestr('../escaped.txt','bad')
        with self.assertRaises(ValueError):extract_zip(archive,self.root/'extract')
        self.assertFalse((self.root/'escaped.txt').exists())
    def test_corrupt_download_not_installed(self):
        (self.root/'dist').mkdir();(self.root/'dist/runtime.zip').write_bytes(b'wrong')
        with self.assertRaises(ValueError):self.backend.download({'sha256':'0'*64,'bundled':'runtime.zip'})
        self.assertFalse(self.backend.runtime_ready())
    def test_local_toolchain_preparation_never_distributes_game_binary(self):
        dist=self.root/'dist';dist.mkdir()
        for name,members in [('extract.zip',['extract-xiso.exe'])]:
            with zipfile.ZipFile(dist/name,'w') as z:
                for member in members:z.writestr(member,b'fixture')
        self.backend.manifest={'extractor':dict(label='extractor',bundled='extract.zip',sha256=hashlib.sha256((dist/'extract.zip').read_bytes()).hexdigest())}
        def fake_install(backend): (backend.local/'tools').mkdir(parents=True)
        with patch('toolchain.install',side_effect=fake_install):self.backend.dependencies()
        self.assertFalse(self.backend.runtime_ready());self.assertTrue((self.backend.local/'tools/extract-xiso.exe').exists())
        self.assertFalse(self.backend.game.exists())
    def test_microsoft_terms_require_explicit_user_checkbox(self):
        with self.assertRaisesRegex(ValueError,'condiciones'):self.backend.start('dependencies')
        self.assertEqual(self.backend.job['state'],'idle')
    def prepared_runtime(self):
        binary=self.backend.runtime/'bin';binary.mkdir(parents=True,exist_ok=True)
        for name in ('gow2.exe','rexruntime.dll','rexgpu-xenos.dll'):(binary/name).write_bytes(b'fixture')
        (self.backend.runtime/'local_build.json').write_text(json.dumps(dict(version='0.1',xex_sha256=XEX_SHA256,rebuilt_locally=True)))
        helpers=self.root/'launcher/entrypoints';helpers.mkdir(parents=True,exist_ok=True)
        for name in (PLAY_NAME,CONFIG_NAME):(helpers/name).write_bytes(b'helper '+name.encode('utf-8'))
    def test_build_creates_both_entrypoints_and_preserves_settings(self):
        self.fake_game();self.prepared_runtime()
        settings=self.backend.defaults();settings['sensitivity']=3.2;self.backend.save_settings(settings)
        finished=threading.Event();self.backend.on_build_complete=finished.set
        with patch('toolchain.build'):
            self.backend.start('build');self.assertTrue(finished.wait(3))
        self.assertEqual(self.backend.job['state'],'done')
        for name in (PLAY_NAME,CONFIG_NAME):self.assertTrue((self.root/name).is_file())
        self.assertEqual(self.backend.settings()['sensitivity'],3.2)
    def test_cleanup_preserves_playable_game_settings_and_saves(self):
        self.fake_game();self.prepared_runtime();self.backend.save_settings(self.backend.defaults())
        for name in ('tools/compiler','downloads/archive','build/native/generated','unpack-fixture/extra','extraction-partial/extra','temp/work/scratch','temp/app/_MEI-running/source','app/current/Fenix-Reborn-App.exe','userdata/save','cache/shader','custom/notes','updates/previous-setup.exe'):
            path=self.backend.local/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'keep or remove')
        before={name:(self.backend.local/name).read_bytes() for name in ('temp/app/_MEI-running/source','app/current/Fenix-Reborn-App.exe','userdata/save','cache/shader','custom/notes','updates/previous-setup.exe','settings.json','game_verified.json','runtime/bin/gow2.exe','game/default.xex')}
        report=release_preparation_files(self.backend)
        self.assertEqual(set(report['removed']),{'tools','downloads','build','unpack-fixture','extraction-partial','temp/work'})
        self.assertEqual(report['skipped'],[])
        for name,content in before.items():self.assertEqual((self.backend.local/name).read_bytes(),content)
        self.assertTrue(self.backend.game_ready());self.assertTrue(self.backend.runtime_ready())
        self.assertIn('--fullscreen',self.backend.launch_args())
    def test_cleanup_rejected_before_success_and_disabled_option_keeps_tools(self):
        tools=self.backend.local/'tools/compiler';tools.parent.mkdir(parents=True);tools.touch()
        with self.assertRaises(ValueError):release_preparation_files(self.backend)
        self.assertTrue(tools.exists());self.fake_game();self.prepared_runtime()
        self.assertTrue(self.backend.cleanup_after_build);self.backend.cleanup_after_build=False
        with patch('toolchain.build'):self.backend.build()
        self.assertTrue(tools.exists())
        self.backend.cleanup_after_build=True
        with patch('toolchain.build',side_effect=RuntimeError('Compilation failed')):
            with self.assertRaises(RuntimeError):self.backend.build()
        self.assertTrue(tools.exists())
    def test_cleanup_skips_junctions_to_external_files(self):
        import os,subprocess
        if os.name!='nt':self.skipTest('Windows junction test')
        self.fake_game();self.prepared_runtime()
        outside=self.root/'outside';outside.mkdir();(outside/'important').write_bytes(b'safe')
        junction=self.backend.local/'tools'
        subprocess.run(['cmd','/c','mklink','/J',str(junction),str(outside)],check=True,capture_output=True)
        try:
            report=release_preparation_files(self.backend)
            self.assertIn('tools',report['skipped']);self.assertEqual((outside/'important').read_bytes(),b'safe')
        finally:junction.rmdir()
    def test_child_download_progress_reaches_state_and_log(self):
        script="import json;print('GOW2_PROGRESS '+json.dumps(dict(kind='total',bytes=104857600)));print('GOW2_PROGRESS '+json.dumps(dict(kind='download',file='headers.cab',done=26214400)))"
        log=run(self.backend,[sys.executable,'-c',script],phase='Prueba')
        self.assertEqual(self.backend.state()['job']['progress'],25)
        self.assertIn('25.0 / 100.0 MB',self.backend.state()['job']['message'])
        self.assertIn('headers.cab',log.read_text('utf-8'))
        script="import json;print('GOW2_PROGRESS '+json.dumps(dict(kind='extract',file='Headers.msi')))"
        run(self.backend,[sys.executable,'-c',script],phase='Prueba')
        self.assertIsNone(self.backend.state()['job']['progress'])
        self.assertIn('Headers.msi',self.backend.state()['job']['message'])
    def test_game_requires_local_build_receipt(self):
        directory=self.backend.runtime/'bin';directory.mkdir(parents=True)
        for name in ('gow2.exe','rexruntime.dll','rexgpu-xenos.dll'):(directory/name).touch()
        self.assertFalse(self.backend.runtime_ready())
        (self.backend.runtime/'local_build.json').write_text(json.dumps(dict(version='0.1',xex_sha256=XEX_SHA256,rebuilt_locally=True)))
        self.assertTrue(self.backend.runtime_ready())
    def test_runtime_libraries_are_architecture_specific(self):
        tools=self.root/'tools'
        for arch in ('x86','x64'):
            folder=tools/'windows/VC/Redist/MSVC/14.50'/arch/'Microsoft.VC143.CRT';folder.mkdir(parents=True)
            (folder/'VCRUNTIME140.dll').touch()
        selected=runtime_dlls(tools)
        self.assertEqual(len(selected),1);self.assertIn('x64',selected[0].parts)
    def test_minimal_tools_exclude_debug_and_unused_programs(self):
        files=['bin/cmake.exe','bin/cmake-gui.exe','bin/ctest.exe','bin/vcruntime140d.dll','share/cmake-3.31/Modules/CMake.cmake','doc/cmake/Copyright.txt','doc/cmake/manual.html']
        directory=self.root/'cmake'
        for name in files:
            path=directory/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'x')
        trim_tool(directory,'cmake')
        self.assertEqual({p.relative_to(directory).as_posix() for p in directory.rglob('*') if p.is_file()},{'bin/cmake.exe','share/cmake-3.31/Modules/CMake.cmake','doc/cmake/Copyright.txt'})
        self.assertFalse(keep_tool_file('llvm',Path('bin/clang.exe')))
        self.assertTrue(keep_tool_file('llvm',Path('bin/clang-cl.exe')))
        self.assertTrue(keep_tool_file('sdk',Path('lib/rexruntime.lib')))
        self.assertFalse(keep_tool_file('sdk',Path('lib/rexruntimed.lib')))
        self.assertFalse(keep_tool_file('sdk',Path('lib/cmake/rexglue/rexglueTargets-debug.cmake')))
    def test_sdk_cabinets_follow_filtered_file_plan(self):
        tables={
          'Directory':[['ROOT','','SourceDir'],['INCLUDE','ROOT','Include'],['LIB','ROOT','Lib'],['X64','LIB','x64'],['ARM','LIB','arm64']],
          'Component':[['header','INCLUDE'],['x64','X64'],['arm','ARM']],
          'File':[['h','header','windows.h','1'],['kernel','x64','kernel32.lib','2'],['unused','x64','unused.lib','3'],['arm','arm','kernel32.lib','4']],
          'Media':[['2','needed.cab'],['3','unneeded.cab'],['4','arm.cab']]}
        def rows(path,query):return tables[query.rsplit('FROM `',1)[1].rstrip('`')]
        with patch.object(sdk_files,'rows',side_effect=rows):
            self.assertEqual(sdk_files.required_cabinets(self.root/'sdk.msi'),{'needed.cab'})
        self.assertFalse(sdk_files.keep_vsix_member('Contents/VC/Tools/MSVC/14.50/lib/onecore/x64/libcpmtd.lib'))
        self.assertTrue(sdk_files.keep_vsix_member('Contents/VC/Tools/MSVC/14.50/lib/onecore/x64/msvcprt.lib'))
        self.assertFalse(sdk_files.keep_vsix_member('Contents/VC/Redist/MSVC/14.50/x64/CRT/msvcp140d.dll'))
    def test_partial_sdk_cannot_be_reported_ready(self):
        tools=self.backend.local/'tools';crt=tools/'windows/VC/Tools/MSVC/14.50.0';sdk=tools/'windows/Windows Kits/10'
        for folder in [crt/'include',crt/'lib/x64',crt/'lib/onecore/x64']+[sdk/'Include/10.0.26100.0'/p for p in ('ucrt','shared','um','winrt')]+[sdk/'Lib/10.0.26100.0'/p/'x64' for p in ('ucrt','um')]:folder.mkdir(parents=True,exist_ok=True)
        with self.assertRaisesRegex(ValueError,'Faltan archivos'):environment(self.backend)
        for file in [crt/'include/vector',crt/'lib/onecore/x64/oldnames.lib',crt/'lib/onecore/x64/msvcrt.lib',sdk/'Include/10.0.26100.0/shared/winapifamily.h',sdk/'Include/10.0.26100.0/um/Windows.h',sdk/'Lib/10.0.26100.0/um/x64/kernel32.lib']:file.touch()
        self.assertIn(str(crt/'lib/onecore/x64'),environment(self.backend)['LIB'])
    def test_mod_authors_and_branding_visible(self):
        self.assertEqual({m['key']:m['authors'] for m in MODS},{'unlock_fps':'illusion y boma','lighting':'illusion y boma','no_ao':'illusion','no_motion_blur':'illusion','no_lens_flares':'boma','texture_streaming':'boma','no_dof_blur':'boma','no_bloom':'boma'})
    def test_added_native_mods_preserve_old_selections_and_reach_launch(self):
        self.fake_game();old=self.backend.defaults();old['mods'].pop('no_dof_blur');old['mods'].pop('no_bloom')
        old['mods']['unlock_fps']=True;self.backend.settings_path.write_text(json.dumps(old),'utf-8')
        loaded=self.backend.settings();self.assertTrue(loaded['mods']['unlock_fps'])
        self.assertFalse(loaded['mods']['no_dof_blur']);self.assertFalse(loaded['mods']['no_bloom'])
        for enabled in (True,False):
            loaded['mods'].update(no_dof_blur=enabled,no_bloom=enabled);self.backend.save_settings(loaded)
            args=self.backend.launch_args()
            for mod in ('no_dof_blur','no_bloom'):
                self.assertIn('--'+('' if enabled else 'no-')+'gow2_mod_'+mod,args)


if __name__=='__main__':unittest.main()
