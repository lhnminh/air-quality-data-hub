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
};

type NodeKind = "source" | "store" | "datahub" | "agent" | "output";
type GraphNode = {
  id: string;
  label: string;
  shortLabel: string;
  kind: NodeKind;
  detail: string;
  unlock: string;
};

type Point = { x: number; y: number };
type Viewport = { x: number; y: number; scale: number };

const GRAPH_WIDTH = 520;
const GRAPH_HEIGHT = 390;

const nodes: GraphNode[] = [
  {
    id: "iqair",
    label: "IQAir",
    shortLabel: "AQ",
    kind: "source",
    detail: "City-wide measured AQI used as a comparison signal, not a district reading.",
    unlock: "Source scope",
  },
  {
    id: "weather",
    label: "Weather",
    shortLabel: "WX",
    kind: "source",
    detail: "Wind, humidity, rain, and temperature provide transport context.",
    unlock: "Freshness",
  },
  {
    id: "cams",
    label: "CAMS model",
    shortLabel: "CM",
    kind: "source",
    detail: "District-coordinate modeled pollutants and history, explicitly distinguished from sensors.",
    unlock: "Data class",
  },
  {
    id: "traffic",
    label: "TomTom",
    shortLabel: "TR",
    kind: "source",
    detail: "Representative road-flow context used to test—not prove—the traffic hypothesis.",
    unlock: "Usage policy",
  },
  {
    id: "neon",
    label: "Neon evidence",
    shortLabel: "DB",
    kind: "store",
    detail: "The bounded operational evidence package for the selected Hanoi district.",
    unlock: "Queryable facts",
  },
  {
    id: "datahub",
    label: "DataHub context",
    shortLabel: "DH",
    kind: "datahub",
    detail: "DataHub tells the agent what the evidence means, where it came from, and how it may be used.",
    unlock: "Schema · lineage · quality",
  },
  {
    id: "agent",
    label: "AirTrace agent",
    shortLabel: "AI",
    kind: "agent",
    detail: "Gemini selects from allowlisted tools and explains only verified, bounded facts.",
    unlock: "Grounded reasoning",
  },
  {
    id: "report",
    label: "Evidence report",
    shortLabel: "RP",
    kind: "output",
    detail: "A source-aware report with ranked hypotheses, limitations, and data-quality notes.",
    unlock: "Traceable insight",
  },
];

const initialPositions: Record<string, Point> = {
  iqair: { x: 55, y: 64 },
  weather: { x: 55, y: 148 },
  cams: { x: 55, y: 232 },
  traffic: { x: 55, y: 316 },
  datahub: { x: 205, y: 112 },
  neon: { x: 205, y: 268 },
  agent: { x: 340, y: 190 },
  report: { x: 465, y: 190 },
};

const edges = [
  { source: "iqair", target: "datahub", label: "catalogued" },
  { source: "weather", target: "datahub", label: "catalogued" },
  { source: "cams", target: "datahub", label: "catalogued" },
  { source: "traffic", target: "datahub", label: "catalogued" },
  { source: "iqair", target: "neon", label: "stored" },
  { source: "weather", target: "neon", label: "stored" },
  { source: "cams", target: "neon", label: "stored" },
  { source: "traffic", target: "neon", label: "stored" },
  { source: "datahub", target: "agent", label: "governs" },
  { source: "neon", target: "agent", label: "evidence" },
  { source: "agent", target: "report", label: "explains" },
  { source: "report", target: "datahub", label: "writes back" },
] as const;

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
    neon: dataMode === "loading" ? "loading" : "ready",
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
            <marker id="graph-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto">
              <path d="M0,0 L0,6 L7,3 z" className="graph-arrow" />
            </marker>
          </defs>
          <rect width={GRAPH_WIDTH} height={GRAPH_HEIGHT} fill="url(#graph-grid)" />
          <g transform={`translate(${viewport.x} ${viewport.y}) scale(${viewport.scale})`}>
            {edges.map((edge) => {
              const start = positions[edge.source];
              const end = positions[edge.target];
              const isConnected = edge.source === selectedNodeId || edge.target === selectedNodeId;
              return (
                <g className={`graph-edge ${isConnected ? "connected" : ""}`} key={`${edge.source}-${edge.target}`}>
                  <line
                    x1={start.x}
                    y1={start.y}
                    x2={end.x}
                    y2={end.y}
                    markerEnd="url(#graph-arrow)"
                  />
                  {isConnected && (
                    <text x={(start.x + end.x) / 2} y={(start.y + end.y) / 2 - 6}>
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
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      setSelectedNodeId(node.id);
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
          <div>
            <span>{selectedNode.kind === "datahub" ? "The DataHub unlock" : selectedNode.unlock}</span>
            <strong>{selectedNode.label}</strong>
          </div>
          <small className={`graph-state ${selectedStatus}`}>{statusLabel(selectedStatus)}</small>
        </div>
        <p>{selectedTrace?.summary ?? selectedNode.detail}</p>
        {selectedNode.kind === "datahub" && (
          <div className="unlock-list">
            <span>Meaning</span><span>Lineage</span><span>Quality</span><span>Audit</span>
          </div>
        )}
      </article>
    </section>
  );
}
