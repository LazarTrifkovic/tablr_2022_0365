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

export interface ServiceRequest {
  id: string;
  cafe_id: string;
  table_number: number;
  kind: "waiter" | "bill";
  status: "OPEN" | "RESOLVED";
  created_at: string;
}

export type WsEvent =
  | { type: "ticket.created" | "ticket.updated"; ticket: Ticket }
  | { type: "request.created" | "request.resolved"; request: ServiceRequest };
