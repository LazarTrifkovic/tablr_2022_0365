import type { Menu, Order } from "./types";

export const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export interface TableCtx {
  cafeId: string;
  table: number;
  sig: string;
}

export function readTableCtx(): TableCtx | null {
  const p = new URLSearchParams(window.location.search);
  const cafeId = p.get("cafe");
  const table = Number(p.get("table"));
  const sig = p.get("sig");
  if (!cafeId || !table || !sig) return null;
  return { cafeId, table, sig };
}

export async function fetchMenu(cafeId: string): Promise<Menu> {
  const r = await fetch(`${API}/api/menu/cafes/${cafeId}/menu`);
  if (!r.ok) throw new Error("Meni nije dostupan");
  return r.json();
}

export async function submitOrder(
  ctx: TableCtx,
  items: { item_id: string; qty: number }[],
  note: string,
): Promise<Order> {
  const r = await fetch(`${API}/api/orders/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      cafe_id: ctx.cafeId,
      table_number: ctx.table,
      sig: ctx.sig,
      note: note || null,
      items,
    }),
  });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail ?? "Porudžbina nije prošla");
  }
  return r.json();
}

export async function sendRequest(
  ctx: TableCtx,
  kind: "waiter" | "bill",
): Promise<void> {
  const r = await fetch(`${API}/api/bar/requests`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      cafe_id: ctx.cafeId,
      table_number: ctx.table,
      sig: ctx.sig,
      kind,
    }),
  });
  if (!r.ok) throw new Error("Zahtev nije prošao");
}

export async function fetchTableOrders(ctx: TableCtx): Promise<Order[]> {
  const r = await fetch(
    `${API}/api/orders/tables/${ctx.cafeId}/${ctx.table}/orders?sig=${ctx.sig}`,
  );
  if (!r.ok) return [];
  return r.json();
}

export async function submitRating(
  ctx: TableCtx,
  orderId: string,
  rating: number,
  comment: string,
): Promise<Order> {
  const r = await fetch(`${API}/api/orders/orders/${orderId}/rating`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ sig: ctx.sig, rating, comment: comment || null }),
  });
  if (!r.ok) {
    const body = await r.json().catch(() => ({}));
    throw new Error(body.detail ?? "Ocena nije prošla");
  }
  return r.json();
}
