import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";


test("contains the four-panel AirTrace workspace and honest draft states", async () => {
  const [page, layout, styles, districtMap] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/globals.css", import.meta.url), "utf8"),
    readFile(new URL("../app/district-map.tsx", import.meta.url), "utf8"),
  ]);

  assert.match(layout, /AirTrace Vietnam/i);
  assert.match(page, /Hanoi air-quality operations/i);
  assert.match(page, /Reading PostgreSQL/i);
  assert.match(page, /Activity graph/i);
  assert.match(page, /Hanoi district map/i);
  assert.match(page, /Observation history/i);
  assert.match(page, /Ask about the air/i);
  assert.match(page, /AI service is not connected yet/i);
  assert.match(page, /Draft interface/i);
  assert.match(page, /air_quality_observations/i);
  assert.match(styles, /grid-template-columns:[^;]+/i);
  assert.match(styles, /\.ai-panel/);
  assert.match(styles, /\.map-panel/);
  assert.match(styles, /\.history-panel/);
  assert.match(styles, /\.chat-panel/);
  assert.match(page, /Selected as context for the future AI report/i);
  assert.doesNotMatch(page, /className="pollutant-strip"/);
  assert.doesNotMatch(districtMap, /status\?\.us_aqi/);
  assert.doesNotMatch(page, /DuckDB/i);
});
