import { useCallback, useEffect, useMemo, useState } from "react";
import {
  fetchMenu,
  fetchTableOrders,
  readTableCtx,
  submitOrder,
  type TableCtx,
} from "./api";
import { STATUS_LABELS, type Menu, type Order } from "./types";

type Cart = Record<string, number>;

export default function App() {
  const ctx = useMemo(readTableCtx, []);
  if (!ctx) {
    return (
      <div className="screen-msg">
        <h1>tablr</h1>
        <p>Skenirajte QR kod sa vašeg stola da biste otvorili meni. 📱</p>
      </div>
    );
  }
  return <GuestApp ctx={ctx} />;
}

function GuestApp({ ctx }: { ctx: TableCtx }) {
  const [menu, setMenu] = useState<Menu | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [cart, setCart] = useState<Cart>({});
  const [note, setNote] = useState("");
  const [sending, setSending] = useState(false);
  const [orders, setOrders] = useState<Order[]>([]);
  const [tab, setTab] = useState<"menu" | "orders">("menu");

  useEffect(() => {
    fetchMenu(ctx.cafeId).then(setMenu).catch((e) => setError(e.message));
  }, [ctx.cafeId]);

  const refreshOrders = useCallback(() => {
    fetchTableOrders(ctx).then(setOrders).catch(() => {});
  }, [ctx]);

  useEffect(() => {
    refreshOrders();
    const t = setInterval(refreshOrders, 5000);
    return () => clearInterval(t);
  }, [refreshOrders]);

  const allItems = useMemo(
    () => new Map(menu?.categories.flatMap((c) => c.items).map((i) => [i.id, i]) ?? []),
    [menu],
  );
  const cartEntries = Object.entries(cart).filter(([, qty]) => qty > 0);
  const total = cartEntries.reduce(
    (sum, [id, qty]) => sum + (allItems.get(id)?.price ?? 0) * qty,
    0,
  );

  const changeQty = (id: string, delta: number) =>
    setCart((c) => ({ ...c, [id]: Math.max(0, (c[id] ?? 0) + delta) }));

  const placeOrder = async () => {
    setSending(true);
    setError(null);
    try {
      await submitOrder(
        ctx,
        cartEntries.map(([item_id, qty]) => ({ item_id, qty })),
        note,
      );
      setCart({});
      setNote("");
      setTab("orders");
      refreshOrders();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Greška");
    } finally {
      setSending(false);
    }
  };

  if (error && !menu) return <div className="screen-msg"><p>⚠️ {error}</p></div>;
  if (!menu) return <div className="screen-msg"><p>Učitavanje menija…</p></div>;

  return (
    <div className="app">
      <header>
        <div>
          <h1>{menu.cafe.name}</h1>
          <span className="table-badge">Sto {ctx.table}</span>
        </div>
        <nav>
          <button className={tab === "menu" ? "active" : ""} onClick={() => setTab("menu")}>
            Meni
          </button>
          <button className={tab === "orders" ? "active" : ""} onClick={() => setTab("orders")}>
            Porudžbine {orders.length > 0 && <em>{orders.length}</em>}
          </button>
        </nav>
      </header>

      {tab === "menu" && (
        <main>
          {menu.categories.map((cat) => (
            <section key={cat.id}>
              <h2>{cat.name}</h2>
              {cat.items.map((item) => (
                <div className={`item ${!item.available ? "unavailable" : ""}`} key={item.id}>
                  <div className="item-info">
                    <strong>{item.name}</strong>
                    {item.description && <small>{item.description}</small>}
                    {item.allergens.length > 0 && (
                      <small className="allergens">⚠ {item.allergens.join(", ")}</small>
                    )}
                  </div>
                  <div className="item-side">
                    <span className="price">{item.price} din</span>
                    {item.available ? (
                      <div className="qty">
                        <button onClick={() => changeQty(item.id, -1)}>−</button>
                        <span>{cart[item.id] ?? 0}</span>
                        <button onClick={() => changeQty(item.id, 1)}>+</button>
                      </div>
                    ) : (
                      <span className="sold-out">nema</span>
                    )}
                  </div>
                </div>
              ))}
            </section>
          ))}
          <div className="spacer" />
        </main>
      )}

      {tab === "orders" && (
        <main>
          {orders.length === 0 && <p className="empty">Nema aktivnih porudžbina za ovaj sto.</p>}
          {orders.map((o) => (
            <div className="order-card" key={o.id}>
              <div className="order-head">
                <span className={`status s-${o.status}`}>{STATUS_LABELS[o.status] ?? o.status}</span>
                <span className="price">{o.total} din</span>
              </div>
              <ul>
                {o.items.map((i, idx) => (
                  <li key={idx}>{i.qty}× {i.name}</li>
                ))}
              </ul>
              {o.note && <small>Napomena: {o.note}</small>}
            </div>
          ))}
        </main>
      )}

      {tab === "menu" && cartEntries.length > 0 && (
        <footer className="cart-bar">
          <input
            placeholder="Napomena (npr. bez leda)"
            value={note}
            maxLength={300}
            onChange={(e) => setNote(e.target.value)}
          />
          <button className="order-btn" disabled={sending} onClick={placeOrder}>
            {sending ? "Šaljem…" : `Poruči · ${total} din`}
          </button>
          {error && <small className="err">{error}</small>}
        </footer>
      )}
    </div>
  );
}
