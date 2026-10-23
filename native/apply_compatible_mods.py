"""Adapt curated retail Xbox 360 fixes to native C++ at their PPC instruction.

Writing PPC opcodes at runtime would leave recompiled C++ unchanged. Keep both
paths compiled and choose once at launch with cvars. Refuse any different input
image and validate the generated PPC address stream before editing a function.
Reference: xenia-canary/game-patches, 4D53082D - Gears of War 2.patch.toml
Authors of the adapted fixes: illusion, boma. See MODS.md for attribution.
"""
from pathlib import Path
import hashlib
import re
import sys
import os

ROOT = Path(__file__).resolve().parent
# Verify the original XEX directly; no separately decrypted game image is
# required or distributed. Each generated instruction is validated below too.
IMAGE_SHA256 = 'c110e168abd4518c510f8358723343e129aed17eea73fe12010b8a0cd0a73bb8'
IMAGE = Path(os.environ.get('GOW2_XEX_PATH', ROOT.parent / '.local/game/default.xex'))
FIXES = {
    0x82806A44: ('lighting', 'REX_STORE_U32(ctx.r6.u32 + 11940, ctx.r11.u32);', 'ctx.r11.s64 = 0;'),
    0x826F9D18: ('no_ao', 'ctx.r11.u64 = REX_LOAD_U32(ctx.r10.u32 + 52);', 'ctx.r11.s64 = 0;'),
    0x8236004C: ('no_motion_blur', 'ctx.r11.u64 = REX_LOAD_U32(ctx.r10.u32 + 44);', 'ctx.r11.s64 = 0;'),
    0x827B817C: ('no_lens_flares', 'ctx.r10.u64 = REX_LOAD_U32(ctx.r11.u32 + 72);', 'ctx.r10.s64 = 0;'),
    0x8280D534: ('texture_streaming', 'ctx.r4.u64 = REX_LOAD_U32(ctx.r1.u32 + 80);', 'ctx.r4.s64 = 196;'),
    0x824A2E94: ('unlock_fps', 'temp.u32 = REX_LOAD_U32(ctx.r3.u32 + 1284);\n\tctx.f1.f64 = double(temp.f32);', '/* PPC nop: keep the existing f1 value. */'),
    0x8298CFB0: ('unlock_fps', 'ctx.r11.s64 = 2;', 'ctx.r11.s64 = 1;'),
    0x827296BC: ('no_dof_blur', 'ctx.f2.f64 = ctx.f4.f64 >= 0.0 ? ctx.f31.f64 : ctx.f28.f64;', 'ctx.fpscr.disableFlushMode(); ctx.f1.f64 = double(float(ctx.f1.f64 - ctx.f1.f64));'),
    0x82729700: ('no_dof_blur', 'ctx.lr = 0x82729704;\n\tsub_827291F8(ctx, base);', 'ctx.fpscr.disableFlushMode(); ctx.f1.f64 = double(float(ctx.f1.f64 - ctx.f1.f64));'),
    0x824ECEF8: ('no_bloom', 'ctx.r10.u64 = REX_LOAD_U32(ctx.r10.u32 + 56);', 'ctx.r10.s64 = 0;'),
    0x824ED078: ('no_bloom', 'ctx.r11.u64 = REX_LOAD_U32(ctx.r10.u32 + 56);', 'ctx.r11.s64 = 0;'),
    0x824ED0A4: ('no_bloom', 'ctx.r10.u64 = REX_LOAD_U32(ctx.r11.u32 + 56);', 'ctx.r10.s64 = 0;'),
}
ENTRY = 0x8280DDC8
CAMERA_ENTRY = 0x827FC468

