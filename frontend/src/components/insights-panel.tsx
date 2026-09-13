"use client";

import { useCallback, useEffect, useState } from "react";
import { EyeOff, Lightbulb, RefreshCw, Sparkles } from "lucide-react";

import { api } from "@/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

type Insight = {
  id: string;
  type: string;
  severity: "info" | "warning" | "critical";
  ref_period: string;
  title: string;
  body: string;
  actions: { description: string; estimated_impact: string | null }[];
  confidence: number;
  evidence: string[];
  model: string;
  generated_at: string;
};

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const severity = {
  critical: { label: "Ação urgente", variant: "destructive" as const },
  warning: { label: "Atenção", variant: "secondary" as const },
  info: { label: "Oportunidade", variant: "outline" as const },
};

function InsightCard({
  insight,
  onDismiss,
  prominent = false,
}: {
  insight: Insight;
  onDismiss: (id: string) => void;
  prominent?: boolean;
}) {
  const status = severity[insight.severity];
  const confidence = insight.confidence >= 0.85 ? "Confiança alta" : "Confiança média";
  return (
    <Card size={prominent ? "default" : "sm"}>
      <CardHeader>
        <div className="flex flex-wrap items-center gap-2">
          <Badge variant={status.variant}>{status.label}</Badge>
          <Badge variant="outline">{confidence}</Badge>
          <span className="text-xs text-muted-foreground">{insight.ref_period}</span>
        </div>
        <CardTitle>{insight.title}</CardTitle>
        <CardDescription className="max-w-[65ch]">{insight.body}</CardDescription>
      </CardHeader>
      {(insight.actions.length > 0 || insight.evidence.length > 0) && (
        <>
          <Separator />
          <CardContent className="flex flex-col gap-4">
            {insight.actions.length > 0 && (
              <ul className="flex list-none flex-col gap-3 p-0">
                {insight.actions.map((action, index) => (
                  <li className="flex min-h-11 items-start gap-3" key={`${action.description}-${index}`}>
                    <Lightbulb className="mt-0.5 size-4 shrink-0 text-primary" aria-hidden="true" />
                    <span className="min-w-0 flex-1">{action.description}</span>
                    {action.estimated_impact !== null && Number(action.estimated_impact) > 0 && (
                      <Badge variant="outline">
                        impacto de até {money.format(Number(action.estimated_impact))}
                      </Badge>
                    )}
                  </li>
                ))}
              </ul>
            )}
            {insight.evidence.length > 0 && (
              <details className="text-sm text-muted-foreground">
                <summary className="min-h-11 cursor-pointer py-3 font-medium text-foreground">
                  Por que estou vendo isso?
                </summary>
                <ul className="ml-5 list-disc space-y-1 pb-2">
                  {insight.evidence.map((item) => <li key={item}>{item}</li>)}
                </ul>
              </details>
            )}
            <Button className="self-start" onClick={() => onDismiss(insight.id)} size="sm" variant="ghost">
              <EyeOff data-icon="inline-start" />
              Não mostrar novamente
            </Button>
          </CardContent>
        </>
      )}
    </Card>
  );
}

export function InsightsPanel() {
  const [insights, setInsights] = useState<Insight[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");

  const load = useCallback(async () => {
    setError("");
    try {
      setInsights(await api<Insight[]>("/api/insights"));
    } catch {
      setError("Não foi possível carregar a leitura financeira.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  useEffect(() => {
    if (!insights.some((insight) => insight.model === "pending-ai")) return;
    const timer = window.setInterval(() => void load(), 3000);
    return () => window.clearInterval(timer);
  }, [insights, load]);

  async function refresh() {
    setRefreshing(true);
    setError("");
    try {
      setInsights(await api<Insight[]>("/api/insights/refresh", { method: "POST" }));
    } catch {
      setError("Não foi possível recalcular os insights agora.");
    } finally {
      setRefreshing(false);
    }
  }

  async function dismiss(id: string) {
    setError("");
    try {
      await api(`/api/insights/${id}/dismiss`, { method: "POST" });
      setInsights((current) => current.filter((insight) => insight.id !== id));
    } catch {
      setError("Não foi possível ocultar o insight agora.");
    }
  }

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Lendo os últimos 12 meses…</CardTitle>
          <CardDescription>Receitas, despesas e saldo estão sendo comparados.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  const generatedAt = insights[0]?.generated_at;
  return (
    <section className="flex flex-col gap-5" aria-label="Insights financeiros">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-medium">
            {insights.length} {insights.length === 1 ? "sinal encontrado" : "sinais encontrados"}
          </p>
          <p className="text-xs text-muted-foreground">
            {generatedAt
              ? `Gerado em ${new Date(generatedAt).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })} · ${insights[0].model === "deterministic" ? "análise local" : insights[0].model === "pending-ai" ? "IA analisando…" : "texto gerado com IA"}`
              : "A análise usa apenas dados financeiros agregados."}
          </p>
        </div>
        <Button disabled={refreshing} onClick={() => void refresh()} variant="outline">
          <RefreshCw data-icon="inline-start" />
          {refreshing ? "Recalculando…" : "Recalcular insights"}
        </Button>
      </div>

      {error && (
        <p aria-live="polite" className="rounded-2xl bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      )}

      {insights.length > 0 ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <div className="lg:col-span-2">
            <InsightCard insight={insights[0]} onDismiss={(id) => void dismiss(id)} prominent />
          </div>
          {insights.slice(1).map((insight) => (
            <InsightCard insight={insight} key={insight.id} onDismiss={(id) => void dismiss(id)} />
          ))}
        </div>
      ) : (
        <Card>
          <CardHeader>
            <Sparkles aria-hidden="true" />
            <CardTitle>Nenhum desvio relevante</CardTitle>
            <CardDescription>
              Ainda não há histórico suficiente ou os números permanecem dentro do padrão.
            </CardDescription>
          </CardHeader>
        </Card>
      )}
    </section>
  );
}
