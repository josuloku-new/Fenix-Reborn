"""Compile and execute the five actual generated DoF/bloom instruction blocks.

The generated game code and this check's binaries stay in the local build
directory. Golden expectations describe the original instruction's behavior
and the replacement PowerPC opcode, independently of the patch generator.
"""
import argparse
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
CASES={0x827296BC:0xEC210828,0x82729700:0xEC210828,
       0x824ECEF8:0x39400000,0x824ED078:0x39600000,0x824ED0A4:0x39400000}

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--generated',type=Path,required=True)
    parser.add_argument('--work',type=Path,required=True)
    parser.add_argument('--toolchain-workspace',type=Path,required=True)
    args=parser.parse_args();blocks={}
    for file in args.generated.glob('gow2_recomp.*.cpp'):
        source=file.read_text('utf-8')
        for pc in CASES:
            marker=f'/* GOW2_MOD:{pc:08X} */';start=source.find(marker)
            if start<0:continue
            end=source.find('\n\t// ',start)
            if end<0 or pc in blocks:raise ValueError(f'Ambiguous generated block {pc:08X}')
            blocks[pc]=source[start:end]
    if blocks.keys()!=CASES.keys():raise ValueError('Compile the adapted game code before this check.')
    functions='\n'.join(f'void Site_{pc:08X}(PPCContext& ctx,uint8_t* base) {{\n{body}\n}}' for pc,body in blocks.items())
    dispatch='\n'.join(f'case 0x{pc:08X}: Site_{pc:08X}(ctx,base); break;' for pc in CASES)
    cases=','.join('{0x%08X,0x%08X}'%(pc,opcode) for pc,opcode in CASES.items())
    harness=r'''
#include <rex/ppc/context.h>
#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <iostream>
bool gow2_mod_no_dof_blur=false,gow2_mod_no_bloom=false;
#define REXCVAR_GET(name) name
uint32_t Load(uint32_t address) { return address * 257 + 3; }
#define REX_LOAD_U32(address) Load(address)
int calls=0,traces=0;
void Gow2TraceVisualMod(unsigned int) { ++traces; }
void sub_827291F8(PPCContext& ctx,uint8_t*) { ++calls;ctx.f1.f64=42.25; }
FUNCTIONS
void Require(bool ok,uint32_t pc,int combination) {
  if(!ok) {std::cerr << "Native instruction mismatch at " << std::hex << pc << ", combination " << combination << "\n";std::abort();}
}
int main() {
  uint8_t* base=nullptr;
  struct Case {uint32_t pc,opcode;};
  const Case cases[]={CASES};
  int checks=0;
  for(int combination=0;combination<4;++combination) for(int sign:{-1,1}) for(const auto& test:cases) {
    gow2_mod_no_dof_blur=bool(combination&1);gow2_mod_no_bloom=bool(combination&2);
    PPCContext ctx{};ctx.r10.u64=64;ctx.r11.u64=32;ctx.lr=0x77777777;
    ctx.f1.f64=5.25;ctx.f2.f64=101;ctx.f4.f64=sign;ctx.f31.f64=8;ctx.f28.f64=6;calls=0;traces=0;
    double f1=5.25,f2=101;uint64_t r10=64,r11=32,lr=0x77777777;int expected_calls=0;
    const bool enabled=test.opcode==0xEC210828 ? gow2_mod_no_dof_blur : gow2_mod_no_bloom;
    if(enabled) {
      if(test.opcode==0xEC210828) f1=0; // fsubs f1,f1,f1
      else if(((test.opcode>>21)&31)==10) r10=0; // li r10,0
      else r11=0; // li r11,0
    } else switch(test.pc) {
      case 0x827296BC:f2=sign>=0 ? 8 : 6;break; // Original fsel.
      case 0x82729700:lr=0x82729704;f1=42.25;expected_calls=1;break; // Original bl.
      case 0x824ECEF8:r10=Load(64+56);break;
      case 0x824ED078:r11=Load(64+56);break;
      case 0x824ED0A4:r10=Load(32+56);break;
    }
    switch(test.pc) {DISPATCH}
    Require(ctx.f1.f64==f1 && ctx.f2.f64==f2 && ctx.r10.u64==r10 && ctx.r11.u64==r11 && ctx.lr==lr && calls==expected_calls && traces==int(enabled),test.pc,combination);
    ++checks;
  }
  std::cout << checks << " generated native instruction checks: independent toggles, enabled opcode equivalence, disabled behavior and LR/call preservation OK\n";
}
'''.replace('FUNCTIONS',functions).replace('CASES',cases).replace('DISPATCH',dispatch)
    args.work.mkdir(parents=True,exist_ok=True);source=args.work/'native_mods_check.cpp';source.write_text(harness,'utf-8')
    sys.path.insert(0,str(ROOT/'launcher'))
    from backend import Backend
    from toolchain import environment,run
    backend=Backend(ROOT,args.toolchain_workspace);tools=backend.local/'tools';env=environment(backend)
    obj=args.work/'native_mods_check.obj';exe=args.work/'native_mods_check.exe'
    run(backend,[tools/'llvm/bin/clang-cl.exe','/nologo','/EHsc','/std:c++latest','/MD','/O2','/c',source,'/I'+str(tools/'sdk/include'),'/Fo:'+str(obj)],env=env,phase='Compilando prueba de mods nativos')
    run(backend,[tools/'llvm/bin/lld-link.exe',obj,'/subsystem:console','/out:'+str(exe)],env=env,phase='Enlazando prueba de mods nativos')
    run(backend,[exe],env=env,phase='Verificando mods activados y desactivados')
    print('Native DoF and bloom instruction checks passed.')

if __name__=='__main__':main()
