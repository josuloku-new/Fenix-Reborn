// Camera layout reference: Xenia Mousehook, GearsOfWars.cc and issue #35.
// Copyright 2023 Ben Vanik. BSD 3-Clause; see licenses/Xenia-Mousehook-BSD.txt.
// Native frame consumption, pointer validation and fractional input by JoSuLoku @2026.
#include "gow2_direct_mouse.h"
#include "direct_mouse.h"
#include <rex/hook.h>
#include <rex/cvar.h>
#include <rex/input/mnk/mnk_input_driver.h>
#include <Windows.h>
#include <chrono>
#include <mutex>

REXCVAR_DEFINE_BOOL(gow2_mouse_direct, true, "Input", "Direct mouse camera input");
REXCVAR_DECLARE(bool, mnk_mode);
REXCVAR_DECLARE(bool, mnk_mouse);
REXCVAR_DECLARE(double, mnk_sensitivity);
REXCVAR_DECLARE(double, gow2_mouse_aim_sensitivity);
REXCVAR_DECLARE(double, gow2_mouse_smoothing_ms);
namespace {
std::mutex mouse_mutex;
Gow2RawMouseSample pending;
bool active = false;
Gow2MouseRotation rotation;
std::chrono::steady_clock::time_point last_motion;
uint32_t LoadGuest(uint8_t* base, uint32_t address) {
  return __builtin_bswap32(*reinterpret_cast<volatile uint32_t*>(base + address));
}
void StoreGuest(uint8_t* base, uint32_t address, uint32_t value) {
  *reinterpret_cast<volatile uint32_t*>(base + address) = __builtin_bswap32(value);
}

bool Accessible(uint8_t* base, uint32_t address, size_t bytes, bool write = false) {
  if (address < 0x10000 || uint64_t(address) + bytes >= 0xA0000000) return false;
  MEMORY_BASIC_INFORMATION region{};
  const auto* ptr = base + address;
  if (!VirtualQuery(ptr, &region, sizeof(region)) || region.State != MEM_COMMIT ||
      (region.Protect & (PAGE_NOACCESS | PAGE_GUARD))) return false;
  if (write && !(region.Protect & (PAGE_READWRITE | PAGE_WRITECOPY | PAGE_EXECUTE_READWRITE))) return false;
  return uintptr_t(ptr) + bytes <= uintptr_t(region.BaseAddress) + region.RegionSize;
}
}

void Gow2PushRawMouse(double dx, double dy) {
  std::lock_guard lock(mouse_mutex);
  if (!active) return;
  pending.x += dx; pending.y += dy;
  last_motion = std::chrono::steady_clock::now();
}
void Gow2SetMouseAim(bool aiming) {
  std::lock_guard lock(mouse_mutex); pending.aiming = aiming;
}
void Gow2ResetRawMouse(bool enabled) {
  std::lock_guard lock(mouse_mutex);
  pending = {}; rotation.Reset(); active = enabled;
}
void Gow2SetRawMouseActive(bool enabled) {
  std::lock_guard lock(mouse_mutex);
  if (active == enabled) return;
  pending = {}; rotation.Reset(); active = enabled;
}

void Gow2ApplyDirectMouse(uint8_t* base, double dt) {
  std::lock_guard lock(mouse_mutex);
  const auto sample = pending; pending.x = pending.y = 0;
  if (!active || !REXCVAR_GET(gow2_mouse_direct) || !REXCVAR_GET(mnk_mode) ||
      !REXCVAR_GET(mnk_mouse) || !rex::input::mnk::IsMouseLookActive()) {
    rotation.Reset(); return;
  }
  auto read = [base](uint32_t address, uint32_t& value) {
    if (!Accessible(base, address, 4)) return false;
    value = LoadGuest(base, address); return true;
  };
  const uint32_t controller = Gow2PlayerController(read);
  static uint32_t previous_controller = UINT32_MAX;
  if (controller != previous_controller) {
    REXLOG_INFO("Direct mouse: player controller {:08X} (dynamic GEngine chain)", controller);
    previous_controller = controller;
  }
  if (!controller || !Accessible(base, controller + 0x60, 8, true)) {
    rotation.Reset(); return; // Drain input during loading; never replay a backlog.
  }
  auto pitch = int32_t(LoadGuest(base, controller + 0x60));
  auto yaw = LoadGuest(base, controller + 0x64);
  const double sensitivity = sample.aiming ? REXCVAR_GET(gow2_mouse_aim_sensitivity) : REXCVAR_GET(mnk_sensitivity);
  if (!rotation.Apply(yaw, pitch, sample.x, sample.y, sensitivity,
                      REXCVAR_GET(gow2_mouse_smoothing_ms), dt)) return;
  StoreGuest(base, controller + 0x60, uint32_t(pitch));
  StoreGuest(base, controller + 0x64, yaw);
  // A small periodic diagnostic, measured at actual game-frame consumption.
  static auto report = std::chrono::steady_clock::time_point{};
  const auto now = std::chrono::steady_clock::now();
  if (now - report > std::chrono::seconds(5)) {
    REXLOG_INFO("Direct mouse: controller={:08X}, dx={:.2f}, dy={:.2f}, aim={}, packet_age={:.1f}ms, game_frame={:.1f}ms",
      controller, sample.x, sample.y, sample.aiming,
      std::chrono::duration<double, std::milli>(now - last_motion).count(), dt * 1000);
    report = now;
  }
}
