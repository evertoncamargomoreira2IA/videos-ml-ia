# AI Manufacturing Video Analyzer — MVP v0.1

**Status:** Initial architecture / discovery artifact  
**Objective:** Transform assembly/debug videos into structured manufacturing events, Lean metrics, anomaly detection and AI-generated reports.

---

## 1. Product Vision

Build an AI system that learns to analyze videos of manufacturing assembly and debugging activities.

The system should:

1. ingest manufacturing videos;
2. detect people, parts, tools and relevant actions;
3. convert visual observations into structured manufacturing events;
4. segment the video into production cycles;
5. calculate Cycle Time, Takt Time, VA/NVA and Yamazumi;
6. detect abnormal cycles and potential failure/debug patterns;
7. compare observed work against a defined standard;
8. generate visual reports and engineering recommendations;
9. learn from corrections made by industrial engineers.

### Core principle

**Video is the raw input. Manufacturing Events are the system's canonical representation.**

Do not use an LLM as the source of truth for numerical calculations. LLMs interpret structured results; deterministic services calculate industrial metrics.

---

# 2. MVP Scope

## Input

- MP4/MOV video
- station identifier
- optional operator identifier
- expected takt time
- optional standard work sequence
- optional product/model identifier

## MVP Output

### A. Annotated video
Overlay:
- detected operator
- detected tools/components
- operation labels
- cycle boundaries
- anomaly markers

### B. Event timeline

Example:

| Start | End | Event | Category | Confidence |
|---:|---:|---|---|---:|
| 12.4 | 14.2 | Pick component A | NVA/Support | 0.94 |
| 14.2 | 20.1 | Install component A | VA | 0.91 |
| 20.1 | 23.5 | Search component | NVA | 0.88 |
| 23.5 | 29.0 | Install component B | VA | 0.93 |

### C. Manufacturing metrics

- Cycle Time
- Mean Cycle Time
- Median Cycle Time
- P90/P95 Cycle Time
- Minimum/Maximum Cycle Time
- Takt Time
- Cycle vs Takt deviation
- VA time
- NVA time
- Waiting time
- Motion/search time
- Rework/debug time
- First-pass yield when available
- cycle-to-cycle variation

### D. Yamazumi

Classify work into configurable buckets:

- Value Added
- Necessary Non-Value Added
- Waste
- Waiting
- Motion
- Transportation
- Search
- Inspection
- Rework

The categories must be configurable by plant/process.

### E. AI report

The report should answer:

- What happened?
- Where was time lost?
- Which cycles were abnormal?
- What are the likely causes?
- What evidence supports the conclusion?
- What should an engineer investigate?
- Which improvement opportunities have the highest potential impact?

---

# 3. System Architecture

```text
                         ┌──────────────────┐
                         │ Manufacturing    │
                         │ Video            │
                         └────────┬─────────┘
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │ Video Ingestion         │
                    │ metadata / validation   │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Vision Pipeline          │
                    │ detection / tracking     │
                    │ action recognition       │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ Manufacturing Event      │
                    │ Engine                   │
                    └────────────┬────────────┘
                                 │
                   ┌─────────────┴─────────────┐
                   ▼                           ▼
          ┌────────────────┐          ┌─────────────────┐
          │ Cycle Engine   │          │ Anomaly Engine  │
          └───────┬────────┘          └────────┬────────┘
                  │                            │
                  └──────────────┬─────────────┘
                                 ▼
                    ┌─────────────────────────┐
                    │ Industrial Metrics       │
                    │ CT / Takt / Yamazumi     │
                    └────────────┬────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │ AI Analysis Layer        │
                    │ GPT / Claude             │
                    └────────────┬────────────┘
                                 │
                  ┌──────────────┴──────────────┐
                  ▼                             ▼
          ┌────────────────┐           ┌─────────────────┐
          │ Dashboard      │           │ Engineering     │
          │                │           │ Report          │
          └────────────────┘           └─────────────────┘

                  Human Engineer Feedback
                            │
                            ▼
                    ┌──────────────────┐
                    │ Label Store      │
                    │ / Training Data  │
                    └────────┬─────────┘
                             │
                             ▼
                    Improved Models
```

