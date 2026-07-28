import { useCallback, useEffect, useState } from "react";
import { authFetch } from "./auth";

interface StaffUser {
  id: string;
  email: string;
  role: string;
  name: string;
}

export default function Staff({ cafeId }: { cafeId: string }) {
  const [staff, setStaff] = useState<StaffUser[]>([]);
  const [f, setF] = useState({ name: "", email: "", password: "", role: "konobar" });
  const [error, setError] = useState<string | null>(null);
  const [ok, setOk] = useState<string | null>(null);

  const load = useCallback(() => {
    authFetch(`/api/auth/cafes/${cafeId}/staff`)
      .then((r) => (r.ok ? r.json() : []))
      .then(setStaff)
      .catch(() => {});
  }, [cafeId]);
  useEffect(() => { load(); }, [load]);

  const add = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null); setOk(null);
    const r = await authFetch(`/api/auth/register`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...f, cafe_id: cafeId, name: f.name.trim(), email: f.email.trim() }),
    });
    if (r.ok) {
      setOk(`Nalog ${f.email.trim()} kreiran.`);
      setF({ name: "", email: "", password: "", role: "konobar" });
      load();
    } else {
      const b = await r.json().catch(() => ({}));
      setError(b.detail ?? "Greška");
    }
  };

  return (
    <div className="staff-page">
      <div className="staff-list">
        <h3>Osoblje ({staff.length})</h3>
        {staff.map((u) => (
          <div className="staff-row" key={u.id}>
            <span className="s-name">{u.name}</span>
            <span className={`s-role s-${u.role}`}>{u.role}</span>
            <span className="s-email">{u.email}</span>
          </div>
        ))}
      </div>

      <form className="staff-add" onSubmit={add}>
        <h3>Dodaj nalog</h3>
        <input placeholder="Ime" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} required />
        <input type="email" placeholder="Email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} required />
        <input type="password" placeholder="Lozinka (min 6)" value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} required />
        <select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}>
          <option value="konobar">konobar</option>
          <option value="vlasnik">vlasnik</option>
        </select>
        <button type="submit">Kreiraj nalog</button>
        {ok && <p className="a-ok">{ok}</p>}
        {error && <p className="a-err">{error}</p>}
      </form>
    </div>
  );
}
