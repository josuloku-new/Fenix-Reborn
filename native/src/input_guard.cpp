#include "input_guard.h"
#include <rex/hook.h>
#include <rex/system/function_dispatcher.h>
#include <Windows.h>

// ReXGlue 0.10 InputSystem refreshes devices_ / device_owners_ on every query.
// Multiple guest threads can clear and repopulate those vectors concurrently.
// Serialize the complete SDK call, including enumeration, assignment and merge.
std::recursive_mutex& Gow2InputMutex() {
  static std::recursive_mutex mutex;
  return mutex;
}

static PPCFunc* Original(const char* name) {
  auto module = GetModuleHandleW(L"rexruntime.dll");
  auto function = module ? reinterpret_cast<PPCFunc*>(GetProcAddress(module, name)) : nullptr;
  if (!function) REX_FATAL("Missing SDK input export: {}", name);
  return function;
}

#define GOW2_INPUT_GUARD(name) \
  extern "C" REX_FUNC(name) { \
    static PPCFunc* original = Original(#name); \
    std::lock_guard lock(Gow2InputMutex()); \
    original(ctx, base); \
  }

GOW2_INPUT_GUARD(__imp__XamInputGetCapabilities)
GOW2_INPUT_GUARD(__imp__XamInputGetCapabilitiesEx)
GOW2_INPUT_GUARD(__imp__XamInputGetState)
GOW2_INPUT_GUARD(__imp__XamInputSetState)
GOW2_INPUT_GUARD(__imp__XamInputGetKeystroke)
GOW2_INPUT_GUARD(__imp__XamInputGetKeystrokeEx)

void InstallGow2InputGuards(rex::runtime::FunctionDispatcher* dispatcher) {
  // Also cover indirect calls through the retail XEX import thunk addresses.
  if (!dispatcher->SetFunction(0x82F4D15C, __imp__XamInputGetCapabilities) ||
      !dispatcher->SetFunction(0x82F4D16C, __imp__XamInputGetState) ||
      !dispatcher->SetFunction(0x82F4D17C, __imp__XamInputSetState)) {
    REX_FATAL("Unable to install serialized GoW2 input imports");
  }
  REXLOG_INFO("GoW2 input: SDK device enumeration and controller queries serialized");
}
