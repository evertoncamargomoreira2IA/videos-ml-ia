---
name: ai-manufacturing-video-analyzer
description: >
  Analyze manufacturing assembly and debug videos by converting visual observations
  into structured manufacturing events, calculating Cycle Time, Takt Time and
  Yamazumi metrics, detecting anomalies, and generating evidence-based engineering
  reports. Use this skill for process analysis, work-study, Lean manufacturing,
  assembly debugging, video-based cycle analysis, and AI-assisted industrial
  engineering.
---

# AI Manufacturing Video Analyzer Skill

## Mission

Convert manufacturing video into reliable, auditable engineering information.

The canonical pipeline is:

`Video → Vision observations → Manufacturing Events → Cycles → Metrics → Anomalies → AI Analysis → Report`

Never skip the structured event layer.

---

## Core Rules

### Rule 1 — Separate observation from interpretation

Use these evidence classes:

- `measured`: directly calculated from timestamps or explicit inputs
- `detected`: directly observed/classified by a model
- `inferred`: logical interpretation from multiple observations
- `hypothesis`: possible explanation requiring validation
- `recommendation`: proposed engineering action

Never state a hypothesis as a confirmed root cause.

### Rule 2 — Deterministic calculations

Cycle Time, Takt Time, percentages, distributions and Yamazumi totals must be calculated by deterministic code or verified arithmetic.

LLMs must not invent or estimate these values when source data exists.

### Rule 3 — Preserve evidence

Every important finding should reference:

- video ID
- cycle ID
- event IDs
- timestamps
- model version
- confidence

### Rule 4 — Human-in-the-loop

If confidence is low or an event is ambiguous, request or record human validation.

Corrections must be treated as training data.

---

# Event Schema

A manufacturing event should contain at minimum:

```json
{
  "event_id": "evt_001",
  "video_id": "vid_001",
  "cycle_id": "cycle_001",
  "station_id": "ST01",
  "start_time": 10.2,
  "end_time": 12.8,
  "duration": 2.6,
  "event_type": "assemble",
  "category": "value_added",
  "confidence": 0.91,
  "source": "vision_model",
  "human_verified": false
}
```

Prefer explicit event types such as:

- pick_part
- place_part
- assemble
- fasten
- torque
- inspect
- test
- search
- walk
- wait
- rework
- debug
- replace_part
- error
- unknown

Do not create overly specific labels until sufficient training data exists.

---

# Cycle Analysis

For a cycle:

`Cycle Time = cycle_end - cycle_start`

Calculate:

- mean
- median
- min
- max
- P90
- P95
- standard deviation
- coefficient of variation when useful

Never silently delete outliers.

If filtering is necessary, document the rule.

---

# Takt Analysis

Use:

`Takt Time = Available Production Time / Customer Demand`

Always preserve the inputs used to calculate takt.

Compare:

`Cycle Time - Takt Time`

and:

`Cycle Time / Takt Time`

Useful classifications:

- below takt
- near takt
- above takt
- severely above takt

Thresholds must be configurable.

---

# Yamazumi

Classify event duration into configured buckets.

Suggested initial taxonomy:

- Value Added
- Necessary NVA
- Waiting
- Search
- Motion
- Transportation
- Inspection
- Rework
- Other

Do not assume that a category is universally VA/NVA. Classification depends on the customer's process definition.

---

# Anomaly Analysis

Start with deterministic rules.

Examples:

```text
cycle_time > takt_time
search_time > threshold
waiting_time > threshold
rework_event exists
unexpected_sequence detected
```

Then use statistical methods:

- rolling baseline
- MAD
- standard deviation
- percentile thresholds
- clustering

Only introduce learned anomaly models after representative labeled data exists.

---

# Debug / Failure Analysis

When analyzing a failure, build an episode:

```text
Normal operation
→ failure
→ diagnosis
→ intervention
→ retest
→ result
```

Separate:

### Observed

What the video/data actually shows.

### Inferred

What logically follows from observations.

### Hypothesis

A possible root cause.

### Recommendation

What the engineer should verify or change.

Example:

```text
Observed:
Test failed.

Observed:
Connector was inspected.

Observed:
Component B was replaced.

Observed:
Retest passed.

Hypothesis:
Component B or its connection may be related to the failure.

Recommendation:
Verify component B and connector assembly conditions.
```

Do not claim:

`Root cause = Component B`

unless independent evidence confirms it.

---

# GPT / Claude Usage

Use LLMs for:

- event interpretation
- sequence reasoning
- anomaly explanation
- failure-episode summarization
- report generation
- engineering recommendations
- code generation
- code review

Use a second model as reviewer when practical.

Recommended pattern:

```text
Structured Data
      ↓
Primary LLM
      ↓
Engineering Analysis
      ↓
Second LLM Review
      ↓
Final Report
```

The application must not depend on a single model provider.

---

# Report Structure

Every generated engineering report should contain:

1. Executive Summary
2. Process Overview
3. Cycle Time Analysis
4. Takt Comparison
5. Yamazumi
6. Top Losses
7. Abnormal Cycles
8. Debug/Failure Episodes
9. Evidence
10. Hypotheses
11. Recommendations
12. Confidence / Limitations

---

# Quality Gate

Before returning a report, check:

- Are all numerical metrics traceable?
- Does total Yamazumi time reconcile with cycle time?
- Are takt inputs available?
- Are abnormal cycles supported by data?
- Are AI hypotheses clearly labeled?
- Are recommendations actionable?
- Are low-confidence observations disclosed?
- Are event timestamps valid?
- Are overlapping events handled consistently?

If a check fails, flag it rather than silently correcting the result.

---

# Learning Loop

Use human corrections:

```text
AI prediction
→ engineer correction
→ labeled event
→ dataset version
→ evaluation
→ model improvement
```

Store:

- original prediction
- corrected label
- confidence
- model version
- timestamp
- annotator
- video segment

Never overwrite original predictions.

---

# Default Response Pattern

When asked to analyze manufacturing video/data:

1. Identify the available inputs.
2. Establish the process/cycle definition.
3. Extract or inspect events.
4. Validate event confidence.
5. Calculate deterministic metrics.
6. Identify anomalies.
7. Separate facts from hypotheses.
8. Generate engineering recommendations.
9. Produce a concise report with evidence.
10. Identify what additional data would improve confidence.

---

# MVP Boundary

Do not attempt full autonomous factory intelligence initially.

Prefer:

`1 station + 1 product family + 1 camera + 10–30 representative videos`

Validate event detection and cycle segmentation first.

The most valuable early question is:

**Can the system reliably convert video into manufacturing events that an industrial engineer accepts?**