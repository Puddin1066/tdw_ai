import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function TrustTerminology() {
  return (
    <Card className="border-border/60 bg-card/30">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Trust terminology</CardTitle>
      </CardHeader>
      <CardContent className="grid gap-2 text-xs text-muted-foreground md:grid-cols-2">
        <p>
          <span className="font-medium text-foreground/90">Live Path:</span> Connector retrieval completed without fallback behavior.
        </p>
        <p>
          <span className="font-medium text-foreground/90">Fallback Path:</span> Connector retrieval degraded from preferred live path.
        </p>
        <p>
          <span className="font-medium text-foreground/90">Mock/Synthetic Fallback:</span> Placeholder or synthetic data path; not decision-grade evidence.
        </p>
        <p>
          <span className="font-medium text-foreground/90">Attributed Source IDs:</span> Source record IDs explicitly referenced by framed evidence or risks.
        </p>
        <p className="md:col-span-2">
          <span className="font-medium text-foreground/90">Deep Coverage:</span> Share of sourced records containing rich connector-specific fields, not only shallow IDs/titles.
        </p>
      </CardContent>
    </Card>
  );
}
