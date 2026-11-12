#pragma once
#include <stddef.h>
struct RecompLauncherCModProvider;
void goldenaxe_load_settings(const char *settings_path);
void goldenaxe_config_image(char *out, size_t cap);
int goldenaxe_config_adopt(const char *line);
int goldenaxe_boss_ai_watchdog_enabled(void);
const struct RecompLauncherCModProvider *goldenaxe_mods(const struct RecompLauncherCModProvider *base);
