"""Tests for gui.py. Run with:  python -m unittest -v

The tests that open the window are skipped when there is no screen (or no
tkinter), for example on a server. On Linux, `xvfb-run python -m unittest`
gives them a virtual screen.
"""

import json
import os
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest import mock

import main
from main import Config

try:
    import tkinter
    import gui
except ImportError:                       # tkinter is not installed
    tkinter = None
    gui = None


PALETTES = {"wall_material": main.WALL_PALETTES,
            "roof_material": main.ROOF_PALETTES}


@unittest.skipIf(gui is None, "tkinter is not available")
class PureFunctionTests(unittest.TestCase):

    def test_label_fallback(self):
        self.assertEqual(gui.pretty_label("door_width_min_m"),
                         "Door width min (m)")
        self.assertEqual(gui.pretty_label("window_spacing_cells"),
                         "Window spacing (squares)")

    def test_field_kinds(self):
        kinds = {f.name: gui.field_kind(f) for f in main.cli_fields()}
        self.assertEqual(kinds["textures_enabled"], "bool")
        self.assertEqual(kinds["wall_material"], "choice")
        self.assertEqual(kinds["seed"], "int")
        self.assertEqual(kinds["houses"], "int")
        self.assertEqual(kinds["width_cm"], "float")
        self.assertEqual(kinds["base_name"], "str")

    def test_numbers_accept_a_decimal_comma(self):
        self.assertEqual(gui.parse_float("7,5"), 7.5)
        self.assertEqual(gui.parse_float(" 10 "), 10.0)
        self.assertIsNone(gui.parse_float("abc"))
        self.assertIsNone(gui.parse_float(""))
        self.assertEqual(gui.parse_value("float", "7,5"), 7.5)
        self.assertEqual(gui.parse_value("int", "3"), 3)

    def test_bad_numbers_are_explained_in_the_language(self):
        for kind, text in (("float", "abc"), ("int", "2.5"), ("float", "")):
            with self.assertRaises(ValueError):
                gui.parse_value(kind, text)
        with self.assertRaises(ValueError) as error:
            gui.parse_value("float", "abc", language="it")
        self.assertIn("non è un numero", str(error.exception))

    def test_empty_optional_number_is_none(self):
        self.assertIsNone(gui.parse_value("int", "  ", optional=True))

    def test_formatting(self):
        self.assertEqual(gui.format_value(5.0), "5")
        self.assertEqual(gui.format_value(0.35), "0.35")
        self.assertEqual(gui.format_value(None), "")

    def base_values(self, **changes):
        values = dict(generate_full_house=True, textures_enabled=True,
                      generate_all_variants=False, door_and_windows=True,
                      houses="2")
        values.update(changes)
        return values

    def test_nothing_is_greyed_out_when_everything_applies(self):
        self.assertEqual(gui.disabled_fields(self.base_values()),
                         {"use_roof"})

    def test_mixing_needs_the_number_of_houses(self):
        off = gui.disabled_fields(self.base_values(houses=""))
        self.assertTrue({"mix_pieces", "houses_spin"} <= off)
        self.assertNotIn("mix_pieces",
                         gui.disabled_fields(self.base_values()))

    def test_materials_need_textures(self):
        off = gui.disabled_fields(self.base_values(textures_enabled=False))
        self.assertTrue({"wall_material", "roof_material", "seed"} <= off)

    def test_all_variants_replaces_the_material_choice(self):
        off = gui.disabled_fields(self.base_values(generate_all_variants=True))
        self.assertTrue({"wall_material", "roof_material"} <= off)
        self.assertNotIn("seed", off)

    def test_door_settings_need_door_and_windows(self):
        off = gui.disabled_fields(self.base_values(door_and_windows=False))
        self.assertTrue({"door_on", "window_width_m", "floor_height_cm"} <= off)

    def test_single_wall_mode_greys_out_the_house_settings(self):
        off = gui.disabled_fields(self.base_values(generate_full_house=False))
        self.assertTrue({"length_cm", "houses", "paper", "complete_only"} <= off)
        self.assertNotIn("use_roof", off)

    def test_every_greyed_setting_exists(self):
        names = {f.name for f in main.cli_fields()} | {"houses_spin"}
        everything = (gui.DOOR_SETTINGS | gui.TEXTURE_SETTINGS
                      | gui.FULL_HOUSE_ONLY | {"use_roof", "mix_pieces"})
        self.assertEqual(everything - names, set())

    def test_sizes_in_squares_are_settings_in_cm(self):
        names = {f.name for f in main.cli_fields()}
        self.assertEqual(set(gui.SQUARE_LINKS) - names, set())


