#include "input_guard.h"
#include <rex/input/input_system.h>
#include <rex/input/nop/nop_input_driver.h>
#include <atomic>
#include <iostream>
#include <thread>
#include <vector>

int main(int argc, char**) {
  using namespace rex::input;
  using rex::X_STATUS;
  using rex::X_RESULT;
  const bool serialized = argc == 1;
  std::cout << (serialized ? "Serialized" : "Unprotected diagnostic") << " SDK stress\n" << std::flush;
  InputSystem input(nullptr);
  input.Setup();
  input.AddDriver(std::make_unique<nop::NopInputDriver>(nullptr, 0));
  input.SetDeviceAssignment(std::make_unique<SlotAssignment>());
  std::atomic<bool> failed = false;
  std::vector<std::thread> threads;
  for (int thread = 0; thread < 8; ++thread) threads.emplace_back([&] {
    for (int i = 0; i < 2000; ++i) {
      std::unique_lock lock(Gow2InputMutex(), std::defer_lock);
      if (serialized) lock.lock();
      X_INPUT_STATE state{};
      X_INPUT_CAPABILITIES caps{};
      X_INPUT_VIBRATION vibration{};
      if (input.GetState(0, &state) != X_ERROR_SUCCESS ||
          input.GetCapabilities(0, 0, &caps) != X_ERROR_SUCCESS ||
          input.SetState(0, &vibration) != X_ERROR_SUCCESS) failed = true;
    }
  });
  for (auto& thread : threads) thread.join();
  input.Shutdown();
  if (failed) return 1;
  std::cout << "8 concurrent callers, 48000 SDK input operations: OK\n";
}
