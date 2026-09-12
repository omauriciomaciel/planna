"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  Building2,
  ChartNoAxesCombined,
  CircleDollarSign,
  CreditCard,
  Landmark,
  Plus,
  Trash2,
} from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldGroup, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { api } from "@/api";

type Member = { id: string; name: string };
type WealthAsset = {
  id: string;
  member_id: string;
  member_name: string;
  type: string;
  name: string;
  value: string;
  source: string;
  valued_at: string | null;
  editable: boolean;
};
type WealthLiability = {
  id: string;
  member_id: string;
  member_name: string;
  type: string;
  name: string;
  balance: string;
  monthly_payment: string | null;
  source: string;
  editable: boolean;
};
type Allocation = { type: string; value: string };
type Wealth = {
  total_assets: string;
  total_liabilities: string;
  net_worth: string;
  debt_ratio: number | null;
  income_commitment: number | null;
  savings_rate: number | null;
  monthly_income: string;
  monthly_expense: string;
  monthly_debt_payments: string;
  assets: WealthAsset[];
  liabilities: WealthLiability[];
  allocation: Allocation[];
};
type History = {
  month: string;
  total_assets: string;
  total_liabilities: string;
  net_worth: string;
};

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const monthName = new Intl.DateTimeFormat("pt-BR", { month: "short", year: "2-digit" });
const selectClass =
  "h-12 w-full rounded-xl border border-border bg-input/45 px-4 text-sm outline-none transition-[background-color,border-color,box-shadow] focus:border-ring focus:bg-card focus:ring-3 focus:ring-ring/20";
const assetLabels: Record<string, string> = {
  cash: "Dinheiro",
  investment: "Investimentos",
  real_estate: "Imóveis",
  pension: "Previdência",
};
const liabilityLabels: Record<string, string> = {
  financing: "Financiamento",
  credit_card: "Cartão",
  loan: "Empréstimo",
};

function percent(value: number | null) {
  return value === null
    ? "Sem base de cálculo"
    : value.toLocaleString("pt-BR", { style: "percent", maximumFractionDigits: 1 });
}

function NetWorthChart({ values }: { values: History[] }) {
  if (!values.length) {
    return (
      <p className="py-12 text-center text-sm text-muted-foreground">
        O primeiro ponto será registrado na próxima atualização patrimonial.
      </p>
    );
  }
  const width = 720;
  const height = 220;
  const pad = 28;
  const numbers = values.map((value) => Number(value.net_worth));
  const min = Math.min(0, ...numbers);
  const max = Math.max(1, ...numbers);
  const range = max - min || 1;
  const points = values.map((value, index) => ({
    x: pad + (index * (width - pad * 2)) / Math.max(1, values.length - 1),
    y: height - pad - ((Number(value.net_worth) - min) / range) * (height - pad * 2),
  }));
  const zeroY = height - pad - ((0 - min) / range) * (height - pad * 2);
  return (
    <div className="flex flex-col gap-4">
      <svg
        aria-label="Evolução mensal do patrimônio líquido"
        className="h-auto w-full"
        role="img"
        viewBox={`0 0 ${width} ${height}`}
      >
        <line
          stroke="var(--border)"
          strokeDasharray="5 6"
          strokeWidth="1"
          x1={pad}
          x2={width - pad}
          y1={zeroY}
          y2={zeroY}
        />
        <path
          d={points.map((point, index) => `${index ? "L" : "M"}${point.x},${point.y}`).join(" ")}
          fill="none"
          stroke="var(--primary)"
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth="3"
        />
        {points.map((point, index) => (
          <circle
            cx={point.x}
            cy={point.y}
            fill="var(--card)"
            key={values[index].month}
            r="4"
            stroke="var(--primary)"
            strokeWidth="3"
          />
        ))}
      </svg>
      <div className="grid gap-2 text-center text-xs text-muted-foreground [grid-template-columns:repeat(auto-fit,minmax(4rem,1fr))]">
        {values.map((value) => (
          <span key={value.month}>
            {monthName.format(new Date(`${value.month}T12:00:00`)).replace(" de ", " ").replace(".", "")}
          </span>
        ))}
      </div>
    </div>
  );
}

