# Paper Houses

Procedural, printable paper houses for tabletop RPGs (built for D&D 5e).

A single Python script draws the cutting and folding templates for a small house, **sized on the 2.5 cm battle-map grid**, and paints them with procedurally generated textures (brick, stone or wood walls; tile, wood or thatch roofs), complete with a door and windows. Everything is drawn as vector graphics straight into the PDF, so it stays sharp at any print size and needs nothing but `reportlab`.

![A4 sheet with four textured short walls](assets/sheet_brick_tiles_short_wall.png)

## Features

- **Grid-accurate**: wall sizes are the *inner* rectangle, measured in 2.5 cm game squares. The 1 cm tabs are added outside and never count towards the house size.
- **Procedural textures**, deterministic for a given `seed`:
  - Walls: brick, stone, wood (horizontal planks)
  - Roofs: wood shingles, clay tiles, thatch
  - Textures only cover the area inside the solid lines. Tabs get the flat base colour only, which makes cutting and gluing easier.
- **A window to set everything**: run `python main.py` and a window opens, with a tab for each group of settings, a log, presets and a button that copies the equivalent command.
- **Nothing to install**: run it from the Actions tab of the GitHub repository, fill a form and download the PDFs (see below).
- **Door and windows scaled to the story world**: 2.5 cm = 1.5 m. Doors are 1 m to 1.5 m wide depending on the wall length, windows are 0.8 x 0.9 m. Arched plank door with frame, hinges and handle, framed windows with sills, round window in the gable. Windows are spread evenly along each wall, with one floor of windows for every 5 cm of wall height.
- **Door on the short or the long side**, your choice.
- **Whole-house mode**: short wall (with the roof gable), long wall and roof sheet, as three separate PDFs plus one combined PDF.
- **Flexible page packing** for the combined PDF, on A4 or US Letter:
  - By default every page is filled with as many copies of one piece as fit, rotating pieces by 90 degrees when it helps.
  - With `--houses N` you get exactly the pieces for N houses, and with `--mix-pieces` different pieces share the same pages to save paper.
- **One door per house**: the door is assigned house by house, so N houses get N doors. The other wall of the pair gets a window in its place.
- **Corner letters** on the side tabs: the two tabs with the same letter (A to D, prefixed by the house number when you print several houses) are glued together.
- **Calibration ruler**: a 5 cm line on every page of the combined PDF, to check that the print is at the right scale.
- **Readable marks**: the half-height mark and the letters change to black or white when they would be hard to see on the wall colour.
- **Textures are drawn once per PDF** and reused for every copy, which roughly halves the size of a textured file with two houses.
- **Checks**: warnings for sizes that are not multiples of 2.5 cm, clear messages for wrong settings, and a hint when a PDF is locked by a viewer.
- Optional: generate all 9 wall/roof material combinations in one run.

## Gallery

Wall and roof materials (top: brick, stone, wood walls; bottom: tiles, wood, thatch roofs):

![Wall and roof materials](assets/materials_gallery.png)

The long wall carries the door. With the "one door per house" option, the second copy on the sheet gets a window instead:

![Long wall sheet, brick, with and without door](assets/sheet_brick_long_wall.png)

The short wall (with the roof gable and its round window) in stone and in wood:

![Short wall in stone and wood](assets/short_wall_stone_wood.png)

## How to read the sheets

| Line | Meaning |
| --- | --- |
| Solid black | **Fold** |
| Dashed black | **Cut** |
| Dashed mark half-way up each side tab (red, or white/black on dark or red walls) | Marks where to cut for the interlocking joint |
| Letter on a side tab (`A` to `D`, e.g. `2B` with several houses) | The two tabs with the same letter go together |

The corners between two side tabs are left blank: they are cut away and do not appear in the folded house. The dashed outline follows the resulting cross shape.

With textures disabled (`TEXTURES_ENABLED = False`) you get just the line templates:

![Plain line template](assets/blank_template.png)

## Scale

| Value | Meaning |
| --- | --- |
| 2.5 cm | one game square, 1.5 m in the fiction |
| 5 cm wall height (default) | 3 m, one storey |
| 7.5 x 12.5 cm footprint (default) | 3 x 5 squares |

## Run it on GitHub (nothing to install)

