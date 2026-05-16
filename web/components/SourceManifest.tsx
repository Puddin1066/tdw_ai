import type { SourceManifestData } from "@/types/artifacts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { EmptyState } from "@/components/EmptyState";

export interface SourceManifestProps {
  manifest: SourceManifestData | null;
}

export function SourceManifest({ manifest }: SourceManifestProps) {
  const entries = manifest?.entries ?? [];

  if (entries.length === 0) {
    return (
      <EmptyState
        title="No source manifest"
        description="source_manifest.json is missing or lists no connector queries for this case."
      />
    );
  }

  const totalRecords = entries.reduce((sum, e) => sum + e.record_count, 0);

  return (
    <div className="space-y-4">
      <Badge variant="outline">{totalRecords} total records</Badge>
      <div className="grid gap-3 md:grid-cols-2">
        {entries.map((entry) => (
          <Card key={`${entry.connector_name}-${entry.retrieved_at}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-mono">{entry.connector_name}</CardTitle>
              <p className="text-xs text-muted-foreground">{entry.source_name}</p>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <p>
                <span className="text-muted-foreground">Records: </span>
                <span className="font-mono">{entry.record_count}</span>
              </p>
              <p>
                <span className="text-muted-foreground">Mode: </span>
                <span className="capitalize">{entry.mode}</span>
              </p>
              {entry.query?.raw_query ? (
                <p className="text-xs text-muted-foreground">{entry.query.raw_query}</p>
              ) : null}
              <p className="text-xs text-muted-foreground">Retrieved: {entry.retrieved_at}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
