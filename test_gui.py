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
    import gui
except ImportError:                       # tkinter is not installed
    gui = None


@unittest.skipIf(gui is None, "tkinter is not available")
class PureFunctionTests(unittest.TestCase):

    def test_labels(self):
        self.assertEqual(gui.pretty_label("door_width_min_m"), "Door width min (m)")
        self.assertEqual(gui.pretty_label("width_cm"), "Width (cm)")
        self.assertEqual(gui.pretty_label("window_spacing_cells"),
                         "Window spacing (squares)")
        self.assertEqual(gui.pretty_label("textures_enabled"), "Paint textures")

    def test_field_kinds(self):
        kinds = {f.name: gui.field_kind(f) for f in main.cli_fields()}
        self.assertEqual(kinds["textures_enabled"], "bool")
        self.assertEqual(kinds["wall_material"], "choice")
        self.assertEqual(kinds["seed"], "int")
        self.assertEqual(kinds["houses"], "int")
        self.assertEqual(kinds["width_cm"], "float")
        self.assertEqual(kinds["base_name"], "str")

    def test_numbers_accept_a_decimal_comma(self):
        self.assertEqual(gui.parse_value("float", "7,5"), 7.5)
        self.assertEqual(gui.parse_value("float", " 10 "), 10.0)
        self.assertEqual(gui.parse_value("int", "3"), 3)

    def test_bad_numbers_are_explained(self):
        for kind, text in (("float", "abc"), ("int", "2.5"), ("float", "")):
            with self.assertRaises(ValueError):
                gui.parse_value(kind, text)

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
        self.assertEqual(gui.disabled_fields(self.base_values()), {"use_roof"})

    def test_mixing_needs_the_number_of_houses(self):
        self.assertIn("mix_pieces", gui.disabled_fields(self.base_values(houses="")))
        self.assertNotIn("mix_pieces", gui.disabled_fields(self.base_values()))

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
        self.assertTrue({"length_cm", "houses", "paper"} <= off)
        self.assertNotIn("use_roof", off)

    def test_every_greyed_setting_exists(self):
        names = {f.name for f in main.cli_fields()}
        everything = (gui.DOOR_SETTINGS | gui.TEXTURE_SETTINGS
                      | gui.FULL_HOUSE_ONLY | {"use_roof", "mix_pieces"})
        self.assertEqual(everything - names, set())


