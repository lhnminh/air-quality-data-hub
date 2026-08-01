# AirTrace front-end mockups

These concepts preserve the current product flow—district selection, historic AQI,
evidence provenance, and the AI investigation assistant—while testing three
different visual identities. They are design references, not implemented screens.

## Core interaction constraint

The existing interactive node graph must remain part of the product. A redesign
may restyle or reposition it, but it must continue to expose the separate source,
database, DataHub, agent, and report nodes; their directional edges; node status;
pan/zoom; dragging; and the expanded canvas view. Cards, a timeline, or a linear
pipeline can supplement the graph, but cannot replace it.

## 01 — Urban Observatory

**Prompt direction:** A dark, map-first environmental command center. The Hanoi
map becomes the canvas, AQI is the primary status signal, the assistant becomes a
focused investigation drawer, and evidence sources form a compact lower strip.

- Best for: an expert monitoring and operations product.
- Strongest idea: distinctive map treatment and excellent at-a-glance hierarchy.
- Tradeoff: dark interfaces can feel more specialist and need careful chart/map
  contrast work.

## 02 — Field Journal

**Prompt direction:** A warm, civic-minded environmental publication. Editorial
typography, ruled dividers, a paper-like map, and a numbered evidence sequence
replace the usual floating dashboard card grid.

- Best for: public-facing explanations and policy storytelling.
- Strongest idea: the clearest brand voice and most approachable reading flow.
- Tradeoff: dense operational workflows would need a secondary workspace mode.

## 03 — Evidence Lab

**Prompt direction:** A light scientific investigation workstation. The map and
history remain familiar, while a structured source-to-DataHub-to-agent pipeline
makes provenance and AI transparency the product signature.

The revised reference, `03-evidence-lab-v2-node-graph.png`, replaces the simplified
pipeline from the first draft with the full interactive node-link model. This is
the preferred Evidence Lab reference.

`04-evidence-lab-report-open.png` shows the corresponding completed-report state.
The report uses the same right-hand Investigation workspace, with the map and
history still visible. The node graph remains accessible through the persistent
**Node graph** tab and **Back to node graph** action.

- Best for: analysts, researchers, and internal decision support.
- Strongest idea: closest to the current functionality while feeling purpose-built.
- Tradeoff: the technical framing is less emotionally distinctive than the Field
  Journal direction.

## Suggested path

Use **Evidence Lab v2** as the structural baseline, including its node graph;
borrow the **Urban Observatory** map emphasis and the **Field Journal** typography
and restrained red accent to give AirTrace a recognisable identity without
sacrificing usability.
