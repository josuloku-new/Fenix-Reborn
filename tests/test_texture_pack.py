import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'launcher'))
from backend import Backend
from texture_pack import bc1_identity,diffuse_name,status

def dds(blocks,width=8,height=4):
    header=bytearray(128);header[:4]=b'DDS '
    struct.pack_into('<I',header,4,124);struct.pack_into('<II',header,12,height,width)
    struct.pack_into('<I',header,76,32);header[84:88]=b'DXT1'
    return header+b''.join(struct.pack('<Q',block) for block in blocks)

class TexturePackTests(unittest.TestCase):
    def test_identity_uses_every_bc1_block_in_linear_order(self):
        values=[0x0123456789abcdef,0xfedcba9876543210]
        expected=14695981039346656037
        for word in values:expected=((expected^word)*1099511628211)&((1<<64)-1)
        identity,w,h,_=bc1_identity(dds(values))
        self.assertEqual((identity,w,h),(f'{expected:016x}_8x4',8,4))
        self.assertNotEqual(identity,bc1_identity(dds(values[::-1]))[0])
        with self.assertRaises(ValueError):bc1_identity(dds(values)[:-1])
        with self.assertRaises(ValueError):bc1_identity(b'DDS ')

    def test_transparent_bc1_is_excluded_from_ai_processing(self):
        self.assertTrue(bc1_identity(dds([0xffff,0xffff]))[3])
        self.assertFalse(bc1_identity(dds([3<<32,0xffff]))[3])

    def test_only_diffuse_assets_are_selected(self):
        for name in ('Cog_Marcus_Game_U_D','COG_DOM_Game_D','Ammo_Box_Tex','BOXDiffuse','COG_City_CrackWall_CP_Tex'):
            self.assertTrue(diffuse_name(name),name)
        for name in ('Cog_Marcus_Game_U_N','Cog_Marcus_Game_U_S','Normal_Tex','T_Water_D','COG_Dom_Cine_Hair_D','T_FX_Screen_Tex','LightMapTexture2D_1'):
            self.assertFalse(diffuse_name(name),name)

    def test_partial_pack_and_missing_loader_cannot_be_enabled(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'launcher').mkdir()
            (root/'launcher/dependencies.json').write_bytes((ROOT/'launcher/dependencies.json').read_bytes())
            backend=Backend(root);pack=backend.local/'mods/textures-hd';pack.mkdir(parents=True)
            identity=bc1_identity(dds([0xffff,0xffff]))[0]
            (pack/(identity+'.dds')).write_bytes(dds([0xffff,0xffff]))
            data=dict(textures=[dict(id=identity)],complete=False)
            (pack/'pack.json').write_text(json.dumps(data))
            backend.runtime.mkdir();(backend.runtime/'texture_loader.json').write_text('{"version":1}')
            self.assertEqual(status(backend),dict(ready=False,count=1,loader=True))
            data['complete']=True;(pack/'pack.json').write_text(json.dumps(data))
            self.assertTrue(status(backend)['ready'])
            (backend.runtime/'texture_loader.json').unlink()
            self.assertFalse(status(backend)['ready'])
