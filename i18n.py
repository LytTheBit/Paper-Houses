"""Everything the user reads, in English and in Italian.

Code, identifiers and comments stay in English. To add a language, add its
code to LANGUAGES and a dictionary to STRINGS with the same keys as "en"
(the tests check that nothing is missing).

Texts with {placeholders} are filled in by tr().
"""

from __future__ import annotations

import os
import sys

LANGUAGES = {"en": "English", "it": "Italiano"}
DEFAULT_LANGUAGE = "en"


def detect_language():
    """'it' if the system is set to Italian, otherwise 'en'."""
    if sys.platform == "win32":
        try:
            import ctypes
            lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
            return "it" if (lang_id & 0xFF) == 0x10 else "en"
        except Exception:
            pass

    for variable in ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG"):
        value = os.environ.get(variable, "")
        if value:
            return "it" if value.lower().startswith("it") else "en"
    return DEFAULT_LANGUAGE


def tr(language, key, **values):
    """The text for `key` in `language` (English if it is missing there)."""
    table = STRINGS.get(language, STRINGS[DEFAULT_LANGUAGE])
    text = table.get(key)
    if text is None:
        text = STRINGS[DEFAULT_LANGUAGE][key]
    return text.format(**values) if values else text


def has_text(language, key):
    return key in STRINGS.get(language, {})


STRINGS = {}

# ============================================================
# ENGLISH
# ============================================================

