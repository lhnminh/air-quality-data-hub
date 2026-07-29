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
  assert.match(page, /Hanoi air-quality operations/i);
  assert.match(page, /Reading PostgreSQL/i);
  assert.match(page, /Activity graph/i);
  assert.match(page, /DataHub turns raw feeds into the trusted context/i);
  assert.match(evidenceGraph, /Interactive agent evidence graph/i);
  assert.match(evidenceGraph, /The DataHub unlock/i);
  assert.match(evidenceGraph, /Schema · lineage · quality/i);
  assert.match(evidenceGraph, /Drag nodes · scroll to zoom/i);
  assert.match(evidenceGraph, /Expand graph/i);
  assert.match(evidenceGraph, /How DataHub unlocks the report/i);
  assert.match(styles, /\.evidence-graph/);
  assert.match(page, /Hanoi district map/i);
  assert.match(page, /displayedLocation.*historical AQI/i);
  assert.match(page, /Ask about the air/i);
  assert.match(page, /api\/investigate/i);
  assert.match(evidenceGraph, /isGeneratingReport \? "running"/i);
  assert.doesNotMatch(page, /Gemini is thinking/i);
  assert.match(page, /Gemini receives only the selected district/i);
  assert.match(page, /Click a district to prepare its AI inspection/i);
  assert.match(styles, /\.report-card/);
  assert.match(page, /Agent evidence trail/i);
  assert.match(page, /Human review needed/i);
  assert.match(styles, /\.tool-trace-card/);
  assert.match(page, /district_air_quality_history/i);
  assert.match(page, /api\/district-air-quality-history/i);
  assert.match(page, /Open-Meteo CAMS daily district-coordinate estimates/i);
  assert.match(page, /Monthly means calculated/i);
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
