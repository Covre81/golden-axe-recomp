/* Golden Axe (W REV01) custom scene renderer.
 * Same shared GameVideo contract and presentation rules as the RKA renderer;
 * the formats and instruction sites are Golden Axe's own:
 *
 *   Plane B is the whole map (no parallax); plane A is the screen-space HUD.
 *   $FF4000  decompressed map, 128x32 block bytes
 *   $FFC214  block dictionary, 8 bytes per 16px block (4 name-table words)
 *   $FFC210/$FFC20C  map X/Y scroll; $FFC228  last camera X
 *   $FFD000  64 entities, 128 bytes each, in VDP sprite coordinates
 *   $FFCB00  640-byte SAT cache, DMA'd to VRAM $A800 at VBlank
 *   $00B7F8  AllocateEntitySprites: culls sprite X outside [$40,$200)
 *
 * The native 320px image is kept pixel-exact whenever it is centered; only
 * the margins are rebuilt. No guest state changes except the optional
 * Expanded Spawn Range X shift, which is session configuration.
 */
#include "goldenaxe_video.h"
#include "genesis_runtime.h"
#include "video/genesis_vdp.h"
#include "video/genesis_dac.h"
#include "cmd_server.h"
#include <limits.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { VIDEO_OFF, VIDEO_FIT, VIDEO_RATIO };
enum { MAX_SPRITES = 2048, HISTORY = 4, SAT_BYTES = 640, MAX_SPAWN_SHIFT = 300 };
enum { SITE_SPRITES_DONE = 0x00B8BE, SITE_SPAWN_PLACED = 0x0139EA };
enum { SPR_OPAQUE = 1, SPR_HIGH = 2 };

typedef struct {
    int16_t x, y;       /* VDP sprite coordinates, not wrapped to 9 bits */
    uint16_t attr;
    uint8_t size, fixed;
} Sprite;
typedef struct {
    uint8_t sat[SAT_BYTES];
    Sprite sprites[MAX_SPRITES];
    unsigned count, serial;
} Scene;

static int s_mode, s_requested_width = 320, s_expanded = 1;
static double s_ratio = 16.0 / 9.0;
static Scene s_history[HISTORY], s_presented;
static unsigned s_serial, s_frames;
static uint8_t *s_spr_idx, *s_spr_flags;
static int s_capacity, s_wide, s_mismatch_frames;
static int s_camera, s_camera_y, s_left, s_origin;
static unsigned s_cells_matched, s_cells_total, s_lines_wide, s_lines_native;
/* Dialog boxes are drawn straight into plane B over the map. */
enum { OVERLAY_MIN_CELLS = 12 };
static int s_overlay;

static unsigned r16(const uint8_t *r, unsigned a)
{ return (r[a & 65535u] << 8) | r[(a + 1) & 65535u]; }
static unsigned r32(const uint8_t *r, unsigned a)
{ return (r16(r, a) << 16) | r16(r, a + 2); }
static unsigned read8(unsigned a)
{
    a &= 0xFFFFFFu;
    return a < 0x80000u ? g_rom[a] : a >= 0xFF0000u ? g_ram[a & 65535u] : 0;
}
static unsigned read16(unsigned a) { return (read8(a) << 8) | read8(a + 1); }
static int unwrap(int value, int reference)
{ return reference + ((value - reference + 512) & 1023) - 512; }

