"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useState } from "react";
import {
  mockDistrictStatuses,
  mockObservations,
  type AirObservation,
  type DistrictAirQualityHistoryObservation,
  type DistrictStatus,
  type ModeledAirQualityObservation,
  type WeatherObservation,
} from "./mock-data";
import HistoryLineChart from "./history-line-chart";
import EvidenceGraph from "./evidence-graph";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type DataMode = "loading" | "postgresql" | "demo";
type HistoryMode = "loading" | "postgresql" | "unavailable";
type HistoryDays = 7 | 30 | 365;
type InvestigationView = "graph" | "report" | "reasoning" | "activity";
type HistoryDisplayObservation = {
  observed_on: string;
  us_aqi: number | null;
  pm2_5_ug_m3: number | null;
  sample_count: number;
};

type InvestigationReport = {
  title: string;
  summary: string;
  numeric_summary: Array<{
    label: string;
    value: string;
    source: string;
    kind?: string;
    severity?: string;
  }>;
  potential_causes: Array<{ label: string; detail: string }>;
  data_quality: string;
  ai_status?: string;
  recommended_action?: {
    type: string;
    description: string;
    requires_human_approval: boolean;
  };
  hypothesis_ranking?: Array<{
    label: string;
    score: number;
    supporting_evidence: string[];
    contradicting_evidence: string[];
  }>;
  assessment_method?: string;
  comparison_note?: string;
  comparison_mode?: boolean;
};

type AgentToolTrace = {
  tool_name: string;
  status: string;
  summary: string;
};

type EvidenceSourceStatus = {
  available_source_count: number;
  sources: Array<{ id: string; label: string; status: string }>;
};

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

async function requestDistrictAirQualityHistory(
  districtName: string,
  days: HistoryDays,
) {
  try {
    const query = new URLSearchParams({
      district_name: districtName,
      days: String(days),
    });
    const response = await fetch(
      `${apiUrl}/api/district-air-quality-history?${query}`,
    );
    if (!response.ok) return null;

    const result = (await response.json()) as {
      observations: DistrictAirQualityHistoryObservation[];
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

async function requestDistrictEvidenceStatus(districtName: string) {
  try {
    const query = new URLSearchParams({ district_name: districtName });
    const response = await fetch(`${apiUrl}/api/district-evidence-status?${query}`);
    if (!response.ok) return null;
    return (await response.json()) as EvidenceSourceStatus;
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

function formatHistoryDate(value: string) {
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(date);
}

function formatHistoryMonth(value: string) {
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("en-GB", {
    month: "short",
    year: "numeric",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(date);
}

function aqiBand(value: number | null) {
  if (value === null) return "Unavailable";
  if (value <= 50) return "Good";
  if (value <= 100) return "Moderate";
  if (value <= 150) return "Unhealthy for sensitive groups";
  if (value <= 200) return "Unhealthy";
  return "Very unhealthy";
}

function monthlyHistoryAverages(
  rows: DistrictAirQualityHistoryObservation[],
): HistoryDisplayObservation[] {
  const monthly = new Map<
    string,
    {
      aqiSum: number;
      aqiCount: number;
      pm2_5Sum: number;
      pm2_5Count: number;
      sampleDates: Set<string>;
    }
  >();

  for (const row of rows) {
    const month = row.observed_on.slice(0, 7);
    const values = monthly.get(month) ?? {
      aqiSum: 0,
      aqiCount: 0,
      pm2_5Sum: 0,
      pm2_5Count: 0,
      sampleDates: new Set<string>(),
    };

    values.sampleDates.add(row.observed_on);
    if (row.us_aqi !== null) {
      values.aqiSum += row.us_aqi;
      values.aqiCount += 1;
    }
    if (row.pm2_5_ug_m3 !== null) {
      values.pm2_5Sum += row.pm2_5_ug_m3;
      values.pm2_5Count += 1;
    }
    monthly.set(month, values);
  }

  return [...monthly.entries()]
    .sort(([left], [right]) => left.localeCompare(right))
    .slice(-12)
    .map(([month, values]) => ({
      observed_on: `${month}-01`,
      us_aqi: values.aqiCount ? values.aqiSum / values.aqiCount : null,
      pm2_5_ug_m3: values.pm2_5Count
        ? values.pm2_5Sum / values.pm2_5Count
        : null,
      sample_count: values.sampleDates.size,
    }));
}

export default function Home() {
  const [observations, setObservations] = useState<AirObservation[]>([]);
  const [districtHistory, setDistrictHistory] = useState<
    DistrictAirQualityHistoryObservation[]
  >([]);
  const [districtStatuses, setDistrictStatuses] = useState<DistrictStatus[]>([]);
  const [evidenceSourceStatus, setEvidenceSourceStatus] =
    useState<EvidenceSourceStatus | null>(null);
  const [dataMode, setDataMode] = useState<DataMode>("loading");
  const [weatherMode, setWeatherMode] = useState<DataMode>("loading");
  const [modeledAirQualityMode, setModeledAirQualityMode] =
    useState<DataMode>("loading");
  const [districtMode, setDistrictMode] = useState<DataMode>("loading");
  const [historyMode, setHistoryMode] = useState<HistoryMode>("loading");
  const [historyDays, setHistoryDays] = useState<HistoryDays>(30);
  const [selectedDistrictName, setSelectedDistrictName] = useState("Hoan Kiem");
  const [comparisonDistrictName, setComparisonDistrictName] = useState<string | null>(null);
  const [showComparisonSuggestion, setShowComparisonSuggestion] = useState(false);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [chatPrompt, setChatPrompt] = useState("");
  const [report, setReport] = useState<InvestigationReport | null>(null);
  const [toolTrace, setToolTrace] = useState<AgentToolTrace[]>([]);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [processingStage, setProcessingStage] = useState(0);
  const [reportError, setReportError] = useState<string | null>(null);
  const [investigationView, setInvestigationView] =
    useState<InvestigationView>("graph");

  const applyResults = useCallback(
    (
      observationResult: AirObservation[] | null,
      weatherResult: WeatherObservation[] | null,
      modeledResult: ModeledAirQualityObservation[] | null,
      districtResult: DistrictStatus[] | null,
      historyResult: DistrictAirQualityHistoryObservation[] | null,
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

      if (!historyResult?.length) {
        setDistrictHistory([]);
        setHistoryMode("unavailable");
      } else {
        setDistrictHistory(historyResult);
        setHistoryMode("postgresql");
      }

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
    const [
      observationResult,
      weatherResult,
      modeledResult,
      districtResult,
      historyResult,
      evidenceResult,
    ] = await Promise.all([
      requestObservations(),
      requestWeather(),
      requestModeledAirQuality(),
      requestDistrictStatuses(),
      requestDistrictAirQualityHistory(selectedDistrictName, historyDays),
      requestDistrictEvidenceStatus(selectedDistrictName),
    ]);
    applyResults(
      observationResult,
      weatherResult,
      modeledResult,
      districtResult,
      historyResult,
    );
    setEvidenceSourceStatus(evidenceResult);
    setIsRefreshing(false);
  }, [applyResults, historyDays, selectedDistrictName]);

  useEffect(() => {
    let cancelled = false;

    void Promise.all([
      requestObservations(),
      requestWeather(),
      requestModeledAirQuality(),
      requestDistrictStatuses(),
      requestDistrictAirQualityHistory(selectedDistrictName, historyDays),
      requestDistrictEvidenceStatus(selectedDistrictName),
    ]).then(([
      observationResult,
      weatherResult,
      modeledResult,
      districtResult,
      historyResult,
      evidenceResult,
    ]) => {
      if (!cancelled) {
        applyResults(
          observationResult,
          weatherResult,
          modeledResult,
          districtResult,
          historyResult,
        );
        setEvidenceSourceStatus(evidenceResult);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [applyResults, historyDays, selectedDistrictName]);

  const selectedDistrict = districtStatuses.find(
    (district) => district.district_name === selectedDistrictName,
  );
  const displayedLocation = selectedDistrict?.district_name ?? selectedDistrictName;
  const selectedAqi = selectedDistrict?.us_aqi ?? observations[0]?.aqi_us ?? null;
  const selectedPm25 = selectedDistrict?.pm2_5_ug_m3 ?? null;
  const selectedWind = selectedDistrict?.wind_speed_kmh ?? null;
  const selectedObservedAt =
    selectedDistrict?.air_quality_observed_at ?? observations[0]?.observed_at ?? null;
  const comparisonSuggestionTarget = districtStatuses.find(
    (district) => district.district_name !== displayedLocation,
  )?.district_name;
  const isMonthlyHistory = historyDays === 365;
  const displayedHistory = useMemo<HistoryDisplayObservation[]>(
    () =>
      isMonthlyHistory
        ? monthlyHistoryAverages(districtHistory)
        : districtHistory.map((row) => ({
            observed_on: row.observed_on,
            us_aqi: row.us_aqi,
            pm2_5_ug_m3: row.pm2_5_ug_m3,
            sample_count: 1,
          })),
    [districtHistory, isMonthlyHistory],
  );
  const historyWithAqi = useMemo(
    () => displayedHistory.filter((row) => row.us_aqi !== null),
    [displayedHistory],
  );
  const chartRows = useMemo(
    () => historyWithAqi.slice(isMonthlyHistory ? -12 : -10),
    [historyWithAqi, isMonthlyHistory],
  );
  const maxChartAqi = Math.max(
    ...chartRows.map((row) => row.us_aqi ?? 0),
    120,
  );

  const selectDistrictForInspection = useCallback((districtName: string) => {
    setSelectedDistrictName(districtName);
    setComparisonDistrictName(null);
    setShowComparisonSuggestion(true);
    setHistoryMode("loading");
    setChatPrompt(`Inspect ${districtName} air quality`);
    setReport(null);
    setToolTrace([]);
    setReportError(null);
    setInvestigationView("graph");
  }, []);

  useEffect(() => {
    if (!isGeneratingReport) return;
    const interval = window.setInterval(() => {
      setProcessingStage((stage) => (stage + 1) % 6);
    }, 1100);
    return () => window.clearInterval(interval);
  }, [isGeneratingReport]);

  const sendInspection = useCallback(async (
    promptOverride?: string,
    comparisonOverride?: string | null,
  ) => {
    const prompt = (promptOverride ?? chatPrompt).trim();
    const activeComparison = comparisonOverride === undefined
      ? comparisonDistrictName
      : comparisonOverride;
    if (!prompt || isGeneratingReport) return;

    setShowComparisonSuggestion(false);
    setProcessingStage(0);
    setIsGeneratingReport(true);
    setReportError(null);
    setInvestigationView("graph");
    try {
      const response = await fetch(`${apiUrl}/api/investigate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          district_name: selectedDistrictName,
          comparison_district_name: activeComparison,
          prompt,
        }),
      });
      const result = (await response.json()) as {
        report?: InvestigationReport;
        tool_trace?: AgentToolTrace[];
        detail?: string;
      };
      if (!response.ok || !result.report) {
        throw new Error(result.detail ?? "AerX could not generate a report.");
      }
      setReport(result.report);
      setToolTrace(result.tool_trace ?? []);
      setInvestigationView("report");
    } catch (error) {
      setReportError(
        error instanceof Error ? error.message : "AerX could not generate a report.",
      );
    } finally {
      setIsGeneratingReport(false);
    }
  }, [chatPrompt, comparisonDistrictName, isGeneratingReport, selectedDistrictName]);

  const prepareComparisonSuggestion = () => {
    if (!comparisonSuggestionTarget || isGeneratingReport) return;
    const prompt = `Compare ${displayedLocation} air quality with ${comparisonSuggestionTarget}`;
    setComparisonDistrictName(comparisonSuggestionTarget);
    setShowComparisonSuggestion(false);
    setChatPrompt(prompt);
    setReport(null);
    setToolTrace([]);
    setReportError(null);
    setInvestigationView("graph");
  };

  return (
    <main className="app-shell" id="top">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="AerX home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 56 56" focusable="false">
              <path className="brand-oxygen-shell" d="M29 5C15.7 4.3 5 14.6 5 28s10.7 23.7 24 23c10.2-.5 18.8-7.4 21.3-16.8" />
              <path className="brand-oxygen-orbit" d="M41.3 9.6C48.3 14 51 22.3 48.2 29.8c-2.7 7.4-10.3 12.4-18.2 11.6" />
              <path className="brand-wind-main" d="M9.5 24.2c3.1-4.7 6.2-4.7 9.3 0s6.2 4.7 9.3 0 6.2-4.7 9.3 0 6.2 4.7 9.3 0" />
              <path className="brand-wind-echo" d="M16.6 31.9c2.1-3.1 4.2-3.1 6.3 0s4.2 3.1 6.3 0 4.2-3.1 6.3 0" />
              <circle className="brand-air-node" cx="45.2" cy="10.6" r="3.1" />
            </svg>
          </span>
          <span>
            <strong>AerX</strong>
            <small>Hanoi air intelligence</small>
          </span>
        </a>

        <div className="location-context" aria-label={`Selected location: Hanoi, ${displayedLocation}`}>
          <span aria-hidden="true">⌖</span>
          <strong>Hanoi / {displayedLocation}</strong>
          <small>District workspace</small>
        </div>

        <div className="header-actions">
          <div className={`data-status ${dataMode}`}>
            <span className="status-dot" />
            {dataMode === "loading"
              ? "Connecting…"
              : dataMode === "postgresql"
                ? "Live · PostgreSQL"
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

      <div className="workspace lab-workspace">
        <section className="environment-workspace" aria-label="Hanoi air quality overview">
          <section className="workspace-panel metric-ribbon" aria-label="Current district metrics">
            <article className="metric-cell metric-aqi">
              <span>US AQI</span>
              <strong>{selectedAqi === null ? "—" : Math.round(selectedAqi)}</strong>
              <small>{aqiBand(selectedAqi)}</small>
            </article>
            <article className="metric-cell">
              <span>PM2.5</span>
              <strong>{selectedPm25 === null ? "—" : selectedPm25.toFixed(1)}</strong>
              <small>{selectedPm25 === null ? "No district value" : "µg/m³"}</small>
            </article>
            <article className="metric-cell">
              <span>Wind</span>
              <strong>{selectedWind === null ? "—" : selectedWind.toFixed(1)}</strong>
              <small>{selectedWind === null ? "No weather value" : "km/h"}</small>
            </article>
            <article className="metric-cell metric-sources">
              <span>Evidence</span>
              <strong>{evidenceSourceStatus?.available_source_count ?? "—"}</strong>
              <small>
                {evidenceSourceStatus ? "evidence sources" : "checking sources"}
              </small>
            </article>
          </section>

          <article className="workspace-panel map-panel" aria-labelledby="map-title">
            <div className="panel-heading map-heading">
              <div>
                <p className="eyebrow">Current conditions</p>
                <h1 id="map-title">Hanoi district map</h1>
              </div>
              <div className="map-heading-meta">
                <span className={`source-badge ${districtMode}`}>
                  {districtMode === "loading"
                    ? "Loading districts"
                    : districtMode === "postgresql"
                      ? "Live model data"
                      : "Sample district data"}
                </span>
                {selectedObservedAt && <small>Updated {formatTime(selectedObservedAt)} ICT</small>}
              </div>
            </div>

            <DistrictMap
              districts={districtStatuses}
              onSelect={selectDistrictForInspection}
              selectedDistrictName={selectedDistrictName}
            />

            <div className="district-selection">
              <div>
                <span className="metric-label">Selected district</span>
                <strong>{displayedLocation}</strong>
              </div>
              <div className="selection-facts" aria-label="Selected district evidence summary">
                <span>{aqiBand(selectedAqi)}</span>
                <span>{readablePollutant(observations[0]?.main_pollutant ?? "p2")} main pollutant</span>
                <span>Click another district to inspect</span>
              </div>
            </div>
          </article>

          <article className="workspace-panel history-panel" aria-labelledby="history-title">
            <div className="panel-heading history-heading">
              <div>
                <p className="eyebrow">Historical evidence</p>
                <h2 id="history-title">{displayedLocation} · {historyDays === 365 ? "12-month" : `${historyDays}-day`} history</h2>
              </div>
              <div className="history-actions" aria-label="History range">
                {([7, 30, 365] as HistoryDays[]).map((days) => (
                  <button
                    className={`range-button ${historyDays === days ? "active" : ""}`}
                    key={days}
                    onClick={() => setHistoryDays(days)}
                    type="button"
                  >
                    {days === 365 ? "1 year" : `${days} days`}
                  </button>
                ))}
              </div>
            </div>

            {historyMode === "loading" ? (
              <div className="history-empty">Loading historical records…</div>
            ) : historyMode === "unavailable" ? (
              <div className="history-empty">
                No modeled history is available for {displayedLocation}.
              </div>
            ) : (
              <div className="history-content">
                {historyDays === 30 ? (
                  <HistoryLineChart location={displayedLocation} rows={displayedHistory} />
                ) : (
                  <div
                    className="chart"
                    aria-label={`${isMonthlyHistory ? "Monthly" : "Daily"} historical ${displayedLocation} US AQI bar chart`}
                  >
                    {chartRows.map((row) => (
                      <div className="chart-column" key={row.observed_on}>
                        <span>{Math.round(row.us_aqi ?? 0)}</span>
                        <div
                          className="chart-bar"
                          style={{
                            height: `${Math.max(((row.us_aqi ?? 0) / maxChartAqi) * 100, 8)}%`,
                          }}
                        />
                        <small>
                          {isMonthlyHistory
                            ? formatHistoryMonth(row.observed_on).slice(0, 3)
                            : formatHistoryDate(row.observed_on).slice(0, 6)}
                        </small>
                      </div>
                    ))}
                  </div>
                )}
                <div className="history-summary">
                  <span>Latest modeled value</span>
                  <strong>{historyWithAqi.at(-1)?.us_aqi === null || historyWithAqi.at(-1)?.us_aqi === undefined
                    ? "—"
                    : Math.round(historyWithAqi.at(-1)!.us_aqi!)}</strong>
                  <small>US AQI</small>
                </div>
              </div>
            )}

            <div className="history-footer">
              <code>district_air_quality_history</code>
              <span>
                {historyMode === "postgresql"
                  ? isMonthlyHistory
                    ? `${displayedHistory.length} monthly means from ${districtHistory.length} daily records`
                    : `${districtHistory.length} daily records loaded`
                  : "Awaiting database import"}
              </span>
            </div>
          </article>
        </section>

        <aside className="workspace-panel ai-panel chat-panel investigation-panel" aria-labelledby="investigation-title">
          <div className="investigation-heading">
            <div>
              <p className="eyebrow">AerX workspace</p>
              <h2 id="investigation-title">Investigation</h2>
            </div>
            <span className={`investigation-state ${isGeneratingReport ? "running" : report ? "ready" : "idle"}`}>
              <i />
              {isGeneratingReport ? "Agent working" : report ? "Report ready" : "Ready"}
            </span>
          </div>

          <div className="investigation-tabs" role="tablist" aria-label="Investigation views">
            {([
              ["graph", "Node graph"],
              ["report", "Report"],
              ["reasoning", "Reasoning trail"],
              ["activity", "Activity log"],
            ] as Array<[InvestigationView, string]>).map(([view, label]) => (
              <button
                type="button"
                role="tab"
                key={view}
                aria-selected={investigationView === view}
                className={investigationView === view ? "active" : ""}
                disabled={view === "report" && !report}
                onClick={() => setInvestigationView(view)}
              >
                {label}
                {view === "report" && report && <i aria-label="Report ready" />}
              </button>
            ))}
          </div>

          <div className="investigation-body">
            {investigationView === "graph" && (
              <section className="graph-view" role="tabpanel" aria-label="Node graph">
                <div className="graph-view-status">
                  <span><i />9 nodes · Live trace</span>
                  <small>{displayedLocation} evidence workspace</small>
                </div>
                <EvidenceGraph
                  districtName={displayedLocation}
                  dataMode={dataMode}
                  weatherMode={weatherMode}
                  modeledAirQualityMode={modeledAirQualityMode}
                  isGeneratingReport={isGeneratingReport}
                  reportReady={Boolean(report)}
                  toolTrace={toolTrace}
                  onOpenReport={() => setInvestigationView("report")}
                />

                {isGeneratingReport && (
                  <article className="agent-processing-card" aria-live="polite">
                    <div className="processing-loader" aria-hidden="true" />
                    <div>
                      <span>AerX investigation in progress</span>
                      <strong>
                        {[
                          "Checking DataHub source contracts",
                          "Reading district air and pollutant evidence",
                          "Checking weather, wind, and dispersion context",
                          "Comparing TomTom traffic conditions",
                          "Checking NASA FIRMS satellite thermal detections",
                          comparisonDistrictName
                            ? `Comparing ${displayedLocation} with ${comparisonDistrictName}`
                            : "Writing a cautious evidence-backed report",
                        ][processingStage]}
                      </strong>
                    </div>
                    <div className="processing-steps" aria-hidden="true">
                      {[0, 1, 2, 3, 4, 5].map((stage) => (
                        <i key={stage} className={stage <= processingStage ? "done" : ""} />
                      ))}
                    </div>
                  </article>
                )}

                {report && !isGeneratingReport && (
                  <button className="report-preview" type="button" onClick={() => setInvestigationView("report")}>
                    <span>Insight · Evidence-backed</span>
                    <strong>{report.title}</strong>
                    <p>{report.summary}</p>
                    <small>Open full report →</small>
                  </button>
                )}
              </section>
            )}

            {investigationView === "report" && report && (
              <article className="investigation-report" role="tabpanel" aria-label="AerX report">
                <div className="report-toolbar">
                  <button type="button" onClick={() => setInvestigationView("graph")}>← Back to node graph</button>
                  <span><i />Evidence-backed · {toolTrace.length} tool checks completed</span>
                </div>
                <div className="report-document">
                  <span className="report-eyebrow">AerX report</span>
                  <h3>{report.title}</h3>
                  <p className="report-summary">{report.summary}</p>

                  <dl className="report-metrics">
                    {report.numeric_summary.map((metric) => (
                      <div
                        key={`${metric.label}-${metric.source}`}
                        className={[
                          "report-metric",
                          metric.kind ? `metric-${metric.kind}` : "",
                          metric.severity ? `metric-${metric.severity}` : "",
                        ].filter(Boolean).join(" ")}
                      >
                        <dt>{metric.label}</dt>
                        <dd>{metric.value}</dd>
                        <small>{metric.source}</small>
                      </div>
                    ))}
                  </dl>

                  <div className="report-analysis-grid">
                    <section className={report.comparison_mode ? "comparison-analysis" : "report-causes"}>
                      <strong>{report.comparison_mode ? "What the evidence suggests" : "Potential causes"}</strong>
                      {report.potential_causes.map((cause) => (
                        <article key={`${cause.label}-${cause.detail}`}>
                          <span aria-hidden="true">{cause.label.slice(0, 1)}</span>
                          <div><b>{cause.label}</b><p>{cause.detail}</p></div>
                        </article>
                      ))}
                    </section>

                    {!report.comparison_mode && report.hypothesis_ranking && (
                      <section className="hypothesis-ranking">
                        <strong>Evidence ranking</strong>
                        <small>{report.assessment_method}</small>
                        {report.hypothesis_ranking.map((hypothesis) => (
                          <article className="hypothesis-row" key={hypothesis.label}>
                            <div><b>{hypothesis.label}</b><span>{hypothesis.score}</span></div>
                            <div className="confidence-track" aria-label={`${hypothesis.label}: ${hypothesis.score} out of 100`}>
                              <i style={{ width: `${Math.min(100, Math.max(0, hypothesis.score))}%` }} />
                            </div>
                            {hypothesis.contradicting_evidence.length > 0 && (
                              <p><em>Limits:</em> {hypothesis.contradicting_evidence.join(" ")}</p>
                            )}
                          </article>
                        ))}
                      </section>
                    )}
                  </div>

                  {!report.comparison_mode && (
                    <section className="report-quality"><strong>Data quality</strong><p>{report.data_quality}</p></section>
                  )}
                  {report.comparison_note && <p className="report-quality comparison-note">{report.comparison_note}</p>}
                  {report.ai_status && <p className="report-quality">{report.ai_status}</p>}

                  <footer className="report-provenance">
                    <div><span>IQAir</span><span>Weather</span><span>CAMS</span><span>Traffic</span><span>NASA FIRMS</span></div>
                    <button type="button" onClick={() => setInvestigationView("activity")}>View activity trace ↗</button>
                  </footer>
                </div>
              </article>
            )}

            {investigationView === "reasoning" && (
              <section className="reasoning-view" role="tabpanel" aria-label="Reasoning trail">
                <div className="secondary-view-heading">
                  <span>Evidence interpretation</span>
                  <h3>Reasoning trail</h3>
                  <p>AerX separates supporting signals from limitations before it writes the report.</p>
                </div>
                {report?.hypothesis_ranking?.length ? report.hypothesis_ranking.map((hypothesis, index) => (
                  <article className="reasoning-step" key={hypothesis.label}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <div>
                      <h4>{hypothesis.label}<small>{hypothesis.score}/100</small></h4>
                      <p><b>Supports:</b> {hypothesis.supporting_evidence.join(" ") || "No supporting evidence recorded."}</p>
                      <p><b>Limits:</b> {hypothesis.contradicting_evidence.join(" ") || "No contradiction recorded."}</p>
                    </div>
                  </article>
                )) : <div className="investigation-empty">Generate a report to inspect its reasoning trail.</div>}
              </section>
            )}

            {investigationView === "activity" && (
              <section className="activity-view" role="tabpanel" aria-label="Activity log">
                <div className="secondary-view-heading">
                  <span>Agent provenance</span>
                  <h3>Activity log</h3>
                  <p>Every allowlisted tool call used to assemble the evidence package appears here.</p>
                </div>
                <article className="tool-trace-card">
                  <span>Agent evidence trail</span>
                  {toolTrace.length ? toolTrace.map((tool, index) => (
                    <div key={`${tool.tool_name}-${index}`}>
                      <strong>{tool.tool_name.replaceAll("_", " ")}</strong>
                      <small className={`tool-status ${tool.status}`}>{tool.status.replaceAll("_", " ")}</small>
                      <p>{tool.summary}</p>
                    </div>
                  )) : (
                    <div><strong>No investigation yet</strong><p>Ask AerX a question to create a verified activity trace.</p></div>
                  )}
                </article>
              </section>
            )}

            {reportError && <p className="report-error">{reportError}</p>}
          </div>

          <div className="chat-composer">
            {showComparisonSuggestion && comparisonSuggestionTarget && !isGeneratingReport && (
              <button className="comparison-suggestion" type="button" onClick={prepareComparisonSuggestion}>
                Compare {displayedLocation} with {comparisonSuggestionTarget}
              </button>
            )}
            <label htmlFor="chat-input">
              {report && investigationView === "report" ? "Ask a follow-up about this report" : `Ask about ${displayedLocation}`}
            </label>
            <div>
              <input
                id="chat-input"
                type="text"
                placeholder={report && investigationView === "report" ? "Ask a follow-up about this report…" : `Ask about ${displayedLocation}…`}
                aria-label="Ask AerX"
                value={chatPrompt}
                onChange={(event) => {
                  setComparisonDistrictName(null);
                  setShowComparisonSuggestion(false);
                  setChatPrompt(event.target.value);
                }}
                onKeyDown={(event) => {
                  if (event.key === "Enter") void sendInspection();
                }}
              />
              <button
                type="button"
                onClick={() => void sendInspection()}
                disabled={!chatPrompt.trim() || isGeneratingReport}
                aria-label="Send inspection"
              >
                →
              </button>
            </div>
          </div>
        </aside>
      </div>
    </main>
  );
}
