/**
 * @file        input/mnk/mnk_input_driver.cpp
 * @brief       Keyboard/mouse input driver implementation.
 *
 * @copyright   Copyright (c) 2026 Tom Clay <tomc@tctechstuff.com>
 *              All rights reserved.
 *
 * @license     BSD 3-Clause License
 *              See LICENSE file in the project root for full license text.
 */
#include "gow2_mnk.h"
#include "gow2_direct_mouse.h"
#include <rex/input/mnk/mnk_input_driver.h>

#include <rex/cvar.h>
#include <rex/input/input.h>
#include <rex/logging.h>
#include <rex/ui/keybinds.h>
#include <rex/ui/virtual_key.h>
#include <rex/ui/window.h>

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <cstring>
#include <string_view>

REXCVAR_DECLARE(bool, mnk_mode);
REXCVAR_DECLARE(bool, mnk_mouse);
REXCVAR_DECLARE(double, mnk_sensitivity);
REXCVAR_DECLARE(bool, gow2_mouse_direct);
REXCVAR_DECLARE(std::string, keybind_a);
REXCVAR_DECLARE(std::string, keybind_b);
REXCVAR_DECLARE(std::string, keybind_x);
REXCVAR_DECLARE(std::string, keybind_y);
REXCVAR_DECLARE(std::string, keybind_left_trigger);
REXCVAR_DECLARE(std::string, keybind_right_trigger);
REXCVAR_DECLARE(std::string, keybind_left_shoulder);
REXCVAR_DECLARE(std::string, keybind_right_shoulder);
REXCVAR_DECLARE(std::string, keybind_lstick_up);
REXCVAR_DECLARE(std::string, keybind_lstick_down);
REXCVAR_DECLARE(std::string, keybind_lstick_left);
REXCVAR_DECLARE(std::string, keybind_lstick_right);
REXCVAR_DECLARE(std::string, keybind_lstick_press);
REXCVAR_DECLARE(std::string, keybind_rstick_up);
REXCVAR_DECLARE(std::string, keybind_rstick_down);
REXCVAR_DECLARE(std::string, keybind_rstick_left);
REXCVAR_DECLARE(std::string, keybind_rstick_right);
REXCVAR_DECLARE(std::string, keybind_rstick_press);
REXCVAR_DECLARE(std::string, keybind_dpad_up);
REXCVAR_DECLARE(std::string, keybind_dpad_down);
REXCVAR_DECLARE(std::string, keybind_dpad_left);
REXCVAR_DECLARE(std::string, keybind_dpad_right);
REXCVAR_DECLARE(std::string, keybind_back);
REXCVAR_DECLARE(std::string, keybind_start);
REXCVAR_DECLARE(std::string, keybind_guide);
REXCVAR_DEFINE_DOUBLE(gow2_mouse_aim_sensitivity, 0.65, "Input", "Mouse sensitivity while aiming").range(0.01, 10.0);
REXCVAR_DEFINE_DOUBLE(gow2_mouse_smoothing_ms, 0.0, "Input", "Mouse smoothing in milliseconds").range(0.0, 30.0);
REXCVAR_DEFINE_DOUBLE(gow2_mouse_deadzone, 9000.0, "Input", "Right-stick deadzone compensation").range(0.0, 16000.0);
namespace rex::input::gow2 {

namespace {

// A single device, so its handle is a constant.
constexpr rex::input::DeviceId kMnkDevice = static_cast<rex::input::DeviceId>(0x4D4E4B00);

// Bind values are a comma-separated list of alternatives, each optionally
// carrying modifier prefixes: "Q,I" or "Shift+W". Modifier matching is exact,
// so "Up" stays silent while Shift is held and "Shift+Up" stays silent without
// it. That is what lets the D-pad share the arrow keys. A consequence is
// that binding a bare modifier name ("Shift") can never fire, since holding it
// makes the live mask non-zero while the bind wants zero.
constexpr uint8_t kModShift = 1u << 0;
constexpr uint8_t kModCtrl = 1u << 1;
constexpr uint8_t kModAlt = 1u << 2;

uint8_t LiveModifiers(const bool (&key_down)[256]) {
  uint8_t mods = 0;
  if (key_down[static_cast<uint16_t>(rex::ui::VirtualKey::kShift)])
    mods |= kModShift;
  if (key_down[static_cast<uint16_t>(rex::ui::VirtualKey::kControl)])
    mods |= kModCtrl;
  if (key_down[static_cast<uint16_t>(rex::ui::VirtualKey::kMenu)])
    mods |= kModAlt;
  return mods;
}

// Strips leading modifier prefixes off 'token', advancing it to the bare key
// name and returning the mask they require.
uint8_t TakeModifiers(std::string_view& token) {
  uint8_t mods = 0;
  for (;;) {
    size_t plus = token.find('+');
    if (plus == std::string_view::npos || plus == 0) {
      break;
    }
    std::string_view head = token.substr(0, plus);
    uint8_t bit = 0;
    if (head == "Shift") {
      bit = kModShift;
    } else if (head == "Ctrl" || head == "Control") {
      bit = kModCtrl;
    } else if (head == "Alt") {
      bit = kModAlt;
    } else {
      break;
    }
    mods |= bit;
    token.remove_prefix(plus + 1);
  }
  return mods;
}

std::string_view TrimSpaces(std::string_view s) {
  while (!s.empty() && s.front() == ' ') {
    s.remove_prefix(1);
  }
  while (!s.empty() && s.back() == ' ') {
    s.remove_suffix(1);
  }
  return s;
}

bool TokenPressed(const bool (&key_down)[256], std::string_view token, uint8_t live_mods) {
  uint8_t want = TakeModifiers(token);
  if (want != live_mods) {
    return false;
  }
  rex::ui::VirtualKey vk = rex::ui::ParseVirtualKey(token);
  if (vk == rex::ui::VirtualKey::kNone) {
    return false;
  }
  uint16_t idx = static_cast<uint16_t>(vk);
  return idx < 256 && key_down[idx];
}


}  // namespace

using rex::input::mnk::IsMouseLookActive;

using rex::ui::VirtualKey;

Gow2MnkInputDriver::Gow2MnkInputDriver(rex::ui::Window* window, size_t window_z_order)
    : InputDriver(window, window_z_order) {}

Gow2MnkInputDriver::~Gow2MnkInputDriver() {
  // Detach handled by OnClosing; if window outlives the driver, clean up here.
  DetachFromWindow();
}

X_STATUS Gow2MnkInputDriver::Setup() {
  rex::input::mnk::SetMouseLookActive(true);
  REXLOG_INFO("GoW2 MnK: automatic camera capture initialized");
  return X_STATUS_SUCCESS;
}

void Gow2MnkInputDriver::OnWindowAvailable(rex::ui::Window* window) {
  if (window) {
    {
      std::lock_guard lock(state_mutex_);
      attached_window_ = window;
    }
    window->AddInputListener(this, window_z_order());
    window->AddListener(this);
    REXLOG_INFO("GoW2 MnK: attached to game window");
    mouse_capture_requested_.store(IsEnabled() && REXCVAR_GET(mnk_mouse));
    ApplyMouseCaptureFromUIThread();
  }
}

void Gow2MnkInputDriver::OnClosing(rex::ui::UIEvent&) {
  DetachFromWindow();
}

void Gow2MnkInputDriver::DetachFromWindow() {
  rex::ui::Window* window = attached_window_;
  if (!window) {
    return;
  }
  window->app_context().CallInUIThreadSynchronous([this, window] {
    // Detach first so nothing new is queued, then run out what already was.
    {
      std::lock_guard lock(state_mutex_);
      attached_window_ = nullptr;
    }
    if (mouse_capture_update_queued_.load(std::memory_order_relaxed)) {
      window->app_context().ExecutePendingFunctionsFromUIThread();
    }
    ReleaseMouseCaptureFromUIThread(window);
    window->RemoveInputListener(this);
    window->RemoveListener(this);
  });
}

bool Gow2MnkInputDriver::IsEnabled() const {
  return REXCVAR_GET(mnk_mode);
}

static bool IsBindPressed(const bool (&key_down)[256], const std::string& cvar_val) {
  const uint8_t live_mods = LiveModifiers(key_down);
  std::string_view rest(cvar_val);
  while (!rest.empty()) {
    size_t comma = rest.find(',');
    std::string_view token = rest.substr(0, comma);
    if (comma == std::string_view::npos) {
      rest = std::string_view();
    } else {
      rest.remove_prefix(comma + 1);
    }
    token = TrimSpaces(token);
    if (!token.empty() && TokenPressed(key_down, token, live_mods)) {
      return true;
    }
  }
  return false;
}

void Gow2MnkInputDriver::EnumerateDevices(std::vector<DeviceInfo>& out) {
  // Disabled means no device at all, so it never occupies a guest user slot.
  if (!IsEnabled()) {
    return;
  }
  DeviceInfo info;
  info.id = kMnkDevice;
  info.name = "Keyboard and Mouse";
  info.synthetic = true;
  out.push_back(info);
}

X_RESULT Gow2MnkInputDriver::GetDeviceCapabilities(DeviceId id, uint32_t flags,
                                               X_INPUT_CAPABILITIES* out_caps) {
  if (!IsEnabled() || id != kMnkDevice) {
    return X_ERROR_DEVICE_NOT_CONNECTED;
  }
  if (out_caps) {
    std::memset(out_caps, 0, sizeof(*out_caps));
    out_caps->type = 0x01;
    out_caps->sub_type = 0x01;
    out_caps->flags = 0;
    out_caps->gamepad.buttons = 0xFFFF;
    out_caps->gamepad.left_trigger = 0xFF;
    out_caps->gamepad.right_trigger = 0xFF;
    out_caps->gamepad.thumb_lx = static_cast<int16_t>(0x7FFF);
    out_caps->gamepad.thumb_ly = static_cast<int16_t>(0x7FFF);
    out_caps->gamepad.thumb_rx = static_cast<int16_t>(0x7FFF);
    out_caps->gamepad.thumb_ry = static_cast<int16_t>(0x7FFF);
    out_caps->vibration.left_motor_speed = 0xFFFF;
    out_caps->vibration.right_motor_speed = 0xFFFF;
  }
  return X_ERROR_SUCCESS;
}

X_RESULT Gow2MnkInputDriver::GetDeviceState(DeviceId id, X_INPUT_STATE* out_state) {
  if (!IsEnabled() || id != kMnkDevice) {
    return X_ERROR_DEVICE_NOT_CONNECTED;
  }

  // Mouse look is opt in. Without this gate, keyboard input alone would hide
  // and lock the cursor, breaking the ImGui overlays.
  QueueMouseCaptureUpdate(IsEnabled() && REXCVAR_GET(mnk_mouse) && IsMouseLookActive() &&
                          has_focus_ && is_active());

  if (!is_active() || !has_focus_) {
    Gow2SetRawMouseActive(false);
    if (out_state) {
      std::memset(out_state, 0, sizeof(*out_state));
      out_state->packet_number = packet_number_;
    }
    return X_ERROR_SUCCESS;
  }

  std::lock_guard lock(state_mutex_);

  uint16_t buttons = 0;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_a)))
    buttons |= X_INPUT_GAMEPAD_A;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_b)))
    buttons |= X_INPUT_GAMEPAD_B;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_x)))
    buttons |= X_INPUT_GAMEPAD_X;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_y)))
    buttons |= X_INPUT_GAMEPAD_Y;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_left_shoulder)))
    buttons |= X_INPUT_GAMEPAD_LEFT_SHOULDER;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_right_shoulder)))
    buttons |= X_INPUT_GAMEPAD_RIGHT_SHOULDER;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_lstick_press)))
    buttons |= X_INPUT_GAMEPAD_LEFT_THUMB;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_rstick_press)))
    buttons |= X_INPUT_GAMEPAD_RIGHT_THUMB;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_back)))
    buttons |= X_INPUT_GAMEPAD_BACK;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_start)))
    buttons |= X_INPUT_GAMEPAD_START;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_guide)))
    buttons |= X_INPUT_GAMEPAD_GUIDE;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_dpad_up)))
    buttons |= X_INPUT_GAMEPAD_DPAD_UP;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_dpad_down)))
    buttons |= X_INPUT_GAMEPAD_DPAD_DOWN;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_dpad_left)))
    buttons |= X_INPUT_GAMEPAD_DPAD_LEFT;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_dpad_right)))
    buttons |= X_INPUT_GAMEPAD_DPAD_RIGHT;

  uint8_t lt = IsBindPressed(key_down_, REXCVAR_GET(keybind_left_trigger)) ? 0xFF : 0;
  uint8_t rt = IsBindPressed(key_down_, REXCVAR_GET(keybind_right_trigger)) ? 0xFF : 0;

  int32_t lx = 0;
  int32_t ly = 0;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_lstick_left)))
    lx -= INT16_MAX;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_lstick_right)))
    lx += INT16_MAX;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_lstick_up)))
    ly += INT16_MAX;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_lstick_down)))
    ly -= INT16_MAX;

  int32_t rx = 0;
  int32_t ry = 0;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_rstick_left)))
    rx -= INT16_MAX;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_rstick_right)))
    rx += INT16_MAX;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_rstick_up)))
    ry += INT16_MAX;
  if (IsBindPressed(key_down_, REXCVAR_GET(keybind_rstick_down)))
    ry -= INT16_MAX;

  const auto now = std::chrono::steady_clock::now();
  const double dt = std::chrono::duration<double>(now - mouse_sample_time_).count();
  mouse_sample_time_ = now;
  const bool direct = REXCVAR_GET(gow2_mouse_direct);
  const bool mouse_look = REXCVAR_GET(mnk_mouse) && IsMouseLookActive();
  Gow2SetRawMouseActive(direct && mouse_look);
  Gow2SetMouseAim(lt != 0);
  if (!direct && mouse_look) {
    if (dt > 0.1) mouse_filter_.Reset();
    mouse_filter_.Update(mouse_dx_, mouse_dy_, std::min(dt, 0.1),
        lt ? REXCVAR_GET(gow2_mouse_aim_sensitivity) : REXCVAR_GET(mnk_sensitivity),
        REXCVAR_GET(gow2_mouse_smoothing_ms),
        REXCVAR_GET(gow2_mouse_deadzone));
    mouse_filter_.Get(rx, ry, REXCVAR_GET(gow2_mouse_deadzone));
  } else {
    mouse_filter_.Reset();
  }
  // Drained unconditionally: deltas keep accumulating in OnMouseMove while the
  // mouse is off, and toggling it on would otherwise dump the whole backlog
  // into one frame as a camera snap.
  mouse_dx_ = 0.0f;
  mouse_dy_ = 0.0f;

  auto clamp16 = [](int32_t v) -> int16_t {
    return static_cast<int16_t>(std::clamp(v, (int32_t)INT16_MIN, (int32_t)INT16_MAX));
  };

  packet_number_++;

  if (out_state) {
    out_state->packet_number = packet_number_;
    out_state->gamepad.buttons = buttons;
    out_state->gamepad.left_trigger = lt;
    out_state->gamepad.right_trigger = rt;
    out_state->gamepad.thumb_lx = clamp16(lx);
    out_state->gamepad.thumb_ly = clamp16(ly);
    out_state->gamepad.thumb_rx = clamp16(rx);
    out_state->gamepad.thumb_ry = clamp16(ry);
  }
  return X_ERROR_SUCCESS;
}

