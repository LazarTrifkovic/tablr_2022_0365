export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface Owner {
  id: string;
  cafe_id: string;
  email: string;
  role: "vlasnik" | "konobar";
  name: string;
}
interface Session {
  token: string;
  user: Owner;
}

const KEY = "tablr_admin_session";

export function getSession(): Session | null {
  const raw = localStorage.getItem(KEY);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as Session;
  } catch {
    return null;
  }
}
export function saveSession(s: Session) {
  localStorage.setItem(KEY, JSON.stringify(s));
}
export function clearSession() {
  localStorage.removeItem(KEY);
}

async function tokenCall(path: string, body: unknown): Promise<Session> {
  const r = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) {
    const b = await r.json().catch(() => ({}));
    throw new Error(b.detail ?? "Greška");
  }
  const data = await r.json();
  const s: Session = { token: data.access_token, user: data.user };
  saveSession(s);
  return s;
}

export const login = (email: string, password: string) =>
  tokenCall("/api/auth/login", { email, password });

export const onboard = (b: {
  cafe_name: string;
  address: string | null;
  email: string;
  password: string;
  name: string;
}) => tokenCall("/api/auth/onboard", b);

/** fetch sa Bearer tokenom; na 401 čisti sesiju i vraća na prijavu. */
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
