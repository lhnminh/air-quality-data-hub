type HistoryLineChartProps = {
  rows: Array<{
    observed_on: string;
    us_aqi: number | null;
  }>;
};

const WIDTH = 640;
const HEIGHT = 190;
const PADDING = { top: 12, right: 14, bottom: 28, left: 38 };

function formatShortDate(value: string) {
  const date = new Date(`${value}T00:00:00Z`);
  if (Number.isNaN(date.getTime())) return value;

  return new Intl.DateTimeFormat("en-GB", {
    day: "2-digit",
    month: "short",
    timeZone: "Asia/Ho_Chi_Minh",
  }).format(date);
}

export default function HistoryLineChart({ rows }: HistoryLineChartProps) {
  const usableRows = rows.filter(
    (row): row is { observed_on: string; us_aqi: number } => row.us_aqi !== null,
  );

  if (usableRows.length < 2) {
    return (
      <div className="history-empty">
        At least two daily AQI values are needed to draw the trend line.
      </div>
    );
  }

  const plotWidth = WIDTH - PADDING.left - PADDING.right;
  const plotHeight = HEIGHT - PADDING.top - PADDING.bottom;
  const observedMaximum = Math.max(...usableRows.map((row) => row.us_aqi));
  const scaleMaximum = Math.max(150, Math.ceil(observedMaximum / 50) * 50);
  const xFor = (index: number) =>
    PADDING.left + (index / (usableRows.length - 1)) * plotWidth;
  const yFor = (aqi: number) =>
    PADDING.top + (1 - Math.min(aqi, scaleMaximum) / scaleMaximum) * plotHeight;

  const points = usableRows.map((row, index) => ({
    ...row,
    x: xFor(index),
    y: yFor(row.us_aqi),
  }));
  const linePath = points
    .map((point, index) => `${index === 0 ? "M" : "L"} ${point.x} ${point.y}`)
    .join(" ");
  const plotBottom = HEIGHT - PADDING.bottom;
  const areaPath = `${linePath} L ${points.at(-1)?.x} ${plotBottom} L ${points[0].x} ${plotBottom} Z`;
  const yTicks = Array.from(
    { length: scaleMaximum / 50 + 1 },
    (_, index) => index * 50,
  );
  const labelIndexes = [...new Set([0, 7, 14, 21, usableRows.length - 1])]
    .filter((index) => index < usableRows.length)
    .sort((left, right) => left - right);

  return (
    <div className="history-line-chart">
      <svg
        aria-label="Thirty-day Hanoi US AQI trend"
        className="history-line-svg"
        role="img"
        viewBox={`0 0 ${WIDTH} ${HEIGHT}`}
      >
        <title>Thirty-day Hanoi US AQI trend</title>

        {yTicks.map((tick) => (
          <g className="history-line-grid" key={tick}>
            <line
              x1={PADDING.left}
              x2={WIDTH - PADDING.right}
              y1={yFor(tick)}
              y2={yFor(tick)}
            />
            <text x={PADDING.left - 8} y={yFor(tick) + 3}>
              {tick}
            </text>
          </g>
        ))}

        <path className="history-line-area" d={areaPath} />
        <path className="history-line-path" d={linePath} />

        {points.map((point) => (
          <circle
            className="history-line-point"
            cx={point.x}
            cy={point.y}
            key={point.observed_on}
            r="3"
          >
            <title>
              {formatShortDate(point.observed_on)}: {Math.round(point.us_aqi)} US AQI
            </title>
          </circle>
        ))}

        {labelIndexes.map((index) => {
          const point = points[index];
          const textAnchor =
            index === 0 ? "start" : index === usableRows.length - 1 ? "end" : "middle";

          return (
            <text
              className="history-line-date"
              key={point.observed_on}
              textAnchor={textAnchor}
              x={point.x}
              y={HEIGHT - 8}
            >
              {formatShortDate(point.observed_on)}
            </text>
          );
        })}
      </svg>
    </div>
  );
}
