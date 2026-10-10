"""Tests for i18n.py: the two languages must say the same things.
Run with:  python -m unittest -v"""

import string
import unittest
from unittest import mock

import i18n
import main
from i18n import STRINGS, detect_language, has_text, tr

try:
    import gui
except ImportError:                       # tkinter is not installed
    gui = None


def placeholders(text):
    return {name for _, name, _, _ in string.Formatter().parse(text) if name}


class CompletenessTests(unittest.TestCase):

    def test_every_language_has_the_same_keys_as_english(self):
        english = set(STRINGS["en"])
        for language in i18n.LANGUAGES:
            self.assertEqual(set(STRINGS[language]), english, language)

    def test_the_same_placeholders_in_every_language(self):
        for key, text in STRINGS["en"].items():
            for language in i18n.LANGUAGES:
                self.assertEqual(placeholders(STRINGS[language][key]),
                                 placeholders(text), (language, key))

    def test_no_text_is_empty(self):
        for language in i18n.LANGUAGES:
            for key, text in STRINGS[language].items():
                self.assertTrue(text.strip(), (language, key))

    def test_every_setting_has_a_label_and_a_help(self):
        for f in main.cli_fields():
            for kind in ("label", "help"):
                for language in i18n.LANGUAGES:
                    self.assertTrue(has_text(language, f"{kind}.{f.name}"),
                                    (language, kind, f.name))

    def test_every_material_has_a_name(self):
        names = set(main.WALL_PALETTES) | set(main.ROOF_PALETTES)
        for name in names:
            for language in i18n.LANGUAGES:
                self.assertTrue(has_text(language, f"material.{name}"), name)

    def test_every_piece_and_side_has_a_name(self):
        for key in ("piece.short", "piece.long", "piece.roof", "piece.wall",
                    "side.short", "side.long", "orientation.landscape",
                    "orientation.portrait"):
            for language in i18n.LANGUAGES:
                self.assertTrue(has_text(language, key), key)

    def test_every_group_has_a_name(self):
        for f in main.cli_fields():
            self.assertTrue(has_text("en", f"group.{f.metadata['group']}"))

    @unittest.skipIf(gui is None, "tkinter is not available")
    def test_every_page_of_the_window_has_its_texts(self):
        for key, _ in gui.PAGES:
            for prefix in ("page", "title", "sub"):
                for language in i18n.LANGUAGES:
                    self.assertTrue(has_text(language, f"{prefix}.{key}"),
                                    (prefix, key))

    @unittest.skipIf(gui is None, "tkinter is not available")
    def test_every_size_in_squares_has_its_text(self):
        for name in gui.SQUARE_LINKS:
            self.assertTrue(has_text("en", f"ui.sq.{name}"), name)

    def test_the_two_languages_really_differ(self):
        different = sum(STRINGS["en"][k] != STRINGS["it"][k]
                        for k in STRINGS["en"])
        # a few texts are the same word in both (a name, "PDF"...)
        self.assertGreater(different, len(STRINGS["en"]) * 0.9)


class TranslationTests(unittest.TestCase):

    def test_text_is_filled_in(self):
        self.assertEqual(tr("en", "msg.part", count=2, name="roof"),
                         "2 × roof")
        self.assertEqual(tr("it", "ui.done", count=1, folder="x"),
                         "Fatto: 1 file PDF in x")

    def test_an_unknown_language_falls_back_to_english(self):
        self.assertEqual(tr("fr", "ui.generate"), "Generate PDFs")

    def test_an_unknown_key_is_an_error(self):
        with self.assertRaises(KeyError):
            tr("en", "does.not.exist")

    def test_repr_placeholders(self):
        self.assertIn("'x'", tr("en", "err.door_on", value="x"))


class DetectLanguageTests(unittest.TestCase):

    def detect(self, **env):
        keys = ("LC_ALL", "LC_MESSAGES", "LANGUAGE", "LANG")
        with mock.patch.dict("os.environ", {}, clear=False), \
                mock.patch.object(i18n.sys, "platform", "linux"):
            for key in keys:
                i18n.os.environ.pop(key, None)
            i18n.os.environ.update(env)
            return detect_language()

    def test_italian(self):
        self.assertEqual(self.detect(LANG="it_IT.UTF-8"), "it")
        self.assertEqual(self.detect(LANGUAGE="it:en"), "it")

    def test_everything_else_is_english(self):
        self.assertEqual(self.detect(LANG="en_US.UTF-8"), "en")
        self.assertEqual(self.detect(LANG="de_DE.UTF-8"), "en")
        self.assertEqual(self.detect(LANG="C"), "en")
        self.assertEqual(self.detect(), "en")

    def test_the_first_variable_set_wins(self):
        self.assertEqual(self.detect(LC_ALL="en_GB", LANG="it_IT"), "en")
        self.assertEqual(self.detect(LC_ALL="it_IT", LANG="en_US"), "it")


if __name__ == "__main__":
    unittest.main()
