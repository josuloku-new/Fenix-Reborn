#pragma once
#include <mutex>
namespace rex::runtime { class FunctionDispatcher; }
std::recursive_mutex& Gow2InputMutex();
void InstallGow2InputGuards(rex::runtime::FunctionDispatcher* dispatcher);