X_RESULT Gow2MnkInputDriver::SetDeviceVibration(DeviceId id, X_INPUT_VIBRATION* vibration) {
  if (!IsEnabled() || id != kMnkDevice) {
    return X_ERROR_DEVICE_NOT_CONNECTED;
  }
  return X_ERROR_SUCCESS;
}

X_RESULT Gow2MnkInputDriver::GetDeviceKeystroke(DeviceId id, uint32_t flags,
                                            X_INPUT_KEYSTROKE* out_keystroke) {
  if (!IsEnabled() || id != kMnkDevice) {
    return X_ERROR_DEVICE_NOT_CONNECTED;
  }
  std::lock_guard lock(state_mutex_);
  if (keystroke_queue_.empty()) {
    return X_ERROR_EMPTY;
  }
  if (out_keystroke) {
    *out_keystroke = keystroke_queue_.front();
  }
  keystroke_queue_.pop();
  return X_ERROR_SUCCESS;
}

void Gow2MnkInputDriver::EnqueueKeystroke(uint16_t vk_pad, bool down) {
  X_INPUT_KEYSTROKE ks = {};
  ks.virtual_key = vk_pad;
  ks.unicode = 0;
  ks.flags = down ? X_INPUT_KEYSTROKE_KEYDOWN : X_INPUT_KEYSTROKE_KEYUP;
  // InputSystem stamps the guest user this device is assigned to.
  ks.user_index = 0;
  ks.hid_code = 0;
  keystroke_queue_.push(ks);
}

