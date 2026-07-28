import { useCallback, useEffect, useState } from "react";
import { authFetch } from "./auth";

interface Item {
  id: string;
  name: string;
  description: string | null;
  price: number;
  available: boolean;
  allergens: string[];
}
interface Category {
  id: string;
  name: string;
  items: Item[];
}

export default function MenuAdmin({ cafeId }: { cafeId: string }) {
  const [cats, setCats] = useState<Category[]>([]);
  const [newCat, setNewCat] = useState("");
  const [error, setError] = useState<string | null>(null);
  // forma za novu stavku po kategoriji
  const [draft, setDraft] = useState<Record<string, { name: string; price: string }>>({});

  const load = useCallback(() => {
    authFetch(`/api/menu/cafes/${cafeId}/menu`)
      .then((r) => r.json())
      .then((m) => setCats(m.categories))
      .catch(() => setError("Ne mogu da učitam meni"));
  }, [cafeId]);
  useEffect(() => { load(); }, [load]);

  const err = async (r: Response) => {
    const b = await r.json().catch(() => ({}));
    setError(b.detail ?? "Greška");
  };

  const addCategory = async () => {
    if (!newCat.trim()) return;
    const r = await authFetch(`/api/menu/cafes/${cafeId}/categories`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: newCat.trim() }),
    });
    if (r.ok) { setNewCat(""); load(); } else err(r);
  };

  const renameCategory = async (id: string, name: string) => {
    const r = await authFetch(`/api/menu/cafes/${cafeId}/categories/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name }),
    });
    if (!r.ok) err(r);
  };

  const deleteCategory = async (id: string) => {
    if (!confirm("Obrisati kategoriju i sve njene stavke?")) return;
    const r = await authFetch(`/api/menu/cafes/${cafeId}/categories/${id}`, { method: "DELETE" });
    if (r.ok) load(); else err(r);
  };

  const addItem = async (catId: string) => {
    const d = draft[catId];
    if (!d?.name.trim() || !d.price) return;
    const r = await authFetch(`/api/menu/cafes/${cafeId}/items`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ category_id: catId, name: d.name.trim(), price: Number(d.price) }),
    });
    if (r.ok) { setDraft((s) => ({ ...s, [catId]: { name: "", price: "" } })); load(); } else err(r);
  };

  const patchItem = async (id: string, body: Partial<Item>) => {
    const r = await authFetch(`/api/menu/cafes/${cafeId}/items/${id}`, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) load(); else err(r);
  };

  const deleteItem = async (id: string) => {
    const r = await authFetch(`/api/menu/cafes/${cafeId}/items/${id}`, { method: "DELETE" });
    if (r.ok) load(); else err(r);
  };

  return (
    <div className="menu-admin">
      {error && <p className="a-err">{error}</p>}
      <div className="add-cat">
        <input placeholder="Nova kategorija (npr. Kokteli)" value={newCat}
          onChange={(e) => setNewCat(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && addCategory()} />
        <button onClick={addCategory}>+ Kategorija</button>
      </div>

      {cats.map((cat) => (
        <section className="a-cat" key={cat.id}>
          <div className="a-cat-head">
            <input className="a-cat-name" defaultValue={cat.name}
              onBlur={(e) => e.target.value.trim() && e.target.value !== cat.name
                && renameCategory(cat.id, e.target.value.trim())} />
            <button className="a-del" onClick={() => deleteCategory(cat.id)}>Obriši kategoriju</button>
          </div>

          {cat.items.map((it) => (
            <div className={`a-item ${!it.available ? "off" : ""}`} key={it.id}>
              <span className="a-iname">{it.name}</span>
              <input className="a-price" type="number" defaultValue={it.price} min={1}
                onBlur={(e) => Number(e.target.value) !== it.price && Number(e.target.value) > 0
                  && patchItem(it.id, { price: Number(e.target.value) })} />
              <span className="a-din">din</span>
              <button className={it.available ? "a-on" : "a-offbtn"}
                onClick={() => patchItem(it.id, { available: !it.available })}>
                {it.available ? "✓ Ima" : "✗ Nema"}
              </button>
              <button className="a-del" onClick={() => deleteItem(it.id)}>✕</button>
            </div>
          ))}

          <div className="a-additem">
            <input placeholder="Naziv stavke" value={draft[cat.id]?.name ?? ""}
              onChange={(e) => setDraft((s) => ({ ...s, [cat.id]: { ...s[cat.id], name: e.target.value, price: s[cat.id]?.price ?? "" } }))} />
            <input placeholder="cena" type="number" min={1} value={draft[cat.id]?.price ?? ""}
              onChange={(e) => setDraft((s) => ({ ...s, [cat.id]: { ...s[cat.id], price: e.target.value, name: s[cat.id]?.name ?? "" } }))} />
            <button onClick={() => addItem(cat.id)}>+ Stavka</button>
          </div>
        </section>
      ))}
      {cats.length === 0 && <p className="a-empty">Još nema kategorija. Dodaj prvu iznad.</p>}
    </div>
  );
}
