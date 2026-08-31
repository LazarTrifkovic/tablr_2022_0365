import { useEffect, useRef, useState } from "react";

// Google Pay JS se učitava sa Google-a; nemamo @types pa tipove držimo labavo.
declare global {
  interface Window {
    google?: { payments?: { api?: { PaymentsClient: new (o: unknown) => GPayClient } } };
  }
}
interface GPayClient {
  isReadyToPay: (r: unknown) => Promise<{ result: boolean }>;
  createButton: (o: unknown) => HTMLElement;
  loadPaymentData: (r: unknown) => Promise<{
    paymentMethodData?: { tokenizationData?: { token?: string } };
  }>;
}

const GPAY_SRC = "https://pay.google.com/gp/p/js/pay.js";

// TEST placeholder gateway — Google vraća lažan token, bez pravog PSP naloga
const cardPaymentMethod = {
  type: "CARD",
  parameters: {
    allowedAuthMethods: ["PAN_ONLY", "CRYPTOGRAM_3DS"],
    allowedCardNetworks: ["MASTERCARD", "VISA"],
  },
  tokenizationSpecification: {
    type: "PAYMENT_GATEWAY",
    parameters: { gateway: "example", gatewayMerchantId: "exampleGatewayMerchantId" },
  },
};
const BASE = { apiVersion: 2, apiVersionMinor: 0 };

function loadScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.google?.payments?.api) return resolve();
    const s = document.createElement("script");
    s.src = GPAY_SRC;
    s.async = true;
    s.onload = () => resolve();
    s.onerror = () => reject(new Error("Google Pay nedostupan"));
    document.head.appendChild(s);
  });
}

export default function GooglePayButton({
  amount,
  disabled,
  onToken,
}: {
  amount: number;
  disabled: boolean;
  onToken: (token: string) => void;
}) {
  const holder = useRef<HTMLDivElement>(null);
  const client = useRef<GPayClient | null>(null);
  const [ready, setReady] = useState(false);

  // najsvežije vrednosti u ref-u da onClick uvek vidi tačan iznos/stanje
  const amountRef = useRef(amount);
  amountRef.current = amount;
  const disabledRef = useRef(disabled);
  disabledRef.current = disabled;
  const onTokenRef = useRef(onToken);
  onTokenRef.current = onToken;

  useEffect(() => {
    let cancelled = false;
    loadScript()
      .then(() => {
        if (cancelled) return null;
        client.current = new window.google!.payments!.api!.PaymentsClient({
          environment: "TEST",
        });
        return client.current.isReadyToPay({ ...BASE, allowedPaymentMethods: [cardPaymentMethod] });
      })
      .then((res) => {
        if (!cancelled && res?.result) setReady(true);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!ready || !holder.current || !client.current) return;
    holder.current.innerHTML = "";
    const btn = client.current.createButton({
      buttonColor: "black",
      buttonType: "pay",
      buttonSizeMode: "fill",
      onClick: async () => {
        if (disabledRef.current || amountRef.current <= 0 || !client.current) return;
        try {
          const data = await client.current.loadPaymentData({
            ...BASE,
            allowedPaymentMethods: [cardPaymentMethod],
            transactionInfo: {
              totalPriceStatus: "FINAL",
              totalPrice: String(amountRef.current),
              currencyCode: "RSD",
              countryCode: "RS",
            },
            merchantInfo: { merchantName: "tablr (TEST)" },
          });
          const token = data?.paymentMethodData?.tokenizationData?.token ?? "";
          if (token) onTokenRef.current(token);
        } catch {
          /* gost odustao ili greška — ignoriši */
        }
      },
    });
    holder.current.appendChild(btn);
  }, [ready]);

  if (!ready) return null;
  return (
    <div
      className="gpay"
      ref={holder}
      style={{ opacity: disabled ? 0.5 : 1, pointerEvents: disabled ? "none" : "auto" }}
    />
  );
}