---

# 4. Recommended Technology Stack

## Backend

- Python
- FastAPI
- Pydantic
- OpenCV
- FFmpeg
- NumPy
- Pandas

## Computer Vision

Start with pretrained models and fine-tune only after collecting representative data.

Potential components:

- object detection
- object tracking
- pose estimation
- action recognition
- temporal event segmentation

The exact vision model should remain replaceable behind a `VisionProvider` interface.

## Data

- PostgreSQL for structured manufacturing data
- Object storage for videos and extracted frames
- Redis/queue for asynchronous video jobs

## Frontend

- React / Next.js
- interactive video player
- timeline
- KPI cards
- Yamazumi visualization
- cycle distribution
- anomaly table
- event correction UI

## AI

Use GPT and Claude as complementary reasoning/coding/review agents.

Recommended pattern:

```text
Vision/Rules → Structured JSON → LLM Analysis → Report
```

not:

```text
Video → LLM → manufacturing metrics
```

---

# 5. Canonical Manufacturing Event Model

The event model is the most important artifact in the system.

Example:

```json
{
  "event_id": "evt_000123",
  "video_id": "vid_001",
  "cycle_id": "cycle_017",
  "station_id": "ST03",
  "operator_id": "OP01",
  "product_id": "MODEL_A",
  "start_time": 153.4,
  "end_time": 155.2,
  "duration": 1.8,
  "event_type": "pick_part",
  "object": "component_A",
  "category": "support",
  "value_class": "NVA",
  "confidence": 0.94,
  "source": "vision_model",
  "human_verified": false
}
```

## Event types — initial vocabulary

- cycle_start
- cycle_end
- pick_part
- place_part
- assemble
- fasten
- torque
- connect
- disconnect
- inspect
- measure
- test
- search
- walk
- reach
- wait
- talk
- rework
- debug
- remove_part
- replace_part
- error
- unknown

The vocabulary must evolve from real production data.

---

# 6. Cycle Detection

A cycle is defined by configurable start/end events.

Example:

```text
cycle_start
  ↓
material handling
  ↓
assembly operations
  ↓
inspection
  ↓
cycle_end
```

Cycle Time:

```text
Cycle Time = cycle_end_timestamp - cycle_start_timestamp
```

For multiple cycles:

```text
CT_mean = mean(cycle_times)
CT_median = median(cycle_times)
CT_P90 = percentile(cycle_times, 90)
```

Outlier policy must be configurable.

Never silently remove outliers from the engineering dataset.

---

# 7. Takt Time

Takt Time:

```text
Takt Time = Available Production Time / Customer Demand
```

The system should store the source inputs:

```json
{
  "available_time_seconds": 25200,
  "customer_demand_units": 600,
  "takt_time_seconds": 42.0
}
```

The UI should distinguish:

- observed Cycle Time
- target Takt Time
- engineering target
- measured production time

---

# 8. Yamazumi Engine

For each cycle:

```text
Total Cycle Time =
    Value Added
  + Necessary NVA
  + Waste
  + Waiting
  + Rework
```

The exact taxonomy is configurable.

Example output:

```json
{
  "cycle_id": "cycle_017",
  "value_added": 28.2,
  "necessary_nva": 5.4,
  "waiting": 4.1,
  "search": 3.2,
  "rework": 2.8,
  "total": 43.7
}
```

The Yamazumi visualization should support:

- single cycle
- average cycle
- station comparison
- operator comparison where appropriate
- current vs future state
- takt reference line

---

# 9. Anomaly Detection

MVP should combine deterministic and statistical approaches.

## Level 1 — Rule based

Examples:

