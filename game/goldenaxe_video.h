#pragma once
#include "game_video.h"
#include <stdint.h>
extern const GameVideo goldenaxe_video;
int goldenaxe_video_hook(uint32_t pc);
void goldenaxe_video_reset(void);
void goldenaxe_video_command(int id, const char *json);
int goldenaxe_video_set_spawn(const char *mode);
const char *goldenaxe_video_spawn_mode(void);
