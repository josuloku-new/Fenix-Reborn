#include "gow2_mods.h"
#include <rex/logging.h>
#include <atomic>
REXCVAR_DEFINE_BOOL(gow2_mod_lighting, true, "Mods", "GoW2 retail MSAA lighting workaround").lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_BOOL(gow2_mod_no_ao, true, "Mods", "Disable ambient occlusion to avoid resolve artifacts").lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_BOOL(gow2_mod_no_motion_blur, false, "Mods", "Disable camera motion blur").lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_BOOL(gow2_mod_no_lens_flares, false, "Mods", "Disable lens flares").lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_BOOL(gow2_mod_texture_streaming, false, "Mods", "Increase texture pool and stabilize streaming budget").lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_BOOL(gow2_mod_unlock_fps, false, "Mods", "Experimental retail FPS unlock and present interval 1").lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_BOOL(gow2_mod_no_dof_blur, false, "Mods", "Reduce depth-of-field gaussian blur; preserve the postprocess pipeline").lifecycle(rex::cvar::Lifecycle::kInitOnly);
REXCVAR_DEFINE_BOOL(gow2_mod_no_bloom, false, "Mods", "Disable bloom glow").lifecycle(rex::cvar::Lifecycle::kInitOnly);

void Gow2TraceVisualMod(unsigned int pc) {
  // Called only inside the enabled branch. Atomic bits cover render threads
  // and keep this diagnostic to at most five lines per game session.
  static std::atomic<unsigned int> seen{0};
  constexpr unsigned int sites[]{0x827296BC, 0x82729700, 0x824ECEF8, 0x824ED078, 0x824ED0A4};
  for (unsigned int i = 0; i < 5; ++i) {
    if (sites[i] != pc) continue;
    const auto bit = 1u << i;
    if (!(seen.fetch_or(bit, std::memory_order_relaxed) & bit))
      REXLOG_INFO("Native visual mod executed: {} at {:08X}", i < 2 ? "no_dof_blur" : "no_bloom", pc);
    return;
  }
}
