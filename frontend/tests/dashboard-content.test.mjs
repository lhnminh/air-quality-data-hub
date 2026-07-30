import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";


test("contains the four-panel AirTrace workspace and Gemini inspection flow", async () => {
  const [page, layout, styles, districtMap, historyLineChart, evidenceGraph] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/district-map.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/history-line-chart.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/evidence-graph.tsx", import.meta.url), "utf8"),
  ]);

  assert.match(layout, /AirTrace Vietnam/i);
  assert.doesNotMatch(page, /Hanoi air-quality operations/i);
  assert.doesNotMatch(page, /Monitor · investigate · explain/i);
  assert.match(page, /Reading PostgreSQL/i);
  assert.match(page, /Activity graph/i);
  assert.match(page, /AI workspace/i);
  assert.match(page, /Current conditions/i);
  assert.match(page, /Daily history from database/i);
  assert.match(page, /AirTrace assistant/i);
  assert.match(styles, /\.eyebrow/);
  assert.doesNotMatch(page, /DataHub turns raw feeds into the trusted context/i);
  assert.doesNotMatch(
    page,
    /Read air-quality feed|Check weather and wind|Compare pollutant signals|Build a bounded report/i,
  );
  assert.doesNotMatch(page, /From data to defensible action/i);
  assert.match(evidenceGraph, /Interactive agent evidence graph/i);
  assert.match(evidenceGraph, /label: "Air quality"/i);
  assert.match(evidenceGraph, /label: "Weather"/i);
  assert.match(evidenceGraph, /label: "Pollutant model"/i);
  assert.match(evidenceGraph, /label: "Traffic"/i);
  assert.match(evidenceGraph, /label: "Database"/i);
  assert.match(evidenceGraph, /label: "DataHub"/i);
  assert.doesNotMatch(`${page}\n${evidenceGraph}`, /Neon/i);
  assert.doesNotMatch(page, /Evidence-first reporting/i);
  assert.doesNotMatch(evidenceGraph, /The DataHub unlock/i);
  assert.doesNotMatch(evidenceGraph, /Schema · lineage · quality/i);
  assert.doesNotMatch(evidenceGraph, /Meaning.*Lineage.*Quality.*Audit/i);
  assert.match(evidenceGraph, /Drag nodes · scroll to zoom/i);
  assert.match(evidenceGraph, /graph-arrow-active/i);
  assert.match(styles, /graph-edge-sweep/i);
  assert.match(styles, /graph-edge-flow/i);
  assert.match(evidenceGraph, /Expand graph/i);
  assert.match(evidenceGraph, /How DataHub unlocks the report/i);
  assert.match(styles, /\.evidence-graph/);
  assert.match(page, /Hanoi district map/i);
  assert.match(page, /displayedLocation.*historical AQI/i);
  assert.match(page, /Ask about the air/i);
  assert.match(page, /Selected district/i);
  assert.match(page, /Click \$\{displayedLocation\} on the map to prepare an inspection/i);
  assert.doesNotMatch(page, /Click a district to prepare a prompt, then send it/i);
  assert.match(page, /api\/investigate/i);
  assert.doesNotMatch(page, /Evidence package is being assembled/i);
  assert.match(evidenceGraph, /isGeneratingReport \? "running"/i);
  assert.doesNotMatch(page, /Gemini is thinking/i);
  assert.match(page, /AirTrace investigation in progress/i);
  assert.doesNotMatch(page, /comparison-picker/i);
  assert.match(page, /comparison-suggestion/i);
  assert.match(page, /Compare \{displayedLocation\} with \{comparisonSuggestionTarget\}/i);
  assert.doesNotMatch(page, /agent-tasks/i);
  assert.match(page, /What the evidence suggests/i);
  assert.match(page, /comparison_district_name/i);
  assert.doesNotMatch(page, /Gemini receives only the selected district/i);
  assert.match(page, /Click a district to prepare its AI inspection/i);
  assert.match(styles, /\.report-card/);
  assert.match(page, /Agent evidence trail/i);
  assert.doesNotMatch(page, /Human review needed/i);
  assert.doesNotMatch(page, /Agent action/i);
  assert.doesNotMatch(styles, /\.agent-audit-card/);
  assert.match(styles, /\.tool-trace-card/);
  assert.match(styles, /\.agent-processing-card/);
  assert.match(styles, /\.processing-loader/);
  assert.doesNotMatch(styles, /\.agent-tasks/);
  assert.doesNotMatch(page, /void sendInspection\(prompt, comparisonSuggestionTarget\)/);
  assert.match(page, /setChatPrompt\(`Inspect \$\{districtName\} air quality`\)/);
  assert.match(page, /prepareComparisonSuggestion/i);
  assert.match(page, /district_air_quality_history/i);
  assert.match(page, /api\/district-air-quality-history/i);
  assert.doesNotMatch(page, /CAMS model estimate · not a ground sensor/i);
  assert.doesNotMatch(page, /Monthly CAMS model averages · not ground-sensor data/i);
  assert.match(page, /monthlyHistoryAverages/i);
  assert.match(page, /HistoryLineChart/i);
  assert.match(historyLineChart, /Thirty-day.*location.*US AQI trend/i);
  assert.match(styles, /\.history-line-path/);
  assert.match(styles, /grid-template-columns:[^;]+/i);
  assert.match(styles, /\.ai-panel/);
  assert.match(styles, /\.map-panel/);
  assert.match(styles, /\.history-panel/);
  assert.match(styles, /\.chat-panel/);
  assert.doesNotMatch(page, /className="pollutant-strip"/);
  assert.doesNotMatch(districtMap, /status\?\.us_aqi/);
  assert.doesNotMatch(page, /DuckDB/i);
});
