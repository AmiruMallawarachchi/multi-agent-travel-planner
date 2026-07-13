"use client"

import {
  Banknote,
  BedDouble,
  Check,
  Circle,
  CircleX,
  CloudSun,
  LoaderCircle,
  MapPinned,
  Map as MapIcon,
  Plane,
  Route,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import type {
  RuntimeState,
  ServiceKey,
  ServiceState,
  TripContext,
  ToolStatus,
} from "@/features/tripweaver/types"

const SERVICE_ICONS: Record<ServiceKey, React.ComponentType<{ className?: string }>> = {
  flight: Plane,
  hotel: BedDouble,
  itinerary: MapIcon,
  weather: CloudSun,
  currency: Banknote,
  location: MapPinned,
}

const STATUS_LABELS: Record<ToolStatus, string> = {
  idle: "Idle",
  running: "Running",
  completed: "Completed",
  failed: "Failed",
  offline: "Offline",
  unavailable: "Unavailable",
}

function StatusMark({ status }: { status: ToolStatus }) {
  if (status === "running") {
    return <LoaderCircle className="size-3.5 animate-spin text-sky-600" aria-hidden="true" />
  }
  if (status === "completed") {
    return <Check className="size-3.5 text-emerald-700" aria-hidden="true" />
  }
  if (status === "failed" || status === "offline") {
    return <CircleX className="size-3.5 text-rose-600" aria-hidden="true" />
  }
  return <Circle className="size-2.5 text-muted-foreground" aria-hidden="true" />
}

function ServiceRow({ service }: { service: ServiceState }) {
  const Icon = SERVICE_ICONS[service.key]
  return (
    <div className="grid grid-cols-[22px_minmax(0,1fr)_auto] items-center gap-2 py-1.5">
      <Icon className="size-[17px] text-foreground" aria-hidden="true" />
      <span className="truncate text-sm">{service.label}</span>
      <span className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <StatusMark status={service.status} />
        {STATUS_LABELS[service.status]}
      </span>
    </div>
  )
}

function ContextValue({ children }: { children: React.ReactNode }) {
  return <dd className="min-w-0 text-sm font-medium text-foreground">{children || "Not provided"}</dd>
}

interface StatusPanelProps {
  runtime: RuntimeState
  tripContext: TripContext
  onQuickAction: (prompt: string) => void
  onUnavailableAction: (feature: string) => void
  className?: string
}

export function StatusPanel({
  runtime,
  tripContext,
  onQuickAction,
  onUnavailableAction,
  className,
}: StatusPanelProps) {
  return (
    <aside className={className} aria-label="Trip status">
      <section className="p-4" aria-labelledby="active-tools-heading">
        <div className="mb-3 flex items-start justify-between gap-2">
          <div>
            <h2 id="active-tools-heading" className="text-xs font-semibold uppercase">
              Active tools &amp; status
            </h2>
            <p className="mt-1 truncate text-xs text-muted-foreground">{runtime.activeAgent}</p>
          </div>
          <span className="mt-0.5 size-2 rounded-full bg-[#2f7d72]" aria-hidden="true" />
        </div>
        <div className="border-t pt-2">
          {Object.values(runtime.services).map((service) => (
            <ServiceRow service={service} key={service.key} />
          ))}
        </div>
      </section>

      <Separator />

      <section className="p-4" aria-labelledby="trip-context-heading">
        <h2 id="trip-context-heading" className="mb-4 text-xs font-semibold uppercase">
          Trip context
        </h2>
        <dl className="grid grid-cols-[82px_minmax(0,1fr)] gap-x-3 gap-y-3 text-muted-foreground">
          <dt className="text-xs">Destination</dt>
          <ContextValue>{tripContext.destination}</ContextValue>
          <dt className="text-xs">Dates</dt>
          <ContextValue>{tripContext.dates}</ContextValue>
          <dt className="text-xs">Travellers</dt>
          <ContextValue>{tripContext.travelers}</ContextValue>
          <dt className="text-xs">Budget</dt>
          <ContextValue>{tripContext.budget}</ContextValue>
          <dt className="text-xs">Preferences</dt>
          <ContextValue>{tripContext.preferences.join(", ")}</ContextValue>
        </dl>
      </section>

      <Separator />

      <section className="p-4" aria-labelledby="quick-actions-heading">
        <h2 id="quick-actions-heading" className="mb-3 text-xs font-semibold uppercase">
          Quick actions
        </h2>
        <div className="space-y-2">
          <Button
            variant="outline"
            className="h-9 w-full justify-start bg-background"
            onClick={() => onQuickAction("Help me search for flights.")}
            aria-label="Search flights"
          >
            <Plane aria-hidden="true" />
            Search flights
          </Button>
          <Button
            variant="outline"
            className="h-9 w-full justify-start bg-background"
            onClick={() => onQuickAction("Help me search for hotels.")}
            aria-label="Search hotels"
          >
            <BedDouble aria-hidden="true" />
            Search hotels
          </Button>
          <Button
            variant="outline"
            className="h-9 w-full justify-start bg-background text-muted-foreground"
            onClick={() => onUnavailableAction("Itinerary MCP")}
            aria-label="Plan itinerary"
          >
            <Route aria-hidden="true" />
            Plan itinerary
            <span className="ml-auto text-[10px] uppercase">Soon</span>
          </Button>
          <Button
            variant="outline"
            className="h-9 w-full justify-start bg-background text-muted-foreground"
            onClick={() => onUnavailableAction("Weather MCP")}
            aria-label="Check weather"
          >
            <CloudSun aria-hidden="true" />
            Check weather
            <span className="ml-auto text-[10px] uppercase">Soon</span>
          </Button>
          <Button
            variant="outline"
            className="h-9 w-full justify-start bg-background text-muted-foreground"
            onClick={() => onUnavailableAction("Currency MCP")}
            aria-label="Convert currency"
          >
            <Banknote aria-hidden="true" />
            Currency converter
            <span className="ml-auto text-[10px] uppercase">Soon</span>
          </Button>
        </div>
      </section>
    </aside>
  )
}
