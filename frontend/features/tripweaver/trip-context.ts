import type { TripContext } from "./types"

const PREFERENCE_LABELS: Record<string, string> = {
  adventure: "Adventure",
  beaches: "Beaches",
  culture: "Culture",
  family: "Family",
  food: "Food",
  luxury: "Luxury",
  museums: "Museums",
  nature: "Nature",
  nightlife: "Nightlife",
  shopping: "Shopping",
  sightseeing: "Sightseeing",
}

function titleCase(value: string) {
  return value
    .trim()
    .replace(/\s+/g, " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase())
}

function findDestination(message: string) {
  const flightMatch = message.match(
    /\bfrom\s+[a-z][a-z .'-]*?\s+to\s+([a-z][a-z .'-]*?)(?=\s+(?:on|for|in|with|departing|leaving)\b|[,.]|$)/i,
  )
  if (flightMatch) {
    return titleCase(flightMatch[1])
  }

  const tripMatch = message.match(
    /\b(?:trip\s+to|travel\s+to|go\s+to|visit|hotels?\s+in|stay\s+in)\s+([a-z][a-z .'-]*?)(?=\s+(?:for|on|in|with|including|during)\b|[,.]|$)/i,
  )
  return tripMatch ? titleCase(tripMatch[1]) : null
}

function findDates(message: string) {
  const isoDates = message.match(/\b\d{4}-\d{2}-\d{2}(?:\s+(?:to|through|-)\s+\d{4}-\d{2}-\d{2})?\b/i)
  if (isoDates) {
    return isoDates[0]
  }

  const monthRange = message.match(
    /\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)(?:\s+\d{1,2}(?:\s*(?:-|to)\s*\d{1,2})?)?(?:,?\s+\d{4})?\b/i,
  )
  return monthRange?.[0] ?? null
}

function findTravelers(message: string) {
  const match = message.match(/\b(\d+)\s+(adult|adults|person|people|traveller|travellers|traveler|travelers)\b/i)
  return match ? `${match[1]} ${match[2].toLocaleLowerCase()}` : null
}

function findBudget(message: string) {
  const match = message.match(
    /\bbudget(?:\s+of)?\s*(?:is\s*)?((?:USD\s*)?\$\s?[\d,]+|(?:USD\s*)?[\d,]+\s*(?:USD|dollars?))/i,
  )
  return match?.[1].replace(/\s+/g, " ") ?? null
}

function findPreferences(message: string) {
  const normalized = message.toLocaleLowerCase()
  return Object.entries(PREFERENCE_LABELS)
    .map(([keyword, label]) => ({ index: normalized.search(new RegExp(`\\b${keyword}\\b`, "i")), label }))
    .filter(({ index }) => index >= 0)
    .toSorted((left, right) => left.index - right.index)
    .map(({ label }) => label)
}

export function extractTripContext(message: string, previous?: TripContext): TripContext {
  const preferences = findPreferences(message)

  return {
    destination: findDestination(message) ?? previous?.destination ?? null,
    dates: findDates(message) ?? previous?.dates ?? null,
    travelers: findTravelers(message) ?? previous?.travelers ?? null,
    budget: findBudget(message) ?? previous?.budget ?? null,
    preferences:
      preferences.length > 0
        ? Array.from(new Set([...(previous?.preferences ?? []), ...preferences]))
        : (previous?.preferences ?? []),
  }
}
