"""Tests de base (M0) : environnement et outils nécessaires."""
import importlib
import shutil
import unittest


class TestEnvironnement(unittest.TestCase):
    def test_paquets(self):
        for m in ["cv2", "numpy", "onnxruntime", "PIL", "scipy"]:
            with self.subTest(paquet=m):
                importlib.import_module(m)

    def test_ffmpeg(self):
        self.assertIsNotNone(shutil.which("ffmpeg"))


if __name__ == "__main__":
    unittest.main()
