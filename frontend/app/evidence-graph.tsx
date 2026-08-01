"use client";

import {
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
  type WheelEvent as ReactWheelEvent,
} from "react";

type SourceMode = "loading" | "postgresql" | "demo";

type ToolTrace = {
  tool_name: string;
  status: string;
  summary: string;
};

type EvidenceGraphProps = {
  districtName: string;
  dataMode: SourceMode;
  weatherMode: SourceMode;
  modeledAirQualityMode: SourceMode;
  isGeneratingReport: boolean;
  reportReady: boolean;
  toolTrace: ToolTrace[];
  onOpenReport?: () => void;
};

type NodeKind = "source" | "store" | "datahub" | "agent" | "output";
type GraphNode = {
  id: string;
  label: string;
  shortLabel: string;
  kind: NodeKind;
  detail: string;
};

type Point = { x: number; y: number };
type Viewport = { x: number; y: number; scale: number };
type GraphEdge = {
  source: string;
  target: string;
  label: string;
  hideLabel?: boolean;
  labelDx?: number;
  labelDy?: number;
};

const GRAPH_WIDTH = 520;
const GRAPH_HEIGHT = 390;

const nodes: GraphNode[] = [
  {
    id: "iqair",
    label: "Air quality",
    shortLabel: "AQ",
    kind: "source",
    detail: "City-wide measured AQI from IQAir, used as a comparison signal rather than a district reading.",
  },
  {
    id: "weather",
    label: "Weather",
    shortLabel: "WX",
    kind: "source",
    detail: "Open-Meteo wind, humidity, rain, and temperature provide transport context.",
  },
  {
    id: "cams",
    label: "Pollutant model",
    shortLabel: "CM",
    kind: "source",
    detail: "Open-Meteo CAMS district-coordinate pollutants and history, explicitly distinguished from sensors.",
  },
  {
    id: "traffic",
    label: "Traffic",
    shortLabel: "TR",
    kind: "source",
    detail: "Representative TomTom road-flow context used to test—not prove—the traffic hypothesis.",
  },
  {
    id: "database",
    label: "Database",
    shortLabel: "DB",
    kind: "store",
    detail: "The bounded operational evidence package for the selected Hanoi district.",
  },
  {
    id: "datahub",
    label: "DataHub",
    shortLabel: "DH",
    kind: "datahub",
    detail: "Tells the agent what evidence means and where it came from.",
  },
  {
    id: "agent",
    label: "AirTrace agent",
    shortLabel: "AI",
    kind: "agent",
    detail: "Gemini selects from allowlisted tools and explains only verified, bounded facts.",
  },
  {
    id: "report",
    label: "Evidence report",
    shortLabel: "RP",
    kind: "output",
    detail: "A source-aware report with ranked hypotheses, limitations, and data-quality notes.",
  },
];

const initialPositions: Record<string, Point> = {
  iqair: { x: 55, y: 64 },
  weather: { x: 55, y: 148 },
  cams: { x: 55, y: 232 },
  traffic: { x: 55, y: 316 },
  datahub: { x: 205, y: 112 },
  database: { x: 205, y: 268 },
  agent: { x: 320, y: 190 },
  report: { x: 450, y: 190 },
};

const edges: GraphEdge[] = [
  { source: "iqair", target: "datahub", label: "catalogued", labelDy: -8 },
  { source: "weather", target: "datahub", label: "catalogued", hideLabel: true },
  { source: "cams", target: "datahub", label: "catalogued", hideLabel: true },
  { source: "traffic", target: "datahub", label: "catalogued", hideLabel: true },
  { source: "iqair", target: "database", label: "stored", labelDy: -8 },
  { source: "weather", target: "database", label: "stored", hideLabel: true },
  { source: "cams", target: "database", label: "stored", hideLabel: true },
  { source: "traffic", target: "database", label: "stored", hideLabel: true },
  { source: "datahub", target: "agent", label: "governs", labelDx: 20, labelDy: 26 },
  { source: "database", target: "agent", label: "evidence", labelDy: 12 },
  { source: "agent", target: "report", label: "explains", labelDy: -8 },
  { source: "report", target: "datahub", label: "writes back", labelDy: -14 },
];