function AllocationChart({ values }: { values: Allocation[] }) {
  const total = values.reduce((sum, value) => sum + Number(value.value), 0);
  let cursor = 0;
  const slices = values.map((value, index) => {
    const start = cursor;
    cursor += (Number(value.value) / Math.max(1, total)) * 100;
    return `var(--chart-${(index % 5) + 1}) ${start}% ${cursor}%`;
  });
  return (
    <div className="grid items-center gap-6 sm:grid-cols-[10rem_1fr]">
      <div
        aria-label={`Alocação dos ativos, total ${money.format(total)}`}
        className="mx-auto aspect-square w-40 rounded-full border-12 border-card"
        role="img"
        style={{ background: values.length ? `conic-gradient(${slices.join(",")})` : "var(--muted)" }}
      />
      {values.length ? (
        <ol className="flex list-none flex-col gap-3 p-0">
          {values.map((value, index) => (
            <li className="grid grid-cols-[auto_1fr_auto] items-center gap-2 text-sm" key={value.type}>
              <i
                className="size-2 rounded-full"
                style={{ background: `var(--chart-${(index % 5) + 1})` }}
              />
              <span>{assetLabels[value.type] ?? value.type}</span>
              <span className="text-right tabular-nums">{money.format(Number(value.value))}</span>
            </li>
          ))}
        </ol>
      ) : (
        <p className="text-sm text-muted-foreground">Cadastre um ativo para ver a composição.</p>
      )}
    </div>
  );
}

function optionalNumber(form: FormData, name: string) {
  const value = String(form.get(name) ?? "").trim();
  return value ? Number(value) : null;
}

