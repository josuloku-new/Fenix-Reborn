#pragma once
#include <algorithm>
#include <cmath>
#include <cstdint>

// A stick represents velocity, while mouse packets represent displacement.
// Preview the current sample immediately, but commit it only once every 8 ms.
// UE3 can query XInput several times per frame; those queries must neither drain
// a mouse packet nor repeatedly amplify it. Tiny/subpixel motion stays intact.
struct Gow2MouseFilter {
  static constexpr double kCountsToStick = 4800.0;
  static constexpr double kSampleSeconds = 0.008;
  double elapsed = 0, pending_x = 0, pending_y = 0, x = 0, y = 0;
  bool have_sample = false;
  void Reset() { *this = {}; }
  void Update(double dx, double dy, double dt, double sensitivity,
              double smoothing_ms, double deadzone) {
    dt = std::max(0.0, dt);
    pending_x += dx; pending_y += dy; elapsed += dt;
    const bool complete = elapsed >= kSampleSeconds;
    if (pending_x == 0 && pending_y == 0) {
      if (complete) { x = y = 0; elapsed = 0; have_sample = false; }
      return;
    }
    // Hold a completed velocity while the next window fills. Otherwise a
    // 1000 Hz query stream would ramp from 1/8 speed in every new window.
    if (!complete && have_sample) return;
    // The minimum window prevents a second near-simultaneous query from
    // turning a tiny packet into a full-stick flick. No 8 ms startup gate.
    const double normalization = (1.0 / 60.0) / std::max(elapsed, kSampleSeconds);
    const double target_x = pending_x * normalization * sensitivity * kCountsToStick;
    const double target_y = -pending_y * normalization * sensitivity * kCountsToStick;
    const double smoothing_time = complete ? elapsed : dt;
    if (complete) { elapsed = pending_x = pending_y = 0; have_sample = true; }
    const double alpha = smoothing_ms <= 0 ? 1.0 :
        1.0 - std::exp(-smoothing_time / (smoothing_ms * 0.001));
    x += alpha * (target_x - x); y += alpha * (target_y - y);
    const double length = std::hypot(x, y);
    // Clamp radially; diagonal flicks must not move faster than horizontal ones.
    const double scaled = std::min(length, 32767.0);
    if (length > 32767.0) { x *= scaled / length; y *= scaled / length; }
  }
  void Get(int32_t& rx, int32_t& ry, double deadzone) const {
    const double length = std::hypot(x, y);
    if (length < 0.01) return;
    const double output = std::min(32767.0, deadzone + length * (32767.0 - deadzone) / 32767.0);
    rx += static_cast<int32_t>(x * output / length);
    ry += static_cast<int32_t>(y * output / length);
  }
};
