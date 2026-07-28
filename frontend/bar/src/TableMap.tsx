import { useEffect, useState, type CSSProperties } from "react";
import { authFetch } from "./auth";
import type { ServiceRequest, Ticket } from "./types";

type TableState = "free" | "busy" | "ready" | "call";

interface TableSpot {
  number: number;
  zone: string | null;
  label: string | null;
  shape: "square" | "round";
  seats: number | null;
  x: number | null;
  y: number | null;
  w: number;
  h: number;
}

const STATE_LABEL: Record<TableState, string> = {
  free: "slobodno",
  busy: "u toku",
  ready: "spremno za nošenje",
  call: "zove / traži račun",
};

interface Props {
  cafeId: string;
  tickets: Ticket[];
  requests: ServiceRequest[];
  onResolveRequest: (id: string) => void;
}

export default function TableMap({ cafeId, tickets, requests, onResolveRequest }: Props) {
  const [tables, setTables] = useState<TableSpot[]>([]);
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    authFetch(`/api/menu/cafes`)
      .then((r) => r.json())
      .then((cafes: { id: string; tables: TableSpot[] }[]) => {
        const cafe = cafes.find((c) => c.id === cafeId);
        if (cafe) setTables(cafe.tables ?? []);
      });
  }, [cafeId]);

  const stateOf = (table: number): TableState => {
    if (requests.some((q) => q.table_number === table)) return "call";
    const active = tickets.filter((t) => t.table_number === table);
    if (active.some((t) => t.status === "READY")) return "ready";
    if (active.length > 0) return "busy";
    return "free";
  };

  const selectedTickets = tickets.filter((t) => t.table_number === selected);
  const selectedRequests = requests.filter((q) => q.table_number === selected);

  // canvas prikaz samo ako svi stolovi imaju poziciju; inače grid grupisan po zoni
  const positioned = tables.length > 0 && tables.every((t) => t.x != null && t.y != null);

  const tile = (t: TableSpot, style?: CSSProperties) => {
    const state = stateOf(t.number);
    const shapeClass = t.shape === "round" ? "tt-round" : "";
    const selClass = selected === t.number ? "tt-selected" : "";
    return (
      <button
        key={t.number}
        className={`table-tile tt-${state} ${shapeClass} ${selClass}`}
        style={style}
        onClick={() => setSelected(selected === t.number ? null : t.number)}
      >
        <span className="tt-num">{t.number}</span>
        <span className="tt-label">{t.label ?? STATE_LABEL[state]}</span>
      </button>
    );
  };

  const zones = (): [string, TableSpot[]][] => {
    const groups = new Map<string, TableSpot[]>();
    for (const t of tables) {
      const z = t.zone ?? "—";
      if (!groups.has(z)) groups.set(z, []);
      groups.get(z)!.push(t);
    }
    return [...groups.entries()];
  };

  return (
    <div className="table-map">
      {positioned ? (
        <div className="map-canvas">
          {tables.map((t) =>
            tile(t, {
              position: "absolute",
              left: `${t.x}%`,
              top: `${t.y}%`,
              width: `${t.w}%`,
              height: `${t.h}%`,
            }),
          )}
        </div>
      ) : (
        zones().map(([zone, spots]) => (
          <div className="map-zone" key={zone}>
            <h4 className="map-zone-title">{zone}</h4>
            <div className="map-grid">{spots.map((t) => tile(t))}</div>
          </div>
        ))
      )}

      {selected !== null && (
        <div className="table-detail">
          <h3>Sto {selected}</h3>
          {selectedRequests.map((q) => (
            <div className="td-request" key={q.id}>
              <span>{q.kind === "bill" ? "🧾 traži račun" : "🔔 zove konobara"}</span>
              <button onClick={() => onResolveRequest(q.id)}>Rešeno</button>
            </div>
          ))}
          {selectedTickets.length === 0 && selectedRequests.length === 0 && (
            <p className="empty">Nema aktivnih porudžbina.</p>
          )}
          {selectedTickets.map((t) => (
            <div className="td-ticket" key={t.order_id}>
              <span className={`td-status td-${t.status}`}>
                {t.status === "CREATED" ? "novo" : t.status === "ACCEPTED" ? "u pripremi" : "spremno"}
              </span>
              <span>{t.items.map((i) => `${i.qty}× ${i.name}`).join(", ")}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
