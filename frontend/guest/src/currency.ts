import { useEffect, useState } from "react";
import { API } from "./api";

export interface FxRate {
  currency: string;
  rsd_per_unit: number;
}
interface FxData {
  fresh: boolean;
  rates: FxRate[];
}

const SYMBOL: Record<string, string> = {
  EUR: "€", USD: "$", GBP: "£", CHF: "CHF", RSD: "din",
};

/** Učitava kursnu listu jednom; vraća listu valuta + funkciju za pretvaranje RSD → izabrana. */
export function useCurrency() {
  const [fx, setFx] = useState<FxData | null>(null);
  const [selected, setSelected] = useState("RSD");

  useEffect(() => {
    fetch(`${API}/api/menu/fx`)
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => d && setFx({ fresh: d.fresh, rates: d.rates }))
      .catch(() => {});
  }, []);

  const options = ["RSD", ...(fx?.rates.map((r) => r.currency) ?? [])];

  /** Prikaz cene: uvek RSD, plus "≈ X €" ako je izabrana strana valuta. */
  function convert(rsd: number): string | null {
    if (selected === "RSD" || !fx) return null;
    const rate = fx.rates.find((r) => r.currency === selected);
    if (!rate) return null;
    const value = rsd / rate.rsd_per_unit;
    const sym = SYMBOL[selected] ?? selected;
    const num = value.toLocaleString("sr-RS", {
      minimumFractionDigits: 2, maximumFractionDigits: 2,
    });
    return selected === "CHF" ? `≈ ${num} ${sym}` : `≈ ${num} ${sym}`;
  }

  return { options, selected, setSelected, convert, fresh: fx?.fresh ?? true };
}
