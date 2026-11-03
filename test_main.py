"""Tests for main.py. Run with:  python -m unittest -v"""

import contextlib
import io
import math
import random
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
                                      textures_enabled=True,
                                      complete_only=False))
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


class CompleteOnlyTests(unittest.TestCase):

    def test_it_is_on_by_default(self):
        self.assertTrue(Config().complete_only)

    def test_the_command_can_switch_it_off(self):
        self.assertEqual(main.config_to_args(Config(complete_only=False)),
                         ["--no-complete-only"])
        parsed = main.build_parser().parse_args(["--no-complete-only"])
        self.assertFalse(parsed.complete_only)


class LanguageTests(unittest.TestCase):

    def run_text(self, **overrides):
        out = io.StringIO()
        with tempfile.TemporaryDirectory() as tmp, \
                contextlib.redirect_stdout(out):
            main.run(make_cfg(tmp, **overrides))
        return out.getvalue()

    def test_english_is_the_default(self):
        text = self.run_text()
        self.assertIn("PDF created", text)
        self.assertIn("Roof:", text)
        self.assertIn("Door on the short side", text)

    def test_the_messages_come_out_in_italian(self):
        text = self.run_text(language="it", houses=2)
        self.assertIn("PDF creato", text)
        self.assertIn("pagina 1:", text)
        self.assertIn("Tetto:", text)
        self.assertIn("Porta sul lato corto", text)
        self.assertIn("lato corto", text)
        for english in ("PDF created", "Roof:", "Door on the", "page 1"):
            self.assertNotIn(english, text)

    def test_warnings_are_translated(self):
        warnings = main.check_settings(Config(mix_pieces=True, language="it"))
        self.assertIn("ATTENZIONE", warnings[0])
        warnings = main.check_dimensions(Config(width_cm=7, language="it"))
        self.assertIn("caselle", warnings[0])

    def test_errors_are_translated(self):
        with self.assertRaises(ValueError) as error:
            main.validate(Config(language="it", wall_material="granite"))
        self.assertIn("deve essere", str(error.exception))
        self.assertIn("brick", str(error.exception))

    def test_an_unknown_language_is_refused(self):
        with self.assertRaises(ValueError):
            main.validate(Config(language="fr"))

    def test_locked_file_message_in_italian(self):
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(canvas.Canvas, "save",
                                   side_effect=PermissionError):
                with self.assertRaises(main.OutputError) as error:
                    with contextlib.redirect_stdout(io.StringIO()):
                        main.run(make_cfg(tmp, language="it"))
            self.assertIn("chiudilo", str(error.exception))

    def test_the_language_option(self):
        parsed = main.build_parser().parse_args(["--language", "it"])
        self.assertEqual(parsed.language, "it")
        self.assertEqual(main.config_to_args(Config(language="it")),
                         ["--language", "it"])

    def test_the_ruler_caption_follows_the_language(self):
        with tempfile.TemporaryDirectory() as a, \
                tempfile.TemporaryDirectory() as b:
            with contextlib.redirect_stdout(io.StringIO()):
                main.run(make_cfg(a, language="en"))
                main.run(make_cfg(b, language="it"))
            self.assertNotEqual((Path(a) / "house_DnD_complete.pdf").read_bytes(),
                                (Path(b) / "house_DnD_complete.pdf").read_bytes())


