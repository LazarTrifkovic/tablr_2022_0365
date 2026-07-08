import { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

interface MenuItem {
  id: string;
  name: string;
  price: number;
  available: boolean;
  note: string | null;
}

interface Category {
  id: string;
  name: string;
  items: MenuItem[];
}

export default function MenuManager({ cafeId }: { cafeId: string }) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [saving, setSaving] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/api/menu/cafes/${cafeId}/menu`)
      .then((r) => r.json())
      .then((menu) => setCategories(menu.categories));
  }, [cafeId]);

  const patchItem = async (itemId: string, body: Partial<MenuItem>) => {
    setSaving(itemId);
    const r = await fetch(`${API}/api/menu/cafes/${cafeId}/items/${itemId}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (r.ok) {
      const updated: MenuItem = await r.json();
      setCategories((cats) =>
        cats.map((c) => ({
          ...c,
          items: c.items.map((i) => (i.id === itemId ? { ...i, ...updated } : i)),
        })),
      );
    }
    setSaving(null);
  };

  return (
    <div className="menu-manager">
      {categories.map((cat) => (
        <section key={cat.id}>
          <h2>{cat.name}</h2>
          {cat.items.map((item) => (
            <div className={`mm-item ${!item.available ? "mm-off" : ""}`} key={item.id}>
              <strong>{item.name}</strong>
              <input
                placeholder="napomena za goste (npr. danas bez limuna)"
                defaultValue={item.note ?? ""}
                maxLength={200}
                onBlur={(e) => {
                  const v = e.target.value.trim() || null;
                  if (v !== (item.note ?? null)) patchItem(item.id, { note: v });
                }}
              />
              <button
                className={item.available ? "avail" : "unavail"}
                disabled={saving === item.id}
                onClick={() => patchItem(item.id, { available: !item.available })}
              >
                {item.available ? "✓ Ima" : "✗ Nema"}
              </button>
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}