static int configure(const char *mode)
{
    if (!mode) return 0;
    int next;
    double ratio = s_ratio;
    if (!strcmp(mode, "off")) next = VIDEO_OFF;
    else if (!strcmp(mode, "fit") || !strcmp(mode, "adaptive")) next = VIDEO_FIT;
    else {
        char *end;
        double w = strtod(mode, &end);
        if (end == mode || *end != ':') return 0;
        const char *den = end + 1;
        double h = strtod(den, &end);
        if (end == den || *end || !(w > 0) || !(h > 0) ||
            !(w / h > 0) || w / h > (double)INT_MAX / 480.0) return 0;
        ratio = w / h; next = VIDEO_RATIO;
    }
    s_mode = next; s_ratio = ratio;
    return 1;
}
static int enabled(void) { return s_mode != VIDEO_OFF; }
static int width(int dw, int dh, int nw, int nh)
{
    if (!enabled()) return 0;
    double result = s_mode == VIDEO_RATIO ? nh * s_ratio :
                    dw > 0 && dh > 0 ? (double)nh * dw / dh : nw;
    if (result > INT_MAX - 1.0) result = INT_MAX - 1.0;
    int pixels = (int)(result + 0.5);
    /* H32 screens are presented at the H40 width, as on a real display. */
    s_requested_width = pixels < 320 ? 320 : pixels;
    return s_requested_width;
}
int goldenaxe_video_set_spawn(const char *mode)
{
    if (mode && !strcmp(mode, "expanded")) s_expanded = 1;
    else if (mode && !strcmp(mode, "original")) s_expanded = 0;
    else return 0;
    return 1;
}
const char *goldenaxe_video_spawn_mode(void) { return s_expanded ? "expanded" : "original"; }
void goldenaxe_video_reset(void)
{
    memset(s_history, 0, sizeof s_history);
    memset(&s_presented, 0, sizeof s_presented);
    s_serial = s_frames = 0;
    s_wide = s_mismatch_frames = 0;
}

/* Rebuild AllocateEntitySprites' list without its X cull: same active and
 * visibility tests, the same Y cull, the same back-to-front baseY buckets.
 * Everything after the cull matches loc_B8C0's piece emission. */
static void capture_piece_list(Scene *s, unsigned e)
{
    unsigned map = r32(g_ram, e + 0x0A) & 0xFFFFFFu;
    if (!map) return;
    int ex = (int16_t)r16(g_ram, e + 0x1C), ey = (int16_t)r16(g_ram, e + 0x18);
    /* Bit 0 of $2(a0) opts out of map scrolling; the two players always
     * belong to the world even though they scroll themselves. */
    int fixed = e >= 0xD100u && (g_ram[e + 2] & 1);
    unsigned count = read8(map) + 1, p = map + 3;
    for (unsigned i = 0; i < count && s->count < MAX_SPRITES; ++i, p += 5) {
        unsigned low = read8(p + 3) + g_ram[e + 9];
        unsigned high = (read8(p + 2) + g_ram[e + 8] + (low >> 8)) | g_ram[e + 0x17];
        Sprite *out = &s->sprites[s->count++];
        out->y = (int16_t)(ey + (int8_t)read8(p));
        out->x = (int16_t)(ex + (int8_t)read8(p + 4));
        out->size = (uint8_t)read8(p + 1);
        out->attr = (uint16_t)((high & 255u) << 8 | (low & 255u));
        out->fixed = (uint8_t)fixed;
    }
}
static void capture_scene(void)
{
    Scene *s = &s_history[++s_serial % HISTORY];
    s->serial = s_serial; s->count = 0;
    memcpy(s->sat, g_ram + 0xCB00, SAT_BYTES);
    for (int bucket = 255; bucket >= 0; --bucket)
        for (unsigned i = 0; i < 64; ++i) {
            unsigned e = 0xD000u + i * 0x80u;
            if (!g_ram[e] || (g_ram[e + 2] & 0x80) ||
                (int)((r16(g_ram, e + 0x20) & 0x1FEu) >> 1) != bucket) continue;
            if ((uint16_t)(r16(g_ram, e + 0x18) - 0x70u) > 0x130u) continue;
            capture_piece_list(s, e);
        }
}
/* Enemies are placed just outside the native edges (sprite X ~$1D0-$200 or
 * ~$60-$70) and walk in. Move only those beyond the wider edge so they enter
 * from it. Width comes from session configuration, never from the display. */
