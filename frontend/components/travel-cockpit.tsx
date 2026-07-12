"use client";

import Image from "next/image";
import { FormEvent, useEffect, useMemo, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowRight,
  BedDouble,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronRight,
  Hotel,
  LoaderCircle,
  MapPin,
  PanelRightOpen,
  Plane,
  Plus,
  Radio,
  Route,
  Send,
  ShieldCheck,
  Sparkles,
  TicketCheck,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  DEFAULT_DESTINATION,
  detectDestination,
  formatDuration,
  formatMoney,
  formatTime,
} from "@/lib/destinations";
import { parseSseStream } from "@/lib/sse";
import type {
  ActivityState,
  BookingConfirmation,
  FlightResult,
  HotelResult,
  Message,
  ToolActivity,
} from "@/lib/types";
import { cn } from "@/lib/utils";

const QUICK_PROMPTS = [
  "Paris hotels, Sep 10-14",
  "CMB to London, Sep 1",
  "When should I visit Kyoto?",
];

const STAGES: Array<{ state: ActivityState; label: string }> = [
  { state: "ROUTING", label: "Route" },
  { state: "SEARCHING", label: "Search" },
  { state: "BOOKING", label: "Book" },
  { state: "RESPONDING", label: "Reply" },
];

const STATUS_COPY: Record<ActivityState, string> = {
  ROUTING: "Plotting the best path",
  SEARCHING: "Searching live availability",
  BOOKING: "Preparing your confirmation",
  RESPONDING: "Assembling your itinerary",
  CLARIFYING: "Waiting for one more detail",
};

const INITIAL_MESSAGE: Message = {
  id: "welcome",
  role: "assistant",
  content:
    "Welcome aboard. Tell me where you want to go, and I will bring flights, stays, and the moving parts of your journey into one view.",
};

