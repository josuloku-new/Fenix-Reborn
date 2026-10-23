import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
from icons import embed_icon
from branding import ICON_NAME

@unittest.skipUnless(os.name=='nt','Windows icon resources')
class IconTests(unittest.TestCase):
    def test_windows_loads_small_and_large_icon_images(self):
        user=ctypes.WinDLL('user32',use_last_error=True)
        user.LoadImageW.argtypes=[wintypes.HANDLE,wintypes.LPCWSTR,wintypes.UINT,ctypes.c_int,ctypes.c_int,wintypes.UINT]
        user.LoadImageW.restype=wintypes.HANDLE
        user.DestroyIcon.argtypes=[wintypes.HANDLE]
        for size in (16,32,48,128,256):
            handle=user.LoadImageW(None,str(ROOT/'launcher/assets'/ICON_NAME),1,size,size,0x10)
            self.assertTrue(handle,ctypes.get_last_error());user.DestroyIcon(handle)

    def test_embedded_icon_is_available_to_windows_shell(self):
        shell=ctypes.WinDLL('shell32',use_last_error=True)
        shell.ExtractIconExW.argtypes=[wintypes.LPCWSTR,ctypes.c_int,ctypes.POINTER(wintypes.HANDLE),ctypes.POINTER(wintypes.HANDLE),wintypes.UINT]
        shell.ExtractIconExW.restype=wintypes.UINT
        user=ctypes.WinDLL('user32');user.DestroyIcon.argtypes=[wintypes.HANDLE]
        with tempfile.TemporaryDirectory() as directory:
            executable=Path(directory)/'icon-fixture.exe';shutil.copy2(sys.executable,executable)
            embed_icon(executable,ROOT/'launcher/assets'/ICON_NAME)
            large=wintypes.HANDLE();small=wintypes.HANDLE()
            self.assertGreater(shell.ExtractIconExW(str(executable),0,ctypes.byref(large),ctypes.byref(small),1),0)
            self.assertTrue(large.value);self.assertTrue(small.value)
            user.DestroyIcon(large);user.DestroyIcon(small)

if __name__=='__main__':unittest.main()
