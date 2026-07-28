import { useEffect, useState } from "react";
import Login from "./Login";
import MenuAdmin from "./MenuAdmin";
import QrCodes from "./QrCodes";
import Staff from "./Staff";
import { authFetch, clearSession, getSession, type Owner } from "./auth";

type Tab = "menu" | "qr" | "staff";

export default function App() {
  const [user, setUser] = useState<Owner | null>(() => getSession()?.user ?? null);
  if (!user) return <Login onDone={setUser} />;
  // admin je za vlasnika; konobar nema šta da radi ovde
  if (user.role !== "vlasnik") {
    return (
      <div className="login-screen">
        <div className="login-card">
          <h1>tablr <span>admin</span></h1>
          <p className="a-err">Admin panel je dostupan samo vlasniku.</p>
          <button onClick={() => { clearSession(); setUser(null); }}>Nazad na prijavu</button>
        </div>
      </div>
    );
  }
  return <AdminShell user={user} onLogout={() => { clearSession(); setUser(null); }} />;
}

function AdminShell({ user, onLogout }: { user: Owner; onLogout: () => void }) {
  const [tab, setTab] = useState<Tab>("menu");
  const [cafeName, setCafeName] = useState("");

  useEffect(() => {
    authFetch(`/api/menu/cafes`)
      .then((r) => r.json())
      .then((cafes: { id: string; name: string }[]) => {
        const c = cafes.find((x) => x.id === user.cafe_id);
        if (c) setCafeName(c.name);
      })
      .catch(() => {});
  }, [user.cafe_id]);

  return (
    <div className="admin">
      <header className="no-print">
        <h1>tablr <span>admin</span></h1>
        <nav>
          <button className={tab === "menu" ? "on" : ""} onClick={() => setTab("menu")}>Meni</button>
          <button className={tab === "qr" ? "on" : ""} onClick={() => setTab("qr")}>QR kodovi</button>
          <button className={tab === "staff" ? "on" : ""} onClick={() => setTab("staff")}>Osoblje</button>
        </nav>
        <div className="a-right">
          <span className="a-cafe">{cafeName || "…"}</span>
          <span className="a-user">{user.name}</span>
          <button className="a-logout" onClick={onLogout}>Odjava</button>
        </div>
      </header>
      <main>
        {tab === "menu" && <MenuAdmin cafeId={user.cafe_id} />}
        {tab === "qr" && <QrCodes cafeId={user.cafe_id} cafeName={cafeName} />}
        {tab === "staff" && <Staff cafeId={user.cafe_id} />}
      </main>
    </div>
  );
}
