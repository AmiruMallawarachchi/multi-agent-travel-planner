export type ActivityState =
  | "ROUTING"
  | "SEARCHING"
  | "BOOKING"
  | "RESPONDING"
  | "CLARIFYING";

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
};

export type HotelResult = {
  id?: string;
  hotel_id?: string;
  name: string;
  city_code?: string;
  address?: string;
  rating?: string;
  check_in?: string;
  check_out?: string;
  room?: string;
  beds?: number;
  bed_type?: string;
  price?: string;
  currency?: string;
  available: boolean;
};

export type FlightResult = {
  id?: string;
  origin?: string;
  destination?: string;
  departure_at?: string;
  arrival_at?: string;
  duration?: string;
  stops: number;
  carrier?: string;
  flight_number?: string;
  aircraft?: string;
  price?: string;
  currency?: string;
  seats?: number;
};

export type BookingConfirmation = {
  type: "hotel" | "flight";
  confirmation_number?: string;
  offer_id?: string;
  traveller_name?: string;
  status?: string;
  booked_at?: string;
  simulated: true;
};

export type SseEvent =
  | { type: "session"; session_id: string }
  | { type: "status"; state: ActivityState; node?: string }
  | { type: "tool"; status: "INVOKED" | "SUCCEEDED" | "FAILED"; tool: string }
  | { type: "token"; content: string }
  | { type: "result"; category: "hotel"; tool: string; items: HotelResult[] }
  | { type: "result"; category: "flight"; tool: string; items: FlightResult[] }
  | { type: "result"; category: "booking"; tool: string; confirmation: BookingConfirmation }
  | { type: "error"; message: string }
  | { type: "done" };

export type ToolActivity = {
  id: string;
  tool: string;
  status: "INVOKED" | "SUCCEEDED" | "FAILED";
};
