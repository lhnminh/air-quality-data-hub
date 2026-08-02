import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";


test("implements the Evidence Lab dashboard without losing the investigation workflow", async () => {
  const [page, layout, styles, districtMap, historyLineChart, evidenceGraph] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/district-map.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/history-line-chart.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/evidence-graph.tsx", import.meta.url), "utf8"),
  ]);

  assert.match(layout, /AerX — Hanoi Air Intelligence/i);

  // Evidence Lab structure and visual language.
  assert.match(page, /className="workspace lab-workspace"/);
  assert.match(page, /environment-workspace/);
  assert.match(page, /metric-ribbon/);
  assert.match(page, /investigation-panel/);
  assert.match(page, /Hanoi district map/i);
  assert.match(page, /Historical evidence/i);
  assert.match(page, /Live · PostgreSQL/i);
  assert.match(styles, /Evidence Lab redesign/i);
  assert.match(styles, /--blue: #1246d7/i);
  assert.match(styles, /grid-template-columns: minmax\(600px, 1\.28fr\) minmax\(500px, 1fr\)/i);

  // The investigation tabs are functional states, not decorative labels.
  assert.match(page, /type InvestigationView = "graph" \| "report" \| "reasoning" \| "activity"/);
  assert.match(page, /Node graph/i);
  assert.match(page, /Reasoning trail/i);
  assert.match(page, /Activity log/i);
  assert.match(page, /Back to node graph/i);
  assert.match(page, /setInvestigationView\("report"\)/);
  assert.match(page, /Evidence-backed/i);
  assert.match(page, /View activity trace/i);
  assert.match(page, /Ask a follow-up about this report/i);

  // The original interactive node graph remains intact and can open the report.
  assert.match(evidenceGraph, /Interactive agent evidence graph/i);
  assert.match(evidenceGraph, /onOpenReport/i);
  assert.match(evidenceGraph, /node\.id === "report" && reportReady/i);
  assert.match(evidenceGraph, /label: "Air quality"/i);
  assert.match(evidenceGraph, /label: "Weather"/i);
  assert.match(evidenceGraph, /label: "Pollutant model"/i);
  assert.match(evidenceGraph, /label: "Traffic"/i);
  assert.match(evidenceGraph, /label: "Database"/i);
  assert.match(evidenceGraph, /label: "DataHub"/i);
  assert.match(evidenceGraph, /Drag nodes · scroll to zoom/i);
  assert.match(evidenceGraph, /Expand graph/i);
  assert.match(styles, /graph-edge-sweep/i);
  assert.match(styles, /graph-edge-flow/i);

  // Existing live behavior remains wired to the same APIs and data semantics.
  assert.match(page, /api\/observations/i);
  assert.match(page, /api\/weather/i);
  assert.match(page, /api\/modeled-air-quality/i);
  assert.match(page, /api\/traffic/i);
  assert.match(page, /api\/fires/i);
  assert.match(page, /api\/districts/i);
  assert.match(page, /api\/district-air-quality-history/i);
  assert.match(page, /api\/investigate/i);
  assert.match(page, /comparison_district_name/i);
  assert.match(page, /setChatPrompt\(`Inspect \$\{districtName\} air quality`\)/);
  assert.match(page, /Compare \{displayedLocation\} with \{comparisonSuggestionTarget\}/i);
  assert.match(page, /district_air_quality_history/i);
  assert.match(page, /monthlyHistoryAverages/i);
  assert.match(page, /HistoryLineChart/i);
  assert.match(historyLineChart, /Thirty-day.*location.*US AQI trend/i);
  assert.match(evidenceGraph, /traffic: sourceStatus\(trafficMode\)/i);
  assert.match(evidenceGraph, /fire: sourceStatus\(fireMode\)/i);
  assert.doesNotMatch(districtMap, /status\?\.us_aqi/);
  assert.doesNotMatch(page, /DuckDB/i);
});