```text
if cycle_time > takt_time:
    flag("above_takt")

if search_time > threshold:
    flag("excessive_search")

if waiting_time > threshold:
    flag("excessive_waiting")

if rework_event exists:
    flag("rework")
```

## Level 2 — Statistical

Use:

- rolling mean
- standard deviation
- MAD
- percentile thresholds
- clustering of cycle signatures

## Level 3 — ML

After enough labeled data:

- anomaly detection
- sequence classification
- failure prediction
- process deviation detection

Do not begin with Level 3.

---

# 10. Debug / Failure Analysis

The system should model a debug sequence as events.

Example:

```text
Test
 ↓
Failure detected
 ↓
Inspect connector
 ↓
Search tool
 ↓
Replace component
 ↓
Retest
 ↓
Pass
```

The AI should produce:

```text
Failure episode:
FE-0042

Observed:
- Test failed at 03:14
- Operator inspected connector
- Component B was replaced
- Retest passed

Likely classification:
Component / connection issue

Evidence:
- failure occurred before replacement
- failure disappeared after replacement

Confidence:
0.78

Engineering action:
Verify component B and connector assembly process.
```

Important: AI must clearly distinguish:

- observed fact
- inference
- hypothesis
- recommendation

Never present a hypothesis as confirmed root cause.

---

# 11. GPT + Claude Multi-Agent Strategy

## Agent 1 — Vision Interpreter

Input:

```json
{
  "events": [...]
}
```

Output:

structured interpretation only.

## Agent 2 — Industrial Engineer

Analyzes:

- CT
- takt
- Yamazumi
- losses
- anomalies

## Agent 3 — Debug Analyst

Analyzes failure episodes and evidence.

## Agent 4 — Report Generator

Produces engineering report.

## Agent 5 — Reviewer

A second LLM reviews the report for:

- unsupported claims
- calculation inconsistencies
- missing evidence
- ambiguous language

Recommended loop:

```text
Data
 ↓
GPT analysis
 ↓
Claude review
 ↓
correction
 ↓
Final report
```

The model provider should be abstracted so the application is not locked into one vendor.

---

# 12. Human-in-the-Loop

Every uncertain event should be correctable.

UI:

```text
AI detected:
[ Search component ] 0.61

Engineer:
[ Search component ] ✓
```

or:

```text
AI detected:
[ Assembly ] 0.72

Engineer changes to:
[ Waiting ] ✓
```

Store:

- original prediction
- corrected label
- user
- timestamp
- model version
- confidence
- video segment

This creates the training dataset.

---

# 13. Training Data Strategy

Every video should eventually produce:

```text
Video
 ├── raw video
 ├── frames
 ├── detections
 ├── events
 ├── human corrections
 ├── cycle labels
 └── anomaly labels
```

Dataset versions:

```text
dataset_v0.1
dataset_v0.2
dataset_v0.3
```

Model versions:

```text
vision_model_v0.1
vision_model_v0.2
event_classifier_v0.1
```

Never overwrite historical labels.

---

# 14. Confidence and Evidence Model

Every AI conclusion should have:

```json
{
  "claim": "Cycle exceeds takt",
  "evidence": [
    "cycle_017",
    "cycle_018",
    "cycle_022"
  ],
  "confidence": 0.97,
  "type": "measured"
}
```

Classification:

- `measured`
- `detected`
- `inferred`
- `hypothesis`
- `recommendation`

This is critical for industrial trust.

---

# 15. Dashboard MVP

## Page 1 — Video Analysis

- video player
- event timeline
- cycle boundaries
- anomaly markers

## Page 2 — Process Analysis

- Cycle Time vs Takt
- cycle distribution
- Yamazumi
- VA/NVA
- top losses

## Page 3 — Debug

- failure episodes
- sequence visualization
- likely causes
- evidence

## Page 4 — AI Report

- executive summary
- findings
- evidence
- opportunities
- recommended actions

