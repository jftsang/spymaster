type CardBadgeProps = {
  card: number;
  kind: "you" | "opp";
};

export const cardLabel = (card: number): string =>
  card > 0 ? String(card) : "👻";

export const CardBadge = ({ card, kind }: CardBadgeProps) => (
  <span
    class={
      "badge card-badge " + (kind === "you" ? "bg-primary" : "bg-danger")
    }
  >
    {cardLabel(card)}
  </span>
);
