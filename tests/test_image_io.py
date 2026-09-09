"""16-bit 灰度 PNG 读入归一化（上游 afad9f5 / tests/test_image_io.py 移植）。"""

import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from utils.io_utils import imread  # noqa: E402


class ImageIOTest(unittest.TestCase):
    def test_imread_normalizes_16_bit_grayscale_png_to_uint8_rgb(self):
        source = np.array(
            [[0, 256], [32768, 65535]],
            dtype=np.uint16,
        )
        with tempfile.TemporaryDirectory() as directory:
            image_path = Path(directory) / "gray16.png"
            Image.fromarray(source).save(image_path)

            loaded = imread(str(image_path))

        self.assertEqual(loaded.dtype, np.uint8)
        self.assertEqual(loaded.shape, (2, 2, 3))
        np.testing.assert_array_equal(
            loaded[:, :, 0],
            np.array([[0, 1], [128, 255]], dtype=np.uint8),
        )
        np.testing.assert_array_equal(loaded[:, :, 0], loaded[:, :, 1])
        np.testing.assert_array_equal(loaded[:, :, 1], loaded[:, :, 2])


if __name__ == "__main__":
    unittest.main()
