export type FestiveEvent = {
  name: string;
  triggerMessage: string;
  windowDays: number;
  monthDay: { month: number; day: number };
};

export const FESTIVE_CALENDAR: FestiveEvent[] = [
  {
    name: "Diwali",
    triggerMessage: "Ready for Diwali?",
    windowDays: 30,
    monthDay: { month: 9, day: 20 },
  },
  {
    name: "Durga Puja",
    triggerMessage: "Puja season is here.",
    windowDays: 21,
    monthDay: { month: 9, day: 2 },
  },
  {
    name: "Eid",
    triggerMessage: "Celebrate in style this Eid.",
    windowDays: 21,
    monthDay: { month: 3, day: 10 },
  },
];

export function getActiveFestiveEvent(today: Date = new Date()): FestiveEvent | null {
  for (const event of FESTIVE_CALENDAR) {
    const eventDate = new Date(
      today.getFullYear(),
      event.monthDay.month,
      event.monthDay.day,
      0,
      0,
      0,
      0,
    );

    const diffMs = eventDate.getTime() - today.getTime();
    const diffDays = Math.ceil(diffMs / (1000 * 60 * 60 * 24));

    if (diffDays >= 0 && diffDays <= event.windowDays) {
      return event;
    }
  }

  return null;
}
