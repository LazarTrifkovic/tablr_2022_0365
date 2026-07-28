import { useEffect, useRef, useState } from "react";
import { authFetch } from "./auth";

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

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v));

export default function TableMapEditor({
  cafeId,
  onDone,
}: {
  cafeId: string;
  onDone: (saved: boolean) => void;
}) {
  const [tables, setTables] = useState<TableSpot[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const canvasRef = useRef<HTMLDivElement>(null);
  // stanje prevlačenja: koji sto, tip (move/resize), i početni offset unutar pločice
  const drag = useRef<{ num: number; mode: "move" | "resize"; dx: number; dy: number } | null>(null);

  useEffect(() => {
    authFetch(`/api/menu/cafes`)
      .then((r) => r.json())
      .then((cafes: { id: string; tables: TableSpot[] }[]) => {
        const cafe = cafes.find((c) => c.id === cafeId);
        // stolovi bez pozicije dobijaju podrazumevanu (da se mogu prevlačiti)
        const list = (cafe?.tables ?? []).map((t, i) => ({
          ...t,
          x: t.x ?? 8 + (i % 5) * 18,
          y: t.y ?? 8 + Math.floor(i / 5) * 22,
          w: t.w ?? 12,
          h: t.h ?? 12,
        }));
        setTables(list);
      })
      .catch(() => setError("Ne mogu da učitam raspored"));
  }, [cafeId]);

  const patch = (num: number, upd: Partial<TableSpot>) =>
    setTables((ts) => ts.map((t) => (t.number === num ? { ...t, ...upd } : t)));

  const sel = tables.find((t) => t.number === selected) ?? null;

  const onPointerDown = (e: React.PointerEvent, t: TableSpot, mode: "move" | "resize") => {
    e.preventDefault();
    e.stopPropagation();
    setSelected(t.number);
    const rect = canvasRef.current!.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * 100;
    const py = ((e.clientY - rect.top) / rect.height) * 100;
    drag.current = { num: t.number, mode, dx: px - (t.x ?? 0), dy: py - (t.y ?? 0) };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const onPointerMove = (e: React.PointerEvent) => {
    if (!drag.current || !canvasRef.current) return;
    const rect = canvasRef.current.getBoundingClientRect();
    const px = ((e.clientX - rect.left) / rect.width) * 100;
    const py = ((e.clientY - rect.top) / rect.height) * 100;
    const d = drag.current;
    const t = tables.find((x) => x.number === d.num);
    if (!t) return;
    if (d.mode === "move") {
      patch(d.num, { x: clamp(px - d.dx, 0, 100 - t.w), y: clamp(py - d.dy, 0, 100 - t.w) });
    } else {
      // resize: nova širina = rastojanje od gornjeg-levog ugla (kvadratno, w=h)
      const nw = clamp(px - (t.x ?? 0), 4, 40);
      patch(d.num, { w: Math.round(nw), h: Math.round(nw) });
    }
  };

  const endDrag = () => { drag.current = null; };

  const addTable = () => {
    const next = tables.length ? Math.max(...tables.map((t) => t.number)) + 1 : 1;
    const nt: TableSpot = {
      number: next, zone: null, label: null, shape: "square", seats: null,
      x: 44, y: 44, w: 12, h: 12,
    };
    setTables((ts) => [...ts, nt]);
    setSelected(next);
  };

  const removeSelected = () => {
    if (selected === null) return;
    setTables((ts) => ts.filter((t) => t.number !== selected));
    setSelected(null);
  };

  const save = async () => {
    setSaving(true);
    setError(null);
    const nums = tables.map((t) => t.number);
    if (new Set(nums).size !== nums.length) {
      setError("Brojevi stolova moraju biti jedinstveni");
      setSaving(false);
      return;
    }
    try {
      const r = await authFetch(`/api/menu/cafes/${cafeId}/tables`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tables }),
      });
      if (!r.ok) {
        const b = await r.json().catch(() => ({}));
        throw new Error(b.detail ?? "Snimanje nije uspelo");
      }
      onDone(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Greška");
      setSaving(false);
    }
  };

  return (
    <div className="map-editor">
      <div className="me-toolbar">
        <strong>Uređivanje rasporeda</strong>
        <span className="me-hint">Prevuci sto da ga pomeriš · ugao za veličinu</span>
        <div className="me-actions">
          <button className="me-add" onClick={addTable}>+ Dodaj sto</button>
          <button className="me-cancel" onClick={() => onDone(false)}>Otkaži</button>
          <button className="me-save" disabled={saving} onClick={save}>
            {saving ? "Snimam…" : "Sačuvaj raspored"}
          </button>
        </div>
      </div>
      {error && <p className="me-err">{error}</p>}

      <div
        className="map-canvas me-canvas"
        ref={canvasRef}
        onPointerMove={onPointerMove}
        onPointerUp={endDrag}
        onPointerLeave={endDrag}
      >
        {tables.map((t) => (
          <div
            key={t.number}
            className={`table-tile tt-free ${t.shape === "round" ? "tt-round" : ""} ${
              selected === t.number ? "tt-selected" : ""
            }`}
            style={{ position: "absolute", left: `${t.x}%`, top: `${t.y}%`, width: `${t.w}%` }}
            onPointerDown={(e) => onPointerDown(e, t, "move")}
          >
            <span className="tt-num">{t.number}</span>
            {t.seats != null && <span className="tt-label">{t.seats} mesta</span>}
            <span
              className="me-resize"
              onPointerDown={(e) => onPointerDown(e, t, "resize")}
            />
          </div>
        ))}
      </div>

      {sel && (
        <div className="me-panel">
          <h3>Sto {sel.number}</h3>
          <label>Broj
            <input type="number" min={1} value={sel.number}
              onChange={(e) => patch(sel.number, { number: Number(e.target.value) })} />
          </label>
          <label>Zona
            <input value={sel.zone ?? ""} placeholder="Unutra / Bašta…"
              onChange={(e) => patch(sel.number, { zone: e.target.value || null })} />
          </label>
          <label>Opis
            <input value={sel.label ?? ""} placeholder="do prozora…"
              onChange={(e) => patch(sel.number, { label: e.target.value || null })} />
          </label>
          <label>Mesta
            <input type="number" min={1} value={sel.seats ?? ""}
              onChange={(e) => patch(sel.number, { seats: e.target.value ? Number(e.target.value) : null })} />
          </label>
          <div className="me-shape">
            <button className={sel.shape === "square" ? "on" : ""}
              onClick={() => patch(sel.number, { shape: "square" })}>▢ Kvadrat</button>
            <button className={sel.shape === "round" ? "on" : ""}
              onClick={() => patch(sel.number, { shape: "round" })}>◯ Okrugao</button>
          </div>
          <button className="me-remove" onClick={removeSelected}>Ukloni sto</button>
        </div>
      )}
    </div>
  );
}
