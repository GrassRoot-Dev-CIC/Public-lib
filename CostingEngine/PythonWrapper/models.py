"""
Data models for costing engine.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List
from decimal import Decimal


@dataclass
class Template:
    """
    Represents a cost estimation template.
    
    Attributes:
        template_id: Unique identifier.
        template_code: Short code (e.g., "DC_RACK_42U_STD").
        template_name: Human-readable name.
        description: Detailed description of what this template covers.
        project_type: Type of project (e.g., "DataCenter", "Airport").
        is_active: Whether template is currently active.
        created_date: When template was created.
        modified_date: When template was last modified.
    """
    template_id: int
    template_code: str
    template_name: str
    description: Optional[str] = None
    project_type: Optional[str] = None
    is_active: bool = True
    created_date: Optional[datetime] = None
    modified_date: Optional[datetime] = None


@dataclass
class TemplateComponent:
    """
    Represents a component within a template.
    
    Attributes:
        template_id: ID of parent template.
        component_code: Short code for component.
        component_name: Human-readable component name.
        category: Component category (e.g., "Equipment", "Cabling", "Labor").
        unit_cost_usd: Cost per unit.
        quantity_factor: Multiplier applied to parameters.
        quantity_type: How quantity is calculated ("PerSquareMeter", "PerRack", "PerFloor", "Fixed").
        unit_of_measure: Unit (e.g., "ea", "m", "hr").
        notes: Additional information about this component.
    """
    template_id: int
    component_code: str
    component_name: str
    category: str
    unit_cost_usd: Decimal
    quantity_factor: Decimal
    quantity_type: str
    unit_of_measure: Optional[str] = None
    notes: Optional[str] = None


@dataclass
class EstimateParameters:
    """
    Input parameters for generating a cost estimate.
    
    Attributes:
        template_id: ID of template to use.
        floor_area_m2: Floor area in square meters.
        num_racks: Number of equipment racks.
        num_floors: Number of floors.
        project_name: Optional project name for metadata.
    """
    template_id: int
    floor_area_m2: Decimal = Decimal('0')
    num_racks: int = 0
    num_floors: int = 1
    project_name: Optional[str] = None


@dataclass
class EstimateLine:
    """
    Single line item in a cost estimate.
    
    Attributes:
        component_code: Component identifier.
        component_name: Component name.
        category: Component category.
        quantity_type: How quantity was calculated.
        unit_of_measure: Unit of measure.
        estimated_quantity: Computed quantity based on parameters.
        unit_cost_usd: Cost per unit.
        line_cost_usd: Total cost for this line (quantity × unit cost).
        notes: Additional information.
        template_code: Code of template used.
        template_name: Name of template used.
    """
    component_code: str
    component_name: str
    category: str
    quantity_type: str
    unit_of_measure: Optional[str]
    estimated_quantity: Decimal
    unit_cost_usd: Decimal
    line_cost_usd: Decimal
    notes: Optional[str] = None
    template_code: Optional[str] = None
    template_name: Optional[str] = None


@dataclass
class CostEstimate:
    """
    Complete cost estimate result.
    
    Attributes:
        lines: List of cost estimate line items.
        parameters: Input parameters used to generate estimate.
        cost_date: When estimate was generated.
        total_cost_usd: Sum of all line costs.
        summary_by_category: Dictionary mapping category to total cost.
    """
    lines: List[EstimateLine]
    parameters: EstimateParameters
    cost_date: datetime
    total_cost_usd: Decimal = field(init=False)
    summary_by_category: dict = field(init=False)

    def __post_init__(self):
        """Calculate derived fields."""
        total = sum(line.line_cost_usd for line in self.lines)
        object.__setattr__(self, 'total_cost_usd', total if self.lines else Decimal('0'))
        
        summary = {}
        for line in self.lines:
            if line.category not in summary:
                summary[line.category] = Decimal('0')
            summary[line.category] += line.line_cost_usd
        object.__setattr__(self, 'summary_by_category', summary)








