#include "mouse_filter.h"
#include "direct_mouse.h"
#include <map>
#include <cstdlib>
#include <iostream>

void Check(bool ok) { if (!ok) std::abort(); }
int main() {
  Gow2MouseFilter slow, fast;
  // Identical motion, polled once or four times per 16ms sample.
  slow.Update(2, 0, .016, 1, 0, 9000);
  for (int i = 0; i < 4; ++i) fast.Update(.5, 0, .004, 1, 0, 9000);
  int32_t sx = 0, sy = 0, fx = 0, fy = 0;
  slow.Get(sx, sy, 9000); fast.Get(fx, fy, 9000);
  Check(std::abs(sx - fx) <= 1 && sy == 0 && fy == 0 && sx > 9000);
  // Repeated queries with no elapsed sample must preserve the current stick.
  fast.Update(0, 0, 0, 1, 0, 9000);
  int32_t repeat = 0, repeat_y = 0; fast.Get(repeat, repeat_y, 9000);
  Check(repeat == fx);
  fast.Update(0, 0, .008, 1, 0, 9000);
  repeat = repeat_y = 0; fast.Get(repeat, repeat_y, 9000);
  Check(repeat == 0 && repeat_y == 0);
  fast.Update(10000, 10000, .016, 10, 0, 9000);
  repeat = repeat_y = 0; fast.Get(repeat, repeat_y, 9000);
  Check(std::hypot(repeat, repeat_y) <= 32767.1);
  fast.Reset(); Check(fast.x == 0 && fast.pending_x == 0);
  // First packet must respond before 8 ms, including fractional motion.
  fast.Update(.125, 0, .001, 1, 2, 9000);
  fx = fy = 0; fast.Get(fx, fy, 9000); Check(fx > 9000 && fx < 32767);
  // Small movements stay ordered; faster gain must not destroy fine aim.
  int previous = 0;
  for (double counts : {.01, .05, .125, .25, .5, 1.0, 2.0}) {
    fast.Reset(); fast.Update(counts, 0, 1.0/60, 1, 0, 9000);
    fx = fy = 0; fast.Get(fx, fy, 9000); Check(fx > previous); previous = fx;
  }
  // Same physical velocity at different XInput poll rates: no recurring
  // sawtooth, no loss from extra queries, no change in steady movement speed.
  for (double interval : {.001, .002, .004, .008, 1.0/60, 1.0/30}) {
    fast.Reset();
    for (int i = 0; i < 1000; ++i) {
      fast.Update(100*interval, 0, interval, 1, 2, 9000);
      if (i > 100) Check(std::abs(fast.x - 8000.0) < 1);
    }
    fast.Update(0, 0, .008, 1, 2, 9000);
    fx = fy = 0; fast.Get(fx, fy, 9000); Check(fx == 0 && fy == 0);
  }
  // Normal camera gain is exactly 3x the previous 1600 scale before clipping;
  // aiming has its own lower setting and reversing direction is symmetric.
  slow.Reset();fast.Reset();
  slow.Update(2, 0, 1.0/60, 1, 0, 9000);
  fast.Update(-2, 0, 1.0/60, .65, 0, 9000);
  Check(std::abs(slow.x - 9600) < .01);
  Check(std::abs(fast.x + slow.x * .65) < .01);
  // Direct camera: identical displacement, independent of render/poll rate.
  for (int fps : {30, 60, 120, 240}) {
    Gow2MouseRotation direct; uint32_t yaw = 0; int32_t pitch = 0;
    for (int i = 0; i < fps; ++i) direct.Apply(yaw, pitch, 1200.0/fps, 0, 1, 0, 1.0/fps);
    Check(std::abs(int32_t(yaw) - 19200) <= 1 && pitch == 0);
    const auto stopped = yaw;
    for (int i = 0; i < fps; ++i) direct.Apply(yaw, pitch, 0, 0, 1, 0, 1.0/fps);
    Check(yaw == stopped);
  }
  Gow2MouseRotation direct; uint32_t yaw = 0; int32_t pitch = 0;
  for (int i = 0; i < 16; ++i) direct.Apply(yaw, pitch, .01, 0, 1, 0, .001);
  Check(yaw == 2); // Fractional packets accumulate instead of being lost.
  direct.Reset();yaw = 0;pitch = 0;
  direct.Apply(yaw, pitch, 2048, 100000, 1, 0, .016);
  Check(yaw == 32768 && pitch == -12001); // Fast 180°, no stick saturation.
  direct.Apply(yaw, pitch, -2048, -100000, 1, 0, .016);
  Check(yaw == 0 && pitch == 10000);
  direct.Reset();direct.Apply(yaw, pitch, 8192, 0, 1, 0, .016);
  Check(yaw == 0 && direct.pending_x == 0); // Multiple turns leave no lagged backlog.
  // Camera lookup follows relocated heaps (e.g. after switching language).
  for (uint32_t heap : {0x40200000u, 0x41800000u}) {
    std::map<uint32_t,uint32_t> memory{{0x8312327C,heap},{heap+0x32C,heap+0x1000},
      {heap+0x330,1},{heap+0x1000,heap+0x2000},{heap+0x2040,heap+0x3000},{heap+0x3000,0x82012340}};
    auto read = [&](uint32_t address,uint32_t& value) {auto it=memory.find(address);if(it==memory.end())return false;value=it->second;return true;};
    Check(Gow2PlayerController(read) == heap+0x3000);
    memory[heap+0x330] = 0;Check(Gow2PlayerController(read) == 0);
    memory[heap+0x330] = 1;memory[heap+0x2040] = 0xFFFFFFF0;Check(Gow2PlayerController(read) == 0);
  }
  std::cout << "Direct camera: displacement, fractional input, FPS independence, fast turns, pitch limits and relocated pointers: OK\n";
  std::cout << "Immediate fractional motion, 3x gain, aim, 30-1000 Hz polling, stop and radial clamp: OK\n";
}