class RoofWindowTests(unittest.TestCase):

    def cfg(self, **kw):
        values = dict(roof_windows=True, width_cm=7.5, length_cm=12.5,
                      roof_height_cm=2.0)
        values.update(kw)
        return Config(**values)

    def test_where_the_windows_go(self):
        expected = {2: [], 3: [(1, 1)], 4: [(1, 2)], 5: [(1, 1), (3, 1)],
                    6: [(1, 1), (4, 1)], 7: [(1, 1), (3, 1), (5, 1)],
                    8: [(1, 1), (3, 2), (6, 1)]}
        for squares, runs in expected.items():
            self.assertEqual(main.roof_window_runs(squares), runs, squares)

    def test_windows_are_symmetric_and_leave_the_ends_free(self):
        for squares in range(3, 25):
            row = [False] * squares
            for first, count in main.roof_window_runs(squares):
                for k in range(count):
                    row[first + k] = True
            self.assertEqual(row, row[::-1], squares)
            self.assertFalse(row[0] or row[-1], squares)
            self.assertTrue(any(row), squares)

    def test_the_sizes_follow_the_right_triangle(self):
        plan = main.roof_window_plan(self.cfg())
        c = 2.6                                          # a square + 1 mm
        half = 3.75
        self.assertAlmostEqual(plan.hypotenuse_cm, c * 4.25 / half)
        self.assertAlmostEqual(plan.wall_height_cm,
                               math.sqrt(plan.hypotenuse_cm ** 2 - c ** 2))
        self.assertAlmostEqual(plan.wall_height_cm, c * 2.0 / half)

    def test_the_window_is_halfway_on_the_slope(self):
        plan = main.roof_window_plan(self.cfg())
        g = (3.75 - 2.6) / 2                       # ridge to the fold, flat
        self.assertAlmostEqual(plan.gap_cm, 2 * g)
        self.assertAlmostEqual(plan.hinge_cm, g / (3.75 / 4.25))

    def test_the_strip_covers_two_windows_and_the_roof_between_them(self):
        plan = main.roof_window_plan(self.cfg())
        self.assertAlmostEqual(plan.ring_across_cm, 2 * 2.6 + plan.gap_cm)

    def test_the_position_moves_the_windows(self):
        at_ridge = main.roof_window_plan(self.cfg(roof_window_position=0.0))
        halfway = main.roof_window_plan(self.cfg())
        at_eaves = main.roof_window_plan(self.cfg(roof_window_position=1.0))
        self.assertAlmostEqual(at_ridge.gap_cm, 0)
        self.assertAlmostEqual(at_ridge.ring_across_cm, 5.2)
        self.assertGreater(halfway.gap_cm, at_ridge.gap_cm)
        self.assertGreater(at_eaves.gap_cm, halfway.gap_cm)
        self.assertAlmostEqual(at_eaves.ring_across_cm, 7.5)
        # the height of the strip does not depend on the position
        self.assertAlmostEqual(at_ridge.wall_height_cm,
                               at_eaves.wall_height_cm)

    def test_the_position_is_kept_between_0_and_1(self):
        low = main.roof_window_plan(self.cfg(roof_window_position=-3))
        high = main.roof_window_plan(self.cfg(roof_window_position=9))
        self.assertAlmostEqual(low.gap_cm, 0)
        self.assertAlmostEqual(high.ring_across_cm, 7.5)

    def test_holes_are_symmetric_on_the_roof_sheet(self):
        plan = main.roof_window_plan(self.cfg())
        sheet = 12.5 + 2 * 1.0
        for (a0, a1), (b0, b1) in zip(plan.holes, plan.holes[::-1]):
            self.assertAlmostEqual(a0 + b1, sheet)
            self.assertAlmostEqual(a1 + b0, sheet)

    def test_why_there_are_no_windows(self):
        self.assertEqual(main.roof_window_plan(Config()).reason, "off")
        self.assertEqual(main.roof_window_plan(
            self.cfg(length_cm=5.0)).reason, "short")
        self.assertEqual(main.roof_window_plan(
            self.cfg(width_cm=5.0)).reason, "narrow")
        self.assertEqual(main.roof_window_plan(
            self.cfg(house_shape="L")).reason, "shape")
        self.assertEqual(main.roof_window_plan(
            self.cfg(roof_type="flat")).reason, "shape")

    def test_a_warning_says_why(self):
        for kw, word in ((dict(length_cm=5.0), "3 squares"),
                         (dict(width_cm=5.0), "narrow"),
                         (dict(house_shape="L"), "rectangular")):
            warnings = main.check_settings(self.cfg(**kw))
            self.assertEqual(len(warnings), 1, kw)
            self.assertIn(word, warnings[0])
        italian = main.check_settings(self.cfg(length_cm=5.0, language="it"))
        self.assertIn("almeno 3 caselle", italian[0])
        self.assertEqual(main.check_settings(self.cfg()), [])

    def test_one_strip_for_every_window(self):
        cases = {5.0: 0, 7.5: 1, 10.0: 1, 12.5: 2, 15.0: 2, 17.5: 3}
        for length, strips in cases.items():
            pieces = main.make_pieces(self.cfg(length_cm=length), "stone",
                                      "tiles")
            kinds = [p for p in pieces if p.role == "strip"]
            self.assertEqual(sum(p.per_house for p in kinds), strips, length)

    def test_windows_of_the_same_width_share_a_piece(self):
        pieces = main.make_pieces(self.cfg(length_cm=20.0), "stone", "tiles")
        kinds = {p.name: p.per_house for p in pieces if p.role == "strip"}
        self.assertEqual(kinds, {"roof strip 1": 2, "roof strip 2": 1})

    def test_the_size_of_the_strip(self):
        plan = main.roof_window_plan(self.cfg())
        strip = [p for p in main.make_pieces(self.cfg(), "stone", "tiles")
                 if p.role == "strip"][0]
        along, across = 2.5, plan.ring_across_cm
        self.assertAlmostEqual(strip.width / cm,
                               2 * along + 2 * across + 0.5)
        self.assertAlmostEqual(strip.height / cm, plan.wall_height_cm)

    def test_the_roof_sheet_keeps_its_size_but_not_its_look(self):
        a = main.make_pieces(self.cfg(roof_windows=False), "stone", "tiles")[2]
        b = main.make_pieces(self.cfg(), "stone", "tiles")[2]
        self.assertAlmostEqual(a.width, b.width)
        self.assertAlmostEqual(a.height, b.height)
        with tempfile.TemporaryDirectory() as tmp, \
                contextlib.redirect_stdout(io.StringIO()):
            main.run(make_cfg(tmp, roof_windows=True, length_cm=12.5))
            with_windows = (Path(tmp) / "house_DnD_complete.pdf").read_bytes()
            main.run(make_cfg(tmp, roof_windows=False, length_cm=12.5))
            without = (Path(tmp) / "house_DnD_complete.pdf").read_bytes()
        self.assertNotEqual(with_windows, without)

    def test_the_strips_are_in_the_pages(self):
        cfg = self.cfg(houses=2, mix_pieces=True)
        pieces = main.make_pieces(cfg, "stone", "tiles")
        pages = main.plan_pages(cfg, pieces)
        strips = sum(1 for page in pages for p in page.placements
                     if p.item.piece.role == "strip")
        self.assertEqual(strips, 2 * 2)

    def test_a_window_is_drawn_on_the_two_walls_that_face_outside(self):
        calls = []
        real = main.window
        with mock.patch.object(main, "window",
                               side_effect=lambda *a, **k: calls.append((a, k))
                               or real(*a, **k)):
            strip = [p for p in main.make_pieces(
                self.cfg(textures_enabled=True), "stone", "tiles")
                if p.role == "strip"][0]
            strip.body(canvas.Canvas(io.BytesIO()))
        self.assertEqual(len(calls), 2)
        for args, kwargs in calls:
            width, height = args[3], args[4]
            self.assertGreater(width, height)            # longer than tall
            self.assertGreaterEqual(kwargs["panes_x"], 2)

    def test_no_window_picture_when_windows_are_off(self):
        calls = []
        with mock.patch.object(main, "window",
                               side_effect=lambda *a, **k: calls.append(1)):
            strip = [p for p in main.make_pieces(
                self.cfg(textures_enabled=True, door_and_windows=False),
                "stone", "tiles") if p.role == "strip"][0]
            strip.body(canvas.Canvas(io.BytesIO()))
        self.assertEqual(calls, [])


