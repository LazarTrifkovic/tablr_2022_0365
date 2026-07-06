import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { Ticket, WsEvent } from "./types";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const WS_URL = API.replace(/^http/, "ws");

const COLUMNS: { status: string; title: string; action?: { to: string; label: string } }[] = [
  { status: "CREATED", title: "Novo", action: { to: "ACCEPTED", label: "Prihvati" } },
  { status: "ACCEPTED", title: "U pripremi", action: { to: "READY", label: "Spremno" } },
  { status: "READY", title: "Spremno", action: { to: "DELIVERED", label: "Isporučeno" } },
];

export default function App() {
  const cafeId = useMemo(
    () => new URLSearchParams(window.location.search).get("cafe"),
    [],
  );
  if (!cafeId) {
    return (
      <div className="screen-msg">
        <h1>tablr bar</h1>
        <p>Otvorite dashboard sa parametrom kafića: <code>?cafe=&lt;id&gt;</code></p>
      </div>
    );
  }
  return <BarApp cafeId={cafeId} />;
}

function BarApp({ cafeId }: { cafeId: string }) {
  const [tickets, setTickets] = useState<Map<string, Ticket>>(new Map());
  const [connected, setConnected] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const upsert = useCallback((ticket: Ticket) => {
    setTickets((prev) => new Map(prev).set(ticket.order_id, ticket));
  }, []);

  const loadTickets = useCallback(async () => {
    const r = await fetch(`${API}/api/bar/tickets?cafe_id=${cafeId}`);
    if (r.ok) {
      const list: Ticket[] = await r.json();
      setTickets(new Map(list.map((t) => [t.order_id, t])));
    }
  }, [cafeId]);

  // WebSocket sa automatskim ponovnim povezivanjem
  useEffect(() => {
    let closed = false;
    let retry: number | undefined;

    const connect = () => {
      const ws = new WebSocket(`${WS_URL}/ws/bar/${cafeId}`);
      wsRef.current = ws;
      ws.onopen = () => {
        setConnected(true);
        loadTickets(); // sinhronizuj propušteno dok smo bili offline
      };
      ws.onmessage = (e) => {
        const event: WsEvent = JSON.parse(e.data);
        upsert(event.ticket);
        if (event.type === "ticket.created") {
          setFlash(event.ticket.order_id);
          setTimeout(() => setFlash(null), 2500);
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closed) retry = window.setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      closed = true;
      window.clearTimeout(retry);
      wsRef.current?.close();
    };
  }, [cafeId, loadTickets, upsert]);

  const setStatus = async (orderId: string, status: string) => {
    const r = await fetch(`${API}/api/bar/tickets/${orderId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status }),
    });
    if (r.ok) upsert(await r.json());
  };

  const byStatus = (status: string) =>
    [...tickets.values()]
      .filter((t) => t.status === status)
      .sort((a, b) => a.created_at.localeCompare(b.created_at));

  return (
    <div className="board">
      <header>
        <h1>tablr <span>bar</span></h1>
        <span className={`conn ${connected ? "on" : "off"}`}>
          {connected ? "● uživo" : "○ ponovno povezivanje…"}
        </span>
      </header>
      <div className="columns">
        {COLUMNS.map((col) => {
          const list = byStatus(col.status);
          return (
            <div className="column" key={col.status}>
              <h2>
                {col.title} <em>{list.length}</em>
              </h2>
              {list.map((t) => (
                <div
                  className={`ticket ${flash === t.order_id ? "flash" : ""}`}
                  key={t.order_id}
                >
                  <div className="ticket-head">
                    <strong>Sto {t.table_number}</strong>
                    <time>
                      {new Date(t.created_at).toLocaleTimeString("sr-RS", {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </time>
                  </div>
                  <ul>
                    {t.items.map((i, idx) => (
                      <li key={idx}>
                        <b>{i.qty}×</b> {i.name}
                      </li>
                    ))}
                  </ul>
                  {t.note && <p className="note">💬 {t.note}</p>}
                  {col.action && (
                    <button onClick={() => setStatus(t.order_id, col.action!.to)}>
                      {col.action.label}
                    </button>
                  )}
                </div>
              ))}
              {list.length === 0 && <p className="empty">—</p>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
