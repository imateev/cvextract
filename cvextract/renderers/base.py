"""
Base interface for CV renderers.

Defines the contract for pluggable CV rendering implementations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..shared import UnitOfWork


class CVRenderer(ABC):
    """
    Abstract base class for CV renderers.

    Implementations of this interface can render CV data to various output formats
    using different templates or rendering engines.
    """

    @abstractmethod
    def render(self, work: "UnitOfWork") -> "UnitOfWork":
        """
        Render CV data to an output file using the specified template.

        Args:
            work: UnitOfWork containing render configuration and paths.
                The renderer should read CV data from work.input, use
                work.config.render.template as the template path, and
                write the rendered output to work.output.

        Returns:
            UnitOfWork with rendered output populated

        Raises:
            FileNotFoundError: If the template file does not exist
            Exception: For rendering-specific errors
        """
        ...
