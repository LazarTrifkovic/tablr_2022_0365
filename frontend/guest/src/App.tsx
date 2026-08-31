import { useCallback, useEffect, useMemo, useState } from "react";
import {
  cancelOrder,
  fetchBill,
  fetchMenu,
  fetchTableOrders,
  payOnline,
  readTableCtx,
  requestBillSplit,
  sendRequest,
  submitOrder,
  submitRating,
  type TableCtx,
} from "./api";
import GooglePayButton from "./GooglePay";
import { useCurrency } from "./currency";
import { STATUS_LABELS, type Bill, type Menu, type Order } from "./types";

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
  const [tab, setTab] = useState<"menu" | "orders" | "racun">("menu");
  const currency = useCurrency();
  // cooldown po vrsti zahteva — sprečava spamovanje konobara
  const [cooldown, setCooldown] = useState<Record<string, boolean>>({});
  const [cancelMsg, setCancelMsg] = useState<string | null>(null);

  const callStaff = async (kind: "waiter" | "bill") => {
    if (cooldown[kind]) return;
    setCooldown((c) => ({ ...c, [kind]: true }));
    try {
      await sendRequest(ctx, kind);
    } catch {
      setCooldown((c) => ({ ...c, [kind]: false }));
      return;
    }
    setTimeout(() => setCooldown((c) => ({ ...c, [kind]: false })), 60_000);
  };

  useEffect(() => {
    fetchMenu(ctx.cafeId).then(setMenu).catch((e) => setError(e.message));
    // osvežavaj meni — bar može da menja dostupnost/napomene u toku smene
    const t = setInterval(
      () => fetchMenu(ctx.cafeId).then(setMenu).catch(() => {}),
      30_000,
    );
    return () => clearInterval(t);
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

  const cancel = async (orderId: string) => {
    setCancelMsg(null);
    try {
      await cancelOrder(ctx, orderId);
      refreshOrders();
    } catch (e) {
      setCancelMsg(e instanceof Error ? e.message : "Greška");
      refreshOrders(); // stanje se možda promenilo (prihvaćeno) — osveži
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
          <select
            className="cur-select"
            value={currency.selected}
            onChange={(e) => currency.setSelected(e.target.value)}
            title="Prikaz cena u valuti"
          >
            {currency.options.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <div className="staff-btns">
          <button disabled={cooldown["waiter"]} onClick={() => callStaff("waiter")}>
            {cooldown["waiter"] ? "✓ Pozvano" : "🔔 Pozovi konobara"}
          </button>
          <button disabled={cooldown["bill"]} onClick={() => callStaff("bill")}>
            {cooldown["bill"] ? "✓ Traženo" : "🧾 Traži račun"}
          </button>
        </div>
        <nav>
          <button className={tab === "menu" ? "active" : ""} onClick={() => setTab("menu")}>
            Meni
          </button>
          <button className={tab === "orders" ? "active" : ""} onClick={() => setTab("orders")}>
            Porudžbine {orders.length > 0 && <em>{orders.length}</em>}
          </button>
          <button className={tab === "racun" ? "active" : ""} onClick={() => setTab("racun")}>
            Račun
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
                    {item.note && <small className="item-note">ℹ {item.note}</small>}
                    {item.allergens.length > 0 && (
                      <small className="allergens">⚠ {item.allergens.join(", ")}</small>
                    )}
                  </div>
                  <div className="item-side">
                    <span className="price">{item.price} din</span>
                    {currency.convert(item.price) && (
                      <span className="price-alt">{currency.convert(item.price)}</span>
                    )}
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
          {cancelMsg && <p className="err cancel-msg">{cancelMsg}</p>}
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
              {o.status === "CREATED" && (
                <button className="cancel-btn" onClick={() => cancel(o.id)}>
                  Otkaži porudžbinu
                </button>
              )}
              {o.status === "DELIVERED" && (
                <RatingBlock ctx={ctx} order={o} onRated={refreshOrders} />
              )}
            </div>
          ))}
        </main>
      )}

      {tab === "racun" && <BillView ctx={ctx} />}

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
            {currency.convert(total) && <em className="btn-alt"> {currency.convert(total)}</em>}
          </button>
          {error && <small className="err">{error}</small>}
        </footer>
      )}
    </div>
  );
}

function RatingBlock({
  ctx,
  order,
  onRated,
}: {
  ctx: TableCtx;
  order: Order;
  onRated: () => void;
}) {
  const [stars, setStars] = useState(0);
  const [hover, setHover] = useState(0);
  const [comment, setComment] = useState("");
  const [sending, setSending] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  // već ocenjeno — prikaži zahvalnicu sa datom ocenom
  if (order.rating != null) {
    return (
      <div className="rating done">
        <span className="rate-stars">{"★".repeat(order.rating)}<span className="off">{"★".repeat(5 - order.rating)}</span></span>
        <small>Hvala na oceni! 🙏</small>
      </div>
    );
  }

  const send = async () => {
    if (stars === 0) return;
    setSending(true);
    setErr(null);
    try {
      await submitRating(ctx, order.id, stars, comment);
      onRated();
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Greška");
      setSending(false);
    }
  };

  return (
    <div className="rating">
      <span className="rate-label">Kako je bilo?</span>
      <div className="rate-stars pick" onMouseLeave={() => setHover(0)}>
        {[1, 2, 3, 4, 5].map((n) => (
          <button
            key={n}
            className={n <= (hover || stars) ? "on" : ""}
            onMouseEnter={() => setHover(n)}
            onClick={() => setStars(n)}
            aria-label={`${n} od 5`}
          >
            ★
          </button>
        ))}
      </div>
      {stars > 0 && (
        <>
          <input
            placeholder="Komentar (opciono)"
            value={comment}
            maxLength={300}
            onChange={(e) => setComment(e.target.value)}
          />
          <button className="rate-send" disabled={sending} onClick={send}>
            {sending ? "Šaljem…" : "Pošalji ocenu"}
          </button>
        </>
      )}
      {err && <small className="err">{err}</small>}
    </div>
  );
}