You can generate the PDFs without downloading anything, from the repository page:

1. Open the **Actions** tab.
2. Pick **Generate paper houses** in the left sidebar.
3. Press **Run workflow**, fill the form and confirm.
4. After about a minute the run turns green. Open it and download the `paper-houses-N` file at the bottom of the page: a zip with the PDFs. The run page also lists what is on every page and how many walls have the door.

| Field | What it does |
| --- | --- |
| Number of houses | Exactly the pieces for that many houses. Leave it empty to fill every page with copies of one piece |
| Paint textures, wall material, roof material | Look of the house. "Every wall/roof combination" makes all 9 versions (needs textures) |
| Side of the house with the door | Short or long side |
| Paper size | A4 or US Letter |
| Different pieces share the same pages | Saves paper (needs a number of houses) |
| One door per house, corner letters, 5 cm ruler | The matching `Config` options |
| Short side, long side, wall height, roof height | Sizes in cm. Wall sizes should be multiples of 2.5 |
| Texture seed | Another number, another variation of the textures |
| Any other option | Any command-line option of `main.py`, for example `--no-door-and-windows --copy-gap-cm 0.3`. Run `python main.py --help` to see them all |

Notes:

- You need a GitHub account. On the original repository only people with write access can run workflows. Everybody else can **fork** the repository (one click, no download), enable Actions in the fork and run it there.
- The PDFs stay attached to the run for 30 days.
- The workflow is the file `.github/workflows/generate.yml`.

## Requirements