static void shift_spawn(void)
{
    if (!enabled() || !s_expanded) return;
    int margin = (s_requested_width - 320) / 2;
    if (margin > MAX_SPAWN_SHIFT) margin = MAX_SPAWN_SHIFT;
    if (margin <= 0) return;
    unsigned a = (g_cpu.A[0] & 65535u) + 0x1C;
    int x = (int)r16(g_ram, a) - 128;
    if (x >= 0 && x < 320) return;
    unsigned moved = (unsigned)(x + 128 + (x < 0 ? -margin : margin)) & 65535u;
    g_ram[a] = (uint8_t)(moved >> 8); g_ram[a + 1] = (uint8_t)moved;
}
int goldenaxe_video_hook(uint32_t pc)
{
    if (pc == SITE_SPRITES_DONE && enabled()) capture_scene();
    else if (pc == SITE_SPAWN_PLACED) shift_spawn();
    return 0;
}

static int tiles(unsigned bits) { return bits == 1 ? 64 : bits == 3 ? 128 : 32; }
static uint16_t plane(const GVDP *v, unsigned base, int x, int y)
{
    int wt = tiles(v->reg[16] & 3), ht = tiles((v->reg[16] >> 4) & 3);
    unsigned cell = (((unsigned)y >> 3) & (ht - 1)) * wt + (((unsigned)x >> 3) & (wt - 1));
    return (uint16_t)r16(v->vram, base + cell * 2u);
}
static uint8_t pixel(const GVDP *v, unsigned attr, int x, int y)
{
    unsigned px = (unsigned)x & 7u, py = (unsigned)y & 7u;
    if (attr & 0x0800) px ^= 7;
    if (attr & 0x1000) py ^= 7;
    unsigned byte = v->vram[((attr & 2047u) * 32u + py * 4u + px / 2u) & 65535u];
    unsigned nibble = px & 1 ? byte & 15 : byte >> 4;
    return nibble ? (uint8_t)(((attr >> 9) & 48u) | nibble) : 0;
}
static int map_width(void) { return (int)r16(g_ram, 0xC228) + 320; }
/* UpdateMap's lookup ($100E/$1024) for one map pixel. */
static uint16_t terrain(int x, int y)
{
    unsigned block = g_ram[0x4000u + (((unsigned)y >> 4) & 31u) * 128u + (((unsigned)x >> 4) & 127u)];
    return (uint16_t)read16(r32(g_ram, 0xC214) + block * 8u +
                            (((unsigned)y >> 3) & 1u) * 4u + (((unsigned)x >> 3) & 1u) * 2u);
}
/* Past either map end, continue the outermost 16px block column. */
static int map_x(int wx, int map_w)
{
    if (wx < 0) return wx & 15;
    if (wx >= map_w) return map_w - 16 + (wx & 15);
    return wx;
}
static int view_left(int camera, int w, int map_w)
{
    if (map_w < w) return (map_w - w) / 2;
    int left = camera - (w - 320) / 2;
    if (left < 0) left = 0;
    if (left > map_w - w) left = map_w - w;
    return left;
}
/* The wide view only applies while the live plane B really shows the map:
 * title, menu and cutscene screens fail this and stay centered. A couple of
 * mismatching frames are tolerated so one stale column cannot flash bars. */
static void qualify_scene(const GVDP *v, int nw, int hb, int vb)
{
    unsigned base = (v->reg[4] & 7u) << 13, table = r32(g_ram, 0xC214) & 0xFFFFFFu;
    s_cells_matched = s_cells_total = 0;
    int ok = nw == 320 && (v->reg[1] & 64) && !(v->reg[12] & 14) && !(v->reg[11] & 7) &&
             map_width() >= 320 && map_width() <= 2048 &&
             ((table && table < 0x80000u) || table >= 0xFF0000u);
    if (ok)
        for (int cy = 0; cy < 28; ++cy)
            for (int cx = 0; cx < 40; ++cx) {
                uint16_t live = plane(v, base, cx * 8 - hb, cy * 8 + vb);
                uint16_t map = terrain(s_camera + cx * 8, s_camera_y + cy * 8);
                if (!live && !map) continue;
                ++s_cells_total;
                s_cells_matched += live == map;
            }
    ok = ok && s_cells_total >= 200 && s_cells_matched * 5 >= s_cells_total * 4;
    s_overlay = ok && s_cells_total - s_cells_matched >= OVERLAY_MIN_CELLS;
    if (ok) { s_wide = 1; s_mismatch_frames = 0; }
    else if (++s_mismatch_frames >= 3) s_wide = 0;
}
/* Present the newest captured actor list whose SAT is the one in VRAM, so
 * margin actors never run a frame ahead of the native picture. */
