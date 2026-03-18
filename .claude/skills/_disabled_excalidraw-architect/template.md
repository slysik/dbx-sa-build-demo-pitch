# Architecture Shell Template

## Layout Constants

```
CANVAS_WIDTH    = 1400
START_X         = 50
START_Y         = 50
TITLE_HEIGHT    = 60
TITLE_GAP       = 20
LANE_WIDTH      = 220
LANE_GAP        = 40
LANE_HEADER_H   = 45
BOX_WIDTH       = 180
BOX_HEIGHT      = 50
BOX_GAP         = 15
BOX_PADDING_X   = 20   # horizontal padding inside lane for boxes
BOX_START_Y     = TITLE_HEIGHT + TITLE_GAP + LANE_HEADER_H + 20
GOV_BAR_HEIGHT  = 70
GOV_BAR_GAP     = 30
MAX_BOXES       = 4     # per lane before overflow grouping
```

## Computed Positions

```
Total lane width = LANE_WIDTH
Total lanes span = (5 * LANE_WIDTH) + (4 * LANE_GAP) = 1260

Lane X positions (left edge):
  Source:    START_X = 50
  Ingest:    START_X + 1*(LANE_WIDTH + LANE_GAP) = 310
  Transform: START_X + 2*(LANE_WIDTH + LANE_GAP) = 570
  Serve:     START_X + 3*(LANE_WIDTH + LANE_GAP) = 830
  Analysis:  START_X + 4*(LANE_WIDTH + LANE_GAP) = 1090

Box X position (centered in lane):
  box_x = lane_x + BOX_PADDING_X = lane_x + 20

Box Y positions (stacked vertically):
  box_1_y = BOX_START_Y = 195
  box_2_y = BOX_START_Y + 1*(BOX_HEIGHT + BOX_GAP) = 260
  box_3_y = BOX_START_Y + 2*(BOX_HEIGHT + BOX_GAP) = 325
  box_4_y = BOX_START_Y + 3*(BOX_HEIGHT + BOX_GAP) = 390

Max content height = BOX_START_Y + 4*(BOX_HEIGHT + BOX_GAP) = 455

Governance bar:
  gov_y = 455 + GOV_BAR_GAP = 485
  gov_x = START_X = 50
  gov_width = total lanes span = 1260
```

## Shell Elements

### Title Bar

```yaml
element:
  type: rectangle
  x: 50
  y: 50
  width: 1260
  height: 60
  backgroundColor: "#2B2D42"
  strokeColor: "#2B2D42"
  fillStyle: solid
  roundness:
    type: 3
    value: 8
  label:
    text: "{TITLE}"
    fontSize: 24
    fontFamily: 3
    textAlign: center
    verticalAlign: middle
    color: "#FFFFFF"
```

### Swim Lane Headers

Each lane header is a colored rectangle with white text label:

```yaml
lanes:
  - name: Source
    x: 50
    y: 130
    width: 220
    height: 45
    backgroundColor: "#F4E4C1"
    labelColor: "#2B2D42"

  - name: Ingest
    x: 310
    y: 130
    width: 220
    height: 45
    backgroundColor: "#E07A5F"
    labelColor: "#FFFFFF"

  - name: Transform
    x: 570
    y: 130
    width: 220
    height: 45
    backgroundColor: "#FF3621"
    labelColor: "#FFFFFF"

  - name: Serve
    x: 830
    y: 130
    width: 220
    height: 45
    backgroundColor: "#C1666B"
    labelColor: "#FFFFFF"

  - name: Analysis
    x: 1090
    y: 130
    width: 220
    height: 45
    backgroundColor: "#D4A574"
    labelColor: "#2B2D42"

lane_common:
  strokeColor: transparent
  fillStyle: solid
  roundness:
    type: 3
    value: 6
  label:
    fontSize: 18
    fontFamily: 3
    textAlign: center
    verticalAlign: middle
```

### Governance Bar

```yaml
element:
  type: rectangle
  x: 50
  y: 485
  width: 1260
  height: 70
  backgroundColor: "#3D405B"
  strokeColor: "#3D405B"
  fillStyle: solid
  roundness:
    type: 3
    value: 8
  label:
    text: "Governance & Security"
    fontSize: 18
    fontFamily: 3
    textAlign: center
    verticalAlign: middle
    color: "#FFFFFF"
```

### Component Box Template

```yaml
component_box:
  type: rectangle
  width: 180
  height: 50
  backgroundColor: "#FAF3E8"
  strokeColor: "#5C5C5C"
  strokeWidth: 1
  fillStyle: solid
  roundness:
    type: 3
    value: 6
  label:
    fontSize: 14
    fontFamily: 3
    textAlign: center
    verticalAlign: middle
    color: "#2B2D42"
```

### Overflow Box Template

When a lane has more than MAX_BOXES components:

```yaml
overflow_box:
  type: rectangle
  width: 180
  height: 50
  backgroundColor: "#F0E6D6"
  strokeColor: "#5C5C5C"
  strokeWidth: 1
  strokeStyle: dashed
  fillStyle: solid
  roundness:
    type: 3
    value: 6
  label:
    text: "+{N} more ({list})"
    fontSize: 12
    fontFamily: 3
    textAlign: center
    verticalAlign: middle
    color: "#5C5C5C"
```

### Lane-to-Lane Arrows

```yaml
arrows:
  - from_lane: Source
    to_lane: Ingest
    start_x: 270    # Source x + LANE_WIDTH
    start_y: 152    # Lane header y + header_h/2
    end_x: 310      # Ingest x
    end_y: 152

  - from_lane: Ingest
    to_lane: Transform
    start_x: 530
    start_y: 152
    end_x: 570
    end_y: 152

  - from_lane: Transform
    to_lane: Serve
    start_x: 790
    start_y: 152
    end_x: 830
    end_y: 152

  - from_lane: Serve
    to_lane: Analysis
    start_x: 1050
    start_y: 152
    end_x: 1090
    end_y: 152

arrow_common:
  type: arrow
  strokeColor: "#5C5C5C"
  strokeWidth: 2
  points: [[0,0], [{LANE_GAP},0]]
  startArrowhead: null
  endArrowhead: arrow
```

### Governance Sub-components

Governance components are placed horizontally inside the governance bar (not stacked vertically):

```yaml
governance_layout:
  # Components are distributed horizontally within the bar
  # Each component is a smaller rectangle or text element
  box_width: 140
  box_height: 35
  box_gap: 15
  y_offset: 502    # gov_y + 17 (centered vertically in bar)
  start_x: 70      # gov_x + 20 padding
  backgroundColor: "#4A4D6E"
  strokeColor: transparent
  label_color: "#FFFFFF"
  fontSize: 12
```

## Color Palette Reference

| Element | Color | Hex |
|---------|-------|-----|
| Source lane | Warm sand | #F4E4C1 |
| Ingest lane | Soft coral | #E07A5F |
| Transform lane | Databricks red-orange | #FF3621 |
| Serve lane | Warm terracotta | #C1666B |
| Analysis lane | Muted gold | #D4A574 |
| Governance bar | Deep warm charcoal | #3D405B |
| Title bar | Near-black warm | #2B2D42 |
| Component boxes | Cream fill | #FAF3E8 |
| Arrows/strokes | Warm gray | #5C5C5C |
| Text (dark) | Near-black warm | #2B2D42 |
| Text (light) | White | #FFFFFF |
