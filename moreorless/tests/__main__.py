import unittest

from .click import ColorTest  # noqa: F401
from .combined import DivergentDiffTest, HunkTest, LineTest, MergeDiffTest  # noqa: F401
from .general import ParityTest  # noqa: F401
from .patch import PatchTest  # noqa: F401

unittest.main()