def has_display():
    if gui is None:
        return False
    try:
        import tkinter
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
        self.app = self.make_app(output_dir=self.tmp)
        self.addCleanup(self.app.root.destroy)

    def make_app(self, **overrides):
        return gui.App(Config, main.run, main.validate,
                       main.resolve_output_dir, main.config_to_args, overrides)

    def wait(self, seconds=60):
        deadline = time.time() + seconds
        while self.app.running and time.time() < deadline:
            self.app.root.update()
            time.sleep(0.02)
        self.app.root.update()
        self.assertFalse(self.app.running, "generation did not finish")

    def test_the_window_shows_every_setting(self):
        self.assertEqual(set(self.app.entries),
                         {f.name for f in main.cli_fields()})

    def test_the_tabs(self):
        titles = [self.app.notebook.tab(t, "text") for t in self.app.notebook.tabs()]
        self.assertEqual(titles, gui.GROUP_ORDER)

    def test_the_form_starts_from_the_given_settings(self):
        app = self.make_app(houses=3, wall_material="stone", width_cm=10.0)
        try:
            cfg, errors = app.collect()
            self.assertEqual(errors, [])
            self.assertEqual((cfg.houses, cfg.wall_material, cfg.width_cm),
                             (3, "stone", 10.0))
        finally:
            app.root.destroy()

    def test_defaults_round_trip_through_the_form(self):
        app = self.make_app()
        try:
            cfg, errors = app.collect()
            self.assertEqual(errors, [])
            self.assertEqual(cfg, Config())
        finally:
            app.root.destroy()

    def test_typing_a_comma_works(self):
        self.app.entries["width_cm"][2].set("7,5")
        cfg, errors = self.app.collect()
        self.assertEqual(cfg.width_cm, 7.5)

    def test_wrong_values_are_listed(self):
        self.app.entries["width_cm"][2].set("abc")
        self.app.entries["seed"][2].set("2.5")
        cfg, errors = self.app.collect()
        self.assertIsNone(cfg)
        self.assertEqual(len(errors), 2)
        self.assertIn("Width (cm)", errors[0])

    def test_generate_with_wrong_values_shows_an_error_and_does_not_run(self):
        self.app.entries["width_cm"][2].set("abc")
        self.app.start()
        self.assertEqual(len(self.errors), 1)
        self.assertFalse(self.app.running)
        self.assertEqual(list(Path(self.tmp).glob("*.pdf")), [])

    def test_generate_with_invalid_settings_shows_the_reason(self):
        self.app.entries["houses"][2].set("0")
        self.app.start()
        self.assertIn("houses", self.errors[0][1])

    def test_generate_writes_the_pdfs_and_reports_in_the_log(self):
        self.app.start()
        self.wait()
        self.assertEqual(len(list(Path(self.tmp).glob("*.pdf"))), 4)
        log = self.app.log.get("1.0", "end")
        self.assertIn("PDF created", log)
        self.assertIn("Done: 4 PDF files", log)
        self.assertEqual(self.errors, [])

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
            self.assertEqual(button.cget("text"), "Generating...")
            gate.set()
            self.wait()

        self.assertEqual(len(calls), 1)
        self.assertEqual(str(button.cget("state")), "normal")
        self.assertEqual(button.cget("text"), "Generate PDFs")

    def test_a_failure_is_shown_and_the_window_stays_usable(self):
        with mock.patch.object(self.app, "run", side_effect=main.OutputError("locked")):
            self.app.start()
            self.wait()
        self.assertEqual(self.errors[0][1], "locked")
        self.assertIn("locked", self.app.log.get("1.0", "end"))
        self.assertFalse(self.app.running)

    def test_warnings_reach_the_log(self):
        self.app.entries["generate_all_variants"][2].set(True)
        self.app.start()
        self.wait()
        self.assertIn("WARNING: generate_all_variants", self.app.log.get("1.0", "end"))

    def widget_state(self, name):
        widget = self.app.entries[name][3][0]
        return "disabled" if widget.instate(["disabled"]) else "enabled"

    def test_settings_are_greyed_out_when_they_do_nothing(self):
        self.assertEqual(self.widget_state("mix_pieces"), "disabled")
        self.app.entries["houses"][2].set("2")
        self.assertEqual(self.widget_state("mix_pieces"), "enabled")
        self.app.entries["houses"][2].set("")
        self.assertEqual(self.widget_state("mix_pieces"), "disabled")

        self.assertEqual(self.widget_state("wall_material"), "disabled")
        self.app.entries["textures_enabled"][2].set(True)
        self.assertEqual(self.widget_state("wall_material"), "enabled")
        self.app.entries["generate_all_variants"][2].set(True)
        self.assertEqual(self.widget_state("wall_material"), "disabled")

    def test_the_command_does_the_same_as_the_window(self):
        self.app.entries["houses"][2].set("2")
        self.app.entries["wall_material"][2].set("stone")
        self.app.entries["textures_enabled"][2].set(True)
        cfg, _ = self.app.collect()
        command = self.app.command_text(cfg)
        self.assertTrue(command.startswith("python main.py "))
        self.assertIn("--houses 2", command)
        self.assertIn("--wall-material stone", command)

    def test_the_command_for_the_defaults_does_not_open_the_window(self):
        self.app.entries["output_dir"][2].set(Config().output_dir)
        cfg, _ = self.app.collect()
        self.assertEqual(self.app.command_text(cfg), "python main.py --no-gui")

    def test_copy_command_uses_the_clipboard(self):
        self.app.entries["houses"][2].set("3")
        self.app.copy_command()
        self.assertIn("--houses 3", self.app.root.clipboard_get())

    def test_reset_restores_the_defaults(self):
        self.app.entries["houses"][2].set("4")
        self.app.entries["textures_enabled"][2].set(True)
        self.app.reset()
        cfg, _ = self.app.collect()
        self.assertEqual(cfg, Config())

    def test_presets_save_and_load(self):
        path = os.path.join(self.tmp, "preset.json")
        self.app.entries["houses"][2].set("2")
        self.app.entries["roof_material"][2].set("tiles")
        self.app.entries["height_cm"][2].set("10")

        with mock.patch.object(gui.filedialog, "asksaveasfilename", return_value=path):
            self.app.save_preset()
        saved = json.loads(Path(path).read_text(encoding="utf-8"))
        self.assertEqual(saved["houses"], 2)
        self.assertEqual(saved["roof_material"], "tiles")

        self.app.reset()
        with mock.patch.object(gui.filedialog, "askopenfilename", return_value=path):
            self.app.load_preset()
        cfg, _ = self.app.collect()
        self.assertEqual((cfg.houses, cfg.roof_material, cfg.height_cm),
                         (2, "tiles", 10.0))

    def test_a_broken_preset_is_reported(self):
        path = os.path.join(self.tmp, "broken.json")
        Path(path).write_text("not json", encoding="utf-8")
        with mock.patch.object(gui.filedialog, "askopenfilename", return_value=path):
            self.app.load_preset()
        self.assertEqual(len(self.errors), 1)

    def test_a_preset_with_unknown_names_is_tolerated(self):
        path = os.path.join(self.tmp, "old.json")
        Path(path).write_text(json.dumps({"houses": 5, "old_option": 1}),
                              encoding="utf-8")
        with mock.patch.object(gui.filedialog, "askopenfilename", return_value=path):
            self.app.load_preset()
        self.assertEqual(self.app.collect()[0].houses, 5)


@unittest.skipIf(gui is None or sys.platform == "win32",
                 "needs tkinter and a system without a screen")
class NoScreenTests(unittest.TestCase):

    def test_without_a_screen_the_message_explains_what_to_do(self):
        env = {k: v for k, v in os.environ.items() if k != "DISPLAY"}
        result = subprocess.run(
            [sys.executable, str(Path(main.__file__)), "--gui"],
            env=env, capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 1)
        self.assertIn("--no-gui", result.stderr)


if __name__ == "__main__":
    unittest.main()