function BillView({ ctx }: { ctx: TableCtx }) {
  const [bill, setBill] = useState<Bill | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [split, setSplit] = useState(false); // mod podele (biranje stavki)
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  const load = useCallback(() => {
    fetchBill(ctx).then(setBill).catch((e) => setError(e.message));
  }, [ctx]);

  useEffect(() => {
    load();
    const t = setInterval(load, 5000); // plaćene stavke otpadaju kad konobar naplati
    return () => clearInterval(t);
  }, [load]);

  const toggle = (id: number) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });

  if (error) return <main><p className="empty">⚠️ {error}</p></main>;
  if (!bill) return <main><p className="empty">Učitavanje računa…</p></main>;
  if (bill.items.length === 0)
    return <main><p className="empty">Nema stavki na računu za ovaj sto.</p></main>;

  const unpaid = bill.items.filter((i) => !i.paid);
  const allPaid = unpaid.length === 0;
  // ceo račun = sve neplaćeno; podela = samo izabrano
  const targetItems = split
    ? bill.items.filter((i) => selected.has(i.order_item_id) && !i.paid)
    : unpaid;
  const targetTotal = targetItems.reduce((sum, i) => sum + i.line_total, 0);

  const pay = async (method: "cash" | "card") => {
    if (sending || targetItems.length === 0) return;
    setSending(true);
    setError(null);
    try {
      const label = method === "cash" ? "keš" : "kartica";
      const detail = split
        ? `${targetItems.map((i) => `${i.qty}× ${i.name}`).join(", ")} — gost plaća: ${label}`
        : `Ceo račun (${targetItems.length} stavki) — gost plaća: ${label}`;
      await requestBillSplit(
        ctx,
        targetItems.map((i) => i.order_item_id),
        detail,
        targetTotal,
      );
      setSent(true);
      setSelected(new Set());
      setSplit(false);
      setTimeout(() => setSent(false), 8000);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Greška");
    } finally {
      setSending(false);
    }
  };

  // online plaćanje (Google Pay TEST) — token ide Payments servisu, on obeleži plaćeno
  const payGoogle = async (token: string) => {
    if (sending || targetItems.length === 0) return;
    setSending(true);
    setError(null);
    try {
      await payOnline(ctx, targetItems.map((i) => i.order_item_id), targetTotal, token);
      setSelected(new Set());
      setSplit(false);
      load(); // plaćene stavke odmah otpadaju
    } catch (e) {
      setError(e instanceof Error ? e.message : "Greška");
    } finally {
      setSending(false);
    }
  };

  const disabled = sending || targetItems.length === 0;

  return (
    <main>
      <div className="receipt">
        <div className="receipt-head">
          <span>Račun</span>
          <span>Sto {bill.table_number}</span>
        </div>
        <ul className="receipt-items">
          {bill.items.map((i) => {
            const selectable = split && !i.paid;
            const cls = i.paid ? "paid" : selected.has(i.order_item_id) ? "sel" : "";
            return (
              <li key={i.order_item_id} className={cls} onClick={selectable ? () => toggle(i.order_item_id) : undefined}>
                {selectable && (
                  <input
                    type="checkbox"
                    checked={selected.has(i.order_item_id)}
                    readOnly
                  />
                )}
                <span className="ri-name">
                  {i.qty}× {i.name}
                  {i.paid && <em> · plaćeno</em>}
                </span>
                <span className="ri-dots" />
                <span className="ri-price">{i.line_total}</span>
              </li>
            );
          })}
        </ul>
        <div className="receipt-total">
          {bill.paid_total > 0 && (
            <div className="rt-row">
              <span>Plaćeno</span>
              <span>{bill.paid_total} din</span>
            </div>
          )}
          <div className="rt-row grand">
            <span>{split ? "Izabrano" : "Ukupno"}</span>
            <span>{(split ? targetTotal : bill.remaining)} din</span>
          </div>
        </div>
      </div>

      {allPaid ? (
        <p className="bill-done">✓ Sve je plaćeno. Hvala!</p>
      ) : (
        <div className="pay-bar">
          {split && (
            <small className="pay-hint">
              {targetItems.length === 0
                ? "Označite svoje stavke na računu."
                : `Naplata izabranog · ${targetTotal} din`}
            </small>
          )}
          <GooglePayButton amount={targetTotal} disabled={disabled} onToken={payGoogle} />
          <div className="pay-or">ili plati kod konobara</div>
          <div className="pay-methods">
            <button disabled={disabled} onClick={() => pay("cash")}>💵 Keš</button>
            <button disabled={disabled} onClick={() => pay("card")}>💳 Kartica</button>
          </div>
          <button
            className="split-toggle"
            onClick={() => { setSplit((s) => !s); setSelected(new Set()); }}
          >
            {split ? "← Ceo račun" : "➗ Podeli račun"}
          </button>
          {sent && <small className="ok">✓ Konobar je obavešten, stiže sa računom.</small>}
          {error && <small className="err">{error}</small>}
          <small className="bill-hint">Google Pay je demo (TEST) — pravo online plaćanje stiže sa produkcijom.</small>
        </div>
      )}
    </main>
  );
}