static void select_scene(const GVDP *v)
{
    unsigned sat = (v->reg[5] & 0x7Eu) << 9;
    if (sat + SAT_BYTES > 65536u) return;
    const Scene *best = NULL;
    for (int i = 0; i < HISTORY; ++i) {
        const Scene *s = &s_history[i];
        if (s->serial && (!best || s->serial > best->serial) &&
            !memcmp(s->sat, v->vram + sat, SAT_BYTES)) best = s;
    }
    if (best && best->serial != s_presented.serial) s_presented = *best;
}
static void draw_sprite(const GVDP *v, const Sprite *s, int line, int w, int origin, int center)
{
    int y = s->y - 128, h = (s->size & 3) + 1, cells = ((s->size >> 2) & 3) + 1;
    if (line < y || line >= y + h * 8) return;
    int left = (s->fixed ? center : origin) + s->x - 128;
    int row = line - y, vflip = s->attr & 0x1000, hflip = s->attr & 0x0800;
    if (vflip) row = h * 8 - 1 - row;
    for (int i = 0; i < cells * 8; ++i) {
        int px = left + i;
        if (px < 0 || px >= w || (s_spr_flags[px] & SPR_OPAQUE)) continue;
        int col = hflip ? cells * 8 - 1 - i : i;
        unsigned tile = (s->attr & 2047u) + (unsigned)(col >> 3) * (unsigned)h + (unsigned)(row >> 3);
        unsigned byte = v->vram[(tile * 32u + (row & 7u) * 4u + (col & 7u) / 2u) & 65535u];
        unsigned nibble = col & 1 ? byte & 15 : byte >> 4;
        if (!nibble) continue;
        s_spr_idx[px] = (uint8_t)(((s->attr >> 9) & 48u) | nibble);
        s_spr_flags[px] = (uint8_t)(SPR_OPAQUE | (s->attr & 0x8000 ? SPR_HIGH : 0));
    }
}
static void present_centered(const uint32_t *native, int nw, uint32_t *out, int w)
{
    for (int x = 0; x < w; ++x) out[x] = 0xFF000000u;
    if (nw < 320) {
        for (int x = 0; x < 320; ++x) out[(w - 320) / 2 + x] = native[x * nw / 320];
    } else memcpy(out + (w - nw) / 2, native, (size_t)nw * sizeof *out);
}
static void scanline(const GVDP *v, int line, const uint32_t *native, int nw,
                     uint32_t *out, int w)
{
    unsigned hs = (v->reg[13] & 63u) << 10;
    int ha = (int16_t)r16(v->vram, hs), hb = (int16_t)r16(v->vram, hs + 2);
    int va = v->vsram[0] & 1023, vb = v->vsram[1] & 1023;
    if (!line) {
        ++s_frames;
        s_lines_wide = s_lines_native = 0;
        if (w > s_capacity) {
            uint8_t *a = malloc((size_t)w), *b = malloc((size_t)w);
            if (a && b) { free(s_spr_idx); free(s_spr_flags); s_spr_idx = a; s_spr_flags = b; s_capacity = w; }
            else { free(a); free(b); }
        }
        s_camera = unwrap(-hb, (int)r16(g_ram, 0xC210));
        s_camera_y = unwrap(vb, (int)r16(g_ram, 0xC20C));
        qualify_scene(v, nw, hb, vb);
        select_scene(v);
        /* A blocking dialog never reaches the capture hook, so after a state
         * load nothing refills the list. Its RAM SAT can also be a frame ahead
         * of VRAM and never match, so a rebuilt list is presented directly. */
        if (s_wide && !s_presented.count) {
            capture_scene();
            s_presented = s_history[s_serial % HISTORY];
        }
        s_left = view_left(s_camera, w, map_width());
        s_origin = s_camera - s_left;
    }
    if (!s_wide || nw != 320 || w > s_capacity) {
        ++s_lines_native;
        present_centered(native, nw, out, w);
        return;
    }
    ++s_lines_wide;
    uint32_t palette[64];
    for (int i = 0; i < 64; ++i) palette[i] = genesis_dac_cram_to_argb(v->cram[i], GENESIS_DAC_NORMAL);
    unsigned backdrop = v->reg[7] & 63, ba = (v->reg[2] & 56u) << 10, bb = (v->reg[4] & 7u) << 13;
    int origin = s_origin, center = (w - nw) / 2, map_w = map_width(), wy = s_camera_y + line;
    int copy = origin == center;

    memset(s_spr_flags, 0, (size_t)w);
    for (unsigned i = 0; i < s_presented.count; ++i)
        draw_sprite(v, &s_presented.sprites[i], line, w, origin, center);

    for (int x = 0; x < w; ++x) {
        int nx = x - origin;
        if (copy && nx == 0) { x += nw - 1; continue; }
        int sx = x - center;
        uint16_t b = 0;
        uint8_t bp = 0;
        int overlay = 0;
        if (s_overlay && sx >= 0 && sx < nw) {
            /* A plane B dialog is screen space like its plane A text: keep
             * it centered and let the world show through where it was. */
            b = plane(v, bb, sx - hb, line + vb);
            overlay = b != terrain(s_camera + sx, wy);
            if (overlay) bp = pixel(v, b, sx - hb, line + vb);
        }
        if (overlay) {
        } else if (nx >= 0 && nx < nw && !s_overlay) {
            b = plane(v, bb, nx - hb, line + vb);
            bp = pixel(v, b, nx - hb, line + vb);
        } else {
            int tx = map_x(s_camera + nx, map_w);
            b = terrain(tx, wy);
            bp = pixel(v, b, tx, wy);
        }
        /* Plane A is screen space. Inside the native width it is exact; a
         * full-width fill reaching a native edge continues past that edge. */
        int ax = (sx < 0 ? sx & 7 : sx >= nw ? nw - 8 + (sx & 7) : sx) - ha;
        uint16_t a = plane(v, ba, ax, line + va);
        uint8_t ap = pixel(v, a, ax, line + va);
        int a_hi = ap && (a & 0x8000), b_hi = bp && (b & 0x8000);
        unsigned f = s_spr_flags[x], s_op = f & SPR_OPAQUE, s_hi = f & SPR_HIGH;
        unsigned idx = s_op && s_hi ? s_spr_idx[x] : a_hi ? ap : b_hi ? bp :
                       s_op ? s_spr_idx[x] : ap ? ap : bp ? bp : backdrop;
        out[x] = palette[idx];
    }
    if (copy) memcpy(out + origin, native, (size_t)nw * sizeof *out);
}
void goldenaxe_video_command(int id, const char *json)
{
    (void)json;
    char out[400];
    snprintf(out, sizeof out, "{\"id\":%d,\"enabled\":%d,\"wide\":%d,\"width\":%d,\"camera\":%d,"
        "\"camera_y\":%d,\"view_left\":%d,\"origin\":%d,\"map_cells_matched\":%u,\"map_cells\":%u,"
        "\"wide_lines\":%u,\"native_lines\":%u,\"frames\":%u,\"sprites\":%u,\"spawn_mode\":\"%s\"}",
        id, enabled(), s_wide, s_requested_width, s_camera, s_camera_y, s_left, s_origin,
        s_cells_matched, s_cells_total, s_lines_wide, s_lines_native, s_frames,
        s_presented.count, goldenaxe_video_spawn_mode());
    cmd_send_response(out);
}
const GameVideo goldenaxe_video = { configure, enabled, width, scanline };
