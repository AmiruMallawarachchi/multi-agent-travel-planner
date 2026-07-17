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
} from "lucide-react"

import { Separator } from "@/components/ui/separator"
import type {
  RuntimeState,
  ServiceKey,
  ServiceState,
  TripContext,
  ToolStatus,
} from "@/features/tripweaver/types"
import { cn } from "@/lib/utils"

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
    <div className="grid min-h-11 grid-cols-[36px_minmax(0,1fr)_auto] items-center gap-2 py-1">
      <span className="glass-control flex size-8 items-center justify-center rounded-xl">
        <Icon className="size-4 text-foreground" aria-hidden="true" />
      </span>
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
  className?: string
}

export function StatusPanel({ runtime, tripContext, className }: StatusPanelProps) {
  return (
    <aside
      className={cn("h-full min-h-0 overflow-y-auto overscroll-contain", className)}
      aria-label="Trip status"
    >
      <section className="p-3.5" aria-labelledby="active-tools-heading">
        <div className="mb-3 flex items-start justify-between gap-2">
          <div>
            <h2 id="active-tools-heading" className="text-xs font-semibold uppercase">
              Active tools &amp; status
            </h2>
            <p className="mt-1 truncate text-xs text-muted-foreground">{runtime.activeAgent}</p>
          </div>
          <span className="mt-0.5 size-2.5 rounded-full bg-emerald-500 shadow-[0_0_0_4px_rgba(16,185,129,0.12)]" aria-hidden="true" />
        </div>
        <div className="glass-divider border-t pt-2">
          {Object.values(runtime.services).map((service) => (
            <ServiceRow service={service} key={service.key} />
          ))}
        </div>
      </section>

      <Separator />

      <section className="p-3.5" aria-labelledby="trip-context-heading">
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
    </aside>
  )
}
