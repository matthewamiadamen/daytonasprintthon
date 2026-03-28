import { useState, useCallback } from "react";

const NETWORK_NODES = [
  { id: "MegaCorp", x: 35, y: 30, size: 18 },
  { id: "NovaBio", x: 65, y: 25, size: 14 },
  { id: "Helix", x: 50, y: 60, size: 16 },
  { id: "Regulator", x: 20, y: 65, size: 10 },
  { id: "Market", x: 80, y: 55, size: 12 },
  { id: "IP Pool", x: 45, y: 85, size: 8 },
  { id: "Investors", x: 15, y: 40, size: 9 },
  { id: "Legal", x: 75, y: 80, size: 7 },
];

const NETWORK_EDGES: [number, number][] = [
  [0, 1], [0, 2], [0, 3], [0, 6], [1, 2], [1, 4], [1, 5],
  [2, 3], [2, 4], [2, 5], [3, 6], [4, 7], [5, 7], [1, 7],
];

const NetworkGraph = () => {
  const [hoveredNode, setHoveredNode] = useState<number | null>(null);

  const isConnected = useCallback((nodeIndex: number) => {
    if (hoveredNode === null) return false;
    if (nodeIndex === hoveredNode) return true;
    return NETWORK_EDGES.some(
      ([a, b]) => (a === hoveredNode && b === nodeIndex) || (b === hoveredNode && a === nodeIndex)
    );
  }, [hoveredNode]);

  const isEdgeConnected = useCallback((a: number, b: number) => {
    if (hoveredNode === null) return false;
    return a === hoveredNode || b === hoveredNode;
  }, [hoveredNode]);

  return (
    <svg viewBox="0 0 100 100" className="w-full" style={{ maxHeight: 450 }}>
      {/* Edges */}
      {NETWORK_EDGES.map(([a, b], i) => {
        const active = isEdgeConnected(a, b);
        const dimmed = hoveredNode !== null && !active;
        return (
          <line
            key={i}
            x1={NETWORK_NODES[a].x} y1={NETWORK_NODES[a].y}
            x2={NETWORK_NODES[b].x} y2={NETWORK_NODES[b].y}
            stroke={active ? "hsl(263 70% 58%)" : "hsl(263 70% 58% / 0.25)"}
            strokeWidth={active ? 0.5 : 0.3}
            opacity={dimmed ? 0.1 : 1}
            style={{ transition: "all 0.4s ease" }}
          />
        );
      })}

      {/* Animated pulse rings on hovered node */}
      {hoveredNode !== null && (
        <>
          <circle
            cx={NETWORK_NODES[hoveredNode].x}
            cy={NETWORK_NODES[hoveredNode].y}
            r={NETWORK_NODES[hoveredNode].size / 4}
            fill="none"
            stroke="hsl(263 70% 58%)"
            strokeWidth={0.15}
            opacity={0.6}
          >
            <animate attributeName="r" from={String(NETWORK_NODES[hoveredNode].size / 4)} to={String(NETWORK_NODES[hoveredNode].size / 2)} dur="1.5s" repeatCount="indefinite" />
            <animate attributeName="opacity" from="0.6" to="0" dur="1.5s" repeatCount="indefinite" />
          </circle>
          <circle
            cx={NETWORK_NODES[hoveredNode].x}
            cy={NETWORK_NODES[hoveredNode].y}
            r={NETWORK_NODES[hoveredNode].size / 4}
            fill="none"
            stroke="hsl(263 70% 58%)"
            strokeWidth={0.15}
            opacity={0.4}
          >
            <animate attributeName="r" from={String(NETWORK_NODES[hoveredNode].size / 4)} to={String(NETWORK_NODES[hoveredNode].size / 2.5)} dur="1.5s" begin="0.5s" repeatCount="indefinite" />
            <animate attributeName="opacity" from="0.4" to="0" dur="1.5s" begin="0.5s" repeatCount="indefinite" />
          </circle>
        </>
      )}

      {/* Nodes */}
      {NETWORK_NODES.map((node, i) => {
        const active = isConnected(i);
        const dimmed = hoveredNode !== null && !active;
        const isHovered = hoveredNode === i;
        const scale = isHovered ? 1.3 : 1;

        return (
          <g
            key={node.id}
            onMouseEnter={() => setHoveredNode(i)}
            onMouseLeave={() => setHoveredNode(null)}
            style={{ cursor: "pointer", transition: "opacity 0.4s ease" }}
            opacity={dimmed ? 0.2 : 1}
          >
            {/* Glow */}
            <circle
              cx={node.x} cy={node.y}
              r={node.size / 6 * scale}
              fill={active ? "hsl(263 70% 58% / 0.4)" : "hsl(263 70% 58% / 0.2)"}
              style={{ transition: "all 0.3s ease" }}
            />
            {/* Core */}
            <circle
              cx={node.x} cy={node.y}
              r={node.size / 8 * scale}
              fill={isHovered ? "hsl(263 70% 68%)" : "hsl(263 70% 58%)"}
              style={{ transition: "all 0.3s ease" }}
            />
            {/* Label */}
            <text
              x={node.x}
              y={node.y + node.size / 4 + 2}
              textAnchor="middle"
              fill={active ? "hsl(0 0% 100%)" : "hsl(215 20% 65%)"}
              fontSize={isHovered ? 3 : 2.5}
              fontFamily="Inter, sans-serif"
              fontWeight={isHovered ? 600 : 400}
              style={{ transition: "all 0.3s ease" }}
            >
              {node.id}
            </text>
          </g>
        );
      })}
    </svg>
  );
};

export default NetworkGraph;
