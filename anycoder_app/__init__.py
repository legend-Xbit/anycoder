"""
AnyCoder - AI Code Generator Package
Modular structure for better code organization and maintainability.
"""

__version__ = "1.0.0"

from . import config
from . import prompts
from . import docs_manager
from . import models
from . import parsers
from . import deploy
from . import themes
from . import ui

__all__ = [
    "config",
    "prompts", 
    "docs_manager",
    "models",
    "parsers",
    "deploy",
    "themes",
    "ui",
]

