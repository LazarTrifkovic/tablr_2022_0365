import { useEffect, useState } from "react";
import { authFetch } from "./auth";

interface MenuItem {
  id: string;
  name: string;
  price: number;
  available: boolean;
  note: string | null;
  allergens: string[];
}

interface Category {
  id: string;
  name: string;
  items: MenuItem[];
}

export default function MenuManager({ cafeId }: { cafeId: string }) {
  const [categories, setCategories] = useState<Category[]>([]);
  const [saving, setSaving] = useState<string | null>(null);
  // predlozi alergena sa OpenFoodFacts po stavci: itemId → tagovi (ili "loading")
  const [suggest, setSuggest] = useState<Record<string, string[] | "loading">>({});

  useEffect(() => {
    authFetch(`/api/menu/cafes/${cafeId}/menu`)
      .then((r) => r.json())
      .then((menu) => setCategories(menu.categories));
  }, [cafeId]);

  const patchItem = async (itemId: string, body: Partial<MenuItem>) => {
    setSaving(itemId);
    const r = await authFetch(`/api/menu/cafes/${cafeId}/items/${itemId}`, {
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

  const askAllergens = async (item: MenuItem) => {
    setSuggest((s) => ({ ...s, [item.id]: "loading" }));
    try {
      const r = await authFetch(`/api/menu/allergens/search?q=${encodeURIComponent(item.name)}`);
      const data = await r.json();
      // predloži samo tagove kojih stavka još nema
      const fresh = (data.allergens as string[]).filter((a) => !item.allergens.includes(a));
      setSuggest((s) => ({ ...s, [item.id]: fresh }));
    } catch {
      setSuggest((s) => ({ ...s, [item.id]: [] }));
    }
  };

  const addAllergen = (item: MenuItem, tag: string) => {
    patchItem(item.id, { allergens: [...item.allergens, tag] });
    setSuggest((s) => ({ ...s, [item.id]: (s[item.id] as string[]).filter((t) => t !== tag) }));
  };

  const removeAllergen = (item: MenuItem, tag: string) =>
    patchItem(item.id, { allergens: item.allergens.filter((a) => a !== tag) });

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
              <div className="mm-allergens">
                <span className="mm-alabel">Alergeni:</span>
                {item.allergens.map((a) => (
                  <button key={a} className="chip" onClick={() => removeAllergen(item, a)} title="ukloni">
                    {a} ✕
                  </button>
                ))}
                {item.allergens.length === 0 && <span className="mm-none">nema</span>}
                <button className="mm-suggest" onClick={() => askAllergens(item)}>
                  🔎 predloži (OpenFoodFacts)
                </button>
                {suggest[item.id] === "loading" && <span className="mm-none">tražim…</span>}
                {Array.isArray(suggest[item.id]) &&
                  (suggest[item.id] as string[]).map((a) => (
                    <button key={a} className="chip chip-add" onClick={() => addAllergen(item, a)}>
                      + {a}
                    </button>
                  ))}
                {Array.isArray(suggest[item.id]) && (suggest[item.id] as string[]).length === 0 &&
                  <span className="mm-none">nema novih predloga</span>}
              </div>
            </div>
          ))}
        </section>
      ))}
    </div>
  );
}
