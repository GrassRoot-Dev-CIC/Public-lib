-- =============================================
-- Costing Engine Database Schema
-- Infrastructure ICT/ELV Design Automation
-- =============================================
-- Purpose: Encode design patterns and cost estimation logic
--          for repeatable BoQ generation on infrastructure projects.
--
-- Design Pattern:
--   Templates contain component definitions with quantity factors.
--   Stored procedure generates line-item estimates from template + parameters.
--   This eliminates repetitive spreadsheet-based costing.
-- =============================================

-- Schema for organizing costing objects
IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'costing')
BEGIN
    EXEC('CREATE SCHEMA costing');
END
GO

-- =============================================
-- Table: costing.Template
-- =============================================
-- Represents a reusable design template for a project type
-- (e.g., "Data Center Rack Standard", "Airport Terminal ICT", etc.)
-- =============================================
CREATE TABLE costing.Template (
    TemplateId          INT IDENTITY(1,1) NOT NULL,
    TemplateName        NVARCHAR(200) NOT NULL,
    TemplateCode        NVARCHAR(50) NOT NULL,
    Description         NVARCHAR(MAX) NULL,
    ProjectType         NVARCHAR(100) NULL,  -- e.g., "Airport", "DataCenter", "Office"
    CreatedDate         DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    ModifiedDate        DATETIME2 NOT NULL DEFAULT GETUTCDATE(),
    IsActive            BIT NOT NULL DEFAULT 1,
    
    CONSTRAINT PK_Template PRIMARY KEY CLUSTERED (TemplateId),
    CONSTRAINT UQ_Template_Code UNIQUE (TemplateCode)
);
GO

CREATE INDEX IX_Template_ProjectType ON costing.Template(ProjectType) WHERE IsActive = 1;
GO

-- =============================================
-- Table: costing.TemplateComponent
-- =============================================
-- Defines components within a template with unit costs and quantity factors.
--
-- Quantity Factor Logic:
--   - For area-based components (cable, conduit): factor is "per m²"
--   - For discrete components (racks, servers): factor is "per unit"
--   - Procedure applies parameters (floor area, rack count, etc.) to compute final quantity.
-- =============================================
CREATE TABLE costing.TemplateComponent (
    TemplateId          INT NOT NULL,
    ComponentCode       NVARCHAR(50) NOT NULL,
    ComponentName       NVARCHAR(200) NOT NULL,
    Category            NVARCHAR(100) NULL,  -- e.g., "Cabling", "Equipment", "Labor"
    UnitCostUSD         DECIMAL(18, 2) NOT NULL,
    QuantityFactor      DECIMAL(18, 4) NOT NULL,
    QuantityType        NVARCHAR(50) NOT NULL,  -- "PerSquareMeter", "PerRack", "PerFloor", "Fixed"
    UnitOfMeasure       NVARCHAR(50) NULL,      -- "m", "ea", "hr"
    Notes               NVARCHAR(MAX) NULL,
    
    CONSTRAINT PK_TemplateComponent PRIMARY KEY CLUSTERED (TemplateId, ComponentCode),
    CONSTRAINT FK_TemplateComponent_Template FOREIGN KEY (TemplateId) 
        REFERENCES costing.Template(TemplateId) ON DELETE CASCADE,
    CONSTRAINT CK_UnitCostUSD CHECK (UnitCostUSD >= 0),
    CONSTRAINT CK_QuantityFactor CHECK (QuantityFactor >= 0)
);
GO

CREATE INDEX IX_TemplateComponent_Category ON costing.TemplateComponent(TemplateId, Category);
GO

-- =============================================
-- Stored Procedure: costing.GenerateCostEstimate
-- =============================================
-- Generates a cost estimate (BoQ line items) from a template and input parameters.
--
-- Logic:
--   1. Retrieve components for the specified template.
--   2. Apply quantity factors based on input parameters (floor area, rack count, etc.).
--   3. Calculate line costs = unit cost × computed quantity.
--   4. Return result set with component details and costs.
--
-- Assumptions (documented for reproducibility):
--   - Floor area is in square meters (m²).
--   - Rack count is discrete unit count.
--   - QuantityType determines which parameter to use:
--       * "PerSquareMeter" → multiply by FloorAreaM2
--       * "PerRack" → multiply by NumRacks
--       * "Fixed" → use QuantityFactor as-is
--   - Costs are in USD.
--
-- Future Extensions:
--   - Add labor rate parameters
--   - Support regional cost adjustments (exchange rates, local labor)
--   - Add contingency and markup calculations
-- =============================================
CREATE OR ALTER PROCEDURE costing.GenerateCostEstimate
    @TemplateId         INT,
    @FloorAreaM2        DECIMAL(18, 2) = 0,
    @NumRacks           INT = 0,
    @NumFloors          INT = 1,
    @ProjectName        NVARCHAR(200) = NULL,  -- For output metadata
    @CostDate           DATETIME2 = NULL OUTPUT  -- Return costing timestamp
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    
    -- Set output timestamp
    SET @CostDate = GETUTCDATE();
    
    -- Validate template exists and is active
    IF NOT EXISTS (SELECT 1 FROM costing.Template WHERE TemplateId = @TemplateId AND IsActive = 1)
    BEGIN
        RAISERROR('Template %d not found or inactive', 16, 1, @TemplateId);
        RETURN;
    END
    
    -- Generate estimate
    SELECT
        c.ComponentCode,
        c.ComponentName,
        c.Category,
        c.QuantityType,
        c.UnitOfMeasure,
        
        -- Compute quantity based on quantity type
        EstimatedQuantity = CASE 
            WHEN c.QuantityType = 'PerSquareMeter' THEN c.QuantityFactor * @FloorAreaM2
            WHEN c.QuantityType = 'PerRack' THEN c.QuantityFactor * @NumRacks
            WHEN c.QuantityType = 'PerFloor' THEN c.QuantityFactor * @NumFloors
            WHEN c.QuantityType = 'Fixed' THEN c.QuantityFactor
            ELSE 0  -- Unknown type, default to 0
        END,
        
        c.UnitCostUSD,
        
        -- Calculate line cost
        LineCostUSD = c.UnitCostUSD * CASE 
            WHEN c.QuantityType = 'PerSquareMeter' THEN c.QuantityFactor * @FloorAreaM2
            WHEN c.QuantityType = 'PerRack' THEN c.QuantityFactor * @NumRacks
            WHEN c.QuantityType = 'PerFloor' THEN c.QuantityFactor * @NumFloors
            WHEN c.QuantityType = 'Fixed' THEN c.QuantityFactor
            ELSE 0
        END,
        
        c.Notes,
        
        -- Metadata
        TemplateCode = t.TemplateCode,
        TemplateName = t.TemplateName,
        ProjectName = @ProjectName,
        CostDate = @CostDate,
        
        -- Input parameters (for audit/reproducibility)
        InputFloorAreaM2 = @FloorAreaM2,
        InputNumRacks = @NumRacks,
        InputNumFloors = @NumFloors
        
    FROM costing.TemplateComponent c
    INNER JOIN costing.Template t ON c.TemplateId = t.TemplateId
    WHERE c.TemplateId = @TemplateId
    ORDER BY c.Category, c.ComponentCode;
    
END
GO

-- =============================================
-- Sample Data: Standard Data Center Rack Template
-- =============================================
-- This demonstrates how to encode a reusable design pattern.
-- =============================================

INSERT INTO costing.Template (TemplateName, TemplateCode, Description, ProjectType)
VALUES (
    'Standard Data Center Rack (42U)',
    'DC_RACK_42U_STD',
    'Standard 42U rack with structured cabling, power, and network equipment for typical data center deployment.',
    'DataCenter'
);
GO

DECLARE @TemplateId INT = SCOPE_IDENTITY();

-- Equipment components (per rack)
INSERT INTO costing.TemplateComponent (TemplateId, ComponentCode, ComponentName, Category, UnitCostUSD, QuantityFactor, QuantityType, UnitOfMeasure, Notes)
VALUES
    (@TemplateId, 'RACK42U', '42U Server Rack with Doors', 'Equipment', 850.00, 1.0, 'PerRack', 'ea', 'Standard 42U rack enclosure'),
    (@TemplateId, 'PDU_DUAL', 'Dual PDU (16A)', 'Equipment', 420.00, 1.0, 'PerRack', 'ea', 'Redundant power distribution per rack'),
    (@TemplateId, 'PATCH_PANEL', '48-Port Cat6A Patch Panel', 'Equipment', 180.00, 1.0, 'PerRack', 'ea', 'Structured cabling termination'),
    (@TemplateId, 'CABLE_MGMT', 'Vertical Cable Manager', 'Equipment', 95.00, 2.0, 'PerRack', 'ea', '2 managers per rack (front/rear)');

-- Cabling (per square meter of raised floor)
INSERT INTO costing.TemplateComponent (TemplateId, ComponentCode, ComponentName, Category, UnitCostUSD, QuantityFactor, QuantityType, UnitOfMeasure, Notes)
VALUES
    (@TemplateId, 'CABLE_CAT6A', 'Cat6A Cable (per meter)', 'Cabling', 2.50, 8.0, 'PerSquareMeter', 'm', 'Assume 8m cable per m² floor area for horizontal runs'),
    (@TemplateId, 'CONDUIT', 'Cable Tray and Conduit', 'Cabling', 12.00, 0.5, 'PerSquareMeter', 'm', 'Estimate 0.5m conduit per m² floor area');

-- Labor (per rack installation)
INSERT INTO costing.TemplateComponent (TemplateId, ComponentCode, ComponentName, Category, UnitCostUSD, QuantityFactor, QuantityType, UnitOfMeasure, Notes)
VALUES
    (@TemplateId, 'LABOR_RACK_INSTALL', 'Rack Installation Labor', 'Labor', 250.00, 4.0, 'PerRack', 'hr', '4 hours per rack at $250/hr blended rate'),
    (@TemplateId, 'LABOR_CABLE_TERM', 'Cable Termination Labor', 'Labor', 180.00, 2.0, 'PerRack', 'hr', '2 hours per rack for terminations');

GO

-- =============================================
-- Example Usage
-- =============================================
-- Generate estimate for a 500 m² data center with 20 racks:
--
-- DECLARE @CostDate DATETIME2;
-- EXEC costing.GenerateCostEstimate 
--     @TemplateId = 1,
--     @FloorAreaM2 = 500,
--     @NumRacks = 20,
--     @ProjectName = 'Customer DC Expansion Phase 1',
--     @CostDate = @CostDate OUTPUT;
--
-- SELECT @CostDate AS EstimateGeneratedAt;
-- =============================================