class ShapeTests(unittest.TestCase):

    def test_offset_of_a_rectangle(self):
        self.assertEqual(
            main.offset_polygon([(0, 0), (10, 0), (10, 5), (0, 5)], 1),
            [(-1, -1), (11, -1), (11, 6), (-1, 6)])

    def test_offset_of_an_l(self):
        outline = main.offset_polygon(
            [(0, 0), (10, 0), (10, 5), (5, 5), (5, 8), (0, 8)], 1)
        self.assertEqual(outline, [(-1, -1), (11, -1), (11, 6), (6, 6),
                                   (6, 9), (-1, 9)])

    def l_pieces(self, **kw):
        values = dict(house_shape="L", width_cm=7.5, length_cm=12.5,
                      wing_length_cm=10.0, height_cm=5.0, roof_height_cm=2.0)
        values.update(kw)
        cfg = Config(**values)
        return cfg, main.make_pieces(cfg, "stone", "tiles")

    def test_an_l_has_six_walls_and_two_roofs(self):
        cfg, pieces = self.l_pieces()
        walls = [p for p in pieces if p.role == "wall"]
        roofs = [p for p in pieces if p.role == "roof"]
        self.assertEqual(len(walls), 6)
        self.assertEqual([p.suffix for p in roofs], [" A", " B"])

    def test_the_walls_have_the_lengths_of_the_outline(self):
        cfg, pieces = self.l_pieces()
        walls = [p for p in pieces if p.role == "wall"]
        lengths = [12.5, 7.5, 5.0, 2.5, 7.5, 10.0]
        for piece, length in zip(walls, lengths):
            self.assertAlmostEqual(piece.width / cm, length + 2.0)

    def test_the_two_gables_have_a_triangle(self):
        cfg, pieces = self.l_pieces()
        walls = [p for p in pieces if p.role == "wall"]
        tall = [p for p in walls if p.height / cm > 7.5]
        self.assertEqual([p.suffix for p in tall], [" 2", " 5"])

    def test_every_corner_letter_is_on_two_walls(self):
        cfg, pieces = self.l_pieces()
        letters = [letter for p in pieces if p.role == "wall"
                   for letter in p.joints]
        self.assertEqual(sorted(letters), sorted(list("ABCDEF") * 2))

    def test_neighbouring_walls_share_a_letter(self):
        cfg, pieces = self.l_pieces()
        walls = [p for p in pieces if p.role == "wall"]
        for i, wall in enumerate(walls):
            self.assertEqual(wall.joints[1], walls[(i + 1) % 6].joints[0])

    def test_one_wall_has_the_door(self):
        for door_on, index in (("short", 1), ("long", 0)):
            cfg, pieces = self.l_pieces(door_on=door_on)
            walls = [p for p in pieces if p.role == "wall"]
            self.assertEqual([i for i, p in enumerate(walls) if p.has_door],
                             [index])

    def test_the_labels_come_from_the_walls(self):
        cfg, pieces = self.l_pieces(houses=1)
        pages = main.plan_pages(cfg, pieces)
        labels = [p.item.labels for page in pages for p in page.placements
                  if p.item.piece.role == "wall"]
        self.assertEqual(sorted(x for pair in labels for x in pair),
                         sorted(list("ABCDEF") * 2))

    def test_a_flat_l_has_a_single_roof(self):
        cfg, pieces = self.l_pieces(roof_type="flat")
        roofs = [p for p in pieces if p.role == "roof"]
        self.assertEqual(len(roofs), 1)
        walls = [p for p in pieces if p.role == "wall"]
        self.assertTrue(all(p.height / cm < 8 for p in walls))   # no gables

    def test_the_flat_roof_of_an_l_covers_the_house_and_a_margin(self):
        cfg, pieces = self.l_pieces(roof_type="flat")
        roof = [p for p in pieces if p.role == "roof"][0]
        self.assertAlmostEqual(roof.width / cm, 12.5 + 2)
        self.assertAlmostEqual(roof.height / cm, 10.0 + 2)

    def test_the_wing_roofs_have_the_length_of_their_wing(self):
        cfg, pieces = self.l_pieces()
        a, b = [p for p in pieces if p.role == "roof"]
        self.assertGreater(a.width, b.width)             # 12.5 against 10
        self.assertAlmostEqual(a.height, b.height)

    def test_an_l_makes_pdfs(self):
        for kw in (dict(), dict(roof_type="flat"),
                   dict(houses=2, mix_pieces=True)):
            with tempfile.TemporaryDirectory() as tmp, \
                    contextlib.redirect_stdout(io.StringIO()):
                files = main.run(make_cfg(
                    tmp, house_shape="L", textures_enabled=True,
                    complete_only=False, **kw))
                self.assertTrue(files[-1].name.endswith("_complete.pdf"))
                self.assertTrue(all(f.exists() for f in files), kw)

    def test_the_pieces_of_an_l_are_written_one_by_one(self):
        with tempfile.TemporaryDirectory() as tmp, \
                contextlib.redirect_stdout(io.StringIO()):
            files = main.run(make_cfg(tmp, house_shape="L",
                                      complete_only=False))
        self.assertEqual(len(files), 8 + 1)

    def test_a_wing_must_be_longer_than_the_width(self):
        for kw in (dict(length_cm=7.5), dict(wing_length_cm=7.5)):
            with self.assertRaises(ValueError):
                main.validate(Config(house_shape="L", **kw))
        main.validate(Config(house_shape="L"))
        # a short wing does not matter for a rectangle
        main.validate(Config(wing_length_cm=1.0))

    def test_wrong_shapes_are_refused(self):
        for kw in (dict(house_shape="T"), dict(roof_type="dome")):
            with self.assertRaises(ValueError):
                main.validate(Config(**kw))

    def test_the_error_is_in_the_language(self):
        with self.assertRaises(ValueError) as error:
            main.validate(Config(house_shape="L", wing_length_cm=7.5,
                                 language="it"))
        self.assertIn("più lunghe", str(error.exception))

    def test_the_wing_counts_as_a_size_in_squares(self):
        warnings = main.check_dimensions(Config(house_shape="L",
                                                wing_length_cm=9.0))
        self.assertEqual(len(warnings), 1)
        self.assertIn("wing_length_cm", warnings[0])
        self.assertEqual(main.check_dimensions(Config(wing_length_cm=9.0)), [])


