"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { RiskMapData, RiskSeverity } from "@/types/artifacts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";

export interface RiskMapProps {
  riskMap: RiskMapData | null;
}

const severityScore: Record<RiskSeverity, number> = {
  low: 1,
  medium: 2,
  high: 3,
  critical: 4,
};

export function RiskMap({ riskMap }: RiskMapProps) {
  if (!riskMap || !riskMap.risks || riskMap.risks.length === 0) {
    return (
      <EmptyState
        title="No risk map"
        description="risk_map.json is missing or contains no categorized translational risks."
      />
    );
  }

  const chartData = riskMap.risks.map((risk) => ({
    name: risk.title.length > 28 ? `${risk.title.slice(0, 28)}…` : risk.title,
    severity: severityScore[risk.severity] ?? 2,
    confidence: risk.confidence,
    category: risk.category,
  }));

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Risk severity & confidence</CardTitle>
        </CardHeader>
        <CardContent className="h-80">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} layout="vertical" margin={{ left: 8, right: 16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis type="number" domain={[0, 4]} stroke="hsl(var(--muted-foreground))" />
              <YAxis
                type="category"
                dataKey="name"
                width={140}
                tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{
                  background: "hsl(var(--card))",
                  border: "1px solid hsl(var(--border))",
                  borderRadius: 8,
                }}
              />
              <Bar dataKey="severity" name="Severity" fill="#2dd4bf" radius={[0, 4, 4, 0]} />
              <Bar dataKey="confidence" name="Confidence" fill="#fbbf24" radius={[0, 4, 4, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      <div className="grid gap-3 md:grid-cols-2">
        {riskMap.risks.map((risk) => (
          <Card key={risk.risk_id}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium">{risk.title}</CardTitle>
              <p className="text-xs capitalize text-muted-foreground">
                {risk.category} · {risk.severity}
                {risk.inferred ? " · inferred" : ""}
              </p>
            </CardHeader>
            <CardContent className="text-sm text-muted-foreground">{risk.description}</CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
