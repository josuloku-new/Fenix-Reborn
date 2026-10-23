#include <cmath>

// clang's PPC translation emits the C23 round-to-nearest-even helper, which
// the Windows CRT used for this build does not export under that name.
extern "C" float roundevenf(float value) {
    if (!std::isfinite(value) || value == 0.0f) return value;
    const float lower = std::floor(value);
    const float fractional = value - lower;
    float result;
    if (fractional < 0.5f) result = lower;
    else if (fractional > 0.5f) result = lower + 1.0f;
    else result = std::fmod(lower, 2.0f) == 0.0f ? lower : lower + 1.0f;
    return result == 0.0f ? std::copysign(0.0f, value) : result;
}