class FlatRoofTests(unittest.TestCase):

    def pieces(self, **kw):
        cfg = Config(roof_type="flat", width_cm=7.5, length_cm=12.5,
                     height_cm=5.0, **kw)
        return cfg, main.make_pieces(cfg, "stone", "stone")

    def test_a_flat_roof_is_the_house_plus_a_margin(self):
        cfg, pieces = self.pieces()
        roof = pieces[2]
        self.assertAlmostEqual(roof.width / cm, 12.5 + 2 * cfg.roof_margin_cm)
        self.assertAlmostEqual(roof.height / cm, 7.5 + 2 * cfg.roof_margin_cm)

    def test_the_short_wall_has_no_gable(self):
        cfg, pieces = self.pieces()
        short = pieces[0]
        self.assertAlmostEqual(short.height / cm, 5.0 + 2)    # tabs, no triangle

    def test_the_margin_changes_the_flat_roof(self):
        cfg, pieces = self.pieces(roof_margin_cm=2.0)
        self.assertAlmostEqual(pieces[2].width / cm, 12.5 + 4)

    def test_no_roof_windows_on_a_flat_roof(self):
        cfg, pieces = self.pieces(roof_windows=True)
        self.assertEqual([p for p in pieces if p.role == "strip"], [])

    def test_the_paving_marks_every_square(self):
        c = canvas.Canvas(io.BytesIO())
        lines = []
        real_line = c.line
        c.line = lambda *a: (lines.append(a), real_line(*a))[1]
        main.paving(c, 10 * cm, 6 * cm, (1 * cm, 1 * cm), 2.5 * cm,
                    {"base": (0.5, 0.5, 0.5)}, random.Random(1))
        # lines of the joints plus two lines for each cross
        self.assertGreater(len(lines), 30)

    def test_the_flat_roof_does_not_change_with_the_roof_pitch(self):
        a = main.make_pieces(Config(roof_type="flat", roof_height_cm=2.0),
                             "stone", "stone")[2]
        b = main.make_pieces(Config(roof_type="flat", roof_height_cm=5.0),
                             "stone", "stone")[2]
        self.assertAlmostEqual(a.width, b.width)
        self.assertAlmostEqual(a.height, b.height)

    def test_it_makes_a_pdf_with_every_material(self):
        for material in main.ROOF_PALETTES:
            with tempfile.TemporaryDirectory() as tmp, \
                    contextlib.redirect_stdout(io.StringIO()):
                files = main.run(make_cfg(
                    tmp, roof_type="flat", textures_enabled=True,
                    roof_material=material))
                self.assertTrue(files[0].exists(), material)