- Python 3.10+
- [ReportLab](https://pypi.org/project/reportlab/)
- tkinter, only for the window. It comes with Python on Windows and macOS. On Linux: `sudo apt install python3-tk`.

```bash
pip install -r requirements.txt
```

## Usage

### The window

```bash
python main.py
```

Started with no options, the program opens a window:

![The settings window](assets/gui.png)

- One tab for each group of settings: **House** (sizes), **Look** (textures, lines), **Door & windows** and **Pages & output**. Move the mouse over a setting to read what it does.
- Settings that do nothing in the current situation are greyed out. For example the materials when textures are off, or *Mix pieces* when the number of houses is empty.
- **Generate PDFs** runs in the background and reports in the log at the bottom. **Open output folder** shows the result.
- **Save preset...** and **Load preset...** keep a set of settings in a small `.json` file, handy for the house types you print often.
- **Copy command** puts the equivalent command-line command in the clipboard, with only the settings that differ from the defaults. It is also a quick way to fill the form of the GitHub workflow.
- Numbers accept the decimal comma: `7,5` works.

The window needs a screen. On a server, or if tkinter is missing, the program says so and suggests the command line.

### The command line

Every setting can also be given as an option, and then no window opens:

```bash
# Two textured brick houses with tiled roofs, pieces mixed on US Letter pages
python main.py --textures-enabled --wall-material brick --roof-material tiles \
               --houses 2 --mix-pieces --paper Letter

# Door on the long side, no calibration ruler
python main.py --door-on long --no-calibration-ruler

# Generate with the defaults of the file, without opening the window
python main.py --no-gui

# Open the window with some settings already filled in
python main.py --gui --houses 3 --wall-material stone

# All the options
python main.py --help
```

The defaults live in the `Config` class at the top of `main.py`. Options and window both start from them.

### What you get

By default the PDFs are written in an `output/` folder next to the script:

| File | Content |
| --- | --- |
| `house_DnD_short_wall.pdf` | Short wall with the roof gable, sized to the piece |
| `house_DnD_long_wall.pdf` | Long wall, sized to the piece |
| `house_DnD_roof.pdf` | Roof sheet, two slopes folded along the ridge |
| `house_DnD_complete.pdf` | The pieces on A4 or Letter pages |

A complete house needs **2 short walls, 2 long walls and 1 roof**. Without `--houses` the combined PDF fills each page with copies of one piece, so you may print more than you need. With `--houses N` it prints exactly what N houses require. The console output lists what is on each page and how many walls have the door.

If a PDF cannot be written (`PermissionError` on Windows), the file is almost always still open in a PDF viewer. The script tells you to close it and run again.

## Configuration

The table lists the defaults currently set in `Config`. In the window they are grouped in the four tabs. Each setting has a matching command-line option: the name with dashes, for example `wall_material` becomes `--wall-material`, and on/off settings accept `--name` and `--no-name`.

| Setting | Default | What it does |
| --- | --- | --- |
| `generate_full_house` | `True` | Whole house (4 PDFs) or a single wall PDF |
| `width_cm` | `7.5` | Short wall inner width (3 squares) |
| `length_cm` | `12.5` | Long wall inner width (5 squares) |
| `height_cm` | `7.5` | Wall inner height (3 squares) |
| `tab_width_cm` | `1.0` | Tab width around the inner rectangle |
| `roof_height_cm` | `5.0` | Height of the roof gable |
| `roof_flap_cm` | `1.0` | Width of the roof flaps on the gable |
| `roof_overhang_cm` | `0.5` | How far each roof slope overhangs the gable side |
| `roof_margin_cm` | `1.0` | Extra margin added on every side of the roof sheet |
| `textures_enabled` | `False` | Textures on or off |
| `wall_material` | `"wood"` | `"brick"`, `"stone"` or `"wood"` |
| `roof_material` | `"thatch"` | `"tiles"`, `"wood"` or `"thatch"` |
| `generate_all_variants` | `False` | Generate all 9 material combinations |
| `seed` | `7` | Different seed, different variation of the same textures |
| `reuse_textures` | `True` | Draw each texture once per PDF and reuse it |
| `door_and_windows` | `True` | Draw door and windows |
| `door_on` | `"short"` | Door on the `"short"` or the `"long"` side |
| `floor_height_cm` | `5.0` | One floor of windows for every this many cm of wall height |
| `window_spacing_cells` | `2.0` | Target distance between windows, in game squares (lower: more windows) |
| `one_door_per_house` | `True` | Only one wall per house gets the door |
| `paper` | `"A4"` | `"A4"` or `"Letter"` |
| `houses` | none | Print exactly the pieces for this many houses |
| `mix_pieces` | `False` | With `houses`: different pieces share the same pages |
| `allow_rotation` | `True` | Allow rotating pieces by 90 degrees |
| `joint_labels` | `True` | Corner letters on the side tabs |
| `calibration_ruler` | `True` | 5 cm ruler on every page of the combined PDF |
| `page_margin_cm`, `copy_gap_cm` | `0.5` | Page margin and gap between pieces |
| `output_dir` | `"output"` | Output folder, relative to the script |
| `base_name` | `"house_DnD"` | Base name of the PDFs |

Colours and dash pattern (`marker_color`, `line_color`, `dash`) can only be changed in the file. Door and window sizes are set in metres of the fiction (`door_width_min_m`, `door_width_max_m`, `door_height_m`, `window_width_m`, `window_height_m`, `window_sill_m`, `round_window_radius_m`) and converted with `cell_cm` and `meters_per_cell`.

To add a material, write a texture function and register it with the `@wall_texture("name", base=(r, g, b))` or `@roof_texture(...)` decorator. It then shows up in the options automatically.

## Printing and assembly

- Print at **100% / "actual size"**, never "fit to page". Otherwise the pieces will not match the 2.5 cm grid. The ruler at the bottom of every page of the combined PDF should measure exactly 5 cm.
- Cut along the dashed lines and fold along the solid ones.
- Thick paper or light card works best.

## Tests

```bash
python -m unittest -v
```

The tests cover geometry, packing, doors and windows, corner letters, colour contrast, validation, the command line, the generated PDFs, and the window (settings form, greying out, generation in the background, presets, copied command). The tests that open the window are skipped when there is no screen or no tkinter. On Linux you can give them a virtual screen with `xvfb-run python -m unittest`.

## Known limitations

- The corner letters tell you which tabs go together. They do not say which tab is slit from the top and which from the bottom for the interlocking joint.
- The packer is a fast heuristic: it is not guaranteed to find the layout with the fewest pages.
- Textures are drawn procedurally and are not meant to look photographic.
- The gallery pictures above were made with an earlier version, which had simpler doors and windows.

## Roadmap

- More materials and window styles
- Optional second storey for larger walls
- Split `main.py` into modules (geometry, textures, openings, layout, command line)
- Preview of the pages inside the window