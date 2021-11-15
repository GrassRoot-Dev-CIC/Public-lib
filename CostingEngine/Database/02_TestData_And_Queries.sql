-- =============================================
-- Costing Engine - Test Data and Queries
-- =============================================
-- Example templates and validation queries
-- =============================================

-- =============================================
-- Additional Template: Airport Terminal ICT
-- =============================================
INSERT INTO costing.Template (TemplateName, TemplateCode, Description, ProjectType)
VALUES (
    'Airport Terminal ICT Package',
    'AIRPORT_ICT_STD',
    'Standard ICT package for airport terminal buildings including networking, WiFi, CCTV, and BMS integration.',
    'Airport'
);
GO

DECLARE @AirportTemplateId INT = SCOPE_IDENTITY();

-- Network infrastructure (per floor area)
INSERT INTO costing.TemplateComponent (TemplateId, ComponentCode, ComponentName, Category, UnitCostUSD, QuantityFactor, QuantityType, UnitOfMeasure, Notes)
VALUES
    (@AirportTemplateId, 'WIFI_AP', 'WiFi 6 Access Point', 'Network', 650.00, 0.02, 'PerSquareMeter', 'ea', 'Approx 1 AP per 50 m² for high-density coverage'),
    (@AirportTemplateId, 'NETWORK_SWITCH', '48-Port PoE+ Switch', 'Network', 2400.00, 0.004, 'PerSquareMeter', 'ea', '1 switch per 250 m²'),
    (@AirportTemplateId, 'BACKBONE_FIBER', 'Fiber Backbone Cabling', 'Cabling', 8.50, 5.0, 'PerSquareMeter', 'm', 'Estimate 5m fiber per m² for vertical/horizontal runs');

-- CCTV (per floor area)
INSERT INTO costing.TemplateComponent (TemplateId, ComponentCode, ComponentName, Category, UnitCostUSD, QuantityFactor, QuantityType, UnitOfMeasure, Notes)
VALUES
    (@AirportTemplateId, 'CCTV_CAMERA', '4K IP Camera with Analytics', 'Security', 850.00, 0.015, 'PerSquareMeter', 'ea', 'Approx 1 camera per 65 m²'),
    (@AirportTemplateId, 'CCTV_NVR', 'Network Video Recorder (128 ch)', 'Security', 4500.00, 0.001, 'PerSquareMeter', 'ea', '1 NVR per 1000 m²');

-- Fixed infrastructure (per floor)
INSERT INTO costing.TemplateComponent (TemplateId, ComponentCode, ComponentName, Category, UnitCostUSD, QuantityFactor, QuantityType, UnitOfMeasure, Notes)
VALUES
    (@AirportTemplateId, 'CORE_SWITCH', 'Core Network Switch', 'Network', 18000.00, 1.0, 'PerFloor', 'ea', 'One core switch per floor for redundancy'),
    (@AirportTemplateId, 'COMMS_ROOM', 'Comms Room Fitout', 'Infrastructure', 12000.00, 1.0, 'PerFloor', 'ea', 'Racks, cooling, UPS per floor');

GO

-- =============================================
-- Test Queries
-- =============================================

-- 1. List all active templates
SELECT 
    TemplateId,
    TemplateCode,
    TemplateName,
    ProjectType,
    ComponentCount = (SELECT COUNT(*) FROM costing.TemplateComponent WHERE TemplateId = t.TemplateId)
FROM costing.Template t
WHERE IsActive = 1
ORDER BY ProjectType, TemplateName;

-- 2. View components for a template
SELECT 
    ComponentCode,
    ComponentName,
    Category,
    QuantityType,
    QuantityFactor,
    UnitCostUSD,
    UnitOfMeasure,
    Notes
FROM costing.TemplateComponent
WHERE TemplateId = 1  -- Data Center template
ORDER BY Category, ComponentCode;

-- 3. Generate estimate: Data Center with 20 racks, 500 m² floor
DECLARE @CostDate1 DATETIME2;
EXEC costing.GenerateCostEstimate 
    @TemplateId = 1,
    @FloorAreaM2 = 500,
    @NumRacks = 20,
    @ProjectName = 'Example DC - 20 Racks',
    @CostDate = @CostDate1 OUTPUT;

-- 4. Generate estimate: Airport terminal, 5000 m², 2 floors
DECLARE @CostDate2 DATETIME2;
EXEC costing.GenerateCostEstimate 
    @TemplateId = 2,
    @FloorAreaM2 = 5000,
    @NumFloors = 2,
    @ProjectName = 'Example Airport Terminal',
    @CostDate = @CostDate2 OUTPUT;

-- 5. Total cost summary from generated estimate
-- (Run after generating estimate)
WITH EstimateSummary AS (
    SELECT
        Category,
        SUM(LineCostUSD) AS CategoryTotal
    FROM (
        -- Re-run estimate inline for demonstration
        SELECT
            c.Category,
            LineCostUSD = c.UnitCostUSD * CASE 
                WHEN c.QuantityType = 'PerSquareMeter' THEN c.QuantityFactor * 500
                WHEN c.QuantityType = 'PerRack' THEN c.QuantityFactor * 20
                WHEN c.QuantityType = 'Fixed' THEN c.QuantityFactor
                ELSE 0
            END
        FROM costing.TemplateComponent c
        WHERE c.TemplateId = 1
    ) AS LineItems
    GROUP BY Category
)
SELECT
    Category,
    CategoryTotal,
    PercentOfTotal = 100.0 * CategoryTotal / SUM(CategoryTotal) OVER()
FROM EstimateSummary
UNION ALL
SELECT
    'TOTAL' AS Category,
    SUM(CategoryTotal),
    100.0
FROM EstimateSummary
ORDER BY 
    CASE WHEN Category = 'TOTAL' THEN 1 ELSE 0 END,
    CategoryTotal DESC;
