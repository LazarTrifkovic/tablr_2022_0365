import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import MenuManager from "./MenuManager";
import TableMap from "./TableMap";
import { orderSound, requestSound, unlockAudio } from "./sounds";
import type { HistoryOrder, ServiceRequest, Ticket, WsEvent } from "./types";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";
const WS_URL = API.replace(/^http/, "ws");

const COLUMNS: { status: string; title: string; action?: { to: string; label: string } }[] = [
  { status: "CREATED", title: "Novo", action: { to: "ACCEPTED", label: "Prihvati" } },
  { status: "ACCEPTED", title: "U pripremi", action: { to: "READY", label: "Spremno" } },
  { status: "READY", title: "Spremno" }, // isporuka ide kroz izbor načina plaćanja
];

// tiket stariji od ovoga (a nije spreman) postaje crven — kasni
const LATE_MINUTES = 8;

const PAY_LABEL: Record<string, string> = { cash: "keš", card: "kartica" };

/** Proteklo vreme kao živi mm:ss brojač. */
function elapsed(iso: string): { label: string; minutes: number } {
  const sec = Math.max(0, Math.floor((Date.now() - new Date(iso).getTime()) / 1000));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  return { label: `${m}:${s.toString().padStart(2, "0")}`, minutes: m };
}

/** Trajanje između dva trenutka, kratko ("4m 12s"); "—" ako nedostaje. */
function duration(fromIso: string | null, toIso: string | null): string {
  if (!fromIso || !toIso) return "—";
  const sec = Math.max(0, Math.floor((new Date(toIso).getTime() - new Date(fromIso).getTime()) / 1000));
  const m = Math.floor(sec / 60);
  const s = sec % 60;
  if (m >= 60) return `${Math.floor(m / 60)}h ${m % 60}m`;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

/** Sekunde → kratak zapis ("4m 12s"). */
function fmtSec(sec: number): string {
  const m = Math.floor(sec / 60);
  const s = Math.round(sec % 60);
  if (m >= 60) return `${Math.floor(m / 60)}h ${m % 60}m`;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

/** Lokalno vreme HH:MM. */
function clock(iso: string): string {
  return new Date(iso).toLocaleTimeString("sr-RS", { hour: "2-digit", minute: "2-digit" });
}

function Stars({ n }: { n: number }) {
  return <span className="stars" title={`${n}/5`}>{"★".repeat(n)}<span className="star-off">{"★".repeat(5 - n)}</span></span>;
}

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
  const [requests, setRequests] = useState<Map<string, ServiceRequest>>(new Map());
  const [connected, setConnected] = useState(false);
  const [flash, setFlash] = useState<string | null>(null);
  const [view, setView] = useState<"board" | "map" | "menu" | "archive">("board");
  const wsRef = useRef<WebSocket | null>(null);

  // jedan otkucaj u sekundi — živi mm:ss tajmeri na tiketima
  const [, setClock] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setClock((c) => c + 1), 1000);
    return () => clearInterval(t);
  }, []);

  // browseri traže klik pre zvuka — otključaj audio na prvu interakciju
  useEffect(() => {
    const unlock = () => unlockAudio();
    window.addEventListener("pointerdown", unlock, { once: true });
    return () => window.removeEventListener("pointerdown", unlock);
  }, []);

  const upsert = useCallback((ticket: Ticket) => {
    setTickets((prev) => new Map(prev).set(ticket.order_id, ticket));
  }, []);

  const loadTickets = useCallback(async () => {
    const r = await fetch(`${API}/api/bar/tickets?cafe_id=${cafeId}`);
    if (r.ok) {
      const list: Ticket[] = await r.json();
      setTickets(new Map(list.map((t) => [t.order_id, t])));
    }
    const rq = await fetch(`${API}/api/bar/requests?cafe_id=${cafeId}`);
    if (rq.ok) {
      const list: ServiceRequest[] = await rq.json();
      setRequests(new Map(list.map((q) => [q.id, q])));
    }
  }, [cafeId]);

  const resolveRequest = async (id: string) => {
    await fetch(`${API}/api/bar/requests/${id}/resolve`, { method: "PATCH" });
    // uklanjanje stiže i kroz WS event; lokalno odmah radi responzivnosti
    setRequests((prev) => {
      const next = new Map(prev);
      next.delete(id);
      return next;
    });
  };

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
        if (event.type === "ticket.created" || event.type === "ticket.updated") {
          upsert(event.ticket);
          if (event.type === "ticket.created") {
            orderSound();
            setFlash(event.ticket.order_id);
            setTimeout(() => setFlash(null), 2500);
          }
        } else if (event.type === "request.created") {
          requestSound();
          setRequests((prev) => new Map(prev).set(event.request.id, event.request));
        } else if (event.type === "request.resolved") {
          setRequests((prev) => {
            const next = new Map(prev);
            next.delete(event.request.id);
            return next;
          });
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

  const setStatus = async (orderId: string, status: string, paymentMethod?: string) => {
    const r = await fetch(`${API}/api/bar/tickets/${orderId}/status`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(paymentMethod ? { status, payment_method: paymentMethod } : { status }),
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
        <div className="view-tabs">
          <button className={view === "board" ? "active" : ""} onClick={() => setView("board")}>
            Porudžbine
          </button>
          <button className={view === "map" ? "active" : ""} onClick={() => setView("map")}>
            Mapa
          </button>
          <button className={view === "menu" ? "active" : ""} onClick={() => setView("menu")}>
            Meni
          </button>
          <button className={view === "archive" ? "active" : ""} onClick={() => setView("archive")}>
            Arhiva
          </button>
        </div>
        <span className={`conn ${connected ? "on" : "off"}`}>
          {connected ? "● uživo" : "○ ponovno povezivanje…"}
        </span>
      </header>
      {view === "menu" && <MenuManager cafeId={cafeId} />}
      {view === "archive" && <Archive cafeId={cafeId} />}
      {view === "map" && (
        <TableMap
          cafeId={cafeId}
          tickets={[...tickets.values()].filter((t) =>
            ["CREATED", "ACCEPTED", "READY"].includes(t.status),
          )}
          requests={[...requests.values()]}
          onResolveRequest={resolveRequest}
        />
      )}
      {view === "board" && (
      <>{/* tabla porudžbina */}
      {requests.size > 0 && (
        <div className="requests-strip">
          {[...requests.values()].map((q) => (
            <div className="request-card" key={q.id}>
              <span className="req-icon">{q.kind === "bill" ? "🧾" : "🔔"}</span>
              <div>
                <strong>Sto {q.table_number}</strong>
                <small>{q.kind === "bill" ? "traži račun" : "zove konobara"}</small>
              </div>
              <button onClick={() => resolveRequest(q.id)}>Rešeno</button>
            </div>
          ))}
        </div>
      )}
      <div className="columns">
        {COLUMNS.map((col) => {
          const list = byStatus(col.status);
          // u koloni "Novo" najstarija porudžbina je prioritet (#1 na redu)
          const ranked = col.status === "CREATED";
          return (
            <div className="column" key={col.status}>
              <h2>
                {col.title} <em>{list.length}</em>
              </h2>
              {list.map((t, idx) => {
                const { label, minutes } = elapsed(t.created_at);
                const late = minutes >= LATE_MINUTES && t.status !== "READY";
                const priority = ranked && idx === 0 && list.length > 1;
                return (
                <div
                  className={`ticket ${flash === t.order_id ? "flash" : ""} ${late ? "late" : ""} ${priority ? "priority" : ""}`}
                  key={t.order_id}
                >
                  <div className="ticket-head">
                    <strong>
                      {ranked && list.length > 1 && (
                        <span className={`rank ${priority ? "rank-1" : ""}`}>#{idx + 1}</span>
                      )}
                      Sto {t.table_number}
                    </strong>
                    <span className={`age ${late ? "age-late" : ""}`}>⏱ {label}</span>
                  </div>
                  {priority && <span className="priority-tag">na redu prvi</span>}
                  <ul>
                    {t.items.map((i, k) => (
                      <li key={k}>
                        <b>{i.qty}×</b> {i.name}
                      </li>
                    ))}
                  </ul>
                  {t.note && <p className="note">💬 {t.note}</p>}
                  {col.status === "READY" ? (
                    <div className="pay-actions">
                      <span className="pay-label">Isporučeno · plaćeno:</span>
                      <button onClick={() => setStatus(t.order_id, "DELIVERED", "cash")}>💵 Keš</button>
                      <button onClick={() => setStatus(t.order_id, "DELIVERED", "card")}>💳 Kartica</button>
                    </div>
                  ) : col.action ? (
                    <button onClick={() => setStatus(t.order_id, col.action!.to)}>
                      {col.action.label}
                    </button>
                  ) : null}
                </div>
                );
              })}
              {list.length === 0 && <p className="empty">—</p>}
            </div>
          );
        })}
      </div>
      </>
      )}
    </div>
  );
}

function Archive({ cafeId }: { cafeId: string }) {
  const [orders, setOrders] = useState<HistoryOrder[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    fetch(`${API}/api/orders/orders/history?cafe_id=${cafeId}`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("Greška pri učitavanju"))))
      .then(setOrders)
      .catch((e) => setError(e.message));
  }, [cafeId]);

  useEffect(() => { load(); }, [load]);

  const summary = useMemo(() => {
    if (!orders) return null;
    const delivered = orders.filter((o) => o.status === "DELIVERED");
    const revenue = delivered.reduce((s, o) => s + o.total, 0);
    const prepDurs = delivered
      .filter((o) => o.accepted_at && o.ready_at)
      .map((o) => new Date(o.ready_at!).getTime() - new Date(o.accepted_at!).getTime());
    const avgPrep = prepDurs.length
      ? Math.round(prepDurs.reduce((s, d) => s + d, 0) / prepDurs.length / 1000)
      : null;
    const rated = delivered.filter((o) => o.rating != null);
    const avgRating = rated.length
      ? (rated.reduce((s, o) => s + (o.rating ?? 0), 0) / rated.length)
      : null;
    const cash = delivered.filter((o) => o.payment_method === "cash").length;
    const card = delivered.filter((o) => o.payment_method === "card").length;
    return { count: delivered.length, revenue, avgPrep, avgRating, rated: rated.length, cash, card };
  }, [orders]);

  if (error) return <div className="archive"><p className="empty">⚠️ {error}</p></div>;
  if (!orders) return <div className="archive"><p className="empty">Učitavanje arhive…</p></div>;

  return (
    <div className="archive">
      <div className="archive-head">
        <h2>Arhiva smene</h2>
        <button className="ghost" onClick={load}>↻ Osveži</button>
      </div>

      {summary && (
        <div className="stats">
          <div className="stat"><span>Porudžbina</span><strong>{summary.count}</strong></div>
          <div className="stat"><span>Pazar</span><strong>{summary.revenue.toLocaleString("sr-RS")} din</strong></div>
          <div className="stat"><span>Ø priprema</span><strong>{summary.avgPrep != null ? fmtSec(summary.avgPrep) : "—"}</strong></div>
          <div className="stat"><span>Ø ocena</span><strong>{summary.avgRating != null ? `★ ${summary.avgRating.toFixed(1)}` : "—"}<small> ({summary.rated})</small></strong></div>
          <div className="stat"><span>Plaćanje</span><strong>💵 {summary.cash} · 💳 {summary.card}</strong></div>
        </div>
      )}

      {orders.length === 0 && <p className="empty">Još nema završenih porudžbina u ovoj smeni.</p>}

      <div className="archive-list">
        {orders.map((o) => {
          const cancelled = o.status === "CANCELLED";
          return (
          <div className={`archive-card ${cancelled ? "cancelled" : ""}`} key={o.id}>
            <div className="ac-top">
              <strong>Sto {o.table_number}</strong>
              <span className="ac-time">{clock(o.created_at)}</span>
              {cancelled ? (
                <span className="ac-cancelled">otkazano</span>
              ) : (
                <span className="ac-total">{o.total.toLocaleString("sr-RS")} din</span>
              )}
            </div>
            <div className="ac-items">
              {o.items.map((i, k) => (
                <span key={k}>{i.qty}× {i.name}</span>
              ))}
            </div>
            {!cancelled && (
              <div className="ac-meta">
                <span>💳 {o.payment_method ? PAY_LABEL[o.payment_method] ?? o.payment_method : "—"}</span>
                <span>prihvat {duration(o.created_at, o.accepted_at)}</span>
                <span>priprema {duration(o.accepted_at, o.ready_at)}</span>
                <span>ukupno {duration(o.created_at, o.delivered_at)}</span>
              </div>
            )}
            {o.rating != null && (
              <div className="ac-rating">
                <Stars n={o.rating} />
                {o.rating_comment && <em>„{o.rating_comment}"</em>}
              </div>
            )}
          </div>
          );
        })}
      </div>
    </div>
  );
}
