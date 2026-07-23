"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import {
  mockObservations,
  mockDistrictStatuses,
  type AirObservation,
  type DistrictStatus,
  type ModeledAirQualityObservation,
  type WeatherObservation,
} from "./mock-data";

const apiUrl =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type DataMode = "loading" | "postgresql" | "demo";

// Start fetching the map bundle as soon as the page JavaScript starts, instead
// of waiting until React reaches the map component during rendering.
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

function windDirectionLabel(degrees: number) {
  const directions = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"];
  return directions[Math.round(degrees / 45) % directions.length];
}

function formatNumber(value: number | null | undefined, digits = 1) {
  return typeof value === "number" ? value.toFixed(digits) : "–";
}

export default function Home() {
  const [observations, setObservations] =
    useState<AirObservation[]>([]);
  const [districtStatuses, setDistrictStatuses] =
    useState<DistrictStatus[]>([]);
  const [dataMode, setDataMode] = useState<DataMode>("loading");
  const [weatherMode, setWeatherMode] = useState<DataMode>("loading");
  const [modeledAirQualityMode, setModeledAirQualityMode] =
    useState<DataMode>("loading");
  const [districtMode, setDistrictMode] = useState<DataMode>("loading");
  const [selectedDistrictName, setSelectedDistrictName] = useState("Hoan Kiem");
  const [isRefreshing, setIsRefreshing] = useState(false);

  const loadObservations = useCallback(async () => {
    const [result, weatherResult, modeledAirQualityResult, districtResult] = await Promise.all([
      requestObservations(),
      requestWeather(),
      requestModeledAirQuality(),
      requestDistrictStatuses(),
    ]);
    if (!result?.length) {
      setObservations(mockObservations);
      setDataMode("demo");
    } else {
      setObservations(result);
      setDataMode("postgresql");
    }
    if (!weatherResult?.length) {
      setWeatherMode("demo");
    } else {
      setWeatherMode("postgresql");
    }
    if (!modeledAirQualityResult?.length) {
      setModeledAirQualityMode("demo");
    } else {
      setModeledAirQualityMode("postgresql");
    }
    if (districtResult === null) {
      setDistrictStatuses(mockDistrictStatuses);
      setDistrictMode("demo");
    } else {
      setDistrictStatuses(districtResult);
      setDistrictMode("postgresql");
      if (districtResult.length) {
        setSelectedDistrictName((current) =>
          districtResult.some((district) => district.district_name === current)
            ? current
            : districtResult[0].district_name,
        );
      }
    }
    setIsRefreshing(false);
  }, []);

  useEffect(() => {
    let cancelled = false;

    void Promise.all([
      requestObservations(),
      requestWeather(),
      requestModeledAirQuality(),
      requestDistrictStatuses(),
    ]).then(([
      result,
      weatherResult,
      modeledAirQualityResult,
      districtResult,
    ]) => {
      if (cancelled) return;

      if (!result?.length) {
        setObservations(mockObservations);
        setDataMode("demo");
      } else {
        setObservations(result);
        setDataMode("postgresql");
      }
      if (!weatherResult?.length) {
        setWeatherMode("demo");
      } else {
        setWeatherMode("postgresql");
      }
      if (!modeledAirQualityResult?.length) {
        setModeledAirQualityMode("demo");
      } else {
        setModeledAirQualityMode("postgresql");
      }
      if (districtResult === null) {
        setDistrictStatuses(mockDistrictStatuses);
        setDistrictMode("demo");
      } else {
        setDistrictStatuses(districtResult);
        setDistrictMode("postgresql");
        if (districtResult.length) {
          setSelectedDistrictName((current) =>
            districtResult.some((district) => district.district_name === current)
              ? current
              : districtResult[0].district_name,
          );
        }
      }
    });

    return () => {
      cancelled = true;
    };
  }, []);

  const selectedDistrict = districtStatuses.find(
    (district) => district.district_name === selectedDistrictName,
  );
  const displayedAqi = selectedDistrict?.us_aqi;
  const displayedLocation = selectedDistrict?.district_name ?? selectedDistrictName;
  const displayedObservedAt = selectedDistrict?.air_quality_observed_at;
  const displayedWindSpeed = selectedDistrict?.wind_speed_kmh;
  const displayedWindDirection = selectedDistrict?.wind_direction_degrees;
  const displayedTemperature = selectedDistrict?.temperature_c;
  const displayedHumidity = selectedDistrict?.relative_humidity_percent;
  const displayedPm25 = selectedDistrict?.pm2_5_ug_m3;
  const displayedPm10 = selectedDistrict?.pm10_ug_m3;
  const displayedNo2 = selectedDistrict?.nitrogen_dioxide_ug_m3;
  const displayedSo2 = selectedDistrict?.sulphur_dioxide_ug_m3;
  const displayedCo = selectedDistrict?.carbon_monoxide_ug_m3;
  const displayedOzone = selectedDistrict?.ozone_ug_m3;
  const hasDistrictData = displayedAqi !== null && displayedAqi !== undefined;
  const collectedDistrictCount = districtStatuses.filter(
    (district) => district.us_aqi !== null && district.us_aqi !== undefined,
  ).length;
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
              <span className="location-pill">{displayedLocation}</span>
            </div>
            <div className="aqi-reading">
              <strong>{displayedAqi ?? "–"}</strong>
              <div>
                <span>
                  {displayedAqi !== null && displayedAqi !== undefined
                    ? aqiDescription(displayedAqi)
                    : "Awaiting collection"}
                </span>
                <small>Modelled district AQI</small>
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
              <span>District explorer</span>
              <span className="coordinates">
                {districtMode === "loading"
                  ? "Loading district data…"
                  : districtMode === "postgresql"
                    ? "Live model data"
                    : "Sample data"}
              </span>
            </div>
            <DistrictMap
              districts={districtStatuses}
              onSelect={setSelectedDistrictName}
              selectedDistrictName={selectedDistrictName}
            />
            <div className="district-detail">
              <strong>{selectedDistrict?.district_name}</strong>
              <span>AQI {displayedAqi ?? "–"} · PM2.5 {formatNumber(displayedPm25)} µg/m³</span>
              <small>Wind {formatNumber(displayedWindSpeed)} km/h {displayedWindDirection === null || displayedWindDirection === undefined ? "–" : windDirectionLabel(displayedWindDirection)}</small>
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
                <dd>{displayedObservedAt ? formatTime(displayedObservedAt) : "Awaiting collection"}</dd>
              </div>
              <div>
                <dt>Collected</dt>
                <dd>{selectedDistrict?.weather_observed_at ? formatTime(selectedDistrict.weather_observed_at) : "Awaiting collection"}</dd>
              </div>
              <div>
                <dt>Provider</dt>
                <dd>{hasDistrictData ? "Open-Meteo CAMS" : "No district record"}</dd>
              </div>
              <div>
                <dt>Records loaded</dt>
                <dd>{collectedDistrictCount} of 8 live</dd>
              </div>
            </dl>
          </article>
        </section>

        <section className="detail-grid">
          <article className="panel trend-panel">
            <div className="panel-title">
              <div>
                <p className="eyebrow">City-wide IQAir observations</p>
                <h2>Hanoi AQI trend</h2>
              </div>
              <span className="time-zone">Separate feed</span>
            </div>
            <p className="trend-note">
              This is IQAir&apos;s city-wide series. It is not directly comparable
              to the selected district&apos;s CAMS-modelled AQI above.
            </p>
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
                <h2>Weather context available</h2>
              </div>
              <span className="not-ready">Not active</span>
            </div>
            <p className="investigation-copy">
              Wind can show whether a possible source sits upwind of Hanoi. This
              is useful context, but one city-level air reading is still not enough
              to attribute a pollution event.
            </p>
            <div className="evidence-list">
              <div><span>Air quality</span><strong className="connected">Connected</strong></div>
              <div>
                <span>Weather and wind</span>
                <strong className={weatherMode === "postgresql" ? "connected" : undefined}>
                  {weatherMode === "postgresql" ? "Connected" : "Sample"}
                </strong>
              </div>
              <div>
                <span>Pollutant signature</span>
                <strong className={modeledAirQualityMode === "postgresql" ? "connected" : undefined}>
                  {modeledAirQualityMode === "postgresql" ? "Connected" : "Sample"}
                </strong>
              </div>
              <div><span>Traffic and fires</span><strong>Planned</strong></div>
            </div>
          </article>
        </section>

        <section className="panel pollutant-panel" aria-label="Modeled pollutant signature">
          <div className="panel-title">
            <div>
              <p className="eyebrow">Pollutant context</p>
              <h2>Pollutant signature — {displayedLocation}</h2>
            </div>
            <span
              className={
                modeledAirQualityMode === "postgresql"
                  ? "weather-source"
                  : "weather-source sample"
              }
            >
              {modeledAirQualityMode === "postgresql" ? "CAMS model" : "Sample model"}
            </span>
          </div>
          <p className="model-note">
            Concentrations in µg/m³ from a regional atmospheric model, useful for
            comparing pollutant patterns but not a replacement for local sensors.
          </p>
          <div className="pollutant-grid">
            <div><span>PM2.5</span><strong>{formatNumber(displayedPm25)}</strong></div>
            <div><span>PM10</span><strong>{formatNumber(displayedPm10)}</strong></div>
            <div><span>NO₂</span><strong>{formatNumber(displayedNo2)}</strong></div>
            <div><span>SO₂</span><strong>{formatNumber(displayedSo2)}</strong></div>
            <div><span>CO</span><strong>{formatNumber(displayedCo)}</strong></div>
            <div><span>O₃</span><strong>{formatNumber(displayedOzone)}</strong></div>
          </div>
        </section>

        <section
          className="panel weather-panel"
          aria-label="Current weather and wind"
        >
          <div className="panel-title">
            <div>
              <p className="eyebrow">Weather context</p>
              <h2>Current wind — {displayedLocation}</h2>
            </div>
            <span
              className={
                weatherMode === "postgresql"
                  ? "weather-source"
                  : "weather-source sample"
              }
            >
              {weatherMode === "postgresql" ? "Open-Meteo" : "Sample weather"}
            </span>
          </div>
          <div className="weather-grid">
            <div>
              <span>Wind</span>
              <strong>
                {formatNumber(displayedWindSpeed)} km/h {displayedWindDirection === null || displayedWindDirection === undefined ? "–" : windDirectionLabel(displayedWindDirection)}
              </strong>
              <small>from {displayedWindDirection ?? "–"}°</small>
            </div>
            <div>
              <span>Gusts</span>
              <strong>{formatNumber(selectedDistrict?.wind_gusts_kmh)} km/h</strong>
              <small>10 m above ground</small>
            </div>
            <div>
              <span>Temperature</span>
              <strong>{formatNumber(displayedTemperature)}°C</strong>
              <small>{formatNumber(displayedHumidity, 0)}% humidity</small>
            </div>
            <div>
              <span>Precipitation</span>
              <strong>{formatNumber(selectedDistrict?.precipitation_mm)} mm</strong>
              <small>Observed {selectedDistrict?.weather_observed_at ? formatTime(selectedDistrict.weather_observed_at) : "–"}</small>
            </div>
          </div>
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
          <span>IQAir + Open-Meteo → PostgreSQL → Python API → this dashboard</span>
        </footer>
      </div>
    </main>
  );
}
