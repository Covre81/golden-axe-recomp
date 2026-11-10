# Golden Axe Recomp

An unofficial native PC port of **Golden Axe**
for the Sega Genesis / Mega Drive, built with the
[Genesis recompilation framework](https://github.com/mstan/segagenesisrecomp).
Play with adaptive widescreen, remappable controls, rewind, and a visual
save-state browser.

Version 1.0 is the first stable release.

You must supply your own **Golden Axe (W)(REV01)** ROM. The source
and release packages do not include the game ROM.

## Controls, saves, and rewind

Default game controls can be remapped in the launcher.

| Tool | Keyboard | Controller |
| --- | --- | --- |
| Save-state browser | F7 | Back/View + RB |
| Rewind browser | F8 | Back/View + right-stick click |

In either browser, use arrows or the D-pad to select, **Enter / A** to load
or restore, and **Esc / B** to cancel. In the save-state browser, **S / X**
saves into the selected slot. Browser button names refer to the Xbox layout.

Rewind needs a few seconds of play to build its history. Its depth and
snapshot interval are configurable in the launcher. Existing
`native_save_N.bin` files work in the visual browser.

<details>
<summary>Direct save-slot shortcuts</summary>

**Shift+F1–F9** saves to a slot. **F1–F6** and **F9** load directly;
**Ctrl+F7** and **Ctrl+F8** load slots 7 and 8.

</details>

## Building from source

Clone with submodules, then place the supported ROM at `game/goldenaxe.bin`:

**Windows:** install Visual Studio 2022 with C++ build tools, CMake, and Python 3.

```powershell
cmake -S . -B build -G "Visual Studio 17 2022" -A x64
cmake --build build --config Release --target GoldenAxeRecomp --parallel
./build/Release/GoldenAxeRecomp.exe
```

**Linux:** install a C/C++ compiler, CMake, Python 3, `pkg-config`, SDL2
development headers, and OpenGL development libraries.

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build --target GoldenAxeRecomp --parallel
./build/GoldenAxeRecomp
```

CMake builds the recompiler and generates the game code from your ROM.
See [RELEASING.md](RELEASING.md) for production builds and packaging.

## How it works

The project recompiles the game's 68000 code to C and uses the shared
[segagenesisrecomp](https://github.com/mstan/segagenesisrecomp) runtime for
graphics, audio, and execution. Code not yet covered by static recompilation
runs through the runtime's 68000 interpreter fallback; coverage reports help
bring more of those routines into the generated code.

Golden Axe's custom renderer reconstructs the wider scenery from the game's level
layouts and live graphics data. The launcher comes
from [recomp-ui](https://github.com/mstan/recomp-ui), and the shared
[rbengine](https://github.com/RetroPortingToolKit/rbengine) snapshot system supports rewind.

## License and acknowledgments

The port and framework use the
[PolyForm Noncommercial 1.0.0 license](LICENSE.md). Third-party components
retain their own licenses; release packages include `THIRD-PARTY-LICENSES.md`
and a `licenses/` directory.

This project is unofficial and is not
affiliated with Sega.