def adapt(body, start, found, audit):
    if start == CAMERA_ENTRY:
        found.add(CAMERA_ENTRY)
        marker = '/* GOW2_DIRECT_MOUSE */'
        if marker not in body:
            if 'sub_827FA238(ctx, base);' not in body or '// fmr f31,f1' not in body:
                raise RuntimeError('Unexpected viewport input tick; refusing direct mouse hook')
            if not audit:
                pos = body.index('REX_FUNC_PROLOGUE();') + len('REX_FUNC_PROLOGUE();')
                body = body[:pos] + '\n\t'+marker+' Gow2ApplyDirectMouse(base, ctx.f1.f64);' + body[pos:]
    addresses = [addr for addr in FIXES if start <= addr < start + len(re.findall(r'(?m)^\t// ', body)) * 4]
    # Existing branches retain their original instruction comments. Skip only
    # already adapted PCs so a new mod can share an old mod's function.
    existing={int(addr,16) for addr in re.findall(r'/\* GOW2_MOD:([0-9A-F]{8}) \*/',body)}
    if existing - (set(FIXES) | {ENTRY}):raise RuntimeError('Unknown native mod marker')
    edits = []
    comments = list(re.finditer(r'(?m)^\t// [^\n]*\n', body))
    for i, comment in enumerate(comments):
        pc = start + i * 4
        next_pos = comments[i + 1].start() if i + 1 < len(comments) else len(body)
        block = body[comment.end():next_pos]
        lr = re.search(r'ctx.lr = 0x([0-9A-Fa-f]+)', block)
        if lr and int(lr[1], 16) != pc + 4 and addresses:
            raise RuntimeError(f'PPC address stream differs in {start:08X} at {pc:08X}')
        if pc not in FIXES: continue
        name, original, replacement = FIXES[pc]
        if block.count(original) != 1:
            raise RuntimeError(f'Unexpected instruction at {pc:08X}: {block[:220]}')
        found.add(pc)
        if pc in existing:
            if replacement not in block or f'REXCVAR_GET(gow2_mod_{name})' not in block:
                raise RuntimeError(f'Changed native mod at {pc:08X}')
            if name in ('no_dof_blur', 'no_bloom'):
                trace = f'Gow2TraceVisualMod(0x{pc:08X}); '
                prefix = f'/* GOW2_MOD:{pc:08X} */ if (REXCVAR_GET(gow2_mod_{name})) {{ '
                if prefix not in block:
                    raise RuntimeError(f'Changed native mod branch at {pc:08X}')
                if trace not in block:
                    edits.append((comment.end(), next_pos, block.replace(prefix, prefix + trace, 1)))
            continue
        print(f'{pc:08X}: {name}: {original}')
        trace = f'Gow2TraceVisualMod(0x{pc:08X}); ' if name in ('no_dof_blur', 'no_bloom') else ''
        patched = f'/* GOW2_MOD:{pc:08X} */ if (REXCVAR_GET(gow2_mod_{name})) {{ {trace}{replacement} }} else {{ {original} }}'
        edits.append((comment.end(), next_pos, block.replace(original, patched)))
    if start == ENTRY:
        found.add(ENTRY)
        marker = f'\n\t/* GOW2_MOD:{ENTRY:08X} */ if (REXCVAR_GET(gow2_mod_texture_streaming)) {{ ctx.r3.s64 = 0; return; }}'
        pos = body.index('REX_FUNC_PROLOGUE();') + len('REX_FUNC_PROLOGUE();')
        if ENTRY not in existing:edits.append((pos, pos, marker))
    if not audit:
        for a, b, replacement in sorted(edits, reverse=True):
            body = body[:a] + replacement + body[b:]
    return body

def main():
    audit = '--audit' in sys.argv
    directory = Path(sys.argv[1]) if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else ROOT / 'generated/default'
    if hashlib.sha256(IMAGE.read_bytes()).hexdigest() != IMAGE_SHA256:
        raise RuntimeError('Unsupported retail image; refusing native mods')
    found, outputs = set(), {}
    pattern = re.compile(r'(DEFINE_REX_FUNC\(sub_([0-9A-Fa-f]{8})\) \{)(.*?)(\n\})', re.S)
    for path in directory.glob('gow2_recomp.*.cpp'):
        source = path.read_text()
        result = pattern.sub(lambda m: m[1] + adapt(m[3], int(m[2], 16), found, audit) + m[4], source)
        if result != source:
            if '#include "gow2_mods.h"' not in result:
                result = '#include "gow2_mods.h"\n' + result
            if '#include "gow2_direct_mouse.h"' not in result:
                result = '#include "gow2_direct_mouse.h"\n' + result
            outputs[path] = result
    if found != set(FIXES) | {ENTRY, CAMERA_ENTRY}:
        raise RuntimeError(f'Missing native patch sites: {(set(FIXES) | {ENTRY, CAMERA_ENTRY}) - found}')
    for path, result in outputs.items(): path.write_text(result)
    print(f'Validated {len(found)} compatible native patch sites; changed {len(outputs)} files')

if __name__ == '__main__': main()
