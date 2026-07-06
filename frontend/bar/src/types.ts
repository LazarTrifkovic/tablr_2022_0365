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

export interface WsEvent {
  type: "ticket.created" | "ticket.updated";
  ticket: Ticket;
}
