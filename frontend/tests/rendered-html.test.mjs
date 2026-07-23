import assert from "node:assert/strict";
import test from "node:test";

async function renderPage() {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}`);
  const { default: worker } = await import(workerUrl.href);

  return worker.fetch(
    new Request("http://localhost/", {
      headers: { accept: "text/html" },
    }),
    {
      ASSETS: {
        fetch: async () => new Response("Not found", { status: 404 }),
      },
    },
    {
      waitUntil() {},
      passThroughOnException() {},
    },
  );
}

test("renders the AirTrace dashboard", async () => {
  const response = await renderPage();
  assert.equal(response.status, 200);

  const html = await response.text();
  assert.match(html, /<title>AirTrace Vietnam<\/title>/i);
  assert.match(html, /Hanoi air-quality operations/i);
  assert.match(html, /Observation history/i);
  assert.match(html, /air_quality_observations/i);
  assert.doesNotMatch(html, /Your site is taking shape/i);
});
