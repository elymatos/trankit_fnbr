"""Repository checkout shim for the vendored Trankit package.

Editable installs normally expose ``trankit/trankit`` directly. When commands
run from this repository root, Python sees the checkout directory first; this
shim extends its package path to the actual source package.
"""

import os

__path__.append(os.path.join(os.path.dirname(__file__), "trankit"))

from .pipeline import Pipeline
from .tpipeline import TPipeline

__version__ = "1.1.2"
__all__ = ["Pipeline", "TPipeline"]