STRINGS["en"] = {
    # ---- Generator messages ----
    "msg.pdf_one": "PDF created: {path} ({w:.2f} × {h:.2f} cm)",
    "msg.pdf_pages": "PDF created: {path} ({count} pages)",
    "msg.pdf_complete": "PDF created: {path} ({count} {paper} pages)",
    "msg.page": "    page {number}: {description}",
    "msg.page_desc": "{paper} {orientation}: {parts}{doors}{rotated}",
    "msg.part": "{count} × {name}",
    "msg.with_door": " ({count} with door)",
    "msg.rotated": ", {count} rotated",
    "orientation.landscape": "landscape",
    "orientation.portrait": "portrait",
    "piece.short": "short wall",
    "piece.long": "long wall",
    "piece.roof": "roof",
    "piece.wall": "wall",
    "side.short": "short",
    "side.long": "long",
    "msg.warn_mix": "WARNING: mix_pieces has no effect without houses "
                    "(set the number of houses to mix the pieces).",
    "msg.warn_variants": "WARNING: generate_all_variants has no effect "
                         "without textures.",
    "msg.warn_dimension": "WARNING: {name} = {value} cm is not a multiple "
                          "of {cell} cm ({squares:.2f} squares).",
    "msg.warn_oversize": "WARNING: {piece} ({w:.2f} × {h:.2f} cm) does not "
                         "fit on {paper}, placing it alone on a larger page.",
    "msg.variant": "--- walls: {wall}, roof: {roof} ---",
    "msg.roof_title": "Roof:",
    "msg.roof_side": "  triangle side = {value:.2f} cm",
    "msg.roof_depth": "  base depth of each slope = {value:.2f} cm",
    "msg.roof_base": "  base size = {length:.2f} × {depth:.2f} cm",
    "msg.roof_sheet": "  final sheet (+{margin} cm per side) = "
                      "{w:.2f} × {h:.2f} cm",
    "msg.door_side": "Door on the {side} side",
    "msg.inner": "Inner rectangle (game squares):",
    "msg.outer": "Outer rectangle (with tabs):",
    "pdf.ruler": "5 cm: print at 100 percent (actual size)",
    "msg.invalid": "Invalid settings:\n{error}",
    "msg.no_tkinter": "The window needs tkinter, which is missing ({error}).\n"
                      "Use the command-line options instead, for example: "
                      "python main.py --help",
    "msg.no_display": "Cannot open a window here ({error}).\n"
                      "Use the command-line options instead, for example: "
                      "python main.py --no-gui",

    # ---- Errors ----
    "err.wall_material": "wall_material must be one of {options} "
                         "(got {value!r})",
    "err.roof_material": "roof_material must be one of {options} "
                         "(got {value!r})",
    "err.door_on": "door_on must be 'short' or 'long' (got {value!r})",
    "err.paper": "paper must be one of {options} (got {value!r})",
    "err.language": "language must be one of {options} (got {value!r})",
    "err.houses": "houses must be at least 1 (got {value})",
    "err.positive": "{name} must be positive (got {value})",
    "err.locked": "Cannot write {path}. If it is open in a PDF viewer, "
                  "close it and run the script again.",
    "err.number_needed": "a number is needed",
    "err.not_number": "'{text}' is not a number",
    "err.not_whole": "'{text}' is not a whole number",

    # ---- Window: general ----
    "ui.title": "Paper Houses",
    "ui.hint": "Move the mouse over a setting to see what it does.",
    "ui.default": "default: {value}",
    "ui.none": "none",
    "ui.language": "Language",
    "ui.generate": "Generate PDFs",
    "ui.generating": "Generating...",
    "ui.open_folder": "Open folder",
    "ui.copy_command": "Copy command",
    "ui.presets": "Presets",
    "ui.load_preset": "Load preset...",
    "ui.save_preset": "Save preset...",
    "ui.reset": "Reset",
    "ui.browse": "Browse...",
    "ui.done": "Done: {count} PDF files in {folder}",
    "ui.copied": "Copied to the clipboard:\n{command}",
    "ui.preset_saved": "Preset saved: {path}",
    "ui.preset_loaded": "Preset loaded: {path}",
    "ui.reset_done": "Settings back to the defaults.",
    "ui.check_settings": "Check the settings",
    "ui.invalid_settings": "Invalid settings",
    "ui.could_not_generate": "Could not generate the PDFs",
    "ui.cannot_load_preset": "Cannot load the preset",
    "ui.dialog_save": "Save the settings",
    "ui.dialog_load": "Load settings",
    "ui.dialog_folder": "Folder for the PDFs",
    "ui.preset_files": "Preset",

    # ---- Window: pages ----
    "page.house": "House",
    "page.look": "Look",
    "page.doors": "Doors & windows",
    "page.pages": "Pages & files",
    "page.advanced": "Advanced",
    "title.house": "How big is the house?",
    "title.look": "How does it look?",
    "title.doors": "Door and windows",
    "title.pages": "Pages and files",
    "title.advanced": "Advanced settings",
    "sub.house": "Sizes are counted in game squares: one square is 2.5 cm "
                 "on paper.",
    "sub.look": "Pick the materials, or leave the textures off to print "
                "only the cutting lines.",
    "sub.doors": "Where the door goes, and how the windows are spread.",
    "sub.pages": "What is written, on which paper, and where.",
    "sub.advanced": "Every value, set directly in cm and metres. What you "
                    "change here also changes in the other pages.",

    # ---- Window: house page ----
    "card.size": "Size",
    "card.picker": "Pick it on the grid",
    "card.amount": "How many houses",
    "ui.sq.width_cm": "Gable side (squares)",
    "ui.sq.length_cm": "Long side (squares)",
    "ui.sq.height_cm": "Wall height (squares)",
    "ui.sq.roof_height_cm": "Roof height (squares)",
    "ui.sq.floor_height_cm": "One floor every (squares)",
    "ui.cm": "= {value} cm",
    "ui.picker_long": "Long side",
    "ui.picker_gable": "Gable side",
    "ui.picker_caption": "{rows} × {cols} squares ({w} × {l} cm)",
    "ui.picker_none": "Move over the grid and click",
    "ui.specific_houses": "Print a specific number of houses",
    "ui.houses_hint": "Leave it off to fill every page with copies of one "
                      "piece.",

    # ---- Window: look page ----
    "card.textures": "Textures",
    "card.variation": "Variation",
    "ui.walls": "Walls",
    "ui.roof": "Roof",
    "ui.new_variation": "New variation",
    "ui.variation_number": "Variation number",
    "material.brick": "Brick",
    "material.stone": "Stone",
    "material.wood": "Wood",
    "material.tiles": "Tiles",
    "material.thatch": "Thatch",

    # ---- Window: doors page ----
    "card.door": "Door",
    "card.windows": "Windows",
    "ui.door_side": "Door on the",
    "ui.side_short": "Short side (with the gable)",
    "ui.side_long": "Long side",
    "ui.window_spacing": "Distance between windows (squares)",
    "ui.more_in_advanced": "The sizes of door and windows are in the "
                           "Advanced page.",

    # ---- Window: pages page ----
    "card.pdf": "PDF",
    "card.layout": "Layout on the pages",
    "card.files": "Files",
    "ui.complete_hint": "Skips the PDFs of the single pieces.",
    "ui.folder": "Folder",
    "ui.file_name": "File name",

    # ---- Groups of the Advanced page ----
    "group.House": "House",
    "group.Look": "Look",
    "group.Door & windows": "Door & windows",
    "group.Pages & output": "Pages & output",

    # ---- Settings: label and help ----
    "label.generate_full_house": "Whole house",
    "help.generate_full_house": "generate the whole house instead of a "
                                "single wall",
    "label.width_cm": "Width, gable side (cm)",
    "help.width_cm": "short side of the house (the one with the gable)",
    "label.length_cm": "Length, long side (cm)",
    "help.length_cm": "long side of the house",
    "label.height_cm": "Wall height (cm)",
    "help.height_cm": "wall height (same for both sides)",
    "label.tab_width_cm": "Tab width (cm)",
    "help.tab_width_cm": "width of the tabs around the inner rectangle",
    "label.roof_height_cm": "Roof height (cm)",
    "help.roof_height_cm": "height of the roof gable (triangle)",
    "label.roof_flap_cm": "Roof flap (cm)",
    "help.roof_flap_cm": "width of the flaps on the roof gable",
    "label.roof_overhang_cm": "Roof overhang (cm)",
    "help.roof_overhang_cm": "how far the roof slope extends beyond the "
                             "gable side",
    "label.roof_margin_cm": "Roof sheet margin (cm)",
    "help.roof_margin_cm": "extra margin added on every side of the roof "
                           "sheet",
    "label.use_roof": "Roof gable (single wall)",
    "help.use_roof": "single-wall mode only: draw the roof gable",
    "label.textures_enabled": "Paint textures",
    "help.textures_enabled": "paint textures (otherwise only lines)",
    "label.wall_material": "Wall material",
    "help.wall_material": "wall material",
    "label.roof_material": "Roof material",
    "help.roof_material": "roof material",
    "label.generate_all_variants": "All material combinations",
    "help.generate_all_variants": "generate every wall/roof material "
                                  "combination",
    "label.seed": "Texture variation",
    "help.seed": "different number, different variation of the textures",
    "label.texture_on_roof_overhang": "Texture on the roof overhang",
    "help.texture_on_roof_overhang": "texture also covers the extra margin "
                                     "of the roof sheet",
    "label.reuse_textures": "Reuse textures (smaller files)",
    "help.reuse_textures": "draw each texture once per PDF and reuse it for "
                           "every copy (smaller, faster files)",
    "label.line_width": "Line width",
    "help.line_width": "line width in points",
    "label.draw_roof_base": "Base line of the gable",
    "help.draw_roof_base": "also draw the base of the gable triangle "
                           "(fold line)",
    "label.door_and_windows": "Door and windows",
    "help.door_and_windows": "draw door and windows",
    "label.door_on": "Door on",
    "help.door_on": "side of the house with the door",
    "label.one_door_per_house": "One door per house",
    "help.one_door_per_house": "only one wall per house gets the door "
                               "(the other gets a window in its place)",
    "label.door_arched": "Arched door",
    "help.door_arched": "door with a rounded top",
    "label.door_width_min_m": "Door width, small wall (m)",
    "help.door_width_min_m": "door width on a 3-square wall",
    "label.door_width_max_m": "Door width, large wall (m)",
    "help.door_width_max_m": "door width on a 5-square wall or more",
    "label.door_height_m": "Door height (m)",
    "help.door_height_m": "door height",
    "label.window_width_m": "Window width (m)",
    "help.window_width_m": "window width",
    "label.window_height_m": "Window height (m)",
    "help.window_height_m": "window height",
    "label.window_sill_m": "Window sill height (m)",
    "help.window_sill_m": "height of the window sill above the ground",
    "label.round_window_radius_m": "Round window radius (m)",
    "help.round_window_radius_m": "radius of the small window in the gable",
    "label.floor_height_cm": "Floor height (cm)",
    "help.floor_height_cm": "one floor of windows for every this many cm "
                            "of wall height",
    "label.window_spacing_cells": "Window spacing (squares)",
    "help.window_spacing_cells": "target distance between windows, in game "
                                 "squares (lower: more windows)",
    "label.cell_cm": "Square size (cm)",
    "help.cell_cm": "side of a game square",
    "label.meters_per_cell": "Square size in the story (m)",
    "help.meters_per_cell": "size of a game square in the fiction",
    "label.complete_only": "Only the complete PDF",
    "help.complete_only": "write only the complete PDF, not the PDFs of "
                          "the single pieces",
    "label.paper": "Paper size",
    "help.paper": "paper size of the complete PDF",
    "label.houses": "Number of houses",
    "help.houses": "number of houses to print. Without it, every page is "
                   "filled with as many copies of one piece as fit",
    "label.mix_pieces": "Mix pieces on the same pages",
    "help.mix_pieces": "needs a number of houses: pack different pieces on "
                       "the same page to save paper",
    "label.allow_rotation": "Allow rotating pieces",
    "help.allow_rotation": "allow rotating pieces by 90 degrees",
    "label.joint_labels": "Corner letters on the tabs",
    "help.joint_labels": "write corner letters on the side tabs: tabs with "
                         "the same letter go together",
    "label.calibration_ruler": "5 cm ruler on every page",
    "help.calibration_ruler": "draw a 5 cm ruler on every page of the "
                              "complete PDF, to check the print scale",
    "label.page_margin_cm": "Page margin (cm)",
    "help.page_margin_cm": "white margin along the edges of the page",
    "label.copy_gap_cm": "Gap between pieces (cm)",
    "help.copy_gap_cm": "gap between two pieces",
    "label.output_dir": "Output folder",
    "help.output_dir": "folder for the PDFs (relative to this script)",
    "label.base_name": "File name",
    "help.base_name": "base name of the PDFs",
    "label.language": "Language",
    "help.language": "language of the messages",
}

