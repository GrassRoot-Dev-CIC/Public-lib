"""
Python wrapper for Costing Engine database.

Provides strongly-typed models and easy-to-use API for generating cost estimates
from the SQL-based costing engine.
"""

from .client import CostingClient
from .models import (
    Template,
    TemplateComponent,
    EstimateParameters,
    EstimateLine,
    CostEstimate,
)

__all__ = [
    'CostingClient',
    'Template',
    'TemplateComponent',
    'EstimateParameters',
    'EstimateLine',
    'CostEstimate',
]

__version__ = '1.0.0'