void Gow2MnkInputDriver::QueueMouseCaptureUpdate(bool should_capture) {
  if (mouse_capture_requested_.exchange(should_capture, std::memory_order_relaxed) ==
      should_capture) return;
  bool already_queued = false;
  if (!mouse_capture_update_queued_.compare_exchange_strong(already_queued, true)) {
    return;
  }
  std::lock_guard lock(state_mutex_);
  if (!attached_window_) {
    mouse_capture_update_queued_.store(false, std::memory_order_relaxed);
    return;
  }
  // Deferred, not CallInUIThread: running inline would re-enter state_mutex_.
  attached_window_->app_context().CallInUIThreadDeferred([this] {
    mouse_capture_update_queued_.store(false, std::memory_order_relaxed);
    ApplyMouseCaptureFromUIThread();
  });
}

void Gow2MnkInputDriver::ApplyMouseCaptureFromUIThread() {
  rex::ui::Window* window = attached_window_;
  if (!window) {
    return;
  }
  bool should_capture = mouse_capture_requested_.load(std::memory_order_relaxed);
  if (!should_capture && !mouse_captured_) {
    return;
  }
  if (!should_capture) {
    ReleaseMouseCaptureFromUIThread(window);
    return;
  }
  // Setting relative mode can flush pending SDL motion. Do it only on a
  // capture transition, never from every motion event / controller query.
  if (mouse_captured_) return;
  precapture_cursor_visibility_ = window->GetCursorVisibility();
  mouse_captured_ = true;
  window->CaptureMouse();
  window->SetCursorVisibility(rex::ui::Window::CursorVisibility::kHidden);
  relative_mouse_mode_ = window->SetRelativeMouseMode(true);
  if (!relative_mouse_mode_) {
    REXLOG_WARN("Pointer lock unavailable, mouse look falls back to recentering the cursor");
  }
  REXLOG_INFO("GoW2 MnK: camera captured, relative={}", relative_mouse_mode_);
  // Reset deltas to avoid a spike on capture start
  std::lock_guard lock(state_mutex_);
  mouse_filter_.Reset();
  mouse_sample_time_ = std::chrono::steady_clock::now();
  Gow2ResetRawMouse(REXCVAR_GET(gow2_mouse_direct));
  mouse_dx_ = 0.0f;
  mouse_dy_ = 0.0f;
}

