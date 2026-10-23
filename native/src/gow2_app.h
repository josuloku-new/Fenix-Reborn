// gow2 - ReXGlue Recompiled Project
//
// Customize your app by overriding virtual hooks from rex::ReXApp.

#pragma once

#include <rex/rex_app.h>
#include <rex/input/mnk/mnk_input_driver.h>
#include <rex/ui/keybinds.h>
#include <rex/input/input_system.h>
#include <rex/logging.h>
#include "gow2_mods.h"
#include "input_guard.h"
#include "gow2_overlay.h"
#include <rex/ui/imgui_drawer.h>
#include <rex/ui/window.h>
#include <imgui.h>
#include <atomic>

std::unique_ptr<rex::input::InputSystem> CreateGow2InputSystem(bool tool_mode);
REXCVAR_DECLARE(bool, fullscreen);

class Gow2App : public rex::ReXApp {
 public:
  using rex::ReXApp::ReXApp;

  static std::unique_ptr<rex::ui::WindowedApp> Create(
      rex::ui::WindowedAppContext& ctx) {
    return std::unique_ptr<Gow2App>(new Gow2App(ctx, "gow2",
        PPCImageConfig));
  }

  // Override virtual hooks for customization:
  // void OnPostInitLogging() override {}
  void OnPreSetup(rex::RuntimeConfig& config) override {
    REXCVAR_SET(fullscreen, true);
    config.gpu_plugin = "xenos";
    config.input_factory = REX_INPUT_BACKEND(CreateGow2InputSystem);
  }
  void OnConfigurePaths(rex::PathConfig& paths) override {
    overlay_config_path_ = paths.config_path;
  }
  void OnConfigureFonts(ImFontAtlas* atlas) override {
    gow2::ConfigureOverlayFonts(atlas);
  }
  void OnCreateDialogs(rex::ui::ImGuiDrawer* drawer) override {
    fps_overlay_ = std::make_unique<gow2::FpsDialog>(drawer);
    // Unregister the SDK callback and use a distinct bind: RegisterBind keeps
    // old entries alive, so registering the same name twice is unsafe.
    rex::ui::UnregisterBind("bind_settings");
    rex::ui::RegisterBind("gow2_bind_settings", "F4", "Settings menu", [this, drawer] {
      if (settings_overlay_) {
        settings_overlay_.reset();
        settings_open_.store(false);
        rex::input::mnk::SetMouseLookActive(mouse_look_before_settings_);
      } else {
        mouse_look_before_settings_ = rex::input::mnk::IsMouseLookActive();
        settings_open_.store(true);
        rex::input::mnk::SetMouseLookActive(false);
        settings_overlay_ = std::make_unique<gow2::SettingsDialog>(drawer, overlay_config_path_);
      }
    });
    rex::ui::RegisterBind("gow2_bind_mouse_capture", "F1", "Capture/release mouse look", [] {
      rex::input::mnk::SetMouseLookActive(!rex::input::mnk::IsMouseLookActive());
    });
  }
  void OnPostSetup() override {
    if (window()) window()->SetTitle("Fenix Reborn · v0.1");
    InstallGow2InputGuards(runtime()->function_dispatcher());
    gow2::InstallFrameCounter(runtime()->function_dispatcher());
    SetGuestFrameStats(gow2::ReadFrameStats);
    if (auto* input = static_cast<rex::input::InputSystem*>(runtime()->input_system())) {
      input->SetActiveCallback([this] {
        if (settings_open_.load()) return false;
        if (!imgui_drawer()) return true;
        const auto& io = imgui_drawer()->GetIO();
        return !io.WantCaptureMouse && !io.WantCaptureKeyboard;
      });
    }
    REXLOG_INFO("GoW2 native mods: lighting={}, no_ao={}, no_motion_blur={}, no_lens_flares={}, texture_streaming={}, no_dof_blur={}, no_bloom={}",
      REXCVAR_GET(gow2_mod_lighting), REXCVAR_GET(gow2_mod_no_ao),
      REXCVAR_GET(gow2_mod_no_motion_blur), REXCVAR_GET(gow2_mod_no_lens_flares),
      REXCVAR_GET(gow2_mod_texture_streaming), REXCVAR_GET(gow2_mod_no_dof_blur),
      REXCVAR_GET(gow2_mod_no_bloom));
    REXLOG_INFO("GoW2 input: direct camera displacement at viewport input tick; analog fallback available");
    REXLOG_INFO("GoW2 experimental FPS unlock: {}", REXCVAR_GET(gow2_mod_unlock_fps));
  }
  void OnShutdown() override {
    rex::ui::UnregisterBind("gow2_bind_settings");
    rex::ui::UnregisterBind("gow2_bind_mouse_capture");
    settings_overlay_.reset();
    fps_overlay_.reset();
  }
  // void OnLoadXexImage(std::string& xex_image) override {}
  // void OnPostLoadXexImage() override {}
  // void OnPostSetup() override {}
  // void OnCreateDialogs(rex::ui::ImGuiDrawer* drawer) override {}
  // std::unique_ptr<rex::ui::ImGuiDialog> CreateAchievementsOverlay() override;
  // std::unique_ptr<rex::ui::AchievementNotificationDialog>
  // CreateAchievementNotificationDialog() override;
  // void OnShutdown() override {}
  // void OnConfigurePaths(rex::PathConfig& paths) override {}
 private:
  std::filesystem::path overlay_config_path_;
  std::unique_ptr<gow2::SettingsDialog> settings_overlay_;
  std::unique_ptr<gow2::FpsDialog> fps_overlay_;
  std::atomic<bool> settings_open_{false};
  bool mouse_look_before_settings_ = true;
};
