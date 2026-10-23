import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
from processes import child_environment,spawn_external

class ProcessTests(unittest.TestCase):
    def test_child_scratch_files_remain_inside_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            local=Path(directory)/'.local'
            code='import json,tempfile;from pathlib import Path;p=Path(tempfile.mkstemp()[1]);print(json.dumps(str(p)))'
            import subprocess
            process=spawn_external([sys.executable,'-c',code],local=local,stdout=subprocess.PIPE,text=True)
            output,_=process.communicate(timeout=10)
            self.assertEqual(process.returncode,0)
            # Resolve both sides: Windows may report the same folder with a short
            # (8.3) name such as RUNNER~1 or with its long name.
            self.assertEqual(Path(json.loads(output)).resolve().parent,(local/'temp/work').resolve())
    def test_relaunch_resets_bootloader_without_mutating_parent_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            original={'TEMP':'outside','_PYI_APPLICATION_HOME_DIR':'parent-bundle','PATH':'custom-path'}
            environment=child_environment(directory,original)
            self.assertEqual(original['TEMP'],'outside')
            self.assertEqual(environment['PYINSTALLER_RESET_ENVIRONMENT'],'1')
            self.assertEqual(environment['PATH'],'custom-path')
            self.assertEqual(environment['TEMP'],environment['TMP'])
            self.assertEqual(environment['TMP'],environment['TMPDIR'])

if __name__=='__main__':unittest.main()
