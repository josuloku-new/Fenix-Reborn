// By JoSuLoku @2026. Application entry points, containing no game code.
#include <Windows.h>
#include "branding.h"

struct Context {
  WCHAR path[32768];
  WCHAR command[32768];
  STARTUPINFOW startup;
  PROCESS_INFORMATION process;
};
static bool Append(WCHAR* target, DWORD& used, const WCHAR* source) {
  while (*source) {
    if (used >= 32767) return false;
    target[used++] = *source++;
  }
  target[used] = 0;
  return true;
}
extern "C" void WINAPI Start() {
  auto* c = static_cast<Context*>(HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, sizeof(Context)));
  if (!c) ExitProcess(1);
  DWORD length = GetModuleFileNameW(nullptr, c->path, 32768), directory = 0;
  if (!length || length >= 32768) ExitProcess(1);
  for (DWORD i = 0; i < length; ++i) if (c->path[i] == L'\\') directory = i + 1;
  c->path[directory] = 0;
  DWORD pathUsed = directory;
  if (!Append(c->path, pathUsed, FENIX_SETUP_NAME)) ExitProcess(1);
  DWORD used = 0;
  if (!Append(c->command, used, L"\"") || !Append(c->command, used, c->path)) ExitProcess(1);
#ifdef FENIX_CONFIGURE
  if (!Append(c->command, used, L"\" --configure")) ExitProcess(1);
#else
  if (!Append(c->command, used, L"\" --play")) ExitProcess(1);
#endif
  // Preserve optional command-line arguments, including the packaging self-test.
  const WCHAR* tail = GetCommandLineW();
  if (*tail == L'\"') { ++tail; while (*tail && *tail != L'\"') ++tail; if (*tail) ++tail; }
  else while (*tail && *tail != L' ' && *tail != L'\t') ++tail;
  if (!Append(c->command, used, tail)) ExitProcess(1);
  c->startup.cb = sizeof(STARTUPINFOW);
  if (!CreateProcessW(c->path, c->command, nullptr, nullptr, FALSE, 0, nullptr, nullptr, &c->startup, &c->process)) {
    MessageBoxW(nullptr, L"No se pudo abrir " FENIX_SETUP_NAME L". Mantén los ejecutables en la misma carpeta.", FENIX_APP_NAME, MB_OK | MB_ICONERROR);
    ExitProcess(1);
  }
  CloseHandle(c->process.hThread); CloseHandle(c->process.hProcess);
  HeapFree(GetProcessHeap(), 0, c);
  ExitProcess(0);
}
