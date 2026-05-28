import { Badge } from "@/components/ui/badge";
import { formatReadinessState, readinessBadgeVariant } from "@/lib/format";

interface ReadinessBadgeProps {
  state: string;
  score?: number;
}

export function ReadinessBadge({ state, score }: ReadinessBadgeProps) {
  return (
    <Badge variant={readinessBadgeVariant(state)} className="capitalize">
      {formatReadinessState(state)}
      {typeof score === "number" ? ` · ${score.toFixed(0)}` : ""}
    </Badge>
  );
}
