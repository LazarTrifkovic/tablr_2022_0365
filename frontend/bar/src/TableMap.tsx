import { useEffect, useState } from "react";
import type { ServiceRequest, Ticket } from "./types";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type TableState = "free" | "busy" | "ready" | "call";

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
  const [tablesCount, setTablesCount] = useState(12);
  const [selected, setSelected] = useState<number | null>(null);

  useEffect(() => {
    fetch(`${API}/api/menu/cafes`)
      .then((r) => r.json())
      .then((cafes: { id: string; tables_count: number }[]) => {
        const cafe = cafes.find((c) => c.id === cafeId);
        if (cafe) setTablesCount(cafe.tables_count);
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

  return (
    <div className="table-map">
      <div className="map-grid">
        {Array.from({ length: tablesCount }, (_, i) => i + 1).map((n) => {
          const state = stateOf(n);
          return (
            <button
              key={n}
              className={`table-tile tt-${state} ${selected === n ? "tt-selected" : ""}`}
              onClick={() => setSelected(selected === n ? null : n)}
            >
              <span className="tt-num">{n}</span>
              <span className="tt-label">{STATE_LABEL[state]}</span>
            </button>
          );
        })}
      </div>

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