# ============================================================
# ITALIAN
# ============================================================

STRINGS["it"] = {
    # ---- Generator messages ----
    "msg.pdf_one": "PDF creato: {path} ({w:.2f} × {h:.2f} cm)",
    "msg.pdf_pages": "PDF creato: {path} ({count} pagine)",
    "msg.pdf_complete": "PDF creato: {path} ({count} pagine {paper})",
    "msg.page": "    pagina {number}: {description}",
    "msg.page_desc": "{paper} {orientation}: {parts}{doors}{rotated}",
    "msg.part": "{count} × {name}",
    "msg.with_door": " ({count} con la porta)",
    "msg.rotated": ", ruotati: {count}",
    "orientation.landscape": "orizzontale",
    "orientation.portrait": "verticale",
    "piece.short": "lato corto",
    "piece.long": "lato lungo",
    "piece.roof": "tetto",
    "piece.wall": "parete",
    "side.short": "corto",
    "side.long": "lungo",
    "msg.warn_mix": "ATTENZIONE: «mescola i pezzi» non ha effetto senza il "
                    "numero di case (indica quante case stampare).",
    "msg.warn_variants": "ATTENZIONE: «tutte le combinazioni» non ha "
                         "effetto senza le texture.",
    "msg.warn_dimension": "ATTENZIONE: {name} = {value} cm non è un "
                          "multiplo di {cell} cm ({squares:.2f} caselle).",
    "msg.warn_oversize": "ATTENZIONE: {piece} ({w:.2f} × {h:.2f} cm) non "
                         "entra in {paper}, lo metto da solo su una pagina "
                         "più grande.",
    "msg.variant": "--- pareti: {wall}, tetto: {roof} ---",
    "msg.roof_title": "Tetto:",
    "msg.roof_side": "  lato del triangolo = {value:.2f} cm",
    "msg.roof_depth": "  profondità di base di ogni falda = {value:.2f} cm",
    "msg.roof_base": "  dimensione di base = {length:.2f} × {depth:.2f} cm",
    "msg.roof_sheet": "  foglio finale (+{margin} cm per lato) = "
                      "{w:.2f} × {h:.2f} cm",
    "msg.door_side": "Porta sul lato {side}",
    "msg.inner": "Rettangolo interno (caselle di gioco):",
    "msg.outer": "Rettangolo esterno (con le linguette):",
    "pdf.ruler": "5 cm: stampa al 100 percento (dimensioni effettive)",
    "msg.invalid": "Impostazioni non valide:\n{error}",
    "msg.no_tkinter": "La finestra richiede tkinter, che non è installato "
                      "({error}).\nUsa invece le opzioni da riga di "
                      "comando, per esempio: python main.py --help",
    "msg.no_display": "Qui non posso aprire una finestra ({error}).\n"
                      "Usa invece le opzioni da riga di comando, per "
                      "esempio: python main.py --no-gui",

    # ---- Errors ----
    "err.wall_material": "wall_material deve essere uno tra {options} "
                         "(ricevuto {value!r})",
    "err.roof_material": "roof_material deve essere uno tra {options} "
                         "(ricevuto {value!r})",
    "err.door_on": "door_on deve essere 'short' o 'long' "
                   "(ricevuto {value!r})",
    "err.paper": "paper deve essere uno tra {options} (ricevuto {value!r})",
    "err.language": "language deve essere uno tra {options} "
                    "(ricevuto {value!r})",
    "err.houses": "houses deve essere almeno 1 (ricevuto {value})",
    "err.positive": "{name} deve essere positivo (ricevuto {value})",
    "err.locked": "Non riesco a scrivere {path}. Se è aperto in un "
                  "visualizzatore di PDF, chiudilo e riavvia il programma.",
    "err.number_needed": "serve un numero",
    "err.not_number": "'{text}' non è un numero",
    "err.not_whole": "'{text}' non è un numero intero",

    # ---- Window: general ----
    "ui.title": "Paper Houses",
    "ui.hint": "Passa il mouse su un'impostazione per vedere cosa fa.",
    "ui.default": "predefinito: {value}",
    "ui.none": "nessuno",
    "ui.language": "Lingua",
    "ui.generate": "Genera i PDF",
    "ui.generating": "Generazione in corso...",
    "ui.open_folder": "Apri la cartella",
    "ui.copy_command": "Copia il comando",
    "ui.presets": "Preset",
    "ui.load_preset": "Carica preset...",
    "ui.save_preset": "Salva preset...",
    "ui.reset": "Ripristina",
    "ui.browse": "Sfoglia...",
    "ui.done": "Fatto: {count} file PDF in {folder}",
    "ui.copied": "Copiato negli appunti:\n{command}",
    "ui.preset_saved": "Preset salvato: {path}",
    "ui.preset_loaded": "Preset caricato: {path}",
    "ui.reset_done": "Impostazioni riportate ai valori di partenza.",
    "ui.check_settings": "Controlla le impostazioni",
    "ui.invalid_settings": "Impostazioni non valide",
    "ui.could_not_generate": "Non sono riuscito a generare i PDF",
    "ui.cannot_load_preset": "Non riesco a caricare il preset",
    "ui.dialog_save": "Salva le impostazioni",
    "ui.dialog_load": "Carica le impostazioni",
    "ui.dialog_folder": "Cartella dei PDF",
    "ui.preset_files": "Preset",

    # ---- Window: pages ----
    "page.house": "Casa",
    "page.look": "Aspetto",
    "page.doors": "Porte e finestre",
    "page.pages": "Fogli e file",
    "page.advanced": "Avanzate",
    "title.house": "Quanto è grande la casa?",
    "title.look": "Che aspetto ha?",
    "title.doors": "Porta e finestre",
    "title.pages": "Fogli e file",
    "title.advanced": "Impostazioni avanzate",
    "sub.house": "Le misure sono in caselle di gioco: una casella sono "
                 "2,5 cm sulla carta.",
    "sub.look": "Scegli i materiali, oppure lascia spente le texture per "
                "stampare solo le linee di taglio.",
    "sub.doors": "Dove va la porta e come sono distribuite le finestre.",
    "sub.pages": "Cosa viene scritto, su che carta e dove.",
    "sub.advanced": "Ogni valore, impostato direttamente in cm e metri. "
                    "Quello che cambi qui cambia anche nelle altre pagine.",

    # ---- Window: house page ----
    "card.size": "Misure",
    "card.picker": "Sceglila sulla griglia",
    "card.amount": "Quante case",
    "ui.sq.width_cm": "Lato corto, con il tetto (caselle)",
    "ui.sq.length_cm": "Lato lungo (caselle)",
    "ui.sq.height_cm": "Altezza delle pareti (caselle)",
    "ui.sq.roof_height_cm": "Altezza del tetto (caselle)",
    "ui.sq.floor_height_cm": "Un piano ogni (caselle)",
    "ui.cm": "= {value} cm",
    "ui.picker_long": "Lato lungo",
    "ui.picker_gable": "Lato corto",
    "ui.picker_caption": "{rows} × {cols} caselle ({w} × {l} cm)",
    "ui.picker_none": "Passa sulla griglia e clicca",
    "ui.specific_houses": "Stampa un numero preciso di case",
    "ui.houses_hint": "Se lo lasci spento, ogni foglio viene riempito con "
                      "copie di un solo pezzo.",

    # ---- Window: look page ----
    "card.textures": "Texture",
    "card.variation": "Variazione",
    "ui.walls": "Pareti",
    "ui.roof": "Tetto",
    "ui.new_variation": "Nuova variazione",
    "ui.variation_number": "Numero della variazione",
    "material.brick": "Mattoni",
    "material.stone": "Pietra",
    "material.wood": "Legno",
    "material.tiles": "Tegole",
    "material.thatch": "Paglia",

    # ---- Window: doors page ----
    "card.door": "Porta",
    "card.windows": "Finestre",
    "ui.door_side": "Porta sul lato",
    "ui.side_short": "Lato corto (con il timpano)",
    "ui.side_long": "Lato lungo",
    "ui.window_spacing": "Distanza tra le finestre (caselle)",
    "ui.more_in_advanced": "Le misure di porta e finestre sono nella pagina "
                           "Avanzate.",

    # ---- Window: pages page ----
    "card.pdf": "PDF",
    "card.layout": "Disposizione sui fogli",
    "card.files": "File",
    "ui.complete_hint": "Salta i PDF dei singoli pezzi.",
    "ui.folder": "Cartella",
    "ui.file_name": "Nome dei file",

    # ---- Groups of the Advanced page ----
    "group.House": "Casa",
    "group.Look": "Aspetto",
    "group.Door & windows": "Porte e finestre",
    "group.Pages & output": "Fogli e file",

    # ---- Settings: label and help ----
    "label.generate_full_house": "Casa intera",
    "help.generate_full_house": "genera la casa intera invece di una sola "
                                "parete",
    "label.width_cm": "Larghezza, lato corto (cm)",
    "help.width_cm": "lato corto della casa (quello con il timpano)",
    "label.length_cm": "Lunghezza, lato lungo (cm)",
    "help.length_cm": "lato lungo della casa",
    "label.height_cm": "Altezza delle pareti (cm)",
    "help.height_cm": "altezza delle pareti (uguale per i due lati)",
    "label.tab_width_cm": "Larghezza linguette (cm)",
    "help.tab_width_cm": "larghezza delle linguette attorno al rettangolo "
                         "interno",
    "label.roof_height_cm": "Altezza del tetto (cm)",
    "help.roof_height_cm": "altezza del timpano (il triangolo del tetto)",
    "label.roof_flap_cm": "Alette del tetto (cm)",
    "help.roof_flap_cm": "larghezza delle alette sul timpano",
    "label.roof_overhang_cm": "Sporgenza del tetto (cm)",
    "help.roof_overhang_cm": "di quanto la falda supera il lato del "
                             "timpano",
    "label.roof_margin_cm": "Margine del foglio del tetto (cm)",
    "help.roof_margin_cm": "margine in più aggiunto su ogni lato del foglio "
                           "del tetto",
    "label.use_roof": "Timpano del tetto (parete singola)",
    "help.use_roof": "solo per la parete singola: disegna il timpano",
    "label.textures_enabled": "Colora con le texture",
    "help.textures_enabled": "colora le texture (altrimenti solo le linee)",
    "label.wall_material": "Materiale delle pareti",
    "help.wall_material": "materiale delle pareti",
    "label.roof_material": "Materiale del tetto",
    "help.roof_material": "materiale del tetto",
    "label.generate_all_variants": "Tutte le combinazioni di materiali",
    "help.generate_all_variants": "genera ogni combinazione di materiali "
                                  "pareti/tetto",
    "label.seed": "Variazione delle texture",
    "help.seed": "numero diverso, variazione diversa delle texture",
    "label.texture_on_roof_overhang": "Texture sulla sporgenza del tetto",
    "help.texture_on_roof_overhang": "la texture copre anche il margine in "
                                     "più del foglio del tetto",
    "label.reuse_textures": "Riusa le texture (file più piccoli)",
    "help.reuse_textures": "disegna ogni texture una sola volta per PDF e "
                           "la riusa per ogni copia (file più piccoli e "
                           "veloci)",
    "label.line_width": "Spessore delle linee",
    "help.line_width": "spessore delle linee in punti",
    "label.draw_roof_base": "Linea di base del timpano",
    "help.draw_roof_base": "disegna anche la base del triangolo del "
                           "timpano (linea di piega)",
    "label.door_and_windows": "Porta e finestre",
    "help.door_and_windows": "disegna porta e finestre",
    "label.door_on": "Porta sul lato",
    "help.door_on": "lato della casa con la porta",
    "label.one_door_per_house": "Una porta per casa",
    "help.one_door_per_house": "una sola parete per casa ha la porta "
                               "(l'altra ha una finestra al suo posto)",
    "label.door_arched": "Porta ad arco",
    "help.door_arched": "porta con la parte alta arrotondata",
    "label.door_width_min_m": "Larghezza porta, parete piccola (m)",
    "help.door_width_min_m": "larghezza della porta su una parete di 3 "
                             "caselle",
    "label.door_width_max_m": "Larghezza porta, parete grande (m)",
    "help.door_width_max_m": "larghezza della porta su una parete di 5 "
                             "caselle o più",
    "label.door_height_m": "Altezza della porta (m)",
    "help.door_height_m": "altezza della porta",
    "label.window_width_m": "Larghezza delle finestre (m)",
    "help.window_width_m": "larghezza delle finestre",
    "label.window_height_m": "Altezza delle finestre (m)",
    "help.window_height_m": "altezza delle finestre",
    "label.window_sill_m": "Altezza del davanzale (m)",
    "help.window_sill_m": "altezza del davanzale da terra",
    "label.round_window_radius_m": "Raggio della finestra tonda (m)",
    "help.round_window_radius_m": "raggio della finestrella nel timpano",
    "label.floor_height_cm": "Altezza di un piano (cm)",
    "help.floor_height_cm": "un piano di finestre ogni tot cm di altezza "
                            "delle pareti",
    "label.window_spacing_cells": "Distanza tra le finestre (caselle)",
    "help.window_spacing_cells": "distanza desiderata tra le finestre, in "
                                 "caselle (più bassa: più finestre)",
    "label.cell_cm": "Lato di una casella (cm)",
    "help.cell_cm": "lato di una casella di gioco",
    "label.meters_per_cell": "Casella nella storia (m)",
    "help.meters_per_cell": "dimensione di una casella nella finzione "
                            "narrativa",
    "label.complete_only": "Solo il PDF completo",
    "help.complete_only": "scrive solo il PDF completo, non i PDF dei "
                          "singoli pezzi",
    "label.paper": "Formato della carta",
    "help.paper": "formato della carta del PDF completo",
    "label.houses": "Numero di case",
    "help.houses": "numero di case da stampare. Se vuoto, ogni pagina è "
                   "riempita con tutte le copie di un pezzo che ci stanno",
    "label.mix_pieces": "Mescola i pezzi sullo stesso foglio",
    "help.mix_pieces": "serve il numero di case: mette pezzi diversi sullo "
                       "stesso foglio per risparmiare carta",
    "label.allow_rotation": "Permetti di ruotare i pezzi",
    "help.allow_rotation": "permette di ruotare i pezzi di 90 gradi",
    "label.joint_labels": "Lettere degli angoli sulle linguette",
    "help.joint_labels": "scrive le lettere degli angoli sulle linguette: "
                         "le linguette con la stessa lettera vanno insieme",
    "label.calibration_ruler": "Righello da 5 cm su ogni foglio",
    "help.calibration_ruler": "disegna un righello da 5 cm su ogni pagina "
                              "del PDF completo, per controllare la scala "
                              "di stampa",
    "label.page_margin_cm": "Margine del foglio (cm)",
    "help.page_margin_cm": "margine bianco lungo i bordi del foglio",
    "label.copy_gap_cm": "Spazio tra i pezzi (cm)",
    "help.copy_gap_cm": "spazio tra due pezzi",
    "label.output_dir": "Cartella di output",
    "help.output_dir": "cartella dei PDF (relativa a questo script)",
    "label.base_name": "Nome dei file",
    "help.base_name": "nome base dei PDF",
    "label.language": "Lingua",
    "help.language": "lingua dei messaggi",
}
