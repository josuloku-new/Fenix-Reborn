import importlib.util
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('native_patch_adapter',ROOT/'native/apply_compatible_mods.py')
adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)

class NativePatchTests(unittest.TestCase):
    def body(self):
        lines=['\n\tREX_FUNC_PROLOGUE();']
        for pc in range(0x824ED078,0x824ED0A8,4):
            original=adapter.FIXES[pc][1] if pc in adapter.FIXES else 'ctx.r12.s64 = 0;'
            lines+=['\t// retail instruction', '\t'+original]
        return '\n'.join(lines)+'\n'

    def test_mod_upgrade_patches_new_site_in_already_patched_function(self):
        pc=0x824ED078;name,original,replacement=adapter.FIXES[pc]
        first=f'/* GOW2_MOD:{pc:08X} */ if (REXCVAR_GET(gow2_mod_{name})) {{ {replacement} }} else {{ {original} }}'
        old=self.body().replace(original,first,1);found=set()
        upgraded=adapter.adapt(old,pc,found,False)
        self.assertEqual(found,{pc,0x824ED0A4});self.assertEqual(upgraded.count('/* GOW2_MOD:824ED078 */'),1)
        self.assertEqual(upgraded.count('Gow2TraceVisualMod(0x824ED078);'),1)
        self.assertEqual(upgraded.count('/* GOW2_MOD:824ED0A4 */'),1)
        again=set();self.assertEqual(adapter.adapt(upgraded,pc,again,False),upgraded)
        self.assertEqual(again,found)

    def test_changed_original_and_changed_existing_patch_are_rejected(self):
        pc=0x824ED078;original=adapter.FIXES[pc][1]
        with self.assertRaisesRegex(RuntimeError,'Unexpected instruction'):
            adapter.adapt(self.body().replace(original,original.replace('56','60')),pc,set(),False)
        patched=adapter.adapt(self.body(),pc,set(),False)
        with self.assertRaisesRegex(RuntimeError,'Changed native mod'):
            adapter.adapt(patched.replace('ctx.r11.s64 = 0;','ctx.r11.s64 = 1;'),pc,set(),False)

    def test_audit_checks_sites_without_changing_generated_code(self):
        body=self.body();found=set()
        self.assertEqual(adapter.adapt(body,0x824ED078,found,True),body)
        self.assertEqual(found,{0x824ED078,0x824ED0A4})

if __name__=='__main__':unittest.main()
