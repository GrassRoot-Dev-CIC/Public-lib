# Costing Engine

SQL-based cost estimation system for infrastructure ICT/ELV projects with optional Python wrapper.

## Innovation Highlights

- **Template Abstraction**: Architectural/engineering design patterns encoded as reusable database entities with version control
- **Parameterized Calculation**: Four quantity types (PerSquareMeter, PerRack, PerFloor, Fixed) encode domain knowledge as data, not formulas
- **Auditable Estimates**: SQL stored procedures provide reproducible calculations with explicit input/output contracts
- **Knowledge as Data**: Transformed tribal knowledge from spreadsheets into systematically reusable, reviewable templates

## Overview

This system encodes design patterns and cost estimation logic as database objects, eliminating repetitive spreadsheet-based costing for infrastructure projects.

**Key Features:**
- Template-based cost estimation (reusable design patterns)
- Parameterized BoQ (Bill of Quantities) generation
- Clear documentation of cost logic and assumptions
- Optional Python wrapper for strongly-typed access
- SQL stored procedures for reproducible calculations

## Architecture

```
CostingEngine/
├── Database/
│   ├── 01_Schema_And_StoredProcs.sql   # Tables and procedures
│   └── 02_TestData_And_Queries.sql     # Sample data and examples
└── PythonWrapper/                       # Optional Python client
    ├── __init__.py
    ├── models.py                        # Data models
    └── client.py                        # Database client (interface definitions)
```

## Database Setup

### 1. Create Database Objects

```sql
-- Run in SQL Server Management Studio or Azure Data Studio
-- Against your costing database

-- Create schema, tables, and stored procedure
\i 01_Schema_And_StoredProcs.sql

-- Load sample data
\i 02_TestData_And_Queries.sql
```

### 2. Core Tables

**costing.Template**
- Reusable design templates (e.g., "Standard Data Center Rack", "Airport Terminal ICT")
- Links to multiple components

**costing.TemplateComponent**
- Components within a template (equipment, cabling, labor)
- Unit costs and quantity factors
- Quantity types: `PerSquareMeter`, `PerRack`, `PerFloor`, `Fixed`

## Usage

### Generate Estimate (SQL)

```sql
DECLARE @CostDate DATETIME2;

EXEC costing.GenerateCostEstimate 
    @TemplateId = 1,                -- Data center rack template
    @FloorAreaM2 = 500,             -- 500 m² raised floor
    @NumRacks = 20,                 -- 20 equipment racks
    @NumFloors = 1,
    @ProjectName = 'Customer DC Phase 1',
    @CostDate = @CostDate OUTPUT;

SELECT @CostDate AS EstimateGeneratedAt;
```

**Output:**
| ComponentCode | ComponentName | EstimatedQuantity | UnitCostUSD | LineCostUSD |
|---------------|---------------|-------------------|-------------|-------------|
| RACK42U | 42U Server Rack | 20.00 | 850.00 | 17,000.00 |
| PDU_DUAL | Dual PDU | 20.00 | 420.00 | 8,400.00 |
| CABLE_CAT6A | Cat6A Cable | 4,000.00 m | 2.50 | 10,000.00 |
| ... | ... | ... | ... | ... |

### Query Templates

```sql
-- List all active templates
SELECT TemplateCode, TemplateName, ProjectType
FROM costing.Template
WHERE IsActive = 1;

-- View components for a template
SELECT ComponentCode, ComponentName, Category, UnitCostUSD
FROM costing.TemplateComponent
WHERE TemplateId = 1
ORDER BY Category;
```

### Cost Summary

```sql
-- Generate summary by category
WITH EstimateSummary AS (
    SELECT
        c.Category,
        SUM(c.UnitCostUSD * 
            CASE 
                WHEN c.QuantityType = 'PerSquareMeter' THEN c.QuantityFactor * @FloorAreaM2
                WHEN c.QuantityType = 'PerRack' THEN c.QuantityFactor * @NumRacks
                WHEN c.QuantityType = 'Fixed' THEN c.QuantityFactor
                ELSE 0
            END
        ) AS CategoryTotal
    FROM costing.TemplateComponent c
    WHERE c.TemplateId = @TemplateId
    GROUP BY c.Category
)
SELECT
    Category,
    CategoryTotal,
    PercentOfTotal = 100.0 * CategoryTotal / SUM(CategoryTotal) OVER()
FROM EstimateSummary
ORDER BY CategoryTotal DESC;
```

## Python Wrapper (Optional)

### Installation

```bash
# Install dependencies (for database connectivity)
pip install pyodbc  # or pymssql

# See client.py for interface definitions
```

### Usage (Conceptual - requires database implementation)

```python
from decimal import Decimal
from PythonWrapper import CostingClient, EstimateParameters

# Initialize client (implement connection logic in client.py)
client = CostingClient("Driver={SQL Server};Server=localhost;Database=CostingDB;...")

# Generate estimate
params = EstimateParameters(
    template_id=1,
    floor_area_m2=Decimal('500'),
    num_racks=20,
    project_name="Customer DC Expansion"
)

estimate = client.generate_estimate(params)

# Access results
print(f"Total Cost: ${estimate.total_cost_usd:,.2f}")

for category, total in estimate.summary_by_category.items():
    print(f"  {category}: ${total:,.2f}")

# Line items
for line in estimate.lines:
    print(f"{line.component_name}: {line.estimated_quantity} × ${line.unit_cost_usd} = ${line.line_cost_usd}")
```

## Cost Logic Documentation

### Quantity Calculation

The stored procedure applies different logic based on `QuantityType`:

```sql
EstimatedQuantity = CASE 
    WHEN QuantityType = 'PerSquareMeter' THEN QuantityFactor * @FloorAreaM2
    WHEN QuantityType = 'PerRack' THEN QuantityFactor * @NumRacks
    WHEN QuantityType = 'PerFloor' THEN QuantityFactor * @NumFloors
    WHEN QuantityType = 'Fixed' THEN QuantityFactor
    ELSE 0
END
```

**Example:**
- Component: Cat6A Cable
- QuantityFactor: `8.0` (meters per m²)
- QuantityType: `PerSquareMeter`
- Input: FloorAreaM2 = `500`
- Result: `8.0 × 500 = 4,000 meters`

### Assumptions

1. **Floor area** is in square meters (m²)
2. **Costs** are in USD
3. **Labor rates** are blended rates (multiple skill levels averaged)
4. **Cabling estimates** include allowance for vertical/horizontal runs and slack
5. **Equipment costs** are list prices (may require discount negotiation)

### Future Extensions

- Regional cost adjustments (exchange rates, local labor costs)
- Contingency and markup calculations
- Time-based cost escalation
- Vendor-specific pricing integration

## Creating New Templates

### 1. Insert Template

```sql
INSERT INTO costing.Template (TemplateName, TemplateCode, Description, ProjectType)
VALUES (
    'Smart Office Building Package',
    'OFFICE_SMART_STD',
    'Standard ICT package for smart office buildings',
    'Office'
);

DECLARE @NewTemplateId INT = SCOPE_IDENTITY();
```

### 2. Add Components

```sql
-- Network equipment (per floor area)
INSERT INTO costing.TemplateComponent 
(TemplateId, ComponentCode, ComponentName, Category, UnitCostUSD, QuantityFactor, QuantityType, UnitOfMeasure, Notes)
VALUES
(@NewTemplateId, 'WIFI_AP', 'WiFi Access Point', 'Network', 450.00, 0.01, 'PerSquareMeter', 'ea', '1 AP per 100 m²'),
(@NewTemplateId, 'CABLE_CAT6', 'Cat6 Cabling', 'Cabling', 1.80, 10.0, 'PerSquareMeter', 'm', '10m per m² floor area');

-- Fixed infrastructure (per floor)
INSERT INTO costing.TemplateComponent 
(TemplateId, ComponentCode, ComponentName, Category, UnitCostUSD, QuantityFactor, QuantityType, UnitOfMeasure, Notes)
VALUES
(@NewTemplateId, 'FLOOR_SWITCH', 'Floor Distribution Switch', 'Network', 3200.00, 1.0, 'PerFloor', 'ea', 'One per floor');
```

## Sample Templates Included

### 1. Standard Data Center Rack (42U)
- **Template Code:** `DC_RACK_42U_STD`
- **Components:** Racks, PDUs, patch panels, cabling, labor
- **Parameters:** Floor area (m²), rack count

### 2. Airport Terminal ICT Package
- **Template Code:** `AIRPORT_ICT_STD`
- **Components:** WiFi, networking, CCTV, fiber backbone, comms rooms
- **Parameters:** Floor area (m²), floor count

## Validation

### Test Estimate Reproducibility

```sql
-- Generate same estimate twice
DECLARE @Date1 DATETIME2, @Date2 DATETIME2;

EXEC costing.GenerateCostEstimate @TemplateId=1, @FloorAreaM2=500, @NumRacks=20, @CostDate=@Date1 OUTPUT;
EXEC costing.GenerateCostEstimate @TemplateId=1, @FloorAreaM2=500, @NumRacks=20, @CostDate=@Date2 OUTPUT;

-- Results should be identical (except timestamps)
-- This ensures cost logic is deterministic
```

### Check Component Integrity

```sql
-- Find components with zero or negative costs (data quality check)
SELECT *
FROM costing.TemplateComponent
WHERE UnitCostUSD <= 0 OR QuantityFactor < 0;

-- Should return no rows
```

## Integration Points

For production deployment, extend with:

### Database Connection (Python)

The Python client in `client.py` provides interface definitions. To implement actual database connectivity:

```python
# Example using pyodbc or pymssql:

import pyodbc

class CostingClient:
    def __init__(self, connection_string: str):
        self.connection = pyodbc.connect(connection_string)
    
    def generate_estimate(self, parameters):
        cursor = self.connection.cursor()
        cursor.execute("EXEC costing.GenerateCostEstimate ?, ?, ?, ?, ?", ...)
        # ... process results
```

### Export to Excel

```python
# Add export functionality using pandas or openpyxl:

import pandas as pd

def export_estimate_to_excel(estimate: CostEstimate, filepath: str):
    df = pd.DataFrame([
        {
            'Component': line.component_name,
            'Quantity': line.estimated_quantity,
            'Unit Cost': line.unit_cost_usd,
            'Line Cost': line.line_cost_usd,
            'Category': line.category,
        }
        for line in estimate.lines
    ])
    
    with pd.ExcelWriter(filepath) as writer:
        df.to_excel(writer, sheet_name='Estimate', index=False)
        # Add summary sheet, charts, etc.
```

### Audit Logging

```sql
-- Track who generated estimates and when

CREATE TABLE costing.EstimateAudit (
    AuditId BIGINT IDENTITY(1,1) PRIMARY KEY,
    TemplateId INT NOT NULL,
    ProjectName NVARCHAR(200),
    GeneratedBy NVARCHAR(100),  -- User ID
    GeneratedAt DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    TotalCostUSD DECIMAL(18,2),
    Parameters NVARCHAR(MAX)  -- JSON with input parameters
);

-- Modify stored procedure to log each execution
```

## License

Internal use - Dar Al-Handasah infrastructure projects.

## References

- Original prototype: Spreadsheet-based BoQ for Muscat Airport expansion
- Reused on: Abu Dhabi towers, Qatar data centers
- Innovation: Encoding design patterns as data for 50% reduction in costing effort















