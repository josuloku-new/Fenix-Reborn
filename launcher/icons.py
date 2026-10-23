"""Embed our own ICO in locally built Windows executables, preserving other resources."""
import ctypes
from ctypes import wintypes
import os
from pathlib import Path
import struct

def embed_icon(executable,icon):
    if os.name!='nt':raise OSError('Windows is required to build Windows executable resources.')
    data=Path(icon).read_bytes()
    reserved,kind,count=struct.unpack_from('<HHH',data)
    if reserved or kind!=1 or not count:raise ValueError('Invalid ICO header.')
    group=bytearray(struct.pack('<HHH',0,1,count));images=[]
    for i in range(count):
        w,h,colors,unused,planes,bits,length,offset=struct.unpack_from('<BBBBHHII',data,6+16*i)
        image=data[offset:offset+length]
        if len(image)!=length:raise ValueError('Truncated ICO image.')
        group.extend(struct.pack('<BBBBHHIH',w,h,colors,unused,planes,bits,length,i+1));images.append(image)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.BeginUpdateResourceW.argtypes=[wintypes.LPCWSTR,wintypes.BOOL];kernel.BeginUpdateResourceW.restype=wintypes.HANDLE
    kernel.UpdateResourceW.argtypes=[wintypes.HANDLE,ctypes.c_void_p,ctypes.c_void_p,wintypes.WORD,ctypes.c_void_p,wintypes.DWORD];kernel.UpdateResourceW.restype=wintypes.BOOL
    kernel.EndUpdateResourceW.argtypes=[wintypes.HANDLE,wintypes.BOOL];kernel.EndUpdateResourceW.restype=wintypes.BOOL
    handle=kernel.BeginUpdateResourceW(str(Path(executable).resolve()),False)
    if not handle:raise ctypes.WinError(ctypes.get_last_error())
    try:
        for resource_id,image in enumerate(images,1):
            if not kernel.UpdateResourceW(handle,3,resource_id,0,image,len(image)):raise ctypes.WinError(ctypes.get_last_error())
        group=bytes(group)
        if not kernel.UpdateResourceW(handle,14,1,0,group,len(group)):raise ctypes.WinError(ctypes.get_last_error())
    except BaseException:
        kernel.EndUpdateResourceW(handle,True);raise
    if not kernel.EndUpdateResourceW(handle,False):raise ctypes.WinError(ctypes.get_last_error())
