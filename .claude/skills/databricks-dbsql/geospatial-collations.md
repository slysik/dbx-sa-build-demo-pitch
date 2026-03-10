# Geospatial Functions (H3 + ST_) and Collations

## Table of Contents

- [H3 Functions](#h3-functions)
  - [Import (Geo to H3)](#h3-import)
  - [Export (H3 to Geo)](#h3-export)
  - [Hierarchy and Traversal](#h3-hierarchy)
  - [Inspection and Conversion](#h3-inspection)
  - [Performance Tips](#h3-performance)
- [ST_ Geometry Functions](#st-geometry-functions)
  - [Constructors](#st-constructors)
  - [Relationships (Predicates)](#st-relationships)
  - [Measurements](#st-measurements)
  - [Transformations](#st-transformations)
  - [Accessors](#st-accessors)
  - [Aggregations](#st-aggregations)
  - [Format Conversion](#st-format-conversion)
- [Combined Patterns: H3 + ST_](#combined-patterns)
- [Collations](#collations)
  - [Types](#collation-types)
  - [Syntax](#collation-syntax)
  - [Hierarchy and Precedence](#collation-hierarchy)
  - [Gotchas](#collation-gotchas)

---

## H3 Functions

Uber's H3 hexagonal grid system. Resolution 0-15 (0 = ~1,107 km edge, 7 = ~1.2 km, 15 = ~0.5 m).

### H3 Import

Convert geographic coordinates/shapes to H3 cell IDs.

| Function | Input | Returns | Notes |
|----------|-------|---------|-------|
| `h3_longlatash3(lon, lat, res)` | lon/lat + resolution | BIGINT | Most common entry point |
| `h3_longlatash3string(lon, lat, res)` | lon/lat + resolution | STRING (hex) | Human-readable cell ID |
| `h3_pointash3(geog, res)` | geometry point | BIGINT | From ST_Point geometry |
| `h3_pointash3string(geog, res)` | geometry point | STRING | |
| `h3_polyfillash3(geog, res)` | polygon geometry | ARRAY\<BIGINT\> | Cells **contained** by polygon |
| `h3_polyfillash3string(geog, res)` | polygon geometry | ARRAY\<STRING\> | |
| `h3_coverash3(geog, res)` | any geometry | ARRAY\<BIGINT\> | Cells that **cover** geometry (superset of polyfill) |
| `h3_coverash3string(geog, res)` | any geometry | ARRAY\<STRING\> | |
| `h3_tessellateaswkb(geog, res)` | any geometry | ARRAY\<STRUCT\> | Tessellation with WKB boundaries |
| `h3_try_coverash3(geog, res)` | any geometry | ARRAY\<BIGINT\> or NULL | Safe version (NULL on invalid input) |
| `h3_try_polyfillash3(geog, res)` | polygon | ARRAY\<BIGINT\> or NULL | Safe version |

```sql
-- Index a table with H3
SELECT *, h3_longlatash3(longitude, latitude, 9) AS h3_cell
FROM catalog.schema.locations;

-- Fill a polygon with cells
SELECT explode(h3_polyfillash3(
  ST_GeomFromWKT('POLYGON((-73.99 40.73, -73.98 40.73, -73.98 40.74, -73.99 40.74, -73.99 40.73))'),
  9
)) AS cell_id;
```

### H3 Export

Convert H3 cell IDs back to geographic representations.

| Function | Returns | Format |
|----------|---------|--------|
| `h3_boundaryaswkt(h3)` | STRING | WKT polygon |
| `h3_boundaryaswkb(h3)` | BINARY | WKB polygon |
| `h3_boundaryasgeojson(h3)` | STRING | GeoJSON |
| `h3_centeraswkt(h3)` | STRING | WKT point |
| `h3_centeraswkb(h3)` | BINARY | WKB point |
| `h3_centerasgeojson(h3)` | STRING | GeoJSON |

```sql
SELECT h3_cell, h3_boundaryaswkt(h3_cell) AS boundary_wkt
FROM catalog.schema.h3_indexed_table;
```

### H3 Hierarchy

| Function | Purpose | Example |
|----------|---------|---------|
| `h3_toparent(h3, res)` | Get parent cell at coarser resolution | `h3_toparent(cell, 5)` |
| `h3_tochildren(h3, res)` | Get children at finer resolution | Returns ARRAY |
| `h3_maxchild(h3, res)` | Max-value child | For range queries |
| `h3_minchild(h3, res)` | Min-value child | For range queries |
| `h3_ischildof(h3a, h3b)` | Is h3a equal to or child of h3b? | For spatial containment |
| `h3_resolution(h3)` | Get resolution of cell | Returns INT (0-15) |
| `h3_compact(cells)` | Compact cell array to fewest cells | Input: ARRAY\<BIGINT\> |
| `h3_uncompact(cells, res)` | Expand compacted cells | Inverse of compact |

```sql
-- Spatial containment check: is store in district?
SELECT s.store_id
FROM stores s
JOIN districts d ON h3_ischildof(
  h3_longlatash3(s.lon, s.lat, 9),
  h3_longlatash3(d.center_lon, d.center_lat, 5)
);
```

### H3 Inspection

| Function | Purpose |
|----------|---------|
| `h3_isvalid(expr)` | Returns true if valid H3 cell ID |
| `h3_ispentagon(h3)` | Returns true if cell is a pentagon (rare edge case) |
| `h3_distance(h3a, h3b)` | Grid distance between two cells (same resolution) |
| `h3_kring(h3, k)` | All cells within grid distance k (disk) |
| `h3_hexring(h3, k)` | Ring of cells at exactly distance k (hollow ring) |
| `h3_kringdistances(h3, k)` | Cells with their distances from origin |
| `h3_h3tostring(h3)` | BIGINT to hex STRING |
| `h3_stringtoh3(str)` | Hex STRING to BIGINT |

```sql
-- Find all H3 cells within 2 hops of a store (for proximity search)
SELECT explode(h3_kring(store_h3_cell, 2)) AS nearby_cell
FROM catalog.schema.stores
WHERE store_id = 42;
```

### H3 Performance

- **Use H3 for spatial joins** -- pre-index both tables at the same resolution, then join on `h3_cell = h3_cell`. Orders of magnitude faster than ST_ geometry joins.
- **Resolution choice:** 7 (~1.2 km) for city-level, 9 (~175 m) for neighborhood, 12 (~9 m) for building-level.
- **Cluster tables by H3 cell** for spatial query performance: `CLUSTER BY (h3_cell)`.
- **kring for proximity** is cheaper than ST_Distance for approximate "within N km" queries.
- **compact/uncompact** to reduce storage when covering large areas at mixed resolutions.

---

## ST_ Geometry Functions

OGC-compliant spatial functions. **Availability:** DBR 16.0+ / DBSQL Serverless.

### ST Constructors

| Function | Creates | Example |
|----------|---------|---------|
| `ST_Point(x, y)` | Point | `ST_Point(-73.99, 40.73)` |
| `ST_MakeLine(p1, p2)` | LineString | From two points |
| `ST_MakeLine(array)` | LineString | From array of points |
| `ST_MakePolygon(line)` | Polygon | From closed LineString |
| `ST_GeomFromWKT(wkt)` | Any geometry | `ST_GeomFromWKT('POINT(-73 40)')` |
| `ST_GeomFromWKB(wkb)` | Any geometry | From WKB binary |
| `ST_GeomFromGeoJSON(json)` | Any geometry | From GeoJSON string |
| `ST_LineFromText(wkt)` | LineString | From WKT |
| `ST_PolygonFromText(wkt)` | Polygon | From WKT |
| `ST_MPointFromText(wkt)` | MultiPoint | From WKT |
| `ST_MLineFromText(wkt)` | MultiLineString | From WKT |
| `ST_MPolyFromText(wkt)` | MultiPolygon | From WKT |
| `ST_GeomCollFromText(wkt)` | GeometryCollection | From WKT |

### ST Relationships

Predicate functions returning BOOLEAN.

| Function | True When |
|----------|-----------|
| `ST_Contains(a, b)` | a fully contains b |
| `ST_Within(a, b)` | a is fully within b (inverse of Contains) |
| `ST_Intersects(a, b)` | a and b share any space |
| `ST_Crosses(a, b)` | a and b cross each other |
| `ST_Overlaps(a, b)` | a and b overlap (same dimension, partial) |
| `ST_Touches(a, b)` | a and b touch at boundary only |
| `ST_Disjoint(a, b)` | a and b share no space |
| `ST_Equals(a, b)` | a and b are geometrically equal |
| `ST_CoveredBy(a, b)` | Every point of a is in b |
| `ST_Covers(a, b)` | Every point of b is in a |
| `ST_DWithin(a, b, dist)` | Distance between a and b <= dist |

```sql
-- Find all stores within a delivery zone polygon
SELECT s.store_id, s.name
FROM catalog.schema.stores s
JOIN catalog.schema.zones z
  ON ST_Contains(z.geometry, ST_Point(s.longitude, s.latitude))
WHERE z.zone_type = 'delivery';
```

### ST Measurements

| Function | Returns | Units |
|----------|---------|-------|
| `ST_Distance(a, b)` | Distance between geometries | Meters (on sphere) |
| `ST_Length(geom)` | Length of LineString | Meters |
| `ST_Area(geom)` | Area of polygon | Square meters |
| `ST_Perimeter(geom)` | Perimeter of polygon | Meters |
| `ST_HausdorffDistance(a, b)` | Max distance of closest points | Meters |

### ST Transformations

| Function | Effect |
|----------|--------|
| `ST_Buffer(geom, dist)` | Expand geometry by distance |
| `ST_Centroid(geom)` | Center point |
| `ST_ConvexHull(geom)` | Smallest convex polygon containing geom |
| `ST_Envelope(geom)` | Bounding box as polygon |
| `ST_Intersection(a, b)` | Geometry where a and b overlap |
| `ST_Union(a, b)` | Combined geometry of a and b |
| `ST_Difference(a, b)` | Part of a not in b |
| `ST_SymDifference(a, b)` | Parts in a or b but not both |
| `ST_Simplify(geom, tol)` | Simplify with tolerance (Douglas-Peucker) |
| `ST_SimplifyPreserveTopology(geom, tol)` | Simplify keeping topology valid |
| `ST_Reverse(geom)` | Reverse coordinate order |
| `ST_FlipCoordinates(geom)` | Swap X/Y |
| `ST_Transform(geom, srid)` | Reproject to different SRID |
| `ST_Translate(geom, dx, dy)` | Move geometry |
| `ST_Scale(geom, fx, fy)` | Scale geometry |
| `ST_ClosestPoint(a, b)` | Point on a closest to b |
| `ST_LineInterpolatePoint(line, frac)` | Point at fraction along line |

### ST Accessors

| Function | Returns |
|----------|---------|
| `ST_X(point)` | X coordinate (longitude) |
| `ST_Y(point)` | Y coordinate (latitude) |
| `ST_Z(point)` | Z coordinate (elevation) |
| `ST_NumPoints(geom)` | Number of points |
| `ST_NumGeometries(geom)` | Number of sub-geometries |
| `ST_GeometryN(geom, n)` | Nth sub-geometry (1-based) |
| `ST_ExteriorRing(poly)` | Outer ring of polygon |
| `ST_InteriorRingN(poly, n)` | Nth inner ring (hole) |
| `ST_StartPoint(line)` | First point of LineString |
| `ST_EndPoint(line)` | Last point of LineString |
| `ST_PointN(line, n)` | Nth point of LineString |
| `ST_GeometryType(geom)` | Type as STRING |
| `ST_SRID(geom)` | Spatial reference ID |
| `ST_IsEmpty(geom)` | True if empty geometry |
| `ST_IsSimple(geom)` | True if no self-intersection |
| `ST_IsValid(geom)` | True if valid OGC geometry |
| `ST_Dimension(geom)` | 0=point, 1=line, 2=polygon |
| `ST_CoordDim(geom)` | Coordinate dimension (2 or 3) |
| `ST_BoundingDiagonal(geom)` | Diagonal of bounding box |

### ST Aggregations

| Function | Purpose |
|----------|---------|
| `ST_Union_Aggr(geom)` | Union all geometries in group |
| `ST_Collect(geom)` | Collect into GeometryCollection |
| `ST_Envelope_Aggr(geom)` | Bounding box of all geometries |
| `ST_Extent(geom)` | Aggregate extent (min/max coords) |

### ST Format Conversion

| Function | Direction |
|----------|-----------|
| `ST_AsWKT(geom)` | Geometry to WKT string |
| `ST_AsWKB(geom)` | Geometry to WKB binary |
| `ST_AsGeoJSON(geom)` | Geometry to GeoJSON string |
| `ST_AsBinary(geom)` | Alias for ST_AsWKB |
| `ST_AsText(geom)` | Alias for ST_AsWKT |

---

## Combined Patterns

### H3 for fast filtering, ST_ for precise calculation

```sql
-- Step 1: Coarse filter with H3 (fast)
WITH nearby AS (
  SELECT c.customer_id, s.store_id, c.lon AS c_lon, c.lat AS c_lat,
         s.lon AS s_lon, s.lat AS s_lat
  FROM catalog.schema.customers c
  JOIN catalog.schema.stores s
    ON h3_longlatash3(c.lon, c.lat, 7) = h3_longlatash3(s.lon, s.lat, 7)
       OR h3_longlatash3(c.lon, c.lat, 7)
          IN (SELECT explode(h3_kring(h3_longlatash3(s.lon, s.lat, 7), 1)))
)
-- Step 2: Precise distance with ST_ (accurate)
SELECT customer_id, store_id,
       ST_Distance(ST_Point(c_lon, c_lat), ST_Point(s_lon, s_lat)) AS distance_m
FROM nearby
WHERE ST_Distance(ST_Point(c_lon, c_lat), ST_Point(s_lon, s_lat)) < 5000;
```

### Spatial aggregation with H3

```sql
-- Aggregate events per hex cell for heatmap
SELECT
  h3_longlatash3(longitude, latitude, 8) AS h3_cell,
  h3_centeraswkt(h3_longlatash3(longitude, latitude, 8)) AS center_wkt,
  COUNT(*) AS event_count,
  AVG(value) AS avg_value
FROM catalog.schema.events
GROUP BY h3_longlatash3(longitude, latitude, 8)
ORDER BY event_count DESC;
```

---

## Collations

### Collation Types

| Collation | Behavior | Use Case |
|-----------|----------|----------|
| `UTF8_BINARY` | Byte-by-byte comparison (default) | Performance-critical, exact matching |
| `UTF8_LCASE` | Case-insensitive comparison | User-facing search (names, emails) |
| `UNICODE` | Unicode-aware (ICU default) | Multi-language, accent-sensitive |
| `UNICODE_CI` | Unicode case-insensitive | Multi-language, case-insensitive |
| Locale-specific | e.g., `de`, `de_CI`, `de_AI` | German/locale-specific sort order |

**Suffixes:** `_CI` = case-insensitive, `_AI` = accent-insensitive, `_CS` = case-sensitive (explicit).

### Collation Syntax

**Column-level:**
```sql
CREATE TABLE catalog.schema.products (
  product_id BIGINT,
  name STRING COLLATE UTF8_LCASE,
  description STRING COLLATE UNICODE,
  sku STRING  -- inherits schema/catalog default (UTF8_BINARY)
);
```

**Schema-level default:**
```sql
CREATE SCHEMA catalog.my_schema DEFAULT COLLATION UTF8_LCASE;
-- All STRING columns in this schema default to UTF8_LCASE
```

**Expression-level:**
```sql
SELECT * FROM catalog.schema.products
WHERE name COLLATE UTF8_LCASE = 'macbook pro';

-- Force binary comparison on a UTF8_LCASE column
WHERE name COLLATE UTF8_BINARY = 'MacBook Pro';
```

**In functions:**
```sql
SELECT COLLATION(name) FROM catalog.schema.products;  -- returns 'UTF8_LCASE'
```

### Collation Hierarchy

Precedence (highest to lowest):
1. **Expression-level** `COLLATE` in WHERE/SELECT
2. **Column-level** `COLLATE` in CREATE TABLE
3. **Schema default** `DEFAULT COLLATION`
4. **System default** `UTF8_BINARY`

**Mixing collations in operations:**
- Same collation: works normally
- Different collations: **error** unless one side uses explicit `COLLATE`
- Compare collated column to literal: literal inherits column collation

```sql
-- ERROR: collation mismatch
SELECT * FROM t1 JOIN t2 ON t1.name_lcase = t2.name_binary;

-- FIX: explicit collation
SELECT * FROM t1 JOIN t2 ON t1.name_lcase = t2.name_binary COLLATE UTF8_LCASE;
```

### Collation Gotchas

| Issue | Detail |
|-------|--------|
| **Performance** | `UTF8_BINARY` is fastest; `UTF8_LCASE` adds minor overhead; `UNICODE` is slowest |
| **Indexes** | Collation applies to clustering and data skipping -- choose before loading data |
| **LIKE/RLIKE** | Collation applies to LIKE but RLIKE (regex) always uses binary comparison |
| **GROUP BY** | Grouping respects collation: `'ABC'` and `'abc'` group together with `UTF8_LCASE` |
| **ORDER BY** | Sort order follows collation rules |
| **MV default** | Use `DEFAULT COLLATION UTF8_BINARY` in MV definition if schema has non-default collation |
| **No ALTER collation** | Cannot change column collation after table creation; must recreate |
| **JOIN collation mismatch** | Two columns with different collations cannot be joined without explicit COLLATE |