function sourceStatus(mode: SourceMode) {
  if (mode === "loading") return "loading";
  if (mode === "demo") return "demo";
  return "ready";
}

function statusLabel(status: string) {
  const labels: Record<string, string> = {
    ready: "Available",
    loading: "Loading",
    demo: "Sample",
    running: "Working",
    waiting: "Waiting",
    connected: "Verified",
    saved: "Saved",
    unavailable: "Unavailable",
    not_configured: "Not configured",
    not_enabled: "Write disabled",
  };
  return labels[status] ?? status.replaceAll("_", " ");
}

export default function EvidenceGraph({
  districtName,
  dataMode,
  weatherMode,
  modeledAirQualityMode,
  isGeneratingReport,
  reportReady,
  toolTrace,
  onOpenReport,
}: EvidenceGraphProps) {
  const [selectedNodeId, setSelectedNodeId] = useState("datahub");
  const [isExpanded, setIsExpanded] = useState(false);
  const [positions, setPositions] = useState(initialPositions);
  const [viewport, setViewport] = useState<Viewport>({ x: 0, y: 0, scale: 1 });
  const svgRef = useRef<SVGSVGElement>(null);
  const gesture = useRef<
    | { kind: "pan"; pointerId: number; lastX: number; lastY: number }
    | { kind: "node"; pointerId: number; nodeId: string; lastX: number; lastY: number }
    | null
  >(null);

  const traceByName = useMemo(
    () => new Map(toolTrace.map((item) => [item.tool_name, item])),
    [toolTrace],
  );
  const dataHubTrace = traceByName.get("get_datahub_context");
  const writeBackTrace = traceByName.get("save_investigation_to_datahub");

  const nodeStatuses: Record<string, string> = {
    iqair: sourceStatus(dataMode),
    weather: sourceStatus(weatherMode),
    cams: sourceStatus(modeledAirQualityMode),
    traffic: reportReady ? "ready" : "waiting",
    database: dataMode === "loading" ? "loading" : "ready",
    datahub: dataHubTrace?.status ?? (isGeneratingReport ? "running" : "ready"),
    agent: isGeneratingReport ? "running" : reportReady ? "ready" : "waiting",
    report: reportReady ? "ready" : isGeneratingReport ? "running" : "waiting",
  };

  const selectedNode = nodes.find((node) => node.id === selectedNodeId) ?? nodes[5];
  const selectedStatus = nodeStatuses[selectedNode.id];
  const selectedTrace =
    selectedNode.id === "datahub"
      ? dataHubTrace
      : selectedNode.id === "report"
        ? writeBackTrace
        : undefined;

  useEffect(() => {
    if (!isExpanded) return;
    const previousOverflow = document.body.style.overflow;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setIsExpanded(false);
    };
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", closeOnEscape);
    return () => {
      document.body.style.overflow = previousOverflow;
      window.removeEventListener("keydown", closeOnEscape);
    };
  }, [isExpanded]);

  const zoom = (amount: number) => {
    setViewport((current) => ({
      ...current,
      scale: Math.min(1.8, Math.max(0.65, current.scale + amount)),
    }));
  };

  const resetGraph = () => {
    setPositions(initialPositions);
    setViewport({ x: 0, y: 0, scale: 1 });
  };

  const beginPan = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (event.button !== 0) return;
    event.currentTarget.setPointerCapture(event.pointerId);
    gesture.current = {
      kind: "pan",
      pointerId: event.pointerId,
      lastX: event.clientX,
      lastY: event.clientY,
    };
  };

  const beginNodeDrag = (event: ReactPointerEvent<SVGGElement>, nodeId: string) => {
    if (event.button !== 0) return;
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    gesture.current = {
      kind: "node",
      pointerId: event.pointerId,
      nodeId,
      lastX: event.clientX,
      lastY: event.clientY,
    };
    setSelectedNodeId(nodeId);
  };

  const moveGesture = (event: ReactPointerEvent<SVGSVGElement>) => {
    const active = gesture.current;
    const rect = svgRef.current?.getBoundingClientRect();
    if (!active || !rect || active.pointerId !== event.pointerId) return;

    const dx = (event.clientX - active.lastX) * (GRAPH_WIDTH / rect.width);
    const dy = (event.clientY - active.lastY) * (GRAPH_HEIGHT / rect.height);
    active.lastX = event.clientX;
    active.lastY = event.clientY;

    if (active.kind === "pan") {
      setViewport((current) => ({ ...current, x: current.x + dx, y: current.y + dy }));
      return;
    }

    setPositions((current) => ({
      ...current,
      [active.nodeId]: {
        x: current[active.nodeId].x + dx / viewport.scale,
        y: current[active.nodeId].y + dy / viewport.scale,
      },
    }));
  };

  const endGesture = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (gesture.current?.pointerId === event.pointerId) gesture.current = null;
  };

  const handleWheel = (event: ReactWheelEvent<SVGSVGElement>) => {
    event.preventDefault();
    zoom(event.deltaY < 0 ? 0.1 : -0.1);
  };

  return (
    <section
      className={`evidence-graph ${isExpanded ? "expanded" : ""}`}
      aria-label="Interactive agent evidence graph"
      aria-modal={isExpanded || undefined}
      role={isExpanded ? "dialog" : undefined}
    >
      {isExpanded && (
        <div className="graph-modal-heading">
          <div>
            <span>Agent provenance</span>
            <h2>How DataHub unlocks the report</h2>
          </div>
          <button type="button" onClick={() => setIsExpanded(false)} aria-label="Close expanded graph">
            Close
          </button>
        </div>
      )}
      <div className="graph-stage">
        <svg
          ref={svgRef}
          className="evidence-graph-svg"
          viewBox={`0 0 ${GRAPH_WIDTH} ${GRAPH_HEIGHT}`}
          role="img"
          aria-label={`Data lineage and agent report graph for ${districtName}`}
          onPointerDown={beginPan}
          onPointerMove={moveGesture}
          onPointerUp={endGesture}
          onPointerCancel={endGesture}
          onWheel={handleWheel}
        >
          <defs>
            <pattern id="graph-grid" width="24" height="24" patternUnits="userSpaceOnUse">
              <circle cx="1" cy="1" r="1" className="graph-grid-dot" />
            </pattern>
            <marker id="graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3.5" orient="auto">
              <path d="M0,0 L0,7 L8,3.5 z" className="graph-arrow" />
            </marker>
            <marker id="graph-arrow-active" markerWidth="8.5" markerHeight="8.5" refX="7.5" refY="3.75" orient="auto">
              <path d="M0,0 L0,7.5 L8.5,3.75 z" className="graph-arrow-active" />
            </marker>
          </defs>
          <rect width={GRAPH_WIDTH} height={GRAPH_HEIGHT} fill="url(#graph-grid)" />
          <g transform={`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`}>
            {edges.map((edge) => {
              const start = positions[edge.source];
              const end = positions[edge.target];
              const deltaX = end.x - start.x;
              const deltaY = end.y - start.y;
              const distance = Math.hypot(deltaX, deltaY) || 1;
              const sourceOffset = edge.source === "datahub" ? 37 : 33;
              const targetOffset = edge.target === "datahub" ? 39 : 35;
              const lineStart = {
                x: start.x + (deltaX / distance) * sourceOffset,
                y: start.y + (deltaY / distance) * sourceOffset,
              };
              const lineEnd = {
                x: end.x - (deltaX / distance) * targetOffset,
                y: end.y - (deltaY / distance) * targetOffset,
              };
              const isConnected = edge.source === selectedNodeId || edge.target === selectedNodeId;
              const arrowGap = isConnected ? 19 : 12;
              const visibleLineEnd = {
                x: lineEnd.x - (deltaX / distance) * arrowGap,
                y: lineEnd.y - (deltaY / distance) * arrowGap,
              };
              const flowPath = `M${lineStart.x},${lineStart.y} L${visibleLineEnd.x},${visibleLineEnd.y}`;
              return (
                <g className={`graph-edge ${isConnected ? "connected" : ""}`} key={`${edge.source}-${edge.target}`}>
                  <line
                    className="graph-edge-base"
                    x1={lineStart.x}
                    y1={lineStart.y}
                    x2={visibleLineEnd.x}
                    y2={visibleLineEnd.y}
                  />
                  <line
                    className="graph-edge-arrow-anchor"
                    x1={visibleLineEnd.x}
                    y1={visibleLineEnd.y}
                    x2={lineEnd.x}
                    y2={lineEnd.y}
                    markerEnd={isConnected ? "url(#graph-arrow-active)" : "url(#graph-arrow)"}
                  />
                  {isConnected && (
                    <path
                      className="graph-edge-flow"
                      d={flowPath}
                      pathLength="1"
                    />
                  )}
                  {isConnected && !edge.hideLabel && (
                    <text
                      x={(start.x + end.x) / 2 + (edge.labelDx ?? 0)}
                      y={(start.y + end.y) / 2 + (edge.labelDy ?? -6)}
                    >
                      {edge.label}
                    </text>
                  )}
                </g>
              );
            })}

            {nodes.map((node) => {
              const point = positions[node.id];
              const isSelected = node.id === selectedNodeId;
              const status = nodeStatuses[node.id];
              return (
                <g
                  className={`graph-node ${node.kind} ${status} ${isSelected ? "selected" : ""}`}
                  key={node.id}
                  transform={`translate(${point.x} ${point.y})`}
                  role="button"
                  tabIndex={0}
                  aria-label={`${node.label}, ${statusLabel(status)}`}
                  onPointerDown={(event) => beginNodeDrag(event, node.id)}
                  onClick={() => {
                    setSelectedNodeId(node.id);
                    if (node.id === "report" && reportReady) onOpenReport?.();
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedNodeId(node.id);
                      if (node.id === "report" && reportReady) onOpenReport?.();
                    }
                  }}
                >
                  <circle className="graph-node-halo" r={node.kind === "datahub" ? 38 : 33} />
                  <circle className="graph-node-body" r={node.kind === "datahub" ? 31 : 27} />
                  <text className="graph-node-short" textAnchor="middle" dominantBaseline="central">
                    {node.shortLabel}
                  </text>
                  <circle className="graph-node-status" cx={node.kind === "datahub" ? 25 : 22} cy={node.kind === "datahub" ? -22 : -19} r="6" />
                  <text className="graph-node-label" textAnchor="middle" y={node.kind === "datahub" ? 51 : 45}>
                    {node.label}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>

        <div className="graph-controls" aria-label="Graph controls">
          <button type="button" onClick={() => zoom(0.15)} aria-label="Zoom in">+</button>
          <button type="button" onClick={() => zoom(-0.15)} aria-label="Zoom out">−</button>
          <button type="button" onClick={resetGraph} aria-label="Reset graph">↺</button>
          <button
            type="button"
            onClick={() => setIsExpanded((current) => !current)}
            aria-label={isExpanded ? "Collapse graph" : "Expand graph"}
            aria-expanded={isExpanded}
          >
            {isExpanded ? "↙" : "↗"}
          </button>
        </div>
        <span className="graph-drag-hint">Drag nodes · scroll to zoom</span>
      </div>

      <div className="graph-legend" aria-label="Graph legend">
        <span><i className="source" />Sources</span>
        <span><i className="datahub" />DataHub</span>
        <span><i className="agent" />Agent</span>
        <span><i className="output" />Outcome</span>
      </div>

      <article className={`graph-inspector ${selectedNode.kind}`} aria-live="polite">
        <div className="graph-inspector-heading">
          <strong>{selectedNode.label}</strong>
          <small className={`graph-state ${selectedStatus}`}>{statusLabel(selectedStatus)}</small>
        </div>
        <p>{selectedTrace?.summary ?? selectedNode.detail}</p>
      </article>
    </section>
  );
}
