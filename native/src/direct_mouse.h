#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

// Displacement -> UE3 Rotator units. No stick, deadzone, speed cap or dt
// multiplier: a physical swipe produces the same angle at every frame rate.
struct Gow2MouseRotation {
  double pending_x = 0, pending_y = 0;
  void Reset() { pending_x = pending_y = 0; }
  bool Apply(uint32_t& yaw, int32_t& pitch, double dx, double dy,
             double sensitivity, double smoothing_ms, double dt) {
    pending_x += dx * sensitivity * 16.0;
    pending_y -= dy * sensitivity * 16.0;
    const double alpha = smoothing_ms <= 0 ? 1.0 :
        -std::expm1(-std::max(0.0, dt) / (smoothing_ms * .001));
    const double x_step = std::trunc(pending_x * alpha);
    const double y_step = std::trunc(pending_y * alpha);
    const auto x = static_cast<int32_t>(std::fmod(x_step, 65536.0));
    const auto y = static_cast<int32_t>(std::clamp(y_step, -65536.0, 65536.0));
    pending_x -= x_step; pending_y -= y_step;
    yaw += static_cast<uint32_t>(x);
    if (y) {
      const int32_t target = int32_t(int16_t(pitch)) + y;
      pitch = std::clamp(target, -12001, 10000);
      if (pitch != target) pending_y = 0; // No accumulated push at a pitch limit.
    }
    return x != 0 || y != 0;
  }
};

// TU0 GEngine -> GamePlayers[0] -> Actor. All reads are validated by the caller;
// the live allocations can move when the language or map changes.
template <typename Read>
uint32_t Gow2PlayerController(Read read) {
  uint32_t engine, players, count, player, controller, vtable;
  auto object = [](uint32_t address) {
    return address >= 0x10000 && address < 0x80000000 && !(address & 3);
  };
  if (!read(0x8312327C, engine) || !object(engine) ||
      !read(engine + 0x32C, players) || !object(players) ||
      !read(engine + 0x330, count) || !count || count > 4 ||
      !read(players, player) || !object(player) ||
      !read(player + 0x40, controller) || !object(controller) ||
      !read(controller, vtable) || vtable < 0x82000000 || vtable >= 0x84000000) return 0;
  return controller;
}
