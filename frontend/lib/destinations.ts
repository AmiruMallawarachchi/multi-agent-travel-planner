export type Destination = {
  city: string;
  country: string;
  code: string;
  image: string;
  timezone: string;
};

const DESTINATIONS: Array<Destination & { terms: string[] }> = [
  {
    city: "Paris",
    country: "France",
    code: "PAR",
    image: "/images/paris.png",
    timezone: "UTC +2",
    terms: ["paris", "par", "france"],
  },
  {
    city: "Kyoto",
    country: "Japan",
    code: "KIX",
    image: "/images/kyoto.png",
    timezone: "UTC +9",
    terms: ["kyoto", "tokyo", "japan", "kix", "nrt", "hnd"],
  },
  {
    city: "London",
    country: "United Kingdom",
    code: "LHR",
    image: "/images/london.png",
    timezone: "UTC +1",
    terms: ["london", "lhr", "lgw", "united kingdom", "uk"],
  },
];

export const DEFAULT_DESTINATION: Destination = {
  city: "Open horizon",
  country: "Your next journey",
  code: "ANY",
  image: "/images/lounge.png",
  timezone: "Local time",
};

export function detectDestination(
  text: string,
  resultCode?: string,
): Destination {
  const haystack = `${text} ${resultCode ?? ""}`.toLowerCase();
  return (
    DESTINATIONS.find((destination) =>
      destination.terms.some((term) => haystack.includes(term)),
    ) ?? DEFAULT_DESTINATION
  );
}

export function formatDuration(value?: string): string {
  if (!value) return "Flexible";
  return value.replace("PT", "").replace("H", "h ").replace("M", "m").trim();
}

export function formatMoney(value?: string, currency = "USD"): string {
  if (!value) return "Price on request";
  const number = Number(value);
  if (Number.isNaN(number)) return `${currency} ${value}`;
  return new Intl.NumberFormat("en", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(number);
}

export function formatTime(value?: string): string {
  if (!value) return "--:--";
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "--:--"
    : new Intl.DateTimeFormat("en", { hour: "2-digit", minute: "2-digit" }).format(date);
}
