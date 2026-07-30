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
type HistoryDisplayObservation = {
  observed_on: string;
  us_aqi: number | null;
  pm2_5_ug_m3: number | null;
  sample_count: number;
};

type InvestigationReport = {
  title: string;
  summary: string;
  numeric_summary: Array<{ label: string; value: string; source: string }>;
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
  const [dataMode, setDataMode] = useState<DataMode>("loading");
  const [weatherMode, setWeatherMode] = useState<DataMode>("loading");
  const [modeledAirQualityMode, setModeledAirQualityMode] =
    useState<DataMode>("loading");
  const [districtMode, setDistrictMode] = useState<DataMode>("loading");
  const [historyMode, setHistoryMode] = useState<HistoryMode>("loading");
  const [historyDays, setHistoryDays] = useState<HistoryDays>(30);
  const [selectedDistrictName, setSelectedDistrictName] = useState("Hoan Kiem");
  const [comparisonDistrictName, setComparisonDistrictName] = useState<string | null>(null);
  const [comparisonTargetName, setComparisonTargetName] = useState("");
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [chatPrompt, setChatPrompt] = useState("");
  const [report, setReport] = useState<InvestigationReport | null>(null);
  const [toolTrace, setToolTrace] = useState<AgentToolTrace[]>([]);
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [processingStage, setProcessingStage] = useState(0);
  const [reportError, setReportError] = useState<string | null>(null);

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
    const results = await Promise.all([
      requestObservations(),
      requestWeather(),
      requestModeledAirQuality(),
      requestDistrictStatuses(),
      requestDistrictAirQualityHistory(selectedDistrictName, historyDays),
    ]);
    applyResults(...results);
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
    ]).then((results) => {
      if (!cancelled) applyResults(...results);
    });

    return () => {
      cancelled = true;
    };
  }, [applyResults, historyDays, selectedDistrictName]);

  const selectedDistrict = districtStatuses.find(
    (district) => district.district_name === selectedDistrictName,
  );
  const displayedLocation = selectedDistrict?.district_name ?? selectedDistrictName;
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
    setComparisonTargetName("");
    setHistoryMode("loading");
    setChatPrompt(`Inspect ${districtName} air quality`);
    setReport(null);
    setToolTrace([]);
    setReportError(null);
  }, []);

  useEffect(() => {
    if (!isGeneratingReport) return;
    const interval = window.setInterval(() => {
      setProcessingStage((stage) => (stage + 1) % 5);
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

    setProcessingStage(0);
    setIsGeneratingReport(true);
    setReportError(null);
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
        throw new Error(result.detail ?? "AirTrace could not generate a report.");
      }
      setReport(result.report);
      setToolTrace(result.tool_trace ?? []);
    } catch (error) {
      setReportError(
        error instanceof Error ? error.message : "AirTrace could not generate a report.",
      );
    } finally {
      setIsGeneratingReport(false);
    }
  }, [chatPrompt, comparisonDistrictName, isGeneratingReport, selectedDistrictName]);

  const prepareComparison = useCallback(() => {
    if (!comparisonTargetName || isGeneratingReport) return;
    const prompt = `Compare ${displayedLocation} air quality with ${comparisonTargetName}`;
    setComparisonDistrictName(comparisonTargetName);
    setChatPrompt(prompt);
    setReport(null);
    setToolTrace([]);
    setReportError(null);
    void sendInspection(prompt, comparisonTargetName);
  }, [comparisonTargetName, displayedLocation, isGeneratingReport, sendInspection]);

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
              <h1 id="ai-activity-title">Activity graph</h1>
            </div>
            <span className="draft-badge">Live trace</span>
          </div>

          <EvidenceGraph
            districtName={displayedLocation}
            dataMode={dataMode}
            weatherMode={weatherMode}
            modeledAirQualityMode={modeledAirQualityMode}
            isGeneratingReport={isGeneratingReport}
            reportReady={Boolean(report)}
            toolTrace={toolTrace}
          />
        </aside>

        <section className="center-column" aria-label="Map and historic air quality">
          <article className="workspace-panel map-panel" aria-labelledby="map-title">
            <div className="panel-heading map-heading">
              <div>
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
              onSelect={selectDistrictForInspection}
              selectedDistrictName={selectedDistrictName}
            />

            <div className="district-selection">
              <div>
                <span className="metric-label">Selected district</span>
                <strong>{displayedLocation}</strong>
              </div>
              <div className="report-context">
                <span>Click a district to prepare its AI inspection</span>
              </div>
            </div>
          </article>

          <article className="workspace-panel history-panel" aria-labelledby="history-title">
            <div className="panel-heading history-heading">
              <div>
                <h2 id="history-title">{displayedLocation} historical AQI</h2>
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
                  <HistoryLineChart
                    location={displayedLocation}
                    rows={displayedHistory}
                  />
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
                            height: `${Math.max(
                              ((row.us_aqi ?? 0) / maxChartAqi) * 100,
                              8,
                            )}%`,
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

                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>{isMonthlyHistory ? "Month" : "Date"}</th>
                        <th>US AQI</th>
                        <th>PM2.5</th>
                      </tr>
                    </thead>
                    <tbody>
                      {displayedHistory.slice(-4).reverse().map((row) => (
                        <tr key={`${row.observed_on}-history`}>
                          <td>
                            {isMonthlyHistory
                              ? formatHistoryMonth(row.observed_on)
                              : formatHistoryDate(row.observed_on)}
                          </td>
                          <td>
                            <strong>
                              {row.us_aqi === null ? "—" : Math.round(row.us_aqi)}
                            </strong>
                          </td>
                          <td>
                            {row.pm2_5_ug_m3 === null
                              ? "—"
                              : `${row.pm2_5_ug_m3.toFixed(1)} µg/m³`}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
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
                  : "Awaiting Neon import"}
              </span>
            </div>
          </article>
        </section>

        <aside className={`workspace-panel chat-panel ${report || isGeneratingReport ? "has-active-report" : ""}`} aria-labelledby="chat-title">
          <div className="panel-heading">
            <div>
              <h2 id="chat-title">Ask about the air</h2>
            </div>
            <span className="source-badge">Gemini</span>
          </div>

          <div className="chat-thread" aria-label="AirTrace investigation report">
            {!report && !isGeneratingReport && (
              <div className="chat-message assistant-message">
                <span>Selected district</span>
                <p>
                  {chatPrompt || `Click ${displayedLocation} on the map to prepare an inspection.`}
                </p>
              </div>
            )}
            {isGeneratingReport && (
              <article className="agent-processing-card" aria-live="polite">
                <div className="processing-loader" aria-hidden="true" />
                <div>
                  <span>AirTrace investigation in progress</span>
                  <strong>
                    {[
                      "Checking DataHub source contracts",
                      "Reading district air and pollutant evidence",
                      "Checking weather, wind, and dispersion context",
                      "Comparing TomTom traffic conditions",
                      comparisonDistrictName
                        ? `Comparing ${displayedLocation} with ${comparisonDistrictName}`
                        : "Writing a cautious evidence-backed report",
                    ][processingStage]}
                  </strong>
                  <p>Gemini receives only the verified evidence package, never direct database access.</p>
                </div>
                <div className="processing-steps" aria-hidden="true">
                  {[0, 1, 2, 3, 4].map((stage) => (
                    <i key={stage} className={stage <= processingStage ? "done" : ""} />
                  ))}
                </div>
              </article>
            )}
            {report && (
              <article className="report-card">
                <span>AirTrace report</span>
                <h3>{report.title}</h3>
                <p>{report.summary}</p>
                <dl className="report-metrics">
                  {report.numeric_summary.map((metric) => (
                    <div key={`${metric.label}-${metric.source}`}>
                      <dt>{metric.label}</dt>
                      <dd>{metric.value}</dd>
                      <small>{metric.source}</small>
                    </div>
                  ))}
                </dl>
                {!report.comparison_mode && (
                  <div className="report-causes">
                    <strong>Potential cause analysis</strong>
                    {report.potential_causes.map((cause) => (
                      <p key={`${cause.label}-${cause.detail}`}><b>{cause.label}:</b> {cause.detail}</p>
                    ))}
                  </div>
                )}
                {report.comparison_mode && report.potential_causes.length > 0 && (
                  <div className="comparison-analysis">
                    <strong>What the evidence suggests</strong>
                    {report.potential_causes.map((interpretation) => (
                      <p key={`${interpretation.label}-${interpretation.detail}`}>
                        <b>{interpretation.label}:</b> {interpretation.detail}
                      </p>
                    ))}
                  </div>
                )}
                {!report.comparison_mode && report.hypothesis_ranking && (
                  <div className="hypothesis-ranking">
                    <strong>Evidence ranking</strong>
                    <small>{report.assessment_method}</small>
                    {report.hypothesis_ranking.map((hypothesis) => (
                      <div className="hypothesis-row" key={hypothesis.label}>
                        <div>
                          <b>{hypothesis.label}</b>
                          <span>Evidence score {hypothesis.score}/100</span>
                        </div>
                        {hypothesis.supporting_evidence.length > 0 && (
                          <p><em>Supports:</em> {hypothesis.supporting_evidence.join(" ")}</p>
                        )}
                        {hypothesis.contradicting_evidence.length > 0 && (
                          <p><em>Limits:</em> {hypothesis.contradicting_evidence.join(" ")}</p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
                {!report.comparison_mode && <p className="report-quality">{report.data_quality}</p>}
                {report.comparison_note && (
                  <p className="report-quality comparison-note">{report.comparison_note}</p>
                )}
                {report.ai_status && <p className="report-quality">{report.ai_status}</p>}
              </article>
            )}
            {toolTrace.length > 0 && (
              <article className="tool-trace-card">
                <span>Agent evidence trail</span>
                {toolTrace.map((tool, index) => (
                  <div key={`${tool.tool_name}-${index}`}>
                    <strong>{tool.tool_name.replaceAll("_", " ")}</strong>
                    <small className={`tool-status ${tool.status}`}>{tool.status.replaceAll("_", " ")}</small>
                    <p>{tool.summary}</p>
                  </div>
                ))}
              </article>
            )}
            {reportError && <p className="report-error">{reportError}</p>}
          </div>

          <details className="agent-tasks" open={!report && !isGeneratingReport}>
            <summary>Try an agent task</summary>
            <div className="suggested-prompts">
              <button type="button" onClick={() => {
                setComparisonDistrictName(null);
                setComparisonTargetName("");
                setChatPrompt(`Inspect ${displayedLocation} air quality`);
                setReport(null);
                setToolTrace([]);
                setReportError(null);
              }} disabled={isGeneratingReport}>
                Inspect {displayedLocation} air quality
              </button>
              <div className="comparison-picker">
                <label htmlFor="comparison-district">Compare {displayedLocation} with</label>
                <div>
                  <select
                    id="comparison-district"
                    value={comparisonTargetName}
                    onChange={(event) => {
                      setComparisonTargetName(event.target.value);
                      setComparisonDistrictName(null);
                    }}
                    disabled={isGeneratingReport}
                  >
                    <option value="">Choose another district</option>
                    {districtStatuses
                      .filter((district) => district.district_name !== displayedLocation)
                      .map((district) => (
                        <option key={district.district_name} value={district.district_name}>
                          {district.district_name}
                        </option>
                      ))}
                  </select>
                  <button
                    type="button"
                    className={`comparison-prompt ${comparisonDistrictName ? "selected" : ""}`}
                    onClick={prepareComparison}
                    disabled={!comparisonTargetName || isGeneratingReport}
                  >
                    Compare districts
                  </button>
                </div>
                <small>Uses the same CAMS, IQAir, weather, traffic, and DataHub context for both districts.</small>
              </div>
            </div>
          </details>

          <div className="chat-composer">
            <label htmlFor="chat-input">Ask AirTrace</label>
            <div>
              <input
                id="chat-input"
                type="text"
                placeholder="Click a district to prepare an inspection"
                value={chatPrompt}
                onChange={(event) => {
                  setComparisonDistrictName(null);
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
            <small>Gemini receives only the selected district&apos;s bounded evidence package.</small>
          </div>
        </aside>
      </div>
    </main>
  );
}
