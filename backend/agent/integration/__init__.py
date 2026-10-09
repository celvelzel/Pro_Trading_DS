"""Thin cross-MAS routing; domain drivers are injected by application assembly."""
from .router import CrossMASRouter, CrossMASRequest, CrossMASResponse

__all__ = ['CrossMASRouter', 'CrossMASRequest', 'CrossMASResponse']
