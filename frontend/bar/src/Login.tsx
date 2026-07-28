import { useState } from "react";
import { login, type StaffUser } from "./auth";

export default function Login({ onLogin }: { onLogin: (u: StaffUser) => void }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const s = await login(email.trim(), password);
      onLogin(s.user);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Greška");
      setBusy(false);
    }
  };

  return (
    <div className="login-screen">
      <form className="login-card" onSubmit={submit}>
        <h1>tablr <span>bar</span></h1>
        <p className="login-sub">Prijava osoblja</p>
        <input
          type="email"
          placeholder="Email"
          autoComplete="username"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <input
          type="password"
          placeholder="Lozinka"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
        <button type="submit" disabled={busy}>
          {busy ? "Prijavljivanje…" : "Prijavi se"}
        </button>
        {error && <p className="login-err">{error}</p>}
        <p className="login-demo">
          Demo: <code>vlasnik@panorama.rs</code> / <code>vlasnik123</code><br />
          <code>konobar@panorama.rs</code> / <code>konobar123</code>
        </p>
      </form>
    </div>
  );
}