---

# 16. Database Model

Initial tables:

```text
projects
videos
stations
operators
products
cycles
events
anomalies
metrics
reports
annotations
model_versions
datasets
```

Relationship:

```text
Project
 └── Video
      └── Cycle
           └── Event
                └── Annotation
```

---

# 17. API MVP

```text
POST   /projects
POST   /videos
POST   /videos/{id}/analyze

GET    /videos/{id}
GET    /videos/{id}/events
GET    /videos/{id}/cycles
GET    /videos/{id}/metrics
GET    /videos/{id}/anomalies

POST   /events/{id}/correct
POST   /cycles/{id}/review

POST   /reports/generate
GET    /reports/{id}
```

---

# 18. MVP Development Roadmap

## Phase 0 — Definition

Goal:

- event vocabulary
- sample videos
- annotation rules
- metric definitions

Deliverable:

`manufacturing_event_schema.json`

## Phase 1 — Video + Manual Events

Build:

- video player
- timeline
- manual event labeling
- Cycle Time engine
- Takt engine
- Yamazumi engine

This validates the data model before ML.

## Phase 2 — AI-assisted Detection

Add:

- object detection
- tracking
- candidate event generation
- confidence scoring

## Phase 3 — Human Feedback

Add:

- correction UI
- annotation storage
- dataset generation
- model evaluation

## Phase 4 — ML

Add:

- event classifier
- anomaly detector
- sequence model

## Phase 5 — Generative AI

Add:

- GPT analysis
- Claude review
- automatic reports
- engineering recommendations

---

# 19. Definition of Done — MVP

The MVP is successful when a user can:

1. upload a video;
2. define takt time;
3. mark or review events;
4. automatically segment cycles;
5. calculate cycle time;
6. generate a Yamazumi;
7. identify cycles above takt;
8. flag anomalies;
9. correct AI predictions;
10. generate an engineering report.

Target:

**One complete analysis from video upload to report without manually calculating metrics in Excel.**

---

# 20. First Pilot

Do not start with 100 different processes.

Choose:

- 1 station
- 1 product family
- 1 camera position
- 1 operator workflow
- 10–30 representative videos
- 1 standard work sequence

Collect:

- normal cycles
- slow cycles
- abnormal cycles
- known failures
- rework cases

The objective is not maximum model complexity.

The objective is to validate:

**Can video reliably become manufacturing events?**

---

# 21. Success Metrics

Technical:

- event precision
- event recall
- cycle boundary accuracy
- anomaly precision
- false positive rate
- confidence calibration

Industrial:

- Cycle Time accuracy
- Yamazumi classification agreement
- time saved by engineer
- report usefulness
- number of actionable findings

Business:

- analysis time before vs after AI
- engineering hours saved
- improvement opportunities identified
- estimated savings validated by engineering

---

# 22. Key Design Principles

1. **Events are the canonical representation.**
2. **Metrics are deterministic.**
3. **LLMs explain and reason over structured evidence.**
4. **Human corrections become training data.**
5. **Every AI conclusion needs evidence and confidence.**
6. **Models must be replaceable.**
7. **Do not train custom ML before collecting representative data.**
8. **Start with one station and one process.**
9. **Preserve raw observations and historical model versions.**
10. **Never confuse correlation or AI inference with confirmed root cause.**

---

# 23. Immediate Next Artifacts

The next development artifacts should be:

```text
01_manufacturing_event_schema.json
02_database_schema.sql
03_metric_engine_spec.md
04_vision_pipeline_spec.md
05_annotation_guidelines.md
06_ai_agent_spec.md
07_api_spec.yaml
08_dashboard_wireframe.md
09_evaluation_dataset_spec.md
10_mvp_backlog.md
```

The most important next file is:

**`01_manufacturing_event_schema.json`**

because it becomes the contract between Computer Vision, ML, metrics, database, GPT and Claude.