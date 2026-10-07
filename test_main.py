"""Tests for main.py. Run with:  python -m unittest -v"""

import math
import tempfile
import unittest
from collections import Counter
from dataclasses import replace
from pathlib import Path
from unittest import mock

from reportlab.lib.units import cm
from reportlab.pdfgen import canvas

import main
from main import Config


def make_cfg(tmp, **overrides):
    return Config(output_dir=tmp, **overrides)


class GeometryTests(unittest.TestCase):

    def test_outward_parallel_keeps_direction_and_distance(self):
        x1, y1, x2, y2 = 0, 0, 3, 4
        px1, py1, px2, py2 = main.outward_parallel(x1, y1, x2, y2, 2)
        # Same direction and length
        self.assertAlmostEqual(px2 - px1, x2 - x1)
        self.assertAlmostEqual(py2 - py1, y2 - y1)
        # Shifted by exactly 2, perpendicular to the segment
        shift = (px1 - x1, py1 - y1)
        self.assertAlmostEqual(math.hypot(*shift), 2)
        self.assertAlmostEqual(shift[0] * (x2 - x1) + shift[1] * (y2 - y1), 0)

    def test_slope_side(self):
        cfg = Config(roof_height_cm=4)
        self.assertAlmostEqual(main.slope_side_cm(cfg, 6), 5)   # 3-4-5

    def test_meters_conversion(self):
        cfg = Config()
        self.assertAlmostEqual(main.meters(cfg, 1.5), 2.5 * cm)


class PackingTests(unittest.TestCase):

    def overlap(self, a, b):
        ax, ay, aw, ah = a
        bx, by, bw, bh = b
        return not (ax + aw <= bx + 1e-6 or bx + bw <= ax + 1e-6
                    or ay + ah <= by + 1e-6 or by + bh <= ay + 1e-6)

    def test_no_overlaps_and_inside_bounds(self):
        sizes = [(40, 30), (25, 25), (60, 20), (15, 50), (30, 30)] * 3
        placed = main.maxrects_pack(sizes, 10, 10, 200, 150)
        rects = []
        for i, (x, y, rotated) in placed.items():
            w, h = sizes[i]
            if rotated:
                w, h = h, w
            self.assertGreaterEqual(x, 10 - 1e-6)
            self.assertGreaterEqual(y, 10 - 1e-6)
            self.assertLessEqual(x + w, 210 + 1e-6)
            self.assertLessEqual(y + h, 160 + 1e-6)
            rects.append((x, y, w, h))
        for i in range(len(rects)):
            for j in range(i + 1, len(rects)):
                self.assertFalse(self.overlap(rects[i], rects[j]))

    def test_rotation_lets_a_piece_fit(self):
        # 100 x 40 piece in a 50 x 120 area only fits rotated
        self.assertEqual(main.maxrects_pack([(100, 40)], 0, 0, 50, 120, True)[0][2],
                         True)
        self.assertEqual(main.maxrects_pack([(100, 40)], 0, 0, 50, 120, False), {})

    def test_pieces_that_do_not_fit_are_left_out(self):
        placed = main.maxrects_pack([(30, 30)] * 10, 0, 0, 70, 70)
        self.assertEqual(len(placed), 4)


class PlanningTests(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def pieces(self, cfg):
        return main.make_pieces(cfg, cfg.wall_material, cfg.roof_material)

    def all_items(self, pages):
        return [p.item for page in pages for p in page.placements]

    def test_one_door_per_house(self):
        for houses in (1, 2, 3):
            cfg = make_cfg(self.tmp, houses=houses, mix_pieces=True)
            items = self.all_items(main.plan_pages(cfg, self.pieces(cfg)))
            door_walls = [i for i in items if i.piece.has_door]
            self.assertEqual(len(door_walls), 2 * houses)
            self.assertEqual(sum(i.door for i in door_walls), houses)

    def test_every_door_when_option_is_off(self):
        cfg = make_cfg(self.tmp, houses=2, one_door_per_house=False)
        items = self.all_items(main.plan_pages(cfg, self.pieces(cfg)))
        self.assertTrue(all(i.door for i in items if i.piece.has_door))

    def test_pieces_per_house(self):
        cfg = make_cfg(self.tmp, houses=3, mix_pieces=True)
        items = self.all_items(main.plan_pages(cfg, self.pieces(cfg)))
        counts = Counter(i.piece.name for i in items)
        self.assertEqual(counts, {"short wall": 6, "long wall": 6, "roof": 3})

    def test_joint_letters_come_in_pairs_per_house(self):
        cfg = make_cfg(self.tmp, houses=2, mix_pieces=True)
        items = self.all_items(main.plan_pages(cfg, self.pieces(cfg)))
        letters = Counter(text for i in items if i.labels for text in i.labels)
        self.assertEqual(len(letters), 8)           # 4 letters x 2 houses
        self.assertTrue(all(n == 2 for n in letters.values()))
        self.assertIn("1A", letters)
        self.assertIn("2D", letters)

    def test_single_house_has_plain_letters(self):
        cfg = make_cfg(self.tmp, houses=1)
        items = self.all_items(main.plan_pages(cfg, self.pieces(cfg)))
        letters = {text for i in items if i.labels for text in i.labels}
        self.assertEqual(letters, {"A", "B", "C", "D"})

    def test_labels_can_be_turned_off(self):
        cfg = make_cfg(self.tmp, houses=1, joint_labels=False)
        items = self.all_items(main.plan_pages(cfg, self.pieces(cfg)))
        self.assertTrue(all(i.labels is None for i in items))

    def test_fill_mode_uses_whole_pairs_of_walls(self):
        cfg = make_cfg(self.tmp)
        for piece in self.pieces(cfg):
            if piece.per_house == 2:
                self.assertEqual(main.max_copies(cfg, piece) % 2, 0)

    def test_pieces_stay_inside_the_page(self):
        cfg = make_cfg(self.tmp, houses=3, mix_pieces=True, paper="Letter")
        for page in main.plan_pages(cfg, self.pieces(cfg)):
            pw, ph = page.size
            for p in page.placements:
                w, h = p.item.piece.width, p.item.piece.height
                if p.rotated:
                    w, h = h, w
                self.assertGreaterEqual(p.x, -1e-6)
                self.assertGreaterEqual(p.y, -1e-6)
                self.assertLessEqual(p.x + w, pw + 1e-6)
                self.assertLessEqual(p.y + h, ph + 1e-6)

    def test_oversized_piece_gets_its_own_page(self):
        cfg = make_cfg(self.tmp, width_cm=50, length_cm=60, houses=1)
        pages = main.plan_pages(cfg, self.pieces(cfg))
        self.assertEqual(len(self.all_items(pages)), 5)


class WindowLayoutTests(unittest.TestCase):

    WIDTHS = [2.5 * n for n in range(1, 13)]        # 1 to 12 squares

    def extents(self, cfg, width_cm, door_layout, door_present=True):
        """(kind, left edge, right edge) of every opening, in points."""
        out = []
        for kind, off in main.opening_positions(cfg, width_cm, door_layout,
                                                door_present):
            half = (main.door_width(cfg, width_cm) if kind == "door"
                    else main.meters(cfg, cfg.window_width_m)) / 2
            out.append((kind, off - half, off + half))
        return sorted(out, key=lambda e: e[1])

    def test_openings_never_overlap_and_stay_inside_the_wall(self):
        cfg = Config()
        for width in self.WIDTHS:
            for door_layout in (True, False):
                items = self.extents(cfg, width, door_layout)
                wall = width * cm / 2
                for kind, left, right in items:
                    self.assertGreaterEqual(left, -wall - 1e-6, width)
                    self.assertLessEqual(right, wall + 1e-6, width)
                for a, b in zip(items, items[1:]):
                    self.assertLess(a[2], b[1], (width, door_layout))

    def test_layout_is_symmetric_with_an_opening_in_the_centre(self):
        cfg = Config()
        for width in self.WIDTHS:
            for door_layout in (True, False):
                offsets = [o for _, o in main.opening_positions(
                    cfg, width, door_layout, True)]
                self.assertIn(0.0, [round(o, 6) for o in offsets])
                self.assertEqual(sorted(round(o, 6) for o in offsets),
                                 sorted(round(-o, 6) for o in offsets))

    def test_wall_with_and_without_door_have_the_same_number_of_openings(self):
        cfg = Config()
        for width in self.WIDTHS:
            self.assertEqual(
                len(main.opening_positions(cfg, width, True, True)),
                len(main.opening_positions(cfg, width, False, True)), width)

    def test_longer_walls_never_get_fewer_windows(self):
        cfg = Config()
        counts = [len(main.opening_positions(cfg, w, False, True))
                  for w in self.WIDTHS]
        self.assertEqual(counts, sorted(counts))
        self.assertGreater(counts[-1], counts[0])

    def test_default_house_sides_are_consistent(self):
        cfg = Config()
        for door_layout in (True, False):
            short = len(main.opening_positions(cfg, cfg.width_cm, door_layout, True))
            long_ = len(main.opening_positions(cfg, cfg.length_cm, door_layout, True))
            self.assertGreaterEqual(long_, short)

    def test_the_door_is_only_in_the_centre(self):
        cfg = Config()
        positions = main.opening_positions(cfg, 12.5, True, True)
        doors = [(k, o) for k, o in positions if k == "door"]
        self.assertEqual(len(doors), 1)
        self.assertEqual(doors[0][1], 0.0)
        self.assertEqual([k for k, _ in main.opening_positions(
            cfg, 12.5, True, False)].count("door"), 0)

    def test_spacing_option_changes_the_number_of_windows(self):
        dense = len(main.opening_positions(
            Config(window_spacing_cells=1.0), 15.0, False, True))
        sparse = len(main.opening_positions(
            Config(window_spacing_cells=3.0), 15.0, False, True))
        self.assertGreater(dense, sparse)

    def test_spacing_must_be_positive(self):
        with self.assertRaises(ValueError):
            main.validate(Config(window_spacing_cells=0))


class FloorTests(unittest.TestCase):

    def test_one_floor_every_five_cm(self):
        cfg = Config()
        expected = {2.5: 1, 5.0: 1, 7.5: 1, 10.0: 2, 12.5: 2, 15.0: 3}
        for height, floors in expected.items():
            self.assertEqual(main.floors_for(cfg, height), floors, height)

    def test_floor_height_is_configurable(self):
        self.assertEqual(main.floors_for(Config(floor_height_cm=2.5), 10), 4)

    def test_upper_floor_has_a_window_where_the_door_is(self):
        cfg = Config()
        openings = main.openings_for(cfg, 12.5, 10.0, True, True)
        ground = [(k, o) for k, o, f in openings if f == 0]
        upper = [(k, o) for k, o, f in openings if f == 1]
        self.assertIn(("door", 0), [(k, round(o)) for k, o in ground])
        self.assertTrue(all(kind == "window" for kind, _ in upper))
        # Same columns as the ground floor
        self.assertEqual(sorted(round(o) for _, o in upper),
                         sorted(round(o) for _, o in ground))

    def test_single_floor_wall_is_unchanged(self):
        cfg = Config()
        openings = main.openings_for(cfg, 12.5, 7.5, True, True)
        self.assertTrue(all(floor == 0 for _, _, floor in openings))

    def test_wall_without_door_repeats_its_windows(self):
        cfg = Config()
        openings = main.openings_for(cfg, 12.5, 15.0, False, True)
        for floor in (0, 1, 2):
            self.assertEqual(
                sum(1 for _, _, f in openings if f == floor), 3)

    def test_floor_height_must_be_positive(self):
        with self.assertRaises(ValueError):
            main.validate(Config(floor_height_cm=0))

    def test_tall_house_builds(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("builtins.print"):
            files = main.run(make_cfg(tmp, height_cm=10.0,
                                      textures_enabled=True))
            self.assertEqual(len(files), 4)


class CommandLineTests(unittest.TestCase):

    def test_defaults_need_no_options(self):
        self.assertEqual(main.config_to_args(Config()), [])

    def test_only_changed_settings_are_listed(self):
        cfg = Config(houses=3, wall_material="stone", textures_enabled=True,
                     one_door_per_house=False, width_cm=10.0)
        args = main.config_to_args(cfg)
        self.assertEqual(
            args, ["--width-cm", "10.0", "--textures-enabled",
                   "--wall-material", "stone", "--no-one-door-per-house",
                   "--houses", "3"])

    def test_the_command_rebuilds_the_same_settings(self):
        cfg = Config(houses=2, mix_pieces=True, paper="Letter", height_cm=10.0,
                     roof_material="tiles", calibration_ruler=False,
                     base_name="my house")
        parsed = main.build_parser().parse_args(main.config_to_args(cfg))
        overrides = {k: v for k, v in vars(parsed).items()
                     if v is not None and k != "gui"}
        self.assertEqual(Config(**overrides), cfg)

    def test_every_setting_belongs_to_a_tab(self):
        for f in main.cli_fields():
            self.assertTrue(f.metadata.get("group"), f.name)

    def test_no_options_opens_the_window(self):
        with mock.patch.object(main, "launch_window", return_value=0) as launch:
            self.assertEqual(main.main([]), 0)
        launch.assert_called_once_with({})

    def test_options_fill_the_window_in_with_gui_flag(self):
        with mock.patch.object(main, "launch_window", return_value=0) as launch:
            main.main(["--gui", "--houses", "2", "--paper", "Letter"])
        launch.assert_called_once_with({"houses": 2, "paper": "Letter"})

    def test_options_alone_generate_without_a_window(self):
        with mock.patch.object(main, "launch_window") as launch, \
                tempfile.TemporaryDirectory() as tmp, \
                mock.patch("builtins.print"):
            self.assertEqual(main.main(["--output-dir", tmp]), 0)
        launch.assert_not_called()

    def test_no_gui_generates_with_the_defaults(self):
        with mock.patch.object(main, "launch_window") as launch, \
                mock.patch.object(main, "run") as run:
            self.assertEqual(main.main(["--no-gui"]), 0)
        launch.assert_not_called()
        run.assert_called_once_with(Config())


class SettingsWarningTests(unittest.TestCase):

    def test_mixing_without_houses_is_reported(self):
        warnings = main.check_settings(Config(mix_pieces=True))
        self.assertEqual(len(warnings), 1)
        self.assertIn("houses", warnings[0])
        self.assertEqual(main.check_settings(Config(mix_pieces=True, houses=2)), [])

    def test_all_variants_without_textures_is_reported(self):
        self.assertEqual(len(main.check_settings(
            Config(generate_all_variants=True))), 1)
        self.assertEqual(main.check_settings(
            Config(generate_all_variants=True, textures_enabled=True)), [])

    def test_the_warning_is_printed_when_running(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("builtins.print") as fake_print:
            main.run(make_cfg(tmp, mix_pieces=True))
        printed = " ".join(str(c.args[0]) for c in fake_print.call_args_list if c.args)
        self.assertIn("mix_pieces has no effect", printed)


class ColourTests(unittest.TestCase):

    def test_marker_stays_red_on_white(self):
        red = (0.85, 0.10, 0.10)
        self.assertEqual(main.readable_on((1, 1, 1), red), red)

    def test_marker_changes_on_red_brick(self):
        red = (0.85, 0.10, 0.10)
        brick = main.WALL_PALETTES["brick"]["base"]
        self.assertNotEqual(main.readable_on(brick, red), red)

    def test_contrast_ratio_extremes(self):
        self.assertAlmostEqual(main.contrast_ratio((0, 0, 0), (1, 1, 1)), 21)


class ValidationTests(unittest.TestCase):

    def test_bad_material_lists_the_options(self):
        with self.assertRaises(ValueError) as error:
            main.validate(Config(wall_material="marble"))
        self.assertIn("brick", str(error.exception))

    def test_bad_values(self):
        for bad in (Config(door_on="top"), Config(paper="A3"),
                    Config(houses=0), Config(width_cm=-1)):
            with self.assertRaises(ValueError):
                main.validate(bad)

    def test_defaults_are_valid(self):
        main.validate(Config())

    def test_dimension_warning(self):
        self.assertEqual(main.check_dimensions(Config()), [])
        warnings = main.check_dimensions(Config(width_cm=7))
        self.assertEqual(len(warnings), 1)
        self.assertIn("width_cm", warnings[0])


class OutputTests(unittest.TestCase):

    def run_quiet(self, cfg):
        with mock.patch("builtins.print"):
            return main.run(cfg)

    def test_whole_house_writes_four_pdfs(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self.run_quiet(make_cfg(tmp))
            self.assertEqual(
                sorted(f.name for f in files),
                ["house_DnD_complete.pdf", "house_DnD_long_wall.pdf",
                 "house_DnD_roof.pdf", "house_DnD_short_wall.pdf"])
            for f in files:
                self.assertTrue(f.read_bytes().startswith(b"%PDF"))

    def test_same_settings_give_identical_files(self):
        with tempfile.TemporaryDirectory() as a, \
                tempfile.TemporaryDirectory() as b:
            kwargs = dict(textures_enabled=True, wall_material="stone",
                          roof_material="thatch", houses=2)
            for tmp in (a, b):
                self.run_quiet(make_cfg(tmp, **kwargs))
            for name in ("house_DnD_complete.pdf", "house_DnD_roof.pdf"):
                self.assertEqual((Path(a) / name).read_bytes(),
                                 (Path(b) / name).read_bytes())

    def test_reusing_textures_makes_the_file_smaller(self):
        with tempfile.TemporaryDirectory() as a, \
                tempfile.TemporaryDirectory() as b:
            kwargs = dict(textures_enabled=True, wall_material="brick",
                          roof_material="tiles", houses=2)
            self.run_quiet(make_cfg(a, reuse_textures=True, **kwargs))
            self.run_quiet(make_cfg(b, reuse_textures=False, **kwargs))
            small = (Path(a) / "house_DnD_complete.pdf").stat().st_size
            big = (Path(b) / "house_DnD_complete.pdf").stat().st_size
            self.assertLess(small, big)

    def test_single_wall_mode(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self.run_quiet(make_cfg(tmp, generate_full_house=False))
            self.assertEqual([f.name for f in files], ["house_DnD.pdf"])

    def test_all_variants(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self.run_quiet(make_cfg(
                tmp, textures_enabled=True, generate_all_variants=True))
            self.assertEqual(len(files), 9 * 4)

    def test_locked_file_gives_a_clear_error(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(canvas.Canvas, "save",
                                   side_effect=PermissionError):
                with self.assertRaises(main.OutputError) as error:
                    self.run_quiet(make_cfg(tmp))
            self.assertIn("close", str(error.exception).lower())

    def test_command_line_overrides(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("builtins.print"):
            code = main.main(["--output-dir", tmp, "--houses", "2",
                              "--paper", "Letter", "--no-calibration-ruler"])
            self.assertEqual(code, 0)

    def test_command_line_reports_invalid_settings(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch("builtins.print"):
            self.assertEqual(main.main(["--output-dir", tmp, "--houses", "0"]), 2)


if __name__ == "__main__":
    unittest.main()