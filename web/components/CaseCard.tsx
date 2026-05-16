import Link from "next/link";
import { ArrowRight } from "lucide-react";
import type { EvidenceDensity } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { formatConfidence } from "@/lib/utils";

export interface CaseCardProps {
  caseId: string;
  targetName: string;
  indicationName: string;
  maturityStage: string;
  confidenceScore: number;
  evidenceDensity: EvidenceDensity;
  topRisk: string;
}

const densityVariant: Record<EvidenceDensity, "success" | "warning" | "danger"> = {
  high: "success",
  medium: "warning",
  low: "danger",
};

export function CaseCard({
  caseId,
  targetName,
  indicationName,
  maturityStage,
  confidenceScore,
  evidenceDensity,
  topRisk,
}: CaseCardProps) {
  return (
    <Link href={`/cases/${caseId}`} className="group block h-full">
      <Card className="h-full border-border/80 bg-card/80 transition-colors hover:border-cockpit-teal/40 hover:bg-card">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <div>
              <p className="font-mono text-xs uppercase tracking-wider text-muted-foreground">
                {caseId}
              </p>
              <CardTitle className="mt-1 text-xl">{targetName}</CardTitle>
              <p className="text-sm text-muted-foreground">{indicationName}</p>
            </div>
            <ArrowRight className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:text-cockpit-teal" />
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-xs text-muted-foreground">Maturity</p>
              <p className="font-medium capitalize">{maturityStage}</p>
            </div>
            <div>
              <p className="text-xs text-muted-foreground">Confidence</p>
              <p className="font-medium">{formatConfidence(confidenceScore)}</p>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Badge variant={densityVariant[evidenceDensity]}>
              Evidence: {evidenceDensity}
            </Badge>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">Top risk</p>
            <p className="line-clamp-2 text-sm text-foreground/90">{topRisk}</p>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