@unittest.skipIf(gui is None or gui.Image is None, "needs tkinter and Pillow")
class DrawingTests(unittest.TestCase):

    ICONS = ("house", "palette", "door", "page", "gear", "play", "folder",
             "copy", "upload", "download", "reset", "dice")

    def test_every_icon_is_drawn(self):
        for name in self.ICONS:
            image = gui.draw_icon(name, 24, "#ffffff")
            self.assertEqual(image.size, (24, 24), name)
            self.assertIsNotNone(image.getbbox(), f"{name} is empty")

    def test_the_icons_of_the_window_exist(self):
        for _, icon in gui.PAGES:
            self.assertIn(icon, self.ICONS)

    def test_logo(self):
        self.assertEqual(gui.draw_logo(48).size, (48, 48))

    def test_every_material_has_a_swatch(self):
        for field, role in (("wall_material", "wall"),
                            ("roof_material", "roof")):
            for name, palette in PALETTES[field].items():
                image = gui.draw_swatch(role, name, palette["base"], (64, 44))
                self.assertEqual(image.size, (64, 44), name)
                self.assertEqual(image.mode, "RGB")

    def test_swatches_differ_between_materials(self):
        images = [gui.draw_swatch("wall", name, p["base"]).tobytes()
                  for name, p in main.WALL_PALETTES.items()]
        self.assertEqual(len(set(images)), len(images))

    def test_wood_looks_different_on_walls_and_roofs(self):
        wall = gui.draw_swatch("wall", "wood", (0.5, 0.35, 0.2)).tobytes()
        roof = gui.draw_swatch("roof", "wood", (0.5, 0.35, 0.2)).tobytes()
        self.assertNotEqual(wall, roof)

    def test_an_unknown_material_still_gets_a_swatch(self):
        image = gui.draw_swatch("wall", "marble", (0.9, 0.9, 0.9))
        self.assertEqual(image.size, (64, 44))

    def test_indicators(self):
        for kind in ("check", "radio"):
            for state in ("normal", "hover", "selected", "disabled",
                          "selected_disabled"):
                image = gui.draw_indicator(kind, state, 18, 7)
                self.assertEqual(image.size, (25, 18))


def has_display():
    if gui is None:
        return False
    try:
        root = tkinter.Tk()
        root.destroy()
        return True
    except Exception:
        return False


@unittest.skipUnless(has_display(), "no screen available for the window")
class WindowTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.errors = []
        patcher = mock.patch.object(
            gui.messagebox, "showerror",
            side_effect=lambda title, text: self.errors.append((title, text)))
        patcher.start()
        self.addCleanup(patcher.stop)
        self.app = self.make_app(language="en", output_dir=self.tmp)
        self.addCleanup(self.close)

    def close(self):
        try:
            self.app.root.destroy()
        except tkinter.TclError:
            pass

    def make_app(self, **overrides):
        return gui.App(Config, main.run, main.validate,
                       main.resolve_output_dir, main.config_to_args,
                       overrides, PALETTES)

    def wait(self, seconds=60):
        deadline = time.time() + seconds
        while self.app.running and time.time() < deadline:
            self.app.root.update()
            time.sleep(0.02)
        self.app.root.update()
        self.assertFalse(self.app.running, "generation did not finish")

    def set(self, name, value):
        self.app.vars[name].set(value)

    def enabled(self, name):
        widget = self.app.widgets[name][0]
        if isinstance(widget, gui.ttk.Widget):
            return not widget.instate(["disabled"])
        return str(widget.cget("state")) != "disabled"

    def texts(self):
        """Every text written on the window, now."""
        found = set()

        def walk(widget):
            for child in widget.winfo_children():
                if "text" in child.keys():
                    found.add(str(child.cget("text")).strip())
                walk(child)

        walk(self.app.shell)
        return found - {""}

    def switch(self, code):
        self.app.lang_var.set(code)
        self.app.change_language()
        self.app.root.update()

    # ---- the form ----

    def test_the_window_has_a_page_for_each_section(self):
        self.assertEqual(list(self.app.pages), [k for k, _ in gui.PAGES])

    def test_every_setting_is_in_the_advanced_page(self):
        self.assertEqual(set(self.app.vars), set(self.app.fields))
        self.assertTrue(set(self.app.vars) <= set(self.app.widgets))

    def test_the_language_is_not_a_setting_of_the_form(self):
        self.assertNotIn("language", self.app.vars)

    def test_the_form_starts_from_the_given_settings(self):
        app = self.make_app(language="en", houses=3, wall_material="stone",
                            width_cm=10.0)
        try:
            cfg, errors = app.collect()
            self.assertEqual(errors, [])
            self.assertEqual((cfg.houses, cfg.wall_material, cfg.width_cm),
                             (3, "stone", 10.0))
        finally:
            app.root.destroy()

    def test_defaults_round_trip_through_the_form(self):
        cfg, errors = self.app.collect()
        self.assertEqual(errors, [])
        self.assertEqual(cfg, Config(output_dir=self.tmp, language="en"))

    def test_wrong_values_are_listed(self):
        self.set("width_cm", "abc")
        self.set("seed", "2.5")
        cfg, errors = self.app.collect()
        self.assertIsNone(cfg)
        self.assertEqual(len(errors), 2)

    # ---- sizes in squares ----

    def test_the_sizes_are_shown_in_squares(self):
        self.assertEqual(self.app.squares["width_cm"].get(), "3")
        self.assertEqual(self.app.squares["length_cm"].get(), "5")
        self.assertEqual(self.app.squares["height_cm"].get(), "3")
        self.assertEqual(self.app.squares["roof_height_cm"].get(), "2")
        self.assertEqual(self.app.cm_text["width_cm"].get(), "= 7.5 cm")

    def test_typing_squares_changes_the_cm(self):
        self.app.squares["width_cm"].set("4")
        self.assertEqual(self.app.vars["width_cm"].get(), "10")
        self.assertEqual(self.app.cm_text["width_cm"].get(), "= 10 cm")

    def test_squares_can_be_fractions_and_use_a_comma(self):
        self.app.squares["roof_height_cm"].set("0,8")
        self.assertEqual(self.app.vars["roof_height_cm"].get(), "2")
        self.app.squares["height_cm"].set("2,5")
        self.assertEqual(self.app.vars["height_cm"].get(), "6.25")

    def test_changing_the_cm_changes_the_squares(self):
        self.set("length_cm", "15")
        self.assertEqual(self.app.squares["length_cm"].get(), "6")

    def test_half_typed_squares_leave_the_cm_alone(self):
        before = self.app.vars["width_cm"].get()
        for text in ("", "-", "abc"):
            self.app.squares["width_cm"].set(text)
            self.assertEqual(self.app.vars["width_cm"].get(), before, text)

    def test_the_square_size_is_used_for_the_conversion(self):
        self.set("cell_cm", "2")
        self.assertEqual(self.app.squares["width_cm"].get(), "3.75")
        self.app.squares["width_cm"].set("4")
        self.assertEqual(self.app.vars["width_cm"].get(), "8")

    def test_arrows_do_not_leave_a_trailing_zero(self):
        self.app.squares["width_cm"].set("3.0")
        self.app._normalize_square("width_cm")
        self.assertEqual(self.app.squares["width_cm"].get(), "3")

    def test_the_collected_sizes_are_in_cm(self):
        self.app.squares["width_cm"].set("3")
        self.app.squares["length_cm"].set("4")
        self.app.squares["height_cm"].set("2")
        cfg, _ = self.app.collect()
        self.assertEqual((cfg.width_cm, cfg.length_cm, cfg.height_cm),
                         (7.5, 10.0, 5.0))

    # ---- the grid ----

    def test_the_grid_shows_the_current_size(self):
        self.assertEqual(self.app.picker.selection, (3, 5))
        self.app.squares["length_cm"].set("7")
        self.assertEqual(self.app.picker.selection, (3, 7))

    def test_clicking_the_grid_sets_the_size(self):
        self.app._pick(2, 6)
        cfg, _ = self.app.collect()
        self.assertEqual((cfg.width_cm, cfg.length_cm), (5.0, 15.0))
        self.assertEqual(self.app.picker.selection, (2, 6))
        self.assertIn("2 × 6 squares", self.app.picker_caption.get())
        self.assertIn("5 × 15 cm", self.app.picker_caption.get())

    def test_the_grid_follows_the_cm_of_the_advanced_page(self):
        self.set("width_cm", "5")
        self.set("length_cm", "7.5")
        self.assertEqual(self.app.picker.selection, (2, 3))

    def test_sizes_that_are_not_whole_squares_or_too_big_clear_the_grid(self):
        self.set("width_cm", "6")                    # 2.4 squares
        self.assertIsNone(self.app.picker.selection)
        self.assertIn("grid", self.app.picker_caption.get().lower())
        self.set("width_cm", "7.5")
        self.set("length_cm", "50")                  # 20 squares
        self.assertIsNone(self.app.picker.selection)

    def test_moving_over_the_grid_previews_the_size(self):
        self.app._picker_hover((4, 8))
        self.assertIn("4 × 8 squares", self.app.picker_caption.get())
        self.app._picker_hover(None)
        self.assertIn("3 × 5 squares", self.app.picker_caption.get())

    def test_grid_cells_react_to_the_mouse(self):
        picker = self.app.picker
        self.app.show_page("house")
        self.app.root.update()
        x = picker.left + picker.gap + 1 * (picker.cell + picker.gap) + 2
        y = picker.top + picker.gap + 2 * (picker.cell + picker.gap) + 2
        picker.event_generate("<Motion>", x=x, y=y)
        self.app.root.update()
        self.assertEqual(picker.hover, (2, 1))
        picker.event_generate("<Button-1>", x=x, y=y)
        self.app.root.update()
        cfg, _ = self.app.collect()
        self.assertEqual((cfg.width_cm, cfg.length_cm), (7.5, 5.0))

    # ---- number of houses ----

    def test_the_switch_and_the_number_of_houses_go_together(self):
        self.assertFalse(self.app.use_houses.get())
        self.app.use_houses.set(True)
        self.assertEqual(self.app.vars["houses"].get(), "1")
        self.set("houses", "4")
        self.assertTrue(self.app.use_houses.get())
        self.app.use_houses.set(False)
        self.assertEqual(self.app.vars["houses"].get(), "")
        self.assertIsNone(self.app.collect()[0].houses)

    def test_the_number_of_houses_box_follows_the_switch(self):
        self.assertFalse(self.enabled("houses_spin"))
        self.app.use_houses.set(True)
        self.assertTrue(self.enabled("houses_spin"))

    # ---- generating ----

    def test_generate_with_wrong_values_shows_an_error_and_does_not_run(self):
        self.set("width_cm", "abc")
        self.app.start()
        self.assertEqual(len(self.errors), 1)
        self.assertFalse(self.app.running)
        self.assertEqual(list(Path(self.tmp).glob("*.pdf")), [])

    def test_generate_with_invalid_settings_shows_the_reason(self):
        self.set("houses", "0")
        self.app.start()
        self.assertIn("houses", self.errors[0][1])

    def test_generate_writes_only_the_complete_pdf_by_default(self):
        self.app.start()
        self.wait()
        self.assertEqual([p.name for p in Path(self.tmp).glob("*.pdf")],
                         ["house_DnD_complete.pdf"])
        log = self.app.log.get("1.0", "end")
        self.assertIn("PDF created", log)
        self.assertIn("Done: 1 PDF files", log)
        self.assertEqual(self.errors, [])

    def test_the_single_pieces_can_be_asked_for(self):
        self.set("complete_only", False)
        self.app.start()
        self.wait()
        self.assertEqual(len(list(Path(self.tmp).glob("*.pdf"))), 4)

    def test_generate_button_is_blocked_while_running(self):
        gate = threading.Event()
        calls = []

        def slow_run(cfg):
            calls.append(cfg)
            gate.wait(10)
            return []

        button = self.app.generate_button
        with mock.patch.object(self.app, "run", slow_run):
            self.app.start()
            self.app.start()                 # ignored: already running
            self.app.root.update()
            self.assertTrue(self.app.running)
            self.assertEqual(str(button.cget("state")), "disabled")
            self.assertIn("Generating", button.cget("text"))
            gate.set()
            self.wait()

        self.assertEqual(len(calls), 1)
        self.assertEqual(str(button.cget("state")), "normal")
        self.assertIn("Generate PDFs", button.cget("text"))

    def test_a_failure_is_shown_and_the_window_stays_usable(self):
        with mock.patch.object(self.app, "run",
                               side_effect=main.OutputError("locked")):
            self.app.start()
            self.wait()
        self.assertEqual(self.errors[0][1], "locked")
        self.assertIn("locked", self.app.log.get("1.0", "end"))
        self.assertFalse(self.app.running)

    def test_warnings_reach_the_log(self):
        self.set("generate_all_variants", True)
        self.app.start()
        self.wait()
        self.assertIn("WARNING: generate_all_variants",
                      self.app.log.get("1.0", "end"))

    def test_the_settings_sent_to_the_generator_carry_the_language(self):
        seen = []
        with mock.patch.object(self.app, "run",
                               side_effect=lambda cfg: seen.append(cfg) or []):
            self.app.start()
            self.wait()
        self.assertEqual(seen[0].language, "en")

    # ---- greying out ----

    def test_settings_are_greyed_out_when_they_do_nothing(self):
        self.assertFalse(self.enabled("mix_pieces"))
        self.set("houses", "2")
        self.assertTrue(self.enabled("mix_pieces"))
        self.set("houses", "")
        self.assertFalse(self.enabled("mix_pieces"))

        self.assertFalse(self.enabled("wall_material"))
        self.set("textures_enabled", True)
        self.assertTrue(self.enabled("wall_material"))
        self.set("generate_all_variants", True)
        self.assertFalse(self.enabled("wall_material"))

    def test_the_door_settings_follow_door_and_windows(self):
        self.assertTrue(self.enabled("door_on"))
        self.assertTrue(self.enabled("floor_height_cm"))
        self.set("door_and_windows", False)
        self.assertFalse(self.enabled("door_on"))
        self.assertFalse(self.enabled("floor_height_cm"))

    # ---- materials ----

    def test_every_material_has_a_button_with_a_picture(self):
        for field in ("wall_material", "roof_material"):
            buttons = self.app.swatch_buttons[field]
            choices = Config.__dataclass_fields__[field].metadata["choices"]()
            self.assertEqual(len(buttons), len(choices))
            for button in buttons:
                self.assertTrue(str(button.cget("image")))

    def test_the_chosen_material_is_framed(self):
        self.set("wall_material", "stone")
        framed = [b.cget("value")
                  for b in self.app.swatch_buttons["wall_material"]
                  if str(b.cget("highlightbackground")) == gui.COLORS["accent"]]
        self.assertEqual(framed, ["stone"])

    def test_a_new_variation_changes_the_seed(self):
        with mock.patch.object(gui.random, "randint", return_value=1234):
            self.app.new_variation()
        self.assertEqual(self.app.vars["seed"].get(), "1234")

    # ---- language ----

    def test_the_language_is_taken_from_the_settings(self):
        app = self.make_app(language="it", output_dir=self.tmp)
        try:
            self.assertEqual(app.language, "it")
            self.assertIn("Genera", app.generate_button.cget("text"))
        finally:
            app.root.destroy()

    def test_an_unknown_language_becomes_english(self):
        app = self.make_app(language="xx", output_dir=self.tmp)
        try:
            self.assertEqual(app.language, "en")
        finally:
            app.root.destroy()

    def test_switching_language_translates_the_window(self):
        self.assertIn("Generate", self.app.generate_button.cget("text"))
        self.switch("it")
        self.assertIn("Genera", self.app.generate_button.cget("text"))
        self.switch("en")
        self.assertIn("Generate", self.app.generate_button.cget("text"))

    def test_switching_language_translates_every_visible_text(self):
        english = self.texts()
        self.switch("it")
        italian = self.texts()
        for word in ("House", "Generate PDFs", "Open folder", "Language"):
            self.assertTrue(any(word in t for t in english), word)
        for word in ("Casa", "Genera i PDF", "Apri la cartella", "Lingua"):
            self.assertTrue(any(word in t for t in italian), word)
        self.assertFalse(any("Open folder" in t for t in italian))
        self.assertFalse(any("Generate PDFs" in t for t in italian))

    def test_switching_language_keeps_the_values_page_and_log(self):
        self.set("houses", "3")
        self.app.squares["length_cm"].set("4")
        self.app.show_page("look")
        self.app.append("hello log\n")
        self.switch("it")
        cfg, _ = self.app.collect()
        self.assertEqual((cfg.houses, cfg.length_cm), (3, 10.0))
        self.assertEqual(self.app.page_var.get(), "look")
        self.assertIn("hello log", self.app.log.get("1.0", "end"))
        self.assertEqual(cfg.language, "it")

    def test_switching_language_keeps_the_picker_in_sync(self):
        self.switch("it")
        self.assertEqual(self.app.picker.selection, (3, 5))
        self.assertIn("7,5", self.app.picker_caption.get())      # decimal comma
        self.assertIn("caselle", self.app.picker_caption.get())
        self.app.squares["roof_height_cm"].set("0,8")
        self.assertEqual(self.app.cm_text["roof_height_cm"].get(), "= 2 cm")
        self.app.squares["height_cm"].set("2,5")
        self.assertEqual(self.app.cm_text["height_cm"].get(), "= 6,25 cm")

    def test_switching_language_while_generating_keeps_the_button_blocked(self):
        gate = threading.Event()

        def slow_run(cfg):
            gate.wait(10)
            return []

        with mock.patch.object(self.app, "run", slow_run):
            self.app.start()
            self.switch("it")
            self.assertEqual(str(self.app.generate_button.cget("state")),
                             "disabled")
            self.assertIn("Generazione", self.app.generate_button.cget("text"))
            gate.set()
            self.wait()
        self.assertIn("Genera", self.app.generate_button.cget("text"))

    def test_generating_in_italian_gives_an_italian_log(self):
        self.switch("it")
        self.app.start()
        self.wait()
        log = self.app.log.get("1.0", "end")
        self.assertIn("PDF creato", log)
        self.assertIn("Fatto: 1 file PDF", log)
        self.assertNotIn("PDF created", log)

    def test_the_hint_follows_the_language(self):
        self.assertIn("Move the mouse", self.app.help_text.get())
        self.switch("it")
        self.assertIn("Passa il mouse", self.app.help_text.get())

    def test_the_descriptions_follow_the_language(self):
        self.assertIn("short side of the house",
                      self.app.describe("width_cm"))
        self.switch("it")
        self.assertIn("lato corto della casa", self.app.describe("width_cm"))
        self.assertIn("predefinito", self.app.describe("width_cm"))

    # ---- pages ----

    def test_pages_can_be_shown(self):
        for key, _ in gui.PAGES:
            self.app.show_page(key)
            self.assertEqual(self.app.page_var.get(), key)

    def test_the_scroll_helper_does_not_fail(self):
        for scroller in self.app.scrollers.values():
            scroller.scroll(3)
            scroller.scroll(-3)

    # ---- command, presets, reset ----

    def test_the_command_does_the_same_as_the_window(self):
        self.set("houses", "2")
        self.set("wall_material", "stone")
        self.set("textures_enabled", True)
        self.set("output_dir", Config().output_dir)
        cfg, _ = self.app.collect()
        command = self.app.command_text(cfg)
        self.assertTrue(command.startswith("python main.py "))
        self.assertIn("--houses 2", command)
        self.assertIn("--wall-material stone", command)

    def test_the_command_for_the_defaults_does_not_open_the_window(self):
        self.set("output_dir", Config().output_dir)
        cfg, _ = self.app.collect()
        self.assertEqual(self.app.command_text(cfg), "python main.py --no-gui")

    def test_the_command_carries_the_italian_language(self):
        self.switch("it")
        self.set("output_dir", Config().output_dir)
        cfg, _ = self.app.collect()
        self.assertIn("--language it", self.app.command_text(cfg))

    def test_copy_command_uses_the_clipboard(self):
        self.set("houses", "3")
        self.app.copy_command()
        self.assertIn("--houses 3", self.app.root.clipboard_get())

    def test_reset_restores_the_defaults(self):
        self.set("houses", "4")
        self.set("textures_enabled", True)
        self.app.squares["width_cm"].set("5")
        self.app.reset()
        cfg, _ = self.app.collect()
        self.assertEqual(cfg, Config(language="en"))
        self.assertEqual(self.app.squares["width_cm"].get(), "3")

    def test_presets_save_and_load(self):
        path = os.path.join(self.tmp, "preset.json")
        self.set("houses", "2")
        self.set("roof_material", "tiles")
        self.app.squares["height_cm"].set("4")

        with mock.patch.object(gui.filedialog, "asksaveasfilename",
                               return_value=path):
            self.app.save_preset()
        saved = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(saved["houses"], 2)
        self.assertEqual(saved["roof_material"], "tiles")
        self.assertEqual(saved["height_cm"], 10.0)
        self.assertNotIn("language", saved)

        self.app.reset()
        with mock.patch.object(gui.filedialog, "askopenfilename",
                               return_value=path):
            self.app.load_preset()
        cfg, _ = self.app.collect()
        self.assertEqual((cfg.houses, cfg.roof_material, cfg.height_cm),
                         (2, "tiles", 10.0))
        self.assertEqual(self.app.squares["height_cm"].get(), "4")

    def test_a_preset_does_not_change_the_language(self):
        path = os.path.join(self.tmp, "preset.json")
        Path(path).write_text(json.dumps({"houses": 2, "language": "it"}),
                              encoding="utf-8")
        with mock.patch.object(gui.filedialog, "askopenfilename",
                               return_value=path):
            self.app.load_preset()
        self.assertEqual(self.app.language, "en")

    def test_a_broken_preset_is_reported(self):
        path = os.path.join(self.tmp, "broken.json")
        Path(path).write_text("not json", encoding="utf-8")
        with mock.patch.object(gui.filedialog, "askopenfilename",
                               return_value=path):
            self.app.load_preset()
        self.assertEqual(len(self.errors), 1)

    def test_a_preset_with_unknown_names_is_tolerated(self):
        path = os.path.join(self.tmp, "old.json")
        Path(path).write_text(json.dumps({"houses": 5, "old_option": 1}),
                              encoding="utf-8")
        with mock.patch.object(gui.filedialog, "askopenfilename",
                               return_value=path):
            self.app.load_preset()
        self.assertEqual(self.app.collect()[0].houses, 5)

    def test_browse_sets_the_folder(self):
        with mock.patch.object(gui.filedialog, "askdirectory",
                               return_value="/somewhere"):
            self.app.browse_output()
        self.assertEqual(self.app.vars["output_dir"].get(), "/somewhere")


@unittest.skipIf(gui is None or sys.platform == "win32",
                 "needs tkinter and a system without a screen")
class NoScreenTests(unittest.TestCase):

    def run_without_screen(self, *args):
        env = {k: v for k, v in os.environ.items() if k != "DISPLAY"}
        return subprocess.run(
            [sys.executable, str(Path(main.__file__)), "--gui", *args],
            env=env, capture_output=True, text=True, timeout=60)

    def test_without_a_screen_the_message_explains_what_to_do(self):
        result = self.run_without_screen()
        self.assertEqual(result.returncode, 1)
        self.assertIn("--no-gui", result.stderr)

    def test_the_message_is_in_the_chosen_language(self):
        result = self.run_without_screen("--language", "it")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Usa invece", result.stderr)


if __name__ == "__main__":
    unittest.main()