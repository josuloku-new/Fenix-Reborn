#pragma once
#include <cstdint>

struct Gow2RawMouseSample { double x = 0, y = 0; bool aiming = false; };
void Gow2PushRawMouse(double dx, double dy);
void Gow2SetMouseAim(bool aiming);
void Gow2ResetRawMouse(bool active);
void Gow2SetRawMouseActive(bool active);
// Called on the game thread at the start of the retail viewport input tick.
void Gow2ApplyDirectMouse(uint8_t* base, double dt);
