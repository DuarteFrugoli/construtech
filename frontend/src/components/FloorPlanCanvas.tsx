import { forwardRef, useMemo } from 'react';

// ── Types ────────────────────────────────────────────────────────────────────

interface DoorData {
  x: number;
  y: number;
  width: number;
  height: number;
  is_horizontal: boolean;
}

interface RoomData {
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  doors: DoorData[];
}

interface TerrainData {
  width: number;
  height: number;
  recuo_frontal: number;
  recuo_lateral: number;
  recuo_fundo: number;
}

interface FloorPlanCanvasProps {
  terrain: TerrainData;
  rooms: RoomData[];
  /** Canvas width in px (default 700) */
  canvasWidth?: number;
  /** Canvas height in px (default 800) */
  canvasHeight?: number;
}

// ── Room colour palette by zone keyword ─────────────────────────────────────

function roomColor(name: string): string {
  const n = name.toLowerCase();
  if (n.includes('sala de estar') || n.includes('living')) return '#dbeafe';   // blue-100
  if (n.includes('sala de jantar') || n.includes('dining')) return '#e0e7ff';  // indigo-100
  if (n.includes('cozinha') || n.includes('kitchen'))       return '#fef9c3';  // yellow-100
  if (n.includes('quarto') || n.includes('bedroom') || n.includes('suite') && !n.includes('banheiro')) return '#dcfce7'; // green-100
  if (n.includes('banheiro') || n.includes('bathroom') || n.includes('lavabo')) return '#f0fdf4'; // green-50
  if (n.includes('garagem') || n.includes('garage'))        return '#f3f4f6';  // gray-100
  if (n.includes('corredor') || n.includes('corridor') || n.includes('hall')) return '#fafafa';
  if (n.includes('escritório') || n.includes('office'))     return '#fef3c7';  // amber-100
  if (n.includes('varanda'))                                return '#ecfdf5';  // emerald-50
  if (n.includes('gourmet'))                                return '#fff7ed';  // orange-50
  if (n.includes('serviço') || n.includes('dependência'))   return '#f5f3ff';  // violet-50
  return '#f9fafb';
}

// ── pt-BR name map ───────────────────────────────────────────────────────────

const PT_NAMES: Record<string, string> = {
  'Living Room':    'Sala de Estar',
  'Dining Room':    'Sala de Jantar',
  'Kitchen':        'Cozinha',
  'Master Bedroom': 'Quarto Principal',
  'Bedroom':        'Quarto',
  'Bathroom':       'Banheiro',
  'Suite Bathroom': 'Banheiro Suíte',
  'Garage':         'Garagem',
  'Corridor':       'Corredor',
};

function ptName(name: string): string {
  // Exact match
  if (PT_NAMES[name]) return PT_NAMES[name];
  // Numbered rooms: "Bedroom 2" → "Quarto 2", "Suite 2" → "Suíte 2"
  const numbered = name.match(/^(.+?)\s+(\d+)$/);
  if (numbered) {
    const base = PT_NAMES[numbered[1]] ?? numbered[1];
    return `${base} ${numbered[2]}`;
  }
  // Suite Bathroom N
  if (name.startsWith('Suite Bathroom ')) {
    return `Banheiro Suíte ${name.split(' ').pop()}`;
  }
  return name;
}

// ── Component ────────────────────────────────────────────────────────────────

const FloorPlanCanvas = forwardRef<SVGSVGElement, FloorPlanCanvasProps>(({
  terrain,
  rooms,
  canvasWidth = 700,
  canvasHeight = 800,
}, ref) => {
  const PADDING = 40; // px around the terrain

  const scale = useMemo(() => {
    const sx = (canvasWidth  - PADDING * 2) / terrain.width;
    const sy = (canvasHeight - PADDING * 2) / terrain.height;
    return Math.min(sx, sy);
  }, [terrain, canvasWidth, canvasHeight]);

  // Terrain rectangle in px
  const tx = PADDING;
  const ty = PADDING;
  const tw = terrain.width  * scale;
  const th = terrain.height * scale;

  // Helpers: convert metres → px
  const px = (mx: number) => tx + mx * scale;
  const py = (my: number) => ty + my * scale;
  const ps = (m:  number) => m  * scale;

  // Door arc path (quarter circle, same convention as Python svg_generator)
  function doorPath(door: DoorData): string {
    const cx = px(door.x);
    const cy = py(door.y);
    const r  = ps(door.is_horizontal ? door.width : door.height) / 2;

    if (door.is_horizontal) {
      // hinge at left, swing up
      return `M ${cx - r} ${cy} A ${r} ${r} 0 0 1 ${cx} ${cy - r}`;
    } else {
      // hinge at top, swing right
      return `M ${cx} ${cy - r} A ${r} ${r} 0 0 1 ${cx + r} ${cy}`;
    }
  }

  // Collect unique door objects (rooms share the same door instance semantically,
  // but the JSON duplicates door data — dedupe by position)
  const seenDoors = new Set<string>();
  const allDoors: DoorData[] = [];
  for (const room of rooms) {
    for (const door of room.doors) {
      const key = `${door.x.toFixed(3)},${door.y.toFixed(3)},${door.is_horizontal}`;
      if (!seenDoors.has(key)) {
        seenDoors.add(key);
        allDoors.push(door);
      }
    }
  }

  // Setback lines
  const rf = terrain.recuo_frontal  * scale;
  const rl = terrain.recuo_lateral  * scale;
  const rb = terrain.recuo_fundo    * scale;

  const isPortrait = terrain.height >= terrain.width;

  return (
    <svg
      ref={ref}
      width={canvasWidth}
      height={canvasHeight}
      viewBox={`0 0 ${canvasWidth} ${canvasHeight}`}
      xmlns="http://www.w3.org/2000/svg"
      style={{ background: '#fff', display: 'block' }}
    >
      {/* ── Terrain outline ── */}
      <rect x={tx} y={ty} width={tw} height={th}
        fill="#f8fafc" stroke="#334155" strokeWidth={2} />

      {/* ── Setback dashed lines ── */}
      {isPortrait ? (
        <>
          {/* frontal (top) */}
          <line x1={tx} y1={ty + rf} x2={tx + tw} y2={ty + rf}
            stroke="#94a3b8" strokeWidth={1} strokeDasharray="6 4" />
          <text x={tx + 4} y={ty + rf - 4} fontSize={10} fill="#64748b">RF: {terrain.recuo_frontal}m</text>
          {/* fundo (bottom) */}
          <line x1={tx} y1={ty + th - rb} x2={tx + tw} y2={ty + th - rb}
            stroke="#94a3b8" strokeWidth={1} strokeDasharray="6 4" />
          <text x={tx + 4} y={ty + th - rb - 4} fontSize={10} fill="#64748b">RFu: {terrain.recuo_fundo}m</text>
          {/* lateral esquerda */}
          <line x1={tx + rl} y1={ty} x2={tx + rl} y2={ty + th}
            stroke="#94a3b8" strokeWidth={1} strokeDasharray="6 4" />
          {/* lateral direita */}
          <line x1={tx + tw - rl} y1={ty} x2={tx + tw - rl} y2={ty + th}
            stroke="#94a3b8" strokeWidth={1} strokeDasharray="6 4" />
        </>
      ) : (
        <>
          {/* frontal (left) */}
          <line x1={tx + rf} y1={ty} x2={tx + rf} y2={ty + th}
            stroke="#94a3b8" strokeWidth={1} strokeDasharray="6 4" />
          <text x={tx + rf + 4} y={ty + 14} fontSize={10} fill="#64748b">RF: {terrain.recuo_frontal}m</text>
          {/* fundo (right) */}
          <line x1={tx + tw - rb} y1={ty} x2={tx + tw - rb} y2={ty + th}
            stroke="#94a3b8" strokeWidth={1} strokeDasharray="6 4" />
          {/* laterais top/bottom */}
          <line x1={tx} y1={ty + rl} x2={tx + tw} y2={ty + rl}
            stroke="#94a3b8" strokeWidth={1} strokeDasharray="6 4" />
          <line x1={tx} y1={ty + th - rl} x2={tx + tw} y2={ty + th - rl}
            stroke="#94a3b8" strokeWidth={1} strokeDasharray="6 4" />
        </>
      )}

      {/* ── Room fills ── */}
      {rooms.map((room, i) => (
        <rect
          key={`fill-${i}`}
          x={px(room.x)} y={py(room.y)}
          width={ps(room.width)} height={ps(room.height)}
          fill={roomColor(ptName(room.name))}
          stroke="none"
        />
      ))}

      {/* ── Walls (room borders), with gaps where doors are ── */}
      {rooms.map((room, i) => {
        const rx = px(room.x);
        const ry = py(room.y);
        const rw = ps(room.width);
        const rh = ps(room.height);

        // Collect door gap segments that cut into this room's walls
        const hGaps: { x1: number; x2: number; wallY: number }[] = [];
        const vGaps: { y1: number; y2: number; wallX: number }[] = [];

        for (const door of room.doors) {
          const dcx = px(door.x);
          const dcy = py(door.y);
          const dr  = ps(door.is_horizontal ? door.width : door.height) / 2;

          if (door.is_horizontal) {
            hGaps.push({ x1: dcx - dr, x2: dcx + dr, wallY: dcy });
          } else {
            vGaps.push({ y1: dcy - dr, y2: dcy + dr, wallX: dcx });
          }
        }

        // Draw the four walls with door gaps cut out
        const wallStyle = { stroke: '#1e293b', strokeWidth: 1.5, fill: 'none' as const };

        const hWalls = (wallY: number, x1: number, x2: number) => {
          const cuts = hGaps
            .filter(g => Math.abs(g.wallY - wallY) < 2)
            .map(g => ({ x1: g.x1, x2: g.x2 }));
          return segmentsWithGaps(x1, x2, cuts).map((seg, si) => (
            <line key={`hw-${i}-${wallY}-${si}`}
              x1={seg.start} y1={wallY} x2={seg.end} y2={wallY} {...wallStyle} />
          ));
        };

        const vWalls = (wallX: number, y1: number, y2: number) => {
          const cuts = vGaps
            .filter(g => Math.abs(g.wallX - wallX) < 2)
            .map(g => ({ x1: g.y1, x2: g.y2 }));
          return segmentsWithGaps(y1, y2, cuts).map((seg, si) => (
            <line key={`vw-${i}-${wallX}-${si}`}
              x1={wallX} y1={seg.start} x2={wallX} y2={seg.end} {...wallStyle} />
          ));
        };

        return (
          <g key={`walls-${i}`}>
            {hWalls(ry,      rx, rx + rw)}
            {hWalls(ry + rh, rx, rx + rw)}
            {vWalls(rx,      ry, ry + rh)}
            {vWalls(rx + rw, ry, ry + rh)}
          </g>
        );
      })}

      {/* ── Door arcs ── */}
      {allDoors.map((door, i) => {
        const cx = px(door.x);
        const cy = py(door.y);
        const r  = ps(door.is_horizontal ? door.width : door.height) / 2;

        return (
          <g key={`door-${i}`}>
            <path d={doorPath(door)}
              fill="none" stroke="#3b82f6" strokeWidth={1.2} />
            {/* door panel line */}
            {door.is_horizontal
              ? <line x1={cx - r} y1={cy} x2={cx} y2={cy - r} stroke="#3b82f6" strokeWidth={1} />
              : <line x1={cx} y1={cy - r} x2={cx + r} y2={cy} stroke="#3b82f6" strokeWidth={1} />
            }
          </g>
        );
      })}

      {/* ── Room labels ── */}
      {rooms.map((room, i) => {
        const cx = px(room.x + room.width  / 2);
        const cy = py(room.y + room.height / 2);
        const area = (room.width * room.height).toFixed(0);
        const label = ptName(room.name);
        const fontSize = Math.max(8, Math.min(12, ps(room.width) / (label.length * 0.6)));

        return (
          <g key={`label-${i}`}>
            <text
              x={cx} y={cy - 5}
              textAnchor="middle" dominantBaseline="middle"
              fontSize={fontSize} fontWeight="600" fill="#1e293b"
              style={{ userSelect: 'none' }}
            >
              {label}
            </text>
            <text
              x={cx} y={cy + fontSize}
              textAnchor="middle" dominantBaseline="middle"
              fontSize={Math.max(7, fontSize - 2)} fill="#64748b"
              style={{ userSelect: 'none' }}
            >
              {room.width.toFixed(1)}m × {room.height.toFixed(1)}m
            </text>
            <text
              x={cx} y={cy + fontSize * 2 + 2}
              textAnchor="middle" dominantBaseline="middle"
              fontSize={Math.max(7, fontSize - 2)} fill="#94a3b8"
              style={{ userSelect: 'none' }}
            >
              {area} m²
            </text>
          </g>
        );
      })}

      {/* ── Cardinal labels (Frente / Fundo) ── */}
      {isPortrait ? (
        <>
          <text x={tx + tw / 2} y={ty - 8} textAnchor="middle" fontSize={11} fontWeight="600" fill="#2563eb">▼ Frente</text>
          <text x={tx + tw / 2} y={ty + th + 18} textAnchor="middle" fontSize={11} fill="#64748b">Fundo</text>
        </>
      ) : (
        <>
          <text x={tx - 6} y={ty + th / 2} textAnchor="end" fontSize={11} fontWeight="600" fill="#2563eb">◀ Frente</text>
          <text x={tx + tw + 6} y={ty + th / 2} textAnchor="start" fontSize={11} fill="#64748b">Fundo</text>
        </>
      )}
    </svg>
  );
});

FloorPlanCanvas.displayName = 'FloorPlanCanvas';

// ── Utility: cut gaps out of a 1-D segment ───────────────────────────────────

function segmentsWithGaps(
  start: number,
  end: number,
  gaps: { x1: number; x2: number }[],
): { start: number; end: number }[] {
  if (gaps.length === 0) return [{ start, end }];

  const sorted = [...gaps].sort((a, b) => a.x1 - b.x1);
  const result: { start: number; end: number }[] = [];
  let cur = start;

  for (const gap of sorted) {
    if (gap.x1 > cur + 0.5) result.push({ start: cur, end: gap.x1 });
    cur = Math.max(cur, gap.x2);
  }
  if (cur < end - 0.5) result.push({ start: cur, end });
  return result;
}

export default FloorPlanCanvas;
export type { RoomData, TerrainData as FloorPlanTerrain, DoorData };
