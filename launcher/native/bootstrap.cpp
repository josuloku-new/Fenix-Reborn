// By JoSuLoku @2026. Native self-contained launcher; no system TEMP extraction.
#include <Windows.h>
#include "bootstrap_config.h"
#include "branding.h"

struct Context {
  WCHAR workspace[32768], path[32768], core[32768], stage[32768], command[32768];
  BYTE buffer[65536];
  STARTUPINFOW startup;
  PROCESS_INFORMATION process;
};
static bool Append(WCHAR* target, DWORD& used, const WCHAR* source) {
  while (*source) { if (used >= 32767) return false; target[used++] = *source++; }
  target[used] = 0; return true;
}
static void Copy(WCHAR* target, const WCHAR* source) {
  DWORD used=0; if (!Append(target,used,source)) ExitProcess(1);
}
static void Directory(Context* c, const WCHAR* relative) {
  Copy(c->path,c->workspace); DWORD used=0; while(c->path[used]) ++used;
  if (!Append(c->path,used,relative)) ExitProcess(1);
  if (!CreateDirectoryW(c->path,nullptr) && GetLastError()!=ERROR_ALREADY_EXISTS) {
    MessageBoxW(nullptr,L"No se puede crear la carpeta de la aplicación. Usa una ubicación con permisos de escritura.",FENIX_APP_NAME,MB_OK|MB_ICONERROR); ExitProcess(1);
  }
}
static bool Matches(Context* c, const BYTE* data, DWORD length) {
  HANDLE file=CreateFileW(c->core,GENERIC_READ,FILE_SHARE_READ|FILE_SHARE_DELETE,nullptr,OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
  if(file==INVALID_HANDLE_VALUE) return false;
  LARGE_INTEGER size; bool equal=GetFileSizeEx(file,&size) && size.QuadPart==length;
  for(DWORD offset=0;equal && offset<length;) {
    DWORD amount=length-offset; if(amount>sizeof(c->buffer)) amount=sizeof(c->buffer);
    DWORD read=0; equal=ReadFile(file,c->buffer,amount,&read,nullptr) && read==amount;
    for(DWORD i=0;equal && i<read;++i) if(c->buffer[i]!=data[offset+i]) equal=false;
    offset+=amount;
  }
  CloseHandle(file); return equal;
}
extern "C" void WINAPI Start() {
  auto* c=static_cast<Context*>(HeapAlloc(GetProcessHeap(),HEAP_ZERO_MEMORY,sizeof(Context)));
  if(!c) ExitProcess(1);
  DWORD length=GetModuleFileNameW(nullptr,c->workspace,32768),directory=0;
  if(!length || length>=32768) ExitProcess(1);
  for(DWORD i=0;i<length;++i) if(c->workspace[i]==L'\\') directory=i+1;
  c->workspace[directory]=0;
  Directory(c,L".local"); Directory(c,L".local\\temp"); Directory(c,L".local\\temp\\work"); Directory(c,L".local\\temp\\app");
  // The Python tools use a separate scratch area from the application runtime.
  Directory(c,L".local\\temp\\work");
  SetEnvironmentVariableW(L"TEMP",c->path); SetEnvironmentVariableW(L"TMP",c->path); SetEnvironmentVariableW(L"TMPDIR",c->path);
  SetEnvironmentVariableW(L"FENIX_REBORN_WORKSPACE",c->workspace);
  SetEnvironmentVariableW(L"PYINSTALLER_RESET_ENVIRONMENT",L"1");
  SetDllDirectoryW(nullptr);
  Directory(c,L".local\\app"); Directory(c,CoreDirectory);
  Copy(c->core,c->path); DWORD used=0; while(c->core[used]) ++used;
  if(!Append(c->core,used,L"\\" FENIX_CORE_NAME)) ExitProcess(1);
  HRSRC resource=FindResourceW(nullptr,MAKEINTRESOURCEW(100),MAKEINTRESOURCEW(10));
  HGLOBAL loaded=resource?LoadResource(nullptr,resource):nullptr;
  const auto* data=static_cast<const BYTE*>(loaded?LockResource(loaded):nullptr);
  DWORD bytes=resource?SizeofResource(nullptr,resource):0;
  if(!data || !bytes) ExitProcess(1);
  if(!Matches(c,data,bytes)) {
    Copy(c->stage,c->core); used=0; while(c->stage[used]) ++used;
    if(!Append(c->stage,used,L".new")) ExitProcess(1);
    HANDLE file=CreateFileW(c->stage,GENERIC_WRITE,0,nullptr,CREATE_ALWAYS,FILE_ATTRIBUTE_NORMAL,nullptr);
    DWORD written=0; bool success=file!=INVALID_HANDLE_VALUE && WriteFile(file,data,bytes,&written,nullptr) && written==bytes;
    if(file!=INVALID_HANDLE_VALUE) CloseHandle(file);
    if(!success || !MoveFileExW(c->stage,c->core,MOVEFILE_REPLACE_EXISTING|MOVEFILE_WRITE_THROUGH)) {
      MessageBoxW(nullptr,L"No se pudo preparar la aplicación en su carpeta local. Comprueba el espacio y los permisos.",FENIX_APP_NAME,MB_OK|MB_ICONERROR); ExitProcess(1);
    }
  }
  used=0; Append(c->command,used,L"\""); if(!Append(c->command,used,c->core) || !Append(c->command,used,L"\"")) ExitProcess(1);
  const WCHAR* tail=GetCommandLineW();
  if(*tail==L'\"') { ++tail; while(*tail && *tail!=L'\"') ++tail; if(*tail) ++tail; }
  else while(*tail && *tail!=L' ' && *tail!=L'\t') ++tail;
  if(!Append(c->command,used,tail)) ExitProcess(1);
  c->startup.cb=sizeof(STARTUPINFOW);
  if(!CreateProcessW(c->core,c->command,nullptr,nullptr,FALSE,0,nullptr,c->workspace,&c->startup,&c->process)) ExitProcess(1);
  CloseHandle(c->process.hThread); WaitForSingleObject(c->process.hProcess,INFINITE);
  DWORD result=1; GetExitCodeProcess(c->process.hProcess,&result); CloseHandle(c->process.hProcess);
  HeapFree(GetProcessHeap(),0,c); ExitProcess(result);
}
