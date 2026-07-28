import { useState } from "react";
import { login, onboard, type Owner } from "./auth";

export default function Login({ onDone }: { onDone: (u: Owner) => void }) {
  const [mode, setMode] = useState<"login" | "onboard">("login");
  const [f, setF] = useState({ cafe_name: "", address: "", email: "", password: "", name: "" });
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const set = (k: keyof typeof f) => (e: React.ChangeEvent<HTMLInputElement>) =>
    setF({ ...f, [k]: e.target.value });

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const s = mode === "login"
        ? await login(f.email.trim(), f.password)
        : await onboard({
            cafe_name: f.cafe_name.trim(), address: f.address.trim() || null,
            email: f.email.trim(), password: f.password, name: f.name.trim(),
          });
      onDone(s.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Greška");
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <h1>tablr <span>admin</span></h1>
        <div className="mode-tabs">
          <button type="button" className={mode === "login" ? "on" : ""} onClick={() => setMode("login")}>
            Prijava
          </button>
          <button type="button" className={mode === "onboard" ? "on" : ""} onClick={() => setMode("onboard")}>
            Registruj kafić
          </button>
        </div>

        {mode === "onboard" && (
          <>
            <input placeholder="Naziv kafića" value={f.cafe_name} onChange={set("cafe_name")} required />
            <input placeholder="Adresa (opciono)" value={f.address} onChange={set("address")} />
            <input placeholder="Vaše ime" value={f.name} onChange={set("name")} required />
          </>
        )}
        <input type="email" placeholder="Email" autoComplete="username" value={f.email} onChange={set("email")} required />
        <input type="password" placeholder="Lozinka" autoComplete={mode === "login" ? "current-password" : "new-password"} value={f.password} onChange={set("password")} required />

        <button type="submit" disabled={busy}>
          {busy ? "Molim sačekajte…" : mode === "login" ? "Prijavi se" : "Napravi kafić"}
        </button>
        {error && <p className="login-err">{error}</p>}
        {mode === "login" && (
          <p className="login-demo">
            Demo: <code>vlasnik@panorama.rs</code> / <code>vlasnik123</code>
          </p>
        )}
      </form>
    </div>
  );
}
