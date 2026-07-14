"use client"

import { CircleHelp, KeyRound, LifeBuoy, ShieldCheck } from "lucide-react"

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog"

interface HelpCenterDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const HELP_ITEMS = [
  {
    title: "Travel results",
    body: "Flight, hotel, weather, currency, itinerary, and place tools are shown in the right status panel while TripWeaver works.",
    Icon: LifeBuoy,
  },
  {
    title: "Account history",
    body: "Signed-in travellers get account-backed chat history. Guests keep history only in this browser.",
    Icon: KeyRound,
  },
  {
    title: "Safety",
    body: "Bookings are simulated. Always verify prices, availability, visa rules, and provider details before purchase.",
    Icon: ShieldCheck,
  },
]

export function HelpCenterDialog({ open, onOpenChange }: HelpCenterDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg rounded-[20px]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CircleHelp className="size-5" aria-hidden="true" />
            Help centre
          </DialogTitle>
          <DialogDescription>
            Practical support for using TripWeaver while the product is in active development.
          </DialogDescription>
        </DialogHeader>

        <div className="glass-control divide-y divide-border/60 overflow-hidden rounded-2xl">
          {HELP_ITEMS.map(({ title, body, Icon }) => (
            <section key={title} className="grid grid-cols-[32px_minmax(0,1fr)] gap-3 p-3">
              <span className="glass-control flex size-8 items-center justify-center rounded-xl">
                <Icon className="size-4 text-muted-foreground" aria-hidden="true" />
              </span>
              <div>
                <h3 className="text-sm font-medium">{title}</h3>
                <p className="mt-1 text-sm leading-6 text-muted-foreground">{body}</p>
              </div>
            </section>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  )
}

