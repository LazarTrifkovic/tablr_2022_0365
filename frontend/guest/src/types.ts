export interface MenuItem {
  id: string;
  name: string;
  description?: string | null;
  price: number;
  available: boolean;
  note?: string | null;
  allergens: string[];
}

export interface Category {
  id: string;
  name: string;
  items: MenuItem[];
}

export interface Menu {
  cafe: { id: string; name: string; slug: string; currency: string };
  categories: Category[];
}

export interface OrderItem {
  item_id: string;
  name: string;
  unit_price: number;
  qty: number;
}

export interface Order {
  id: string;
  status: string;
  total: number;
  note: string | null;
  created_at: string;
  rating: number | null;
  rating_comment: string | null;
  items: OrderItem[];
}

export interface BillItem {
  order_item_id: number;
  name: string;
  unit_price: number;
  qty: number;
  line_total: number;
  paid: boolean;
}

export interface Bill {
  cafe_id: string;
  table_number: number;
  items: BillItem[];
  subtotal: number;
  paid_total: number;
  remaining: number;
}

export const STATUS_LABELS: Record<string, string> = {
  CREATED: "Poslato",
  ACCEPTED: "U pripremi",
  READY: "Spremno — stiže",
  DELIVERED: "Isporučeno",
  CANCELLED: "Otkazano",
};
