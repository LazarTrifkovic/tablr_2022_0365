import { useState } from "react";
import { login, type StaffUser } from "./auth";

// demo nalozi (dev/ispit) — pred-popunjeni da se ne kuca pri svakoj prijavi
const DEMO = {
  konobar: { email: "konobar", password: "konobar" },
  vlasnik: { email: "admin", password: "admin" },
};

export default function Login({ onLogin }: { onLogin: (u: StaffUser) => void }) {
  const [email, setEmail] = useState(DEMO.konobar.email);
  const [password, setPassword] = useState(DEMO.konobar.password);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const fill = (r: keyof typeof DEMO) => {
    setEmail(DEMO[r].email);
    setPassword(DEMO[r].password);
    setError(null);
  };

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
        <div className="demo-fill">
          <button type="button" onClick={() => fill("konobar")}>Konobar</button>
          <button type="button" onClick={() => fill("vlasnik")}>Admin</button>
        </div>
        <input
          type="text"
          placeholder="Korisničko ime"
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
          Demo: <code>konobar</code> / <code>konobar</code><br />
          <code>admin</code> / <code>admin</code>
        </p>
      </form>
    </div>
  );
}
