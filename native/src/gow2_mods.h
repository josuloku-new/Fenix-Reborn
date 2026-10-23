#pragma once
#include <rex/cvar.h>
REXCVAR_DECLARE(bool, gow2_mod_lighting);
REXCVAR_DECLARE(bool, gow2_mod_no_ao);
REXCVAR_DECLARE(bool, gow2_mod_no_motion_blur);
REXCVAR_DECLARE(bool, gow2_mod_no_lens_flares);
REXCVAR_DECLARE(bool, gow2_mod_texture_streaming);
REXCVAR_DECLARE(bool, gow2_mod_unlock_fps);
REXCVAR_DECLARE(bool, gow2_mod_no_dof_blur);
REXCVAR_DECLARE(bool, gow2_mod_no_bloom);

// One diagnostic per active visual patch site, without per-frame log traffic.
void Gow2TraceVisualMod(unsigned int pc);
