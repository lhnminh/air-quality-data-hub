"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { mockObservations, type AirObservation } from "./mock-data";

const apiUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type DataMode = "loading" | "postgresql" | "demo";

async function requestObservations() {
  try {
    const response = await fetch(`${apiUrl}/api/observations?limit=20`);
    if (!response.ok) return null;

    const result = (await response.json()) as {
      observations: AirObservation[];
    };
    return result.observations;
  } catch {
    return null;
  }
}

function readablePollutant(code: string) {
  const pollutantNames: Record<string, string> = {
    p1: "PM10",
    p2: "PM2.5",
    o3: "Ozone",
    n2: "NO₂",
    s2: "SO₂",
    co: "CO",
  };
  return pollutantNames[code.toLowerCase()] ?? code.toUpperCase();
}

function aqiDescription(aqi: number) {
  if (aqi <= 50) return "Good";
  if (aqi <= 100) return "Moderate";
  if (aqi <= 150) return "Unhealthy for sensitive groups";
  if (aqi <= 200) return "Unhealthy";
  if (aqi <= 300) return "Very unhealthy";
  return "Hazardous";
}

function formatTime(value: string) {
  const date = new Date(value.replace(" ", "T"));
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(date);
}

export default function Home() {
  const [observations, setObservations] =
    useState<AirObservation[]>(mockObservations);
  const [dataMode, setDataMode] = useState<DataMode>("loading");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadObservations = useCallback(async () => {
    const result = await requestObservations();
    if (!result || result.length === 0) {
      setObservations(mockObservations);
      setDataMode("demo");
    } else {
      setObservations(result);
      setDataMode("postgresql");
    }
    setIsRefreshing(false);
  }, []);

  useEffect(() => {
    let cancelled = false;

    void requestObservations().then((result) => {
      if (cancelled) return;

      if (!result || result.length === 0) {
        setObservations(mockObservations);
        setDataMode("demo");
      } else {
        setObservations(result);
        setDataMode("postgresql");
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const latest = observations[0];
  const chartRows = useMemo(
    () => [...observations].slice(0, 8).reverse(),
    [observations],
  );
  const maxChartAqi = Math.max(...chartRows.map((row) => row.aqi_us), 120);

  return (
    <main>
      <header className="topbar">
        <a className="brand" href="#top" aria-label="AirTrace home">
          <span className="brand-mark">A</span>
          <span>
            <strong>AirTrace</strong>
            <small>Vietnam</small>
          </span>
        </a>

        <div className="header-actions">
          <div className={`data-status ${dataMode}`}>
            <span className="status-dot" />
            {dataMode === "loading"
              ? "Connecting…"
              : dataMode === "postgresql"
                ? "Reading PostgreSQL"
                : "Demo data"}
          </div>
          <button
            className="refresh-button"
            onClick={() => {
              setIsRefreshing(true);
              void loadObservations();
            }}
            disabled={isRefreshing}
          >
            {isRefreshing ? "Refreshing…" : "Refresh data"}
          </button>
        </div>
      </header>

      <div className="page" id="top">
        <section className="intro">
          <div>
            <p className="eyebrow">Hanoi air-quality operations</p>
            <h1>Know what the air is doing—and what to check next.</h1>
          </div>
          <p className="intro-copy">
            A first look at current observations, data health, and the evidence
            AirTrace will use to investigate pollution events.
          </p>
        </section>

        {dataMode === "demo" && (
          <aside className="demo-notice">
            <strong>Showing sample data.</strong> Start the Python API to replace
            these examples with rows from the PostgreSQL database.
          </aside>
        )}

        <section className="overview-grid" aria-label="Current overview">
          <article className="aqi-card">
            <div className="card-heading">
              <span>Current US AQI</span>
              <span className="location-pill">Hanoi</span>
            </div>
            <div className="aqi-reading">
              <strong>{latest.aqi_us}</strong>
              <div>
                <span>{aqiDescription(latest.aqi_us)}</span>
                <small>Main pollutant: {readablePollutant(latest.main_pollutant)}</small>
              </div>
            </div>
            <div className="aqi-scale" aria-label="AQI scale">
              <span className="active" />
              <span />
              <span />
              <span />
              <span />
            </div>
            <p className="card-note">
              Sensitive people may want to reduce prolonged outdoor activity.
            </p>
          </article>

          <article className="map-card">
            <div className="card-heading">
              <span>Observation location</span>
              <span className="coordinates">
                {latest.latitude.toFixed(3)}, {latest.longitude.toFixed(3)}
              </span>
            </div>
            <div className="map-visual" aria-label="Simplified map of Hanoi">
              <span className="road road-one" />
              <span className="road road-two" />
              <span className="road road-three" />
              <span className="river" />
              <span className="map-label old-quarter">Old Quarter</span>
              <span className="map-label west-lake">West Lake</span>
              <span className="sensor-marker">
                <b>{latest.aqi_us}</b>
                <small>AQI</small>
              </span>
            </div>
          </article>

          <article className="health-card">
            <div className="card-heading">
              <span>Data health</span>
              <span className="health-label">Available</span>
            </div>
            <dl className="health-list">
              <div>
                <dt>Observed</dt>
                <dd>{formatTime(latest.observed_at)}</dd>
              </div>
              <div>
                <dt>Collected</dt>
                <dd>{formatTime(latest.collected_at)}</dd>
              </div>
              <div>
                <dt>Provider</dt>
                <dd>{latest.source}</dd>
              </div>
              <div>
                <dt>Records loaded</dt>
                <dd>{observations.length}</dd>
              </div>
            </dl>
          </article>
        </section>

        <section className="detail-grid">
          <article className="panel trend-panel">
            <div className="panel-title">
              <div>
                <p className="eyebrow">Recent observations</p>
                <h2>AQI trend</h2>
              </div>
              <span className="time-zone">Hanoi time</span>
            </div>
            <div className="chart" aria-label="Recent AQI bar chart">
              {chartRows.map((row, index) => (
                <div className="chart-column" key={`${row.observed_at}-${index}`}>
                  <span>{row.aqi_us}</span>
                  <div
                    className="chart-bar"
                    style={{ height: `${Math.max((row.aqi_us / maxChartAqi) * 100, 8)}%` }}
                  />
                  <small>{formatTime(row.observed_at).split(", ").at(-1)}</small>
                </div>
              ))}
            </div>
          </article>

          <article className="panel investigation-panel">
            <div className="panel-title">
              <div>
                <p className="eyebrow">Source investigation</p>
                <h2>Waiting for more evidence</h2>
              </div>
              <span className="not-ready">Not active</span>
            </div>
            <p className="investigation-copy">
              One IQAir city reading is enough for the dashboard, but not enough
              to explain the cause. Weather, traffic, fire, and nearby sensor data
              will appear here as we add each source.
            </p>
            <div className="evidence-list">
              <div><span>Air quality</span><strong className="connected">Connected</strong></div>
              <div><span>Weather and wind</span><strong>Next</strong></div>
              <div><span>Traffic and fires</span><strong>Planned</strong></div>
            </div>
          </article>
        </section>

        <section className="panel table-panel">
          <div className="panel-title">
            <div>
              <p className="eyebrow">Stored in PostgreSQL</p>
              <h2>Observation history</h2>
            </div>
            <code>air_quality_observations</code>
          </div>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>Observed</th>
                  <th>City</th>
                  <th>US AQI</th>
                  <th>Main pollutant</th>
                  <th>Source</th>
                </tr>
              </thead>
              <tbody>
                {observations.map((row, index) => (
                  <tr key={`${row.observed_at}-${index}`}>
                    <td>{formatTime(row.observed_at)}</td>
                    <td>{row.city}, {row.country}</td>
                    <td><strong>{row.aqi_us}</strong></td>
                    <td>{readablePollutant(row.main_pollutant)}</td>
                    <td>{row.source}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>

        <footer>
          <span>AirTrace learning project</span>
          <span>IQAir → PostgreSQL → Python API → this dashboard</span>
        </footer>
      </div>
    </main>
  );
}