void Gow2MnkInputDriver::ReleaseMouseCaptureFromUIThread(rex::ui::Window* window) {
  if (!mouse_captured_) {
    return;
  }
  mouse_captured_ = false;
  Gow2ResetRawMouse(false);
  REXLOG_INFO("GoW2 MnK: camera released");
  window->SetCursorVisibility(precapture_cursor_visibility_);
  window->SetRelativeMouseMode(false);
  relative_mouse_mode_ = false;
  window->ReleaseMouse();
}

void Gow2MnkInputDriver::RecenterCursorFromUIThread(int32_t x, int32_t y) {
  rex::ui::Window* window = attached_window_;
  if (!window) {
    return;
  }
  int32_t width = int32_t(window->GetActualPhysicalWidth());
  int32_t height = int32_t(window->GetActualPhysicalHeight());
  if (width <= 0 || height <= 0) {
    return;
  }
  // Only once the pointer has drifted well off the middle, to keep warps rare.
  if (std::abs(x - width / 2) < width / 4 && std::abs(y - height / 2) < height / 4) {
    return;
  }
  int32_t center_x = 0;
  int32_t center_y = 0;
  if (window->WarpMouseToCenter(center_x, center_y)) {
    prev_mouse_x_ = center_x;
    prev_mouse_y_ = center_y;
  }
}

