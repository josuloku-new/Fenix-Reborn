#pragma once
#include <rex/ui/imgui_dialog.h>
#include <rex/ui/overlay/debug_overlay.h>
#include <filesystem>
#include <string>
namespace rex::runtime { class FunctionDispatcher; }

namespace gow2 {
// These IDs match the console language selected by the launcher.
int OverlayLanguage();
const char* Tr(const char* english);
const char* SettingLabel(const std::string& name);
const char* ModAuthors(const std::string& name);
void ConfigureOverlayFonts(ImFontAtlas* atlas);
void InstallFrameCounter(rex::runtime::FunctionDispatcher* dispatcher);
rex::ui::FrameStats ReadFrameStats();

class SettingsDialog final : public rex::ui::ImGuiDialog {
 public:
  SettingsDialog(rex::ui::ImGuiDrawer* drawer, std::filesystem::path path);
  ~SettingsDialog();
 protected:
  void OnDraw(ImGuiIO& io) override;
 private:
  std::filesystem::path config_path_;
  char search_buf_[128] = {};
  std::string selected_category_;
  std::string capturing_bind_name_;
};

class FpsDialog final : public rex::ui::ImGuiDialog {
 public:
  explicit FpsDialog(rex::ui::ImGuiDrawer* drawer) : ImGuiDialog(drawer) {}
 protected:
  void OnDraw(ImGuiIO& io) override;
};
}  // namespace gow2