class TabsTests(unittest.TestCase):

    def sizes(self, **kw):
        cfg = Config(width_cm=7.5, length_cm=12.5, height_cm=7.5,
                     roof_height_cm=5.0, **kw)
        short, long_, _ = main.make_pieces(cfg, "stone", "tiles")[:3]
        return ((short.width / cm, short.height / cm),
                (long_.width / cm, long_.height / cm))

    def test_tabs_are_on_by_default(self):
        self.assertTrue(Config().top_bottom_tabs)
        short, long_ = self.sizes()
        self.assertEqual(long_, (14.5, 9.5))

    def test_without_the_top_and_bottom_tabs_the_walls_are_smaller(self):
        (_, short_h), long_ = self.sizes(top_bottom_tabs=False)
        self.assertEqual(long_, (14.5, 7.5))           # only the inner part
        self.assertAlmostEqual(short_h, self.sizes()[0][1] - 1.0)

    def test_the_side_tabs_stay(self):
        (short_w, _), (long_w, _) = self.sizes(top_bottom_tabs=False)
        self.assertEqual((short_w, long_w), (9.5, 14.5))

    def test_a_flat_roof_wall_loses_both_tabs(self):
        cfg = Config(roof_type="flat", height_cm=5.0, top_bottom_tabs=False)
        short = main.make_pieces(cfg, "stone", "stone")[0]
        self.assertAlmostEqual(short.height / cm, 5.0)

    def test_it_works_with_every_shape(self):
        for kw in (dict(), dict(roof_type="flat"), dict(house_shape="L"),
                   dict(house_shape="L", roof_type="flat")):
            with tempfile.TemporaryDirectory() as tmp, \
                    contextlib.redirect_stdout(io.StringIO()):
                files = main.run(make_cfg(tmp, top_bottom_tabs=False,
                                          textures_enabled=True, **kw))
                self.assertTrue(files[0].exists(), kw)


class NewTextureTests(unittest.TestCase):

    def test_the_new_materials_exist(self):
        for name in ("marble", "ice"):
            self.assertIn(name, main.WALL_TEXTURES)
            self.assertIn(name, main.WALL_PALETTES)
        for name in ("stone", "blue_tiles"):
            self.assertIn(name, main.ROOF_TEXTURES)
            self.assertIn(name, main.ROOF_PALETTES)

    def test_every_wall_texture_draws_something(self):
        for name, draw in main.WALL_TEXTURES.items():
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, invariant=1)
            draw(c, 0, 0, 5 * cm, 3 * cm, main.WALL_PALETTES[name],
                 random.Random(1))
            c.showPage()
            c.save()
            self.assertGreater(len(buffer.getvalue()), 1500, name)

    def test_every_roof_texture_draws_something(self):
        for name, draw in main.ROOF_TEXTURES.items():
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, invariant=1)
            draw(c, 5 * cm, 3 * cm, main.ROOF_PALETTES[name],
                 random.Random(1))
            c.showPage()
            c.save()
            self.assertGreater(len(buffer.getvalue()), 1500, name)

    def test_textures_are_the_same_every_time(self):
        for name in ("marble", "ice"):
            outputs = []
            for _ in range(2):
                buffer = io.BytesIO()
                c = canvas.Canvas(buffer, invariant=1)
                main.WALL_TEXTURES[name](c, 0, 0, 5 * cm, 3 * cm,
                                         main.WALL_PALETTES[name],
                                         random.Random(5))
                c.save()
                outputs.append(buffer.getvalue())
            self.assertEqual(outputs[0], outputs[1], name)

    def test_the_materials_are_different_from_each_other(self):
        outputs = set()
        for name, draw in main.WALL_TEXTURES.items():
            buffer = io.BytesIO()
            c = canvas.Canvas(buffer, invariant=1)
            draw(c, 0, 0, 5 * cm, 3 * cm, main.WALL_PALETTES[name],
                 random.Random(1))
            c.save()
            outputs.add(buffer.getvalue())
        self.assertEqual(len(outputs), len(main.WALL_TEXTURES))

    def test_the_command_line_accepts_the_new_materials(self):
        parsed = main.build_parser().parse_args(
            ["--wall-material", "ice", "--roof-material", "blue_tiles"])
        self.assertEqual((parsed.wall_material, parsed.roof_material),
                         ("ice", "blue_tiles"))

    def test_the_window_picture_accepts_any_number_of_panes(self):
        for panes in (1, 2, 4, 6):
            c = canvas.Canvas(io.BytesIO())
            main.window(c, 2 * cm, 2 * cm, 3 * cm, 1 * cm, panes_x=panes)


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
            main.validate(Config(wall_material="granite"))
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

    def test_by_default_only_the_complete_pdf_is_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self.run_quiet(make_cfg(tmp))
            self.assertEqual([f.name for f in files],
                             ["house_DnD_complete.pdf"])
            self.assertEqual(len(list(Path(tmp).glob("*.pdf"))), 1)
            self.assertTrue(files[0].read_bytes().startswith(b"%PDF"))

    def test_whole_house_can_also_write_the_single_pieces(self):
        with tempfile.TemporaryDirectory() as tmp:
            files = self.run_quiet(make_cfg(tmp, complete_only=False))
            self.assertEqual(
                sorted(f.name for f in files),
                ["house_DnD_complete.pdf", "house_DnD_long_wall.pdf",
                 "house_DnD_roof.pdf", "house_DnD_short_wall.pdf"])
            for f in files:
                self.assertTrue(f.read_bytes().startswith(b"%PDF"))

    def test_the_complete_pdf_is_the_same_with_or_without_the_pieces(self):
        with tempfile.TemporaryDirectory() as a, \
                tempfile.TemporaryDirectory() as b:
            self.run_quiet(make_cfg(a, complete_only=True, houses=2))
            self.run_quiet(make_cfg(b, complete_only=False, houses=2))
            self.assertEqual((Path(a) / "house_DnD_complete.pdf").read_bytes(),
                             (Path(b) / "house_DnD_complete.pdf").read_bytes())

    def test_same_settings_give_identical_files(self):
        with tempfile.TemporaryDirectory() as a, \
                tempfile.TemporaryDirectory() as b:
            kwargs = dict(textures_enabled=True, wall_material="stone",
                          roof_material="thatch", houses=2,
                          complete_only=False)
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
            walls, roofs = len(main.WALL_PALETTES), len(main.ROOF_PALETTES)
            self.assertEqual((walls, roofs), (5, 5))
            self.assertEqual(len(files), walls * roofs)

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