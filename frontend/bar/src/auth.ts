export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface StaffUser {
  id: string;
  cafe_id: string;
  email: string;
  role: "vlasnik" | "konobar";
  name: string;
}

interface Session {
  token: string;
  user: StaffUser;
}

const KEY = "tablr_bar_session";

export function getSession(): Session | null {
  const raw = localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}

export function saveSession(s: Session): void {
  localStorage.setItem(KEY, JSON.stringify(s));
}

export function clearSession(): void {
  localStorage.removeItem(KEY);
}

export async function login(email: string, password: string): Promise<Session> {
  const r = await fetch(`${API}/api/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!r.ok) {
    const b = await r.json().catch(() => ({}));
    throw new Error(b.detail ?? "Prijava nije uspela");
  }
  const data = await r.json();
  const s: Session = { token: data.access_token, user: data.user };
  saveSession(s);
  return s;
}

/** fetch koji dodaje Bearer token; na 401 (istekla smena) čisti sesiju i vraća na prijavu. */
export async function authFetch(path: string, opts: RequestInit = {}): Promise<Response> {
  const s = getSession();
  const headers = new Headers(opts.headers);
  if (s) headers.set("Authorization", `Bearer ${s.token}`);
  const r = await fetch(`${API}${path}`, { ...opts, headers });
  if (r.status === 401) {
    clearSession();
    window.location.reload();
  }
  return r;
}
