import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";


test("contains the important AirTrace dashboard content", async () => {
  const [page, layout] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/layout.tsx", import.meta.url), "utf8"),
  ]);

  assert.match(layout, /AirTrace Vietnam/i);
  assert.match(page, /Hanoi air-quality operations/i);
  assert.match(page, /Reading PostgreSQL/i);
  assert.match(page, /Observation history/i);
  assert.match(page, /air_quality_observations/i);
  assert.doesNotMatch(page, /DuckDB/i);
});