void Gow2MnkInputDriver::SetKeyState(uint16_t vk, bool down) {
  if (vk < 256) {
    key_down_[vk] = down;
  }
}

void Gow2MnkInputDriver::OnKeyDown(rex::ui::KeyEvent& e) {
  if (!IsEnabled() || !has_focus_)
    return;
  std::lock_guard lock(state_mutex_);
  uint16_t vk = static_cast<uint16_t>(e.virtual_key());
  SetKeyState(vk, true);
}

void Gow2MnkInputDriver::OnKeyUp(rex::ui::KeyEvent& e) {
  if (!IsEnabled())
    return;
  std::lock_guard lock(state_mutex_);
  uint16_t vk = static_cast<uint16_t>(e.virtual_key());
  SetKeyState(vk, false);
}

void Gow2MnkInputDriver::OnMouseDown(rex::ui::MouseEvent& e) {
  if (!IsEnabled() || !has_focus_)
    return;
  if (is_active() && REXCVAR_GET(mnk_mouse) && IsMouseLookActive()) {
    mouse_capture_requested_.store(true);
    ApplyMouseCaptureFromUIThread();
  }
  std::lock_guard lock(state_mutex_);
  switch (e.button()) {
    case rex::ui::MouseEvent::Button::kLeft:
      SetKeyState(static_cast<uint16_t>(VirtualKey::kLButton), true);
      break;
    case rex::ui::MouseEvent::Button::kRight:
      SetKeyState(static_cast<uint16_t>(VirtualKey::kRButton), true);
      break;
    case rex::ui::MouseEvent::Button::kMiddle:
      SetKeyState(static_cast<uint16_t>(VirtualKey::kMButton), true);
      break;
    default:
      break;
  }
}

void Gow2MnkInputDriver::OnMouseUp(rex::ui::MouseEvent& e) {
  if (!IsEnabled())
    return;
  std::lock_guard lock(state_mutex_);
  switch (e.button()) {
    case rex::ui::MouseEvent::Button::kLeft:
      SetKeyState(static_cast<uint16_t>(VirtualKey::kLButton), false);
      break;
    case rex::ui::MouseEvent::Button::kRight:
      SetKeyState(static_cast<uint16_t>(VirtualKey::kRButton), false);
      break;
    case rex::ui::MouseEvent::Button::kMiddle:
      SetKeyState(static_cast<uint16_t>(VirtualKey::kMButton), false);
      break;
    default:
      break;
  }
}

void Gow2MnkInputDriver::OnMouseMove(rex::ui::MouseEvent& e) {
  if (!IsEnabled() || !has_focus_)
    return;
  if (is_active() && REXCVAR_GET(mnk_mouse) && IsMouseLookActive()) {
    mouse_capture_requested_.store(true);
    ApplyMouseCaptureFromUIThread();
  }
  int32_t x = e.x();
  int32_t y = e.y();
  {
    std::lock_guard lock(state_mutex_);
    if (relative_mouse_mode_) {
      // The pointer is locked, so the absolute position no longer moves.
      mouse_dx_ += e.dx();
      mouse_dy_ += e.dy();
    } else {
      mouse_dx_ += float(x - prev_mouse_x_);
      mouse_dy_ += float(y - prev_mouse_y_);
    }
    if (REXCVAR_GET(gow2_mouse_direct) && REXCVAR_GET(mnk_mouse) &&
        IsMouseLookActive() && is_active()) {
      Gow2SetRawMouseActive(true);
      Gow2PushRawMouse(relative_mouse_mode_ ? e.dx() : float(x - prev_mouse_x_),
                       relative_mouse_mode_ ? e.dy() : float(y - prev_mouse_y_));
    }
  }
  prev_mouse_x_ = x;
  prev_mouse_y_ = y;
  // Without a pointer lock the cursor still has to be kept off the edges.
  if (mouse_captured_ && !relative_mouse_mode_) {
    RecenterCursorFromUIThread(x, y);
  }
}

void Gow2MnkInputDriver::OnLostFocus(rex::ui::UISetupEvent&) {
  has_focus_ = false;
  Gow2ResetRawMouse(false);
  // Withdraw the request too, or an update queued before the focus loss grabs
  // the cursor straight back.
  mouse_capture_requested_.store(false, std::memory_order_relaxed);
  {
    std::lock_guard lock(state_mutex_);
    std::memset(key_down_, 0, sizeof(key_down_));
    mouse_filter_.Reset();
    mouse_sample_time_ = std::chrono::steady_clock::now();
    mouse_dx_ = 0.0f;
    mouse_dy_ = 0.0f;
  }
  if (attached_window_) {
    ReleaseMouseCaptureFromUIThread(attached_window_);
  }
}

void Gow2MnkInputDriver::OnGotFocus(rex::ui::UISetupEvent&) {
  has_focus_ = true;
  rex::input::mnk::SetMouseLookActive(true);
  mouse_capture_requested_.store(IsEnabled() && REXCVAR_GET(mnk_mouse) && is_active());
  ApplyMouseCaptureFromUIThread();
}

}  // namespace rex::input::gow2
