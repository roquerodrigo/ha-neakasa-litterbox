"""Base coordinator entities for Neakasa Litterbox."""

from .cat_entity import NeakasaCatEntity
from .device_entity import NeakasaDeviceEntity

__all__ = [
    "NeakasaCatEntity",
    "NeakasaDeviceEntity",
]