export function WealthPanel({
  members,
  onChanged,
  refreshKey,
}: {
  members: Member[];
  onChanged: () => Promise<void>;
  refreshKey: string;
}) {
  const [wealth, setWealth] = useState<Wealth | null>(null);
  const [history, setHistory] = useState<History[]>([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(async (signal?: AbortSignal) => {
    setError("");
    try {
      const [nextWealth, nextHistory] = await Promise.all([
        api<Wealth>("/api/net-worth", { signal }),
        api<History[]>("/api/net-worth/history", { signal }),
      ]);
      setWealth(nextWealth);
      setHistory(nextHistory);
    } catch (loadError) {
      if (loadError instanceof DOMException && loadError.name === "AbortError") return;
      setError("Não foi possível carregar o patrimônio.");
    } finally {
      if (!signal?.aborted) setLoading(false);
    }
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    const timer = window.setTimeout(() => void load(controller.signal), 0);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [load, refreshKey]);

  async function mutate(key: string, url: string, init: RequestInit) {
    setPending(key);
    setError("");
    try {
      await api(url, init);
      await Promise.all([load(), onChanged()]);
      return true;
    } catch (mutationError) {
      setError(
        mutationError instanceof Error
          ? mutationError.message
          : "Não foi possível atualizar o patrimônio.",
      );
      return false;
    } finally {
      setPending("");
    }
  }

  async function createAsset(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const target = event.currentTarget;
    const form = new FormData(target);
    const done = await mutate("new-asset", "/api/assets", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: form.get("member_id"),
        type: form.get("type"),
        name: form.get("name"),
        current_value: Number(form.get("current_value")),
      }),
    });
    if (done) target.reset();
  }

  async function createLiability(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const target = event.currentTarget;
    const form = new FormData(target);
    const done = await mutate("new-liability", "/api/liabilities", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        member_id: form.get("member_id"),
        type: form.get("type"),
        name: form.get("name"),
        current_balance: Number(form.get("current_balance")),
        original_amount: optionalNumber(form, "original_amount"),
        interest_rate: optionalNumber(form, "interest_rate"),
        monthly_payment: optionalNumber(form, "monthly_payment"),
        due_day: optionalNumber(form, "due_day"),
      }),
    });
    if (done) target.reset();
  }

  async function updateValue(
    event: FormEvent<HTMLFormElement>,
    kind: "assets" | "liabilities",
    id: string,
  ) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const field = kind === "assets" ? "current_value" : "current_balance";
    await mutate(`${kind}:${id}`, `/api/${kind}/${id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ [field]: Number(form.get("value")) }),
    });
  }

  async function remove(kind: "assets" | "liabilities", id: string, name: string) {
    if (!window.confirm(`Remover “${name}” do patrimônio?`)) return;
    await mutate(`${kind}:${id}`, `/api/${kind}/${id}`, { method: "DELETE" });
  }

  if (loading || !wealth) {
    return (
      <Card aria-live="polite">
        <CardHeader>
          <CardTitle>Consolidando o patrimônio…</CardTitle>
          <CardDescription>Ativos, dívidas e histórico estão sendo organizados.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <section aria-labelledby="wealth-title" className="flex flex-col gap-5">
      <div className="flex flex-col gap-1">
        <p className="text-sm font-semibold tracking-[0.08em] text-primary uppercase">Patrimônio</p>
        <h2 className="font-heading text-2xl font-semibold tracking-[-0.03em] sm:text-3xl" id="wealth-title">
          O que a casa construiu
        </h2>
        <p className="max-w-[65ch] text-sm text-muted-foreground">
          Saldos e investimentos conectados, bens informados e todas as dívidas em uma conta só.
        </p>
      </div>

      {error && (
        <p aria-live="polite" className="rounded-2xl bg-destructive/10 px-4 py-3 text-sm text-destructive">
          {error}
        </p>
      )}

      <div className="grid gap-5 lg:grid-cols-[1.2fr_0.8fr]">
        <Card className="border-primary bg-primary text-primary-foreground">
          <CardHeader>
            <CardDescription className="text-primary-foreground">Patrimônio líquido real</CardDescription>
            <CardTitle className="text-4xl font-semibold tracking-[-0.045em] tabular-nums sm:text-5xl">
              {money.format(Number(wealth.net_worth))}
            </CardTitle>
          </CardHeader>
          <CardContent className="mt-auto grid gap-4 border-t border-primary-foreground/15 pt-5 sm:grid-cols-2">
            <div>
              <p className="text-xs text-primary-foreground">Total em ativos</p>
              <p className="mt-1 text-lg font-semibold tabular-nums">
                {money.format(Number(wealth.total_assets))}
              </p>
            </div>
            <div>
              <p className="text-xs text-primary-foreground">Total em passivos</p>
              <p className="mt-1 text-lg font-semibold tabular-nums">
                {money.format(Number(wealth.total_liabilities))}
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Saúde patrimonial</CardTitle>
            <CardDescription>Três relações para acompanhar mês a mês.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 sm:grid-cols-3 lg:grid-cols-1">
            <div>
              <p className="text-xs text-muted-foreground">Dívidas sobre ativos</p>
              <p className="mt-1 text-xl font-semibold tabular-nums">{percent(wealth.debt_ratio)}</p>
            </div>
            <Separator />
            <div>
              <p className="text-xs text-muted-foreground">Renda comprometida</p>
              <p className="mt-1 text-xl font-semibold tabular-nums">
                {percent(wealth.income_commitment)}
              </p>
            </div>
            <Separator />
            <div>
              <p className="text-xs text-muted-foreground">Taxa de poupança no mês</p>
              <p className="mt-1 text-xl font-semibold tabular-nums">{percent(wealth.savings_rate)}</p>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-[1.4fr_1fr]">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ChartNoAxesCombined aria-hidden="true" className="size-4" />
              Evolução do patrimônio
            </CardTitle>
            <CardDescription>Um ponto por mês, atualizado quando contas ou valores mudam.</CardDescription>
          </CardHeader>
          <CardContent>
            <NetWorthChart values={history} />
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle>Alocação dos ativos</CardTitle>
            <CardDescription>Como o patrimônio bruto está distribuído hoje.</CardDescription>
          </CardHeader>
          <CardContent>
            <AllocationChart values={wealth.allocation} />
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-5 xl:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Building2 aria-hidden="true" className="size-4" />
              Ativos
            </CardTitle>
            <CardDescription>Contas e investimentos entram pelo Pluggy; outros bens são manuais.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <details className="rounded-2xl bg-muted/60 p-4">
              <summary className="min-h-11 cursor-pointer py-3 font-medium">
                <Plus aria-hidden="true" className="mr-2 inline size-4" />Adicionar ativo manual
              </summary>
              <form className="pt-4" onSubmit={createAsset}>
                <FieldGroup>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field>
                      <FieldLabel htmlFor="asset-name">Nome</FieldLabel>
                      <Input id="asset-name" maxLength={160} name="name" required />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="asset-value">Valor atual</FieldLabel>
                      <Input id="asset-value" min="0" name="current_value" required step="0.01" type="number" />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="asset-type">Tipo</FieldLabel>
                      <select className={selectClass} id="asset-type" name="type">
                        <option value="real_estate">Imóvel</option>
                        <option value="pension">Previdência</option>
                        <option value="investment">Investimento</option>
                        <option value="cash">Dinheiro</option>
                      </select>
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="asset-member">Responsável</FieldLabel>
                      <select className={selectClass} id="asset-member" name="member_id">
                        {members.map((member) => (
                          <option key={member.id} value={member.id}>{member.name}</option>
                        ))}
                      </select>
                    </Field>
                  </div>
                  <Button disabled={pending === "new-asset"} type="submit">
                    <Plus data-icon="inline-start" />
                    {pending === "new-asset" ? "Salvando…" : "Salvar ativo"}
                  </Button>
                </FieldGroup>
              </form>
            </details>
            <Separator />
            {wealth.assets.length ? (
              <ul className="flex list-none flex-col gap-1 p-0">
                {wealth.assets.map((item) => (
                  <li className="flex flex-col gap-3 rounded-2xl px-3 py-3 hover:bg-muted/45" key={item.id}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{item.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {assetLabels[item.type] ?? item.type} · {item.member_name}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <Badge variant={item.source === "pluggy" ? "secondary" : "outline"}>
                          {item.source === "pluggy" ? "Pluggy" : "Manual"}
                        </Badge>
                        <span className="font-semibold tabular-nums">{money.format(Number(item.value))}</span>
                      </div>
                    </div>
                    {item.editable && (
                      <form className="flex flex-wrap gap-2" onSubmit={(event) => updateValue(event, "assets", item.id)}>
                        <Input aria-label={`Novo valor de ${item.name}`} className="min-w-40 flex-1" defaultValue={item.value} min="0" name="value" required step="0.01" type="number" />
                        <Button disabled={pending === `assets:${item.id}`} size="sm" type="submit" variant="outline">Atualizar</Button>
                        <Button aria-label={`Remover ${item.name}`} disabled={pending === `assets:${item.id}`} onClick={() => remove("assets", item.id, item.name)} size="icon-lg" type="button" variant="destructive"><Trash2 /></Button>
                      </form>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">Nenhum ativo cadastrado.</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CreditCard aria-hidden="true" className="size-4" />
              Passivos
            </CardTitle>
            <CardDescription>Faturas e empréstimos conectados somam-se às dívidas manuais.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            <details className="rounded-2xl bg-muted/60 p-4">
              <summary className="min-h-11 cursor-pointer py-3 font-medium">
                <Plus aria-hidden="true" className="mr-2 inline size-4" />Adicionar passivo manual
              </summary>
              <form className="pt-4" onSubmit={createLiability}>
                <FieldGroup>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Field>
                      <FieldLabel htmlFor="liability-name">Nome</FieldLabel>
                      <Input id="liability-name" maxLength={160} name="name" required />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="liability-balance">Saldo devedor</FieldLabel>
                      <Input id="liability-balance" min="0" name="current_balance" required step="0.01" type="number" />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="liability-type">Tipo</FieldLabel>
                      <select className={selectClass} id="liability-type" name="type">
                        <option value="financing">Financiamento</option>
                        <option value="loan">Empréstimo</option>
                        <option value="credit_card">Cartão</option>
                      </select>
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="liability-member">Responsável</FieldLabel>
                      <select className={selectClass} id="liability-member" name="member_id">
                        {members.map((member) => (
                          <option key={member.id} value={member.id}>{member.name}</option>
                        ))}
                      </select>
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="original-amount">Valor original</FieldLabel>
                      <Input id="original-amount" min="0" name="original_amount" step="0.01" type="number" />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="monthly-payment">Parcela mensal</FieldLabel>
                      <Input id="monthly-payment" min="0" name="monthly_payment" step="0.01" type="number" />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="interest-rate">Taxa informada</FieldLabel>
                      <Input id="interest-rate" min="0" name="interest_rate" step="0.0001" type="number" />
                    </Field>
                    <Field>
                      <FieldLabel htmlFor="due-day">Dia do vencimento</FieldLabel>
                      <Input id="due-day" max="31" min="1" name="due_day" type="number" />
                    </Field>
                  </div>
                  <Button disabled={pending === "new-liability"} type="submit">
                    <Plus data-icon="inline-start" />
                    {pending === "new-liability" ? "Salvando…" : "Salvar passivo"}
                  </Button>
                </FieldGroup>
              </form>
            </details>
            <Separator />
            {wealth.liabilities.length ? (
              <ul className="flex list-none flex-col gap-1 p-0">
                {wealth.liabilities.map((item) => (
                  <li className="flex flex-col gap-3 rounded-2xl px-3 py-3 hover:bg-muted/45" key={item.id}>
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="truncate font-medium">{item.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {liabilityLabels[item.type] ?? item.type} · {item.member_name}
                        </p>
                      </div>
                      <div className="flex shrink-0 items-center gap-2">
                        <Badge variant={item.source === "pluggy" ? "secondary" : "outline"}>
                          {item.source === "pluggy" ? "Pluggy" : "Manual"}
                        </Badge>
                        <span className="font-semibold tabular-nums">{money.format(Number(item.balance))}</span>
                      </div>
                    </div>
                    {item.editable && (
                      <form className="flex flex-wrap gap-2" onSubmit={(event) => updateValue(event, "liabilities", item.id)}>
                        <Input aria-label={`Novo saldo de ${item.name}`} className="min-w-40 flex-1" defaultValue={item.balance} min="0" name="value" required step="0.01" type="number" />
                        <Button disabled={pending === `liabilities:${item.id}`} size="sm" type="submit" variant="outline">Atualizar</Button>
                        <Button aria-label={`Remover ${item.name}`} disabled={pending === `liabilities:${item.id}`} onClick={() => remove("liabilities", item.id, item.name)} size="icon-lg" type="button" variant="destructive"><Trash2 /></Button>
                      </form>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">Nenhum passivo cadastrado.</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card size="sm">
        <CardContent className="grid gap-4 sm:grid-cols-3">
          <div className="flex items-center gap-3">
            <CircleDollarSign aria-hidden="true" className="size-5 text-primary" />
            <div><p className="text-xs text-muted-foreground">Renda no mês</p><p className="font-semibold tabular-nums">{money.format(Number(wealth.monthly_income))}</p></div>
          </div>
          <div className="flex items-center gap-3">
            <Landmark aria-hidden="true" className="size-5 text-primary" />
            <div><p className="text-xs text-muted-foreground">Parcelas e faturas</p><p className="font-semibold tabular-nums">{money.format(Number(wealth.monthly_debt_payments))}</p></div>
          </div>
          <div className="flex items-center gap-3">
            <ChartNoAxesCombined aria-hidden="true" className="size-5 text-primary" />
            <div><p className="text-xs text-muted-foreground">Gastos no mês</p><p className="font-semibold tabular-nums">{money.format(Number(wealth.monthly_expense))}</p></div>
          </div>
        </CardContent>
      </Card>
    </section>
  );
}
