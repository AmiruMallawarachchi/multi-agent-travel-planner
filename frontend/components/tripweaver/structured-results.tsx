"use client"

import {
  Banknote,
  BedDouble,
  CalendarDays,
  CloudSun,
  Clock3,
  ExternalLink,
  Map as MapIcon,
  MapPinned,
  Plane,
  Star,
  UsersRound,
} from "lucide-react"

import type { StructuredResult } from "@/features/tripweaver/types"

type DataRecord = Record<string, unknown>

function record(value: unknown): DataRecord | null {
  return value !== null && typeof value === "object" && !Array.isArray(value)
    ? (value as DataRecord)
    : null
}

function records(value: unknown) {
  return Array.isArray(value)
    ? value.map(record).filter((item): item is DataRecord => item !== null)
    : []
}

function text(value: unknown, fallback = "Not provided") {
  return typeof value === "string" && value.trim() ? value : fallback
}

function displayNumber(value: unknown, fallback = "-") {
  return typeof value === "number" && Number.isFinite(value) ? value.toLocaleString() : fallback
}

function safeHttpUrl(value: unknown) {
  if (typeof value !== "string") return null
  try {
    const url = new URL(value)
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null
  } catch {
    return null
  }
}

function placeMapUrl(place: DataRecord) {
  const coordinates = record(place.coordinates)
  const latitude = coordinates?.latitude
  const longitude = coordinates?.longitude
  if (typeof latitude === "number" && typeof longitude === "number") {
    return `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`
  }
  const address = text(place.address, text(place.name, ""))
  return address
    ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`
    : null
}

function ResultHeading({ result }: { result: StructuredResult }) {
  const details = {
    flight: { icon: Plane, label: "Flight options" },
    hotel: { icon: BedDouble, label: "Hotel options" },
    itinerary: { icon: MapIcon, label: "Structured itinerary" },
    weather: { icon: CloudSun, label: "Weather outlook" },
    currency: { icon: Banknote, label: "Currency result" },
    location: { icon: MapPinned, label: "Places found" },
  }[result.type]
  const Icon = details.icon

  return (
    <div className="flex items-center gap-2 text-xs font-semibold">
      <Icon className="size-3.5 text-[#2f7d72]" aria-hidden="true" />
      {details.label}
    </div>
  )
}

function FlightPreview({ data }: { data: unknown }) {
  const options = records(data).slice(0, 3)
  return (
    <div className="divide-y divide-border/60">
      {options.map((option, index) => {
        const departure = record(option.departure)
        const arrival = record(option.arrival)
        return (
          <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 py-2" key={`${text(option.flight_number)}-${index}`}>
            <div className="min-w-0">
              <p className="truncate text-xs font-medium">
                {text(option.airline)} {text(option.flight_number, "")}
              </p>
              <p className="truncate text-[11px] text-muted-foreground">
                {text(departure?.airport_code)} {text(departure?.time, "")} to {text(arrival?.airport_code)} {text(arrival?.time, "")}
              </p>
            </div>
            <p className="text-right text-xs font-semibold">
              {text(option.currency, "")} {displayNumber(option.price)}
            </p>
          </div>
        )
      })}
      {options.length === 0 ? <p className="py-2 text-xs text-muted-foreground">No options returned.</p> : null}
    </div>
  )
}

function HotelPreview({ data }: { data: unknown }) {
  const options = records(data).slice(0, 3)
  return (
    <div className="divide-y divide-border/60">
      {options.map((option, index) => (
        <div className="grid grid-cols-[minmax(0,1fr)_auto] gap-3 py-2" key={`${text(option.name)}-${index}`}>
          <div className="min-w-0">
            <p className="truncate text-xs font-medium">{text(option.name)}</p>
            <p className="flex items-center gap-1 text-[11px] text-muted-foreground">
              <Star className="size-3" aria-hidden="true" />
              {displayNumber(option.overall_rating)}
              <span>{displayNumber(option.review_count, "0")} reviews</span>
            </p>
          </div>
          <p className="text-right text-xs font-semibold">
            {text(option.currency, "")} {displayNumber(option.price_per_night)}
            <span className="block text-[10px] font-normal text-muted-foreground">per night</span>
          </p>
        </div>
      ))}
      {options.length === 0 ? <p className="py-2 text-xs text-muted-foreground">No options returned.</p> : null}
    </div>
  )
}

function ItineraryPreview({ data }: { data: unknown }) {
  const itinerary = record(data)
  return (
    <dl className="grid grid-cols-2 gap-x-5 gap-y-2 py-2 text-xs sm:grid-cols-4">
      <div>
        <dt className="text-[10px] uppercase text-muted-foreground">Destination</dt>
        <dd className="truncate font-medium">{text(itinerary?.destination)}</dd>
      </div>
      <div>
        <dt className="text-[10px] uppercase text-muted-foreground">Duration</dt>
        <dd className="font-medium">{displayNumber(itinerary?.duration_days)} days</dd>
      </div>
      <div>
        <dt className="text-[10px] uppercase text-muted-foreground">Travellers</dt>
        <dd className="font-medium">{displayNumber(itinerary?.travelers)}</dd>
      </div>
      <div>
        <dt className="text-[10px] uppercase text-muted-foreground">Pace</dt>
        <dd className="capitalize font-medium">{text(itinerary?.pace)}</dd>
      </div>
    </dl>
  )
}

function WeatherPreview({ data }: { data: unknown }) {
  const weather = record(data)
  const location = record(weather?.location)
  const current = record(weather?.current)
  const units = record(current?.units)
  const daily = records(weather?.daily).slice(0, 3)

  return (
    <div className="py-2">
      <div className="flex items-end justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-xs font-medium">
            {text(location?.name)}{location?.country ? `, ${text(location.country)}` : ""}
          </p>
          <p className="text-[11px] text-muted-foreground">{text(current?.weather, "Forecast")}</p>
        </div>
        {current?.temperature !== undefined ? (
          <p className="text-lg font-semibold">
            {displayNumber(current.temperature)}{text(units?.temperature, "")}
          </p>
        ) : null}
      </div>
      {daily.length ? (
        <div className="glass-divider mt-2 grid grid-cols-3 divide-x divide-border/60 border-t pt-2 text-center text-xs">
          {daily.map((day) => (
            <div className="min-w-0 px-2" key={text(day.date)}>
              <p className="truncate font-medium">{text(day.date)}</p>
              <p className="truncate text-muted-foreground">{text(day.weather)}</p>
              <p>{displayNumber(day.temperature_max)} / {displayNumber(day.temperature_min)}</p>
            </div>
          ))}
        </div>
      ) : null}
    </div>
  )
}

function CurrencyPreview({ data }: { data: unknown }) {
  if (Array.isArray(data)) {
    return <p className="py-2 text-xs">{data.length.toLocaleString()} supported currencies returned.</p>
  }
  const result = record(data)
  return (
    <div className="flex items-end justify-between gap-4 py-2">
      <div>
        <p className="text-[10px] uppercase text-muted-foreground">Reference rate</p>
        <p className="text-xs font-medium">
          1 {text(result?.from_currency)} = {displayNumber(result?.rate)} {text(result?.to_currency)}
        </p>
        <p className="text-[11px] text-muted-foreground">As of {text(result?.as_of)}</p>
      </div>
      {result?.converted_amount !== undefined ? (
        <p className="text-right text-lg font-semibold">
          {displayNumber(result.converted_amount)} {text(result.to_currency, "")}
        </p>
      ) : null}
    </div>
  )
}

function LocationPreview({ data }: { data: unknown }) {
  const places = records(data).slice(0, 3)
  return (
    <div className="space-y-2 py-2">
      {places.map((place, index) => {
        const mapUrl = placeMapUrl(place)
        return (
          <div
            className="glass-control grid grid-cols-[28px_minmax(0,1fr)_auto] gap-2.5 rounded-lg p-2.5"
            key={`${text(place.name)}-${index}`}
          >
            <span className="flex size-7 items-center justify-center rounded-md bg-primary/10 text-xs font-semibold text-primary">
              {index + 1}
            </span>
            <div className="min-w-0">
              <p className="truncate text-xs font-semibold">{text(place.name)}</p>
              <p className="truncate text-[11px] text-muted-foreground">
                {text(place.category, text(place.region, "Location"))} - {text(place.address, text(place.country, ""))}
              </p>
              <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-[10px] text-muted-foreground">
                {place.rating !== undefined ? (
                  <span className="flex items-center gap-1">
                    <Star className="size-3 fill-current text-amber-500" aria-hidden="true" />
                    {displayNumber(place.rating)}
                    {place.review_count !== undefined
                      ? ` (${displayNumber(place.review_count)} reviews)`
                      : ""}
                  </span>
                ) : null}
                {place.open_state ? (
                  <span className="font-medium text-emerald-700 dark:text-emerald-300">
                    {text(place.open_state)}
                  </span>
                ) : null}
              </div>
            </div>
            {mapUrl ? (
              <a
                href={mapUrl}
                target="_blank"
                rel="noreferrer"
                className="glass-interactive flex size-8 items-center justify-center rounded-md text-muted-foreground hover:text-foreground"
                aria-label={`Open ${text(place.name)} in maps`}
              >
                <ExternalLink className="size-3.5" aria-hidden="true" />
              </a>
            ) : null}
          </div>
        )
      })}
      {places.length === 0 ? <p className="py-2 text-xs text-muted-foreground">No places returned.</p> : null}
    </div>
  )
}

export function StructuredResultPreview({ result }: { result: StructuredResult }) {
  return (
    <section className="glass-divider border-t pt-3" aria-label={`${result.type} result`}>
      <ResultHeading result={result} />
      {result.type === "flight" ? <FlightPreview data={result.data} /> : null}
      {result.type === "hotel" ? <HotelPreview data={result.data} /> : null}
      {result.type === "itinerary" ? <ItineraryPreview data={result.data} /> : null}
      {result.type === "weather" ? <WeatherPreview data={result.data} /> : null}
      {result.type === "currency" ? <CurrencyPreview data={result.data} /> : null}
      {result.type === "location" ? <LocationPreview data={result.data} /> : null}
    </section>
  )
}

export function itineraryDestination(data: unknown) {
  return text(record(data)?.destination, "Trip")
}

export function ItineraryDetails({ data }: { data: unknown }) {
  const itinerary = record(data)
  const days = records(itinerary?.days)

  return (
    <div className="space-y-5">
      <dl className="glass-divider grid grid-cols-2 gap-3 border-y py-3 text-sm sm:grid-cols-4">
        <div>
          <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <CalendarDays className="size-3.5" aria-hidden="true" /> Dates
          </dt>
          <dd className="mt-1 font-medium">{text(itinerary?.start_date)} to {text(itinerary?.end_date)}</dd>
        </div>
        <div>
          <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <Clock3 className="size-3.5" aria-hidden="true" /> Duration
          </dt>
          <dd className="mt-1 font-medium">{displayNumber(itinerary?.duration_days)} days</dd>
        </div>
        <div>
          <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <UsersRound className="size-3.5" aria-hidden="true" /> Travellers
          </dt>
          <dd className="mt-1 font-medium">{displayNumber(itinerary?.travelers)}</dd>
        </div>
        <div>
          <dt className="text-xs text-muted-foreground">Pace</dt>
          <dd className="mt-1 capitalize font-medium">{text(itinerary?.pace)}</dd>
        </div>
      </dl>

      <div className="divide-y divide-border/60">
        {days.map((day, index) => (
          <section className="py-4 first:pt-0" key={text(day.date, String(index))}>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h3 className="text-sm font-semibold">{text(day.title, `Day ${index + 1}`)}</h3>
              <time className="text-xs text-muted-foreground">{text(day.date, "")}</time>
            </div>
            <ol className="mt-3 space-y-3 border-l pl-4">
              {records(day.items).map((item, itemIndex) => (
                <li className="relative grid grid-cols-[minmax(0,1fr)_auto] gap-2" key={`${text(item.name)}-${itemIndex}`}>
                  <span className="absolute -left-[21px] top-1.5 size-2.5 rounded-full border-2 border-background bg-primary" aria-hidden="true" />
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <p className="text-sm font-medium">{text(item.name)}</p>
                      {item.category ? (
                        <span className="rounded-md bg-primary/10 px-1.5 py-0.5 text-[10px] capitalize text-primary">
                          {text(item.category)}
                        </span>
                      ) : null}
                    </div>
                    <p className="text-xs capitalize text-muted-foreground">
                      {text(item.time_slot, "Flexible time")} - {displayNumber(item.duration_minutes)} minutes
                    </p>
                    {item.address ? (
                      <p className="mt-1 truncate text-xs text-muted-foreground">{text(item.address)}</p>
                    ) : null}
                  </div>
                  {safeHttpUrl(item.source_url) ? (
                    <a
                      href={safeHttpUrl(item.source_url) ?? undefined}
                      target="_blank"
                      rel="noreferrer"
                      className="glass-interactive flex size-8 items-center justify-center rounded-md text-muted-foreground hover:text-foreground"
                      aria-label={`Open details for ${text(item.name)}`}
                    >
                      <ExternalLink className="size-3.5" aria-hidden="true" />
                    </a>
                  ) : null}
                </li>
              ))}
            </ol>
          </section>
        ))}
      </div>

      {itinerary?.disclaimer ? (
        <p className="glass-divider border-t pt-3 text-xs text-muted-foreground">{text(itinerary.disclaimer)}</p>
      ) : null}
    </div>
  )
}
