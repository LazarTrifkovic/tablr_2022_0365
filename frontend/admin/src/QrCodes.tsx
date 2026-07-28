import { useEffect, useState } from "react";
import QRCode from "qrcode";
import { authFetch } from "./auth";

interface QrLink {
  table_number: number;
  url: string;
}

export default function QrCodes({ cafeId, cafeName }: { cafeId: string; cafeName: string }) {
  const [links, setLinks] = useState<QrLink[]>([]);
  const [images, setImages] = useState<Record<number, string>>({});
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    authFetch(`/api/menu/cafes/${cafeId}/qr-links`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error("Ne mogu da učitam QR linkove"))))
      .then(setLinks)
      .catch((e) => setError(e.message));
  }, [cafeId]);

  useEffect(() => {
    // generiši QR sliku (data URL) za svaki sto — client-side, offline
    links.forEach((l) => {
      QRCode.toDataURL(l.url, { width: 260, margin: 1 })
        .then((dataUrl) => setImages((im) => ({ ...im, [l.table_number]: dataUrl })))
        .catch(() => {});
    });
  }, [links]);

  if (error) return <p className="a-err">{error}</p>;
  if (links.length === 0)
    return <p className="a-empty">Nema stolova. Dodaj stolove u editoru mape (bar dashboard) pa se vrati.</p>;

  return (
    <div className="qr-page">
      <div className="qr-toolbar no-print">
        <p>QR kodovi za {links.length} stolova — odštampaj i zalepi na svaki sto.</p>
        <button onClick={() => window.print()}>🖨️ Štampaj sve</button>
      </div>
      <div className="qr-grid">
        {links.map((l) => (
          <div className="qr-card" key={l.table_number}>
            <strong>{cafeName}</strong>
            <div className="qr-table">Sto {l.table_number}</div>
            {images[l.table_number]
              ? <img src={images[l.table_number]} alt={`QR sto ${l.table_number}`} />
              : <div className="qr-ph">…</div>}
            <small>Skeniraj i poruči sa telefona</small>
          </div>
        ))}
      </div>
    </div>
  );
}
