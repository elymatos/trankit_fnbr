"""ASGI entry point for the self-contained Trankit FNBr service."""

from trankit_fnbr.api import create_app
from trankit_fnbr.runtime import LazyConfiguredPipeline


app = create_app(LazyConfiguredPipeline())
