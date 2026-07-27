"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  mockDistrictStatuses,
  mockObservations,
  type AirObservation,
  type DistrictStatus,
  type ModeledAirQualityObservation,
  type WeatherObservation,
} from "./mock-data";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type DataMode = "loading" | "postgresql" | "demo";

// Loading the map only in the browser keeps MapLibre away from server rendering.
const districtMapModule = import("./district-map");
const DistrictMap = dynamic(() => districtMapModule, { ssr: false });

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

async function requestWeather() {
  try {
    const response = await fetch(`${apiUrl}/api/weather?limit=1`);
    if (!response.ok) return null;

    const result = (await response.json()) as {
      observations: WeatherObservation[];
    };
    return result.observations;
  } catch {
    return null;
  }
}

async function requestModeledAirQuality() {
  try {
    const response = await fetch(`${apiUrl}/api/modeled-air-quality?limit=1`);
    if (!response.ok) return null;

    const result = (await response.json()) as {
      observations: ModeledAirQualityObservation[];
    };
    return result.observations;
  } catch {
    return null;
  }
}

async function requestDistrictStatuses() {
  try {
    const response = await fetch(`${apiUrl}/api/districts`);
    if (!response.ok) return null;

    const result = (await response.json()) as { districts: DistrictStatus[] };
    return result.districts;
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

function modeLabel(mode: DataMode) {
  if (mode === "loading") return "Checking";
  if (mode === "postgresql") return "Connected";
  return "Sample data";
}

export default function Home() {
  const [observations, setObservations] = useState<AirObservation[]>([]);
  const [districtStatuses, setDistrictStatuses] = useState<DistrictStatus[]>([]);
  const [dataMode, setDataMode] = useState<DataMode>("loading");
  const [weatherMode, setWeatherMode] = useState<DataMode>("loading");
  const [modeledAirQualityMode, setModeledAirQualityMode] =
    useState<DataMode>("loading");
  const [districtMode, setDistrictMode] = useState<DataMode>("loading");
  const [selectedDistrictName, setSelectedDistrictName] = useState("Hoan Kiem");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const applyResults = useCallback(
    (
      observationResult: AirObservation[] | null,
      weatherResult: WeatherObservation[] | null,
      modeledResult: ModeledAirQualityObservation[] | null,
      districtResult: DistrictStatus[] | null,
    ) => {
      if (!observationResult?.length) {
        setObservations(mockObservations);
        setDataMode("demo");
      } else {
        setObservations(observationResult);
        setDataMode("postgresql");
      }

      setWeatherMode(weatherResult?.length ? "postgresql" : "demo");
      setModeledAirQualityMode(modeledResult?.length ? "postgresql" : "demo");

      if (!districtResult?.length) {
        setDistrictStatuses(mockDistrictStatuses);
        setDistrictMode("demo");
      } else {
        setDistrictStatuses(districtResult);
        setDistrictMode("postgresql");
        setSelectedDistrictName((current) =>
          districtResult.some((district) => district.district_name === current)
            ? current
            : districtResult[0].district_name,
        );
      }
    },
    [],
  );

  const loadDashboard = useCallback(async () => {
    const results = await Promise.all([
      requestObservations(),
      requestWeather(),
      requestModeledAirQuality(),
      requestDistrictStatuses(),
    ]);
    applyResults(...results);
    setIsRefreshing(false);
  }, [applyResults]);

  useEffect(() => {
    let cancelled = false;

    void Promise.all([
      requestObservations(),
      requestWeather(),
      requestModeledAirQuality(),
      requestDistrictStatuses(),
    ]).then((results) => {
      if (!cancelled) applyResults(...results);
    });

    return () => {
      cancelled = true;
    };
  }, [applyResults]);

  const selectedDistrict = districtStatuses.find(
    (district) => district.district_name === selectedDistrictName,
  );
  const displayedAqi = selectedDistrict?.us_aqi;
  const displayedLocation = selectedDistrict?.district_name ?? selectedDistrictName;
  const chartRows = useMemo(
    () => [...observations].slice(0, 8).reverse(),
    [observations],
  );
  const maxChartAqi = Math.max(...chartRows.map((row) => row.aqi_us), 120);

  return (
    <main className="app-shell" id="top">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="AirTrace home">
          <span className="brand-mark">A</span>
          <span>
            <strong>AirTrace</strong>
            <small>Vietnam</small>
          </span>
        </a>

        <div className="workspace-title">
          <span>Hanoi air-quality operations</span>
          <small>Monitor · investigate · explain</small>
        </div>

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
              void loadDashboard();
            }}
            disabled={isRefreshing}
          >
            {isRefreshing ? "Refreshing…" : "Refresh data"}
          </button>
        </div>
      </header>

      <div className="workspace">
        <aside className="workspace-panel ai-panel" aria-labelledby="ai-activity-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">AI workspace</p>
              <h1 id="ai-activity-title">Activity graph</h1>
            </div>
            <span className="draft-badge">Draft</span>
          </div>

          <p className="panel-intro">
            A preview of the evidence AirTrace will use before producing an
            explanation.
          </p>

          <ol className="activity-flow">
            <li className={dataMode === "loading" ? "active" : "complete"}>
              <span className="flow-node" />
              <div>
                <strong>Read air-quality feed</strong>
                <small>{modeLabel(dataMode)} · IQAir observations</small>
              </div>
            </li>
            <li className={weatherMode === "loading" ? "active" : "complete"}>
              <span className="flow-node" />
              <div>
                <strong>Check weather and wind</strong>
                <small>{modeLabel(weatherMode)} · Open-Meteo</small>
              </div>
            </li>
            <li
              className={
                modeledAirQualityMode === "loading" ? "active" : "complete"
              }
            >
              <span className="flow-node" />
              <div>
                <strong>Compare pollutant signals</strong>
                <small>{modeLabel(modeledAirQualityMode)} · CAMS model</small>
              </div>
            </li>
            <li className="planned">
              <span className="flow-node" />
              <div>
                <strong>Build an AI summary</strong>
                <small>Coming soon · AI service not connected</small>
              </div>
            </li>
          </ol>

          <div className="draft-note">
            <strong>Still being built</strong>
            <p>
              This becomes an interactive evidence graph when the AI service is
              connected.
            </p>
          </div>
        </aside>

        <section className="center-column" aria-label="Map and historic air quality">
          <article className="workspace-panel map-panel" aria-labelledby="map-title">
            <div className="panel-heading map-heading">
              <div>
                <p className="eyebrow">Current conditions</p>
                <h2 id="map-title">Hanoi district map</h2>
              </div>
              <span className={`source-badge ${districtMode}`}>
                {districtMode === "loading"
                  ? "Loading districts"
                  : districtMode === "postgresql"
                    ? "Live model data"
                    : "Sample district data"}
              </span>
            </div>

            <DistrictMap
              districts={districtStatuses}
              onSelect={setSelectedDistrictName}
              selectedDistrictName={selectedDistrictName}
            />

            <div className="district-selection">
              <div>
                <span className="metric-label">Selected district</span>
                <strong>{displayedLocation}</strong>
              </div>
              <div className="report-context">
                <span className="report-context-dot" />
                <span>Selected as context for the future AI report</span>
              </div>
            </div>
          </article>

          <article className="workspace-panel history-panel" aria-labelledby="history-title">
            <div className="panel-heading history-heading">
              <div>
                <p className="eyebrow">Stored in PostgreSQL</p>
                <h2 id="history-title">Observation history</h2>
              </div>
              <div className="history-actions" aria-label="History range">
                <button className="range-button active" type="button">Recent</button>
                <button className="range-button" type="button" disabled>7 days · Soon</button>
                <button className="range-button" type="button" disabled>30 days · Soon</button>
              </div>
            </div>

            <p className="history-note">
              City-wide IQAir readings are shown separately from the selected
              district&apos;s CAMS-modelled AQI.
            </p>

            <div className="history-content">
              <div className="chart" aria-label="Recent Hanoi AQI bar chart">
                {chartRows.map((row, index) => (
                  <div className="chart-column" key={`${row.observed_at}-${index}`}>
                    <span>{row.aqi_us}</span>
                    <div
                      className="chart-bar"
                      style={{
                        height: `${Math.max((row.aqi_us / maxChartAqi) * 100, 8)}%`,
                      }}
                    />
                    <small>{formatTime(row.observed_at).split(", ").at(-1)}</small>
                  </div>
                ))}
              </div>

              <div className="table-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>Observed</th>
                      <th>US AQI</th>
                      <th>Pollutant</th>
                    </tr>
                  </thead>
                  <tbody>
                    {observations.slice(0, 4).map((row, index) => (
                      <tr key={`${row.observed_at}-history-${index}`}>
                        <td>{formatTime(row.observed_at)}</td>
                        <td><strong>{row.aqi_us}</strong></td>
                        <td>{readablePollutant(row.main_pollutant)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="history-footer">
              <code>air_quality_observations</code>
              <span>{observations.length} records loaded</span>
            </div>
          </article>
        </section>

        <aside className="workspace-panel chat-panel" aria-labelledby="chat-title">
          <div className="panel-heading">
            <div>
              <p className="eyebrow">AirTrace assistant</p>
              <h2 id="chat-title">Ask about the air</h2>
            </div>
            <span className="draft-badge">Draft</span>
          </div>

          <div className="chat-status">
            <span className="chat-status-icon">AI</span>
            <div>
              <strong>Chat is being built</strong>
              <small>The AI service is not connected yet.</small>
            </div>
          </div>

          <div className="chat-thread" aria-label="Draft chatbot conversation">
            <div className="chat-message assistant-message">
              <span>Draft report preview</span>
              <p>
                {typeof displayedAqi === "number"
                  ? `${displayedLocation} is currently ${aqiDescription(displayedAqi).toLowerCase()}. The AI report will explain the supporting evidence.`
                  : `A ${displayedLocation} summary will appear here when district data is available.`}
              </p>
            </div>
          </div>

          <div className="suggested-prompts">
            <span>Suggested prompts · Coming soon</span>
            <button type="button" disabled>Why is AQI elevated?</button>
            <button type="button" disabled>Which district has cleaner air?</button>
          </div>

          <div className="chat-composer">
            <label htmlFor="chat-input">Ask AirTrace</label>
            <div>
              <input
                id="chat-input"
                type="text"
                placeholder="Chat coming soon"
                disabled
              />
              <button type="button" disabled aria-label="Send message">→</button>
            </div>
            <small>Draft interface · messages cannot be sent yet</small>
          </div>
        </aside>
      </div>
    </main>
  );
}
