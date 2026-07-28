export interface TicketItem {
  name: string;
  qty: number;
}

export interface Ticket {
  order_id: string;
  cafe_id: string;
  table_number: number;
  status: string;
  note: string | null;
  created_at: string;
  items: TicketItem[];
}

export interface HistoryItem {
  item_id: string;
  name: string;
  unit_price: number;
  qty: number;
}

// završena porudžbina iz arhive smene (orders /orders/history)
export interface HistoryOrder {
  id: string;
  table_number: number;
  status: string;
  note: string | null;
  total: number;
  payment_method: string | null;
  rating: number | null;
  rating_comment: string | null;
  created_at: string;
  accepted_at: string | null;
  ready_at: string | null;
  delivered_at: string | null;
  cancelled_at: string | null;
  items: HistoryItem[];
}

export interface ServiceRequest {
  id: string;
  cafe_id: string;
  table_number: number;
  kind: "waiter" | "bill" | "bill_split";
  status: "OPEN" | "RESOLVED";
  created_at: string;
  detail?: string | null;
  item_ids?: number[] | null;
  amount?: number | null;
}

export type WsEvent =
  | { type: "ticket.created" | "ticket.updated"; ticket: Ticket }
  | { type: "request.created" | "request.resolved"; request: ServiceRequest };
