#include "gow2_mnk.h"
#include <rex/cvar.h>
#include <rex/input/input_system.h>
#include <rex/input/sdl/sdl_input_driver.h>
#include <rex/input/xinput/xinput_input_driver.h>
#include <rex/input/nop/nop_input_driver.h>

REXCVAR_DECLARE(std::string, input_backend);

std::unique_ptr<rex::input::InputSystem> CreateGow2InputSystem(bool tool_mode) {
  using namespace rex::input;
  using rex::X_STATUS;
  if (tool_mode) return CreateDefaultInputSystem(true);
  auto input = std::make_unique<InputSystem>(nullptr);
  std::unique_ptr<InputDriver> pad;
  if (REXCVAR_GET(input_backend) == "xinput")
    pad = std::make_unique<xinput::XinputInputDriver>(nullptr, 0);
  else
    pad = std::make_unique<sdl::SDLInputDriver>(nullptr, 0);
  if (pad->Setup() == X_STATUS_SUCCESS) input->AddDriver(std::move(pad));
  auto mnk = std::make_unique<gow2::Gow2MnkInputDriver>(nullptr, 0);
  if (mnk->Setup() == X_STATUS_SUCCESS) input->AddDriver(std::move(mnk));
  input->AddDriver(std::make_unique<nop::NopInputDriver>(nullptr, 1));
  input->SetDeviceAssignment(std::make_unique<SlotAssignment>());
  return input;
}