function createId(prefix: string) {
  return `${prefix}-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

export function TravelCockpit() {
  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
  const [draft, setDraft] = useState("");
  const [sessionId, setSessionId] = useState<string>();
  const [activity, setActivity] = useState<ActivityState>();
  const [tools, setTools] = useState<ToolActivity[]>([]);
  const [hotels, setHotels] = useState<HotelResult[]>([]);
  const [flights, setFlights] = useState<FlightResult[]>([]);
  const [booking, setBooking] = useState<BookingConfirmation>();
  const [activeTab, setActiveTab] = useState("overview");
  const [streaming, setStreaming] = useState(false);
  const [backendOnline, setBackendOnline] = useState<boolean>();
  const [mobilePanelOpen, setMobilePanelOpen] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    fetch("/api/health")
      .then((response) => setBackendOnline(response.ok))
      .catch(() => setBackendOnline(false));
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, streaming]);

  const destination = useMemo(() => {
    const conversation = messages.map((message) => message.content).join(" ");
    const code = flights[0]?.destination || hotels[0]?.city_code;
    return detectDestination(conversation, code);
  }, [flights, hotels, messages]);

  const origin = flights[0]?.origin || "CMB";
  const destinationCode = flights[0]?.destination || hotels[0]?.city_code || destination.code;

  async function sendMessage(messageOverride?: string) {
    const message = (messageOverride ?? draft).trim();
    if (!message || streaming) return;

    const userMessage: Message = { id: createId("user"), role: "user", content: message };
    const assistantId = createId("assistant");
    setMessages((current) => [
      ...current,
      userMessage,
      { id: assistantId, role: "assistant", content: "" },
    ]);
    setDraft("");
    setStreaming(true);
    setActivity("ROUTING");
    setTools([]);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, session_id: sessionId }),
      });
      if (!response.ok || !response.body) {
        throw new Error(response.status === 429 ? "Please wait a moment before sending again." : "The travel service is unavailable.");
      }

      for await (const event of parseSseStream(response.body)) {
        if (event.type === "session") setSessionId(event.session_id);
        if (event.type === "status") setActivity(event.state);
        if (event.type === "tool") {
          setTools((current) => {
            if (event.status === "INVOKED") {
              return [...current, { id: createId("tool"), tool: event.tool, status: event.status }];
            }
            const match = [...current].reverse().find((item) => item.tool === event.tool);
            return match
              ? current.map((item) => (item.id === match.id ? { ...item, status: event.status } : item))
              : [...current, { id: createId("tool"), tool: event.tool, status: event.status }];
          });
        }
        if (event.type === "token") {
          setActivity("RESPONDING");
          setMessages((current) =>
            current.map((item) =>
              item.id === assistantId ? { ...item, content: item.content + event.content } : item,
            ),
          );
        }
        if (event.type === "result" && event.category === "hotel") {
          setHotels(event.items);
          setActiveTab("hotels");
        }
        if (event.type === "result" && event.category === "flight") {
          setFlights(event.items);
          setActiveTab("flights");
        }
        if (event.type === "result" && event.category === "booking") {
          setBooking(event.confirmation);
          setActiveTab("overview");
        }
        if (event.type === "error") throw new Error(event.message);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : "Something went wrong. Please try again.";
      setMessages((current) =>
        current.map((item) =>
          item.id === assistantId && !item.content ? { ...item, content: message } : item,
        ),
      );
    } finally {
      setStreaming(false);
      setActivity(undefined);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void sendMessage();
  }

  function prepareBooking(type: "hotel" | "flight", offerId?: string) {
    if (!offerId) return;
    setDraft(
      type === "hotel"
        ? `Book hotel offer ${offerId} for `
        : `Book flight offer ${offerId} for `,
    );
    textareaRef.current?.focus();
  }

  function resetTrip() {
    setMessages([INITIAL_MESSAGE]);
    setDraft("");
    setSessionId(undefined);
    setActivity(undefined);
    setTools([]);
    setHotels([]);
    setFlights([]);
    setBooking(undefined);
    setActiveTab("overview");
    setMobilePanelOpen(false);
  }

  return (
    <div className="app-frame">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark"><Route size={18} strokeWidth={1.8} /></span>
          <div>
            <strong>TripWeaver</strong>
            <span>AI travel studio</span>
          </div>
        </div>
        <div className="topbar-actions">
          <span className={cn("system-state", backendOnline === false && "is-offline")}>
            <i /> {backendOnline === false ? "Backend offline" : "Systems ready"}
          </span>
          <Button variant="secondary" size="sm" onClick={resetTrip}>
            <Plus size={15} /> New trip
          </Button>
        </div>
      </header>

      <main className="cockpit-layout">
        <section className="chat-deck" aria-label="Travel conversation">
          <div className="section-heading">
            <div>
              <span className="eyebrow">Travel concierge</span>
              <h1>Where to next?</h1>
            </div>
            <span className="agent-pill"><Sparkles size={13} /> Multi-agent</span>
          </div>

          <ActivityTimeline activity={activity} tools={tools} streaming={streaming} />

          <div className="message-list" aria-live="polite">
            {messages.map((message) => (
              <article key={message.id} className={cn("message-row", `is-${message.role}`)}>
                <div className="message-meta">
                  <span>{message.role === "assistant" ? "TripWeaver" : "You"}</span>
                  {message.role === "assistant" && <span className="agent-dot" />}
                </div>
                <div className="message-bubble">
                  {message.content ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
                  ) : (
                    <span className="typing-indicator"><i /><i /><i /></span>
                  )}
                </div>
              </article>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="prompt-strip" aria-label="Suggested prompts">
            {QUICK_PROMPTS.map((prompt) => (
              <button key={prompt} onClick={() => void sendMessage(prompt)} disabled={streaming}>
                {prompt}<ChevronRight size={13} />
              </button>
            ))}
          </div>

          <form className="composer" onSubmit={submit}>
            <textarea
              ref={textareaRef}
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  event.currentTarget.form?.requestSubmit();
                }
              }}
              placeholder="Ask about a place, flight, or hotel..."
              rows={1}
              disabled={streaming}
              aria-label="Message TripWeaver"
            />
            <Button size="icon" type="submit" disabled={!draft.trim() || streaming} title="Send message" aria-label="Send message">
              {streaming ? <LoaderCircle className="spin" size={18} /> : <Send size={18} />}
            </Button>
          </form>
          <div className="composer-footnote">
            <span><ShieldCheck size={13} /> Secure session</span>
            <span>Bookings are simulated</span>
          </div>
        </section>

        <TripDeck
          className={mobilePanelOpen ? "is-mobile-open" : ""}
          destination={destination}
          origin={origin}
          destinationCode={destinationCode}
          sessionId={sessionId}
          activeTab={activeTab}
          onTabChange={setActiveTab}
          hotels={hotels}
          flights={flights}
          booking={booking}
          streaming={streaming}
          activity={activity}
          onPrepareBooking={prepareBooking}
          onClose={() => setMobilePanelOpen(false)}
        />
      </main>

      <Button
        className="mobile-trip-toggle"
        onClick={() => setMobilePanelOpen(true)}
        title="Open trip canvas"
      >
        <PanelRightOpen size={17} /> Trip canvas
        {(hotels.length > 0 || flights.length > 0) && (
          <span>{hotels.length + flights.length}</span>
        )}
      </Button>
      {mobilePanelOpen && <button className="mobile-scrim" aria-label="Close trip canvas" onClick={() => setMobilePanelOpen(false)} />}
    </div>
  );
}

function ActivityTimeline({
  activity,
  tools,
  streaming,
}: {
  activity?: ActivityState;
  tools: ToolActivity[];
  streaming: boolean;
}) {
  const latestTool = tools.at(-1);
  return (
    <div className="activity-board">
      <div className="activity-copy">
        <span className={cn("live-signal", !streaming && "is-idle")}><Radio size={13} /></span>
        <div>
          <span>Live orchestration</span>
          <strong>{activity ? STATUS_COPY[activity] : "Ready for a new route"}</strong>
        </div>
        {latestTool && (
          <span className={cn("tool-chip", `is-${latestTool.status.toLowerCase()}`)}>
            {latestTool.status === "SUCCEEDED" ? <Check size={12} /> : <LoaderCircle size={12} />}
            {latestTool.tool.replaceAll("_", " ")}
          </span>
        )}
      </div>
      <div className="timeline-grid">
        {STAGES.map((stage) => (
          <div key={stage.state} className={cn("timeline-stage", activity === stage.state && "is-active")}>
            <i /><span>{stage.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

type TripDeckProps = {
  className?: string;
  destination: typeof DEFAULT_DESTINATION;
  origin: string;
  destinationCode: string;
  sessionId?: string;
  activeTab: string;
  onTabChange: (tab: string) => void;
  hotels: HotelResult[];
  flights: FlightResult[];
  booking?: BookingConfirmation;
  streaming: boolean;
  activity?: ActivityState;
  onPrepareBooking: (type: "hotel" | "flight", offerId?: string) => void;
  onClose: () => void;
};

function TripDeck({
  className,
  destination,
  origin,
  destinationCode,
  sessionId,
  activeTab,
  onTabChange,
  hotels,
  flights,
  booking,
  streaming,
  activity,
  onPrepareBooking,
  onClose,
}: TripDeckProps) {
  return (
    <aside className={cn("trip-deck", className)} aria-label="Live trip canvas">
      <button className="mobile-close" onClick={onClose} title="Close trip canvas" aria-label="Close trip canvas"><X size={18} /></button>
      <section className="destination-canvas">
        <Image key={destination.image} src={destination.image} alt={`${destination.city} destination view`} fill priority sizes="(max-width: 900px) 100vw, 50vw" />
        <div className="image-shade" />
        <svg className="route-line" viewBox="0 0 600 220" preserveAspectRatio="none" aria-hidden="true">
          <path d="M90 165 C210 22 390 25 520 145" />
          <circle cx="90" cy="165" r="5" />
          <circle cx="520" cy="145" r="5" />
        </svg>
        <div className="canvas-topline">
          <span><MapPin size={13} /> Destination canvas</span>
          <span>{destination.timezone}</span>
        </div>
        <div className="destination-copy">
          <span>{destination.country}</span>
          <h2>{destination.city}</h2>
        </div>
        <div className="route-board">
          <div><span>From</span><strong>{origin}</strong></div>
          <ArrowRight size={20} />
          <div><span>To</span><strong>{destinationCode}</strong></div>
          <div className="route-status"><i /> {streaming ? "Planning" : "Ready"}</div>
        </div>
      </section>

      <section className="results-workspace">
        <div className="workspace-heading">
          <div>
            <span className="eyebrow">Live itinerary</span>
            <h2>Your trip, assembled</h2>
          </div>
          <span className="session-code">{sessionId ? sessionId.slice(0, 8) : "NEW TRIP"}</span>
        </div>

        <Tabs className="tabs-root" value={activeTab} onValueChange={onTabChange}>
          <TabsList>
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="flights">Flights {flights.length ? `(${flights.length})` : ""}</TabsTrigger>
            <TabsTrigger value="hotels">Stays {hotels.length ? `(${hotels.length})` : ""}</TabsTrigger>
          </TabsList>

          <TabsContent value="overview" className="tab-scroll">
            {booking && <BookingCard confirmation={booking} />}
            <JourneyOverview
              destination={destination.city}
              flights={flights}
              hotels={hotels}
              activity={activity}
              streaming={streaming}
            />
          </TabsContent>
          <TabsContent value="flights" className="tab-scroll result-stack">
            {flights.length ? flights.map((flight, index) => (
              <FlightCard key={flight.id || index} flight={flight} onPrepareBooking={onPrepareBooking} />
            )) : <EmptyResults type="flight" streaming={streaming} />}
          </TabsContent>
          <TabsContent value="hotels" className="tab-scroll result-stack">
            {hotels.length ? hotels.map((hotel, index) => (
              <HotelCard key={hotel.id || hotel.hotel_id || index} hotel={hotel} onPrepareBooking={onPrepareBooking} />
            )) : <EmptyResults type="hotel" streaming={streaming} />}
          </TabsContent>
        </Tabs>
      </section>
    </aside>
  );
}

function JourneyOverview({
  destination,
  flights,
  hotels,
  activity,
  streaming,
}: {
  destination: string;
  flights: FlightResult[];
  hotels: HotelResult[];
  activity?: ActivityState;
  streaming: boolean;
}) {
  const steps = [
    { icon: MapPin, label: "Destination", value: destination },
    { icon: Plane, label: "Flight options", value: flights.length ? `${flights.length} live matches` : "Not searched yet" },
    { icon: Hotel, label: "Stay options", value: hotels.length ? `${hotels.length} live matches` : "Not searched yet" },
  ];
  return (
    <div className="overview-panel">
      <div className="overview-status">
        <div className={cn("status-icon", streaming && "is-working")}>
          {streaming ? <LoaderCircle className="spin" size={20} /> : <Sparkles size={20} />}
        </div>
        <div>
          <span>Planner status</span>
          <strong>{activity ? STATUS_COPY[activity] : flights.length || hotels.length ? "Your options are ready" : "Tell me the shape of your trip"}</strong>
        </div>
      </div>
      <div className="journey-steps">
        {steps.map((step, index) => (
          <div className="journey-step" key={step.label}>
            <span className="step-index">0{index + 1}</span>
            <step.icon size={17} />
            <div><span>{step.label}</span><strong>{step.value}</strong></div>
          </div>
        ))}
      </div>
      <div className="trust-row">
        <span><Radio size={13} /> Amadeus test data</span>
        <span><ShieldCheck size={13} /> No payment collected</span>
      </div>
    </div>
  );
}

function FlightCard({ flight, onPrepareBooking }: { flight: FlightResult; onPrepareBooking: TripDeckProps["onPrepareBooking"] }) {
  return (
    <article className="result-card flight-card">
      <div className="card-topline">
        <span className="provider-mark"><Plane size={14} /> {flight.carrier || "Airline"} {flight.flight_number}</span>
        <span className="availability">{flight.seats ? `${flight.seats} seats` : "Live offer"}</span>
      </div>
      <div className="flight-route">
        <div><strong>{flight.origin || "---"}</strong><span>{formatTime(flight.departure_at)}</span></div>
        <div className="flight-path"><span>{formatDuration(flight.duration)}</span><i /><small>{flight.stops ? `${flight.stops} stop` : "Nonstop"}</small></div>
        <div><strong>{flight.destination || "---"}</strong><span>{formatTime(flight.arrival_at)}</span></div>
      </div>
      <div className="card-footer">
        <div><span>Per traveller</span><strong>{formatMoney(flight.price, flight.currency)}</strong></div>
        <Button variant="secondary" size="sm" onClick={() => onPrepareBooking("flight", flight.id)} disabled={!flight.id}>
          Prepare booking <ChevronRight size={14} />
        </Button>
      </div>
    </article>
  );
}

function HotelCard({ hotel, onPrepareBooking }: { hotel: HotelResult; onPrepareBooking: TripDeckProps["onPrepareBooking"] }) {
  return (
    <article className="result-card hotel-card">
      <div className="card-topline">
        <span className="provider-mark"><Hotel size={14} /> {hotel.city_code || "Stay"}</span>
        <span className="availability"><i /> Available</span>
      </div>
      <h3>{hotel.name}</h3>
      <p>{hotel.address || "Live property offer from the Amadeus test environment"}</p>
      <div className="hotel-facts">
        <span><BedDouble size={14} /> {(hotel.room || hotel.bed_type || "Room").replaceAll("_", " ")}</span>
        <span><CalendarDays size={14} /> {hotel.check_in || "Flexible dates"}</span>
        {hotel.rating && <span><Sparkles size={14} /> {hotel.rating} star</span>}
      </div>
      <div className="card-footer">
        <div><span>Total stay</span><strong>{formatMoney(hotel.price, hotel.currency)}</strong></div>
        <Button variant="secondary" size="sm" onClick={() => onPrepareBooking("hotel", hotel.id)} disabled={!hotel.id}>
          Prepare booking <ChevronRight size={14} />
        </Button>
      </div>
    </article>
  );
}

function BookingCard({ confirmation }: { confirmation: BookingConfirmation }) {
  return (
    <article className="booking-card">
      <span className="booking-icon"><CheckCircle2 size={22} /></span>
      <div>
        <span className="eyebrow">Simulated confirmation</span>
        <h3>{confirmation.type === "flight" ? "Flight held" : "Stay held"} for {confirmation.traveller_name || "traveller"}</h3>
        <div className="confirmation-code"><TicketCheck size={15} /> {confirmation.confirmation_number || "Confirmation ready"}</div>
      </div>
      <span className="simulation-label">No payment</span>
    </article>
  );
}

function EmptyResults({ type, streaming }: { type: "flight" | "hotel"; streaming: boolean }) {
  const Icon = type === "flight" ? Plane : Hotel;
  return (
    <div className="empty-results">
      <span>{streaming ? <LoaderCircle className="spin" size={21} /> : <Icon size={21} />}</span>
      <h3>{streaming ? `Searching ${type}s` : `No ${type} search yet`}</h3>
      <p>{streaming ? "Live options will arrive here as the specialist agent finds them." : `Ask TripWeaver for ${type} options and this canvas will fill with live cards.`}</p>
    </div>
  );
}
