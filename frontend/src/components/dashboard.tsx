"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import {
  ArrowDownRight,
  ArrowUpRight,
  Landmark,
  LogOut,
  RefreshCw,
  Search,
  WalletCards,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Field, FieldLabel } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";

const PluggyConnect = dynamic(
  () => import("react-pluggy-connect").then((module) => module.PluggyConnect),
  { ssr: false },
);

type Member = { id: string; name: string };
type Me = {
  name: string;
  household: { name: string; members: Member[] };
};
type Account = {
  id: string;
  member_id: string;
  member_name: string;
  institution_name: string;
  name: string;
  balance: string;
  currency: string;
  last_synced_at: string | null;
};
type Category = { id: string; name: string; kind: string };
type Kpi = { value: string; variation: number | null };
type Kpis = {
  income: Kpi;
  expense: Kpi;
  balance: Kpi;
  net_worth: Kpi;
};
type Trend = { month: string; income: string; expense: string; balance: string };
type Expense = { category_id: string | null; category: string; amount: string };
type Transaction = {
  id: string;
  date: string;
  description: string;
  merchant_name: string | null;
  amount: string;
  type: "debit" | "credit";
  status: string;
  source: string;
  category_id: string | null;
  category_name: string | null;
  account_id: string;
  account_name: string;
  member_id: string;
  member_name: string;
  installment_current: number | null;
  installment_total: number | null;
};
type TransactionPage = { items: Transaction[]; next_cursor: string | null };
type Preset = "month" | "quarter" | "year" | "custom";

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const shortDate = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" });
const monthName = new Intl.DateTimeFormat("pt-BR", { month: "short" });

function iso(date: Date) {
  const pad = (value: number) => String(value).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
}

function presetDates(preset: Preset) {
  const today = new Date();
  const start = new Date(today);
  if (preset === "month") start.setDate(1);
  if (preset === "quarter") start.setMonth(Math.floor(today.getMonth() / 3) * 3, 1);
  if (preset === "year") start.setMonth(0, 1);
  return { from: iso(start), to: iso(today) };
}

async function json<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { credentials: "include", ...init });
  if (!response.ok) throw new Error(await response.text());
  return response.json();
}

function queryString(values: Record<string, string>) {
  const params = new URLSearchParams();
  Object.entries(values).forEach(([key, value]) => value && params.set(key, value));
  return params.toString();
}

function Variation({ value, expense = false }: { value: number | null; expense?: boolean }) {
  if (value === null) return <span className="text-xs text-muted-foreground">Sem histórico</span>;
  const favorable = expense ? value <= 0 : value >= 0;
  const Icon = value >= 0 ? ArrowUpRight : ArrowDownRight;
  return (
    <span className={favorable ? "text-xs text-primary" : "text-xs text-destructive"}>
      <Icon className="mr-1 inline size-3.5" aria-hidden="true" />
      {Math.abs(value).toLocaleString("pt-BR", { style: "percent", maximumFractionDigits: 1 })}
      <span className="text-muted-foreground"> vs. período anterior</span>
    </span>
  );
}

function KpiCard({ label, data, expense }: { label: string; data: Kpi; expense?: boolean }) {
  return (
    <Card>
      <CardHeader className="gap-1">
        <CardDescription>{label}</CardDescription>
        <CardTitle className="font-heading text-2xl font-semibold tabular-nums">
          {money.format(Number(data.value))}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Variation value={data.variation} expense={expense} />
      </CardContent>
    </Card>
  );
}

function TrendChart({ values }: { values: Trend[] }) {
  const width = 720;
  const height = 220;
  const pad = 24;
  const max = Math.max(1, ...values.flatMap((value) => [Number(value.income), Number(value.expense)]));
  const path = (key: "income" | "expense") =>
    values
      .map((value, index) => {
        const x = pad + (index * (width - pad * 2)) / Math.max(1, values.length - 1);
        const y = height - pad - (Number(value[key]) / max) * (height - pad * 2);
        return `${index ? "L" : "M"}${x},${y}`;
      })
      .join(" ");
  return (
    <div>
      <div className="mb-4 flex gap-5 text-xs text-muted-foreground">
        <span><i className="mr-2 inline-block size-2 rounded-full bg-primary" />Receitas</span>
        <span><i className="mr-2 inline-block size-2 rounded-full bg-destructive" />Despesas</span>
      </div>
      <svg aria-label="Receitas e despesas nos últimos 12 meses" className="h-auto w-full" viewBox={`0 0 ${width} ${height}`} role="img">
        <path d={path("income")} fill="none" stroke="var(--primary)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" />
        <path d={path("expense")} fill="none" stroke="var(--destructive)" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" />
      </svg>
      <div className="grid grid-cols-6 gap-1 text-center text-xs text-muted-foreground sm:grid-cols-12">
        {values.map((value) => <span key={value.month}>{monthName.format(new Date(`${value.month}T12:00:00`)).replace(".", "")}</span>)}
      </div>
    </div>
  );
}

function ExpenseChart({ values }: { values: Expense[] }) {
  const total = values.reduce((sum, value) => sum + Number(value.amount), 0);
  let cursor = 0;
  const slices = values.slice(0, 5).map((value, index) => {
    const start = cursor;
    cursor += (Number(value.amount) / Math.max(1, total)) * 100;
    return `var(--chart-${index + 1}) ${start}% ${cursor}%`;
  });
  return (
    <div className="grid items-center gap-6 sm:grid-cols-[10rem_1fr]">
      <div
        aria-label={`Despesas por categoria, total ${money.format(total)}`}
        className="mx-auto aspect-square w-40 rounded-full border-12 border-card"
        role="img"
        style={{ background: values.length ? `conic-gradient(${slices.join(",")})` : "var(--muted)" }}
      />
      {values.length ? (
        <ol className="flex list-none flex-col gap-3 p-0">
          {values.slice(0, 5).map((value, index) => (
            <li className="grid grid-cols-[auto_1fr_auto] items-center gap-2 text-sm" key={value.category_id ?? "none"}>
              <i className="size-2 rounded-full" style={{ background: `var(--chart-${index + 1})` }} />
              <span className="truncate">{value.category}</span>
              <span className="tabular-nums">{money.format(Number(value.amount))}</span>
            </li>
          ))}
        </ol>
      ) : <p className="text-sm text-muted-foreground">Nenhuma despesa neste período.</p>}
    </div>
  );
}

export function Dashboard({ me, onLogout, pendingLogout }: { me: Me; onLogout: () => void; pendingLogout: boolean }) {
  const initial = presetDates("month");
  const [preset, setPreset] = useState<Preset>("month");
  const [from, setFrom] = useState(initial.from);
  const [to, setTo] = useState(initial.to);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [appliedSearch, setAppliedSearch] = useState("");
  const [account, setAccount] = useState("");
  const [member, setMember] = useState("");
  const [category, setCategory] = useState("");
  const [type, setType] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [syncing, setSyncing] = useState(false);
  const [connectToken, setConnectToken] = useState("");

  const transactionParams = useMemo(() => ({
    date_from: from,
    date_to: to,
    search: appliedSearch,
    account_id: account,
    member_id: member,
    category_id: category,
    type,
  }), [from, to, appliedSearch, account, member, category, type]);

  const load = useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const period = queryString({ date_from: from, date_to: to });
      const [nextAccounts, nextCategories, nextKpis, nextTrends, nextExpenses, page] = await Promise.all([
        json<Account[]>("/api/accounts"),
        json<Category[]>("/api/categories"),
        json<Kpis>(`/api/analytics/kpis?${period}`),
        json<Trend[]>(`/api/analytics/trends?${queryString({ date_to: to })}`),
        json<Expense[]>(`/api/analytics/expenses-by-category?${period}`),
        json<TransactionPage>(`/api/transactions?${queryString(transactionParams)}`),
      ]);
      setAccounts(nextAccounts);
      setCategories(nextCategories);
      setKpis(nextKpis);
      setTrends(nextTrends);
      setExpenses(nextExpenses);
      setTransactions(page.items);
      setNextCursor(page.next_cursor);
    } catch {
      setError("Não foi possível carregar os dados financeiros.");
    } finally {
      setLoading(false);
    }
  }, [from, to, transactionParams]);

  useEffect(() => {
    const timer = window.setTimeout(() => void load(), 0);
    return () => window.clearTimeout(timer);
  }, [load]);

  function choosePreset(value: Preset) {
    setPreset(value);
    if (value !== "custom") {
      const dates = presetDates(value);
      setFrom(dates.from);
      setTo(dates.to);
    }
  }

  async function sync() {
    setSyncing(true);
    setError("");
    try {
      await json("/api/pluggy/sync", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
      await load();
    } catch {
      setError("Não foi possível sincronizar com o Pluggy.");
    } finally {
      setSyncing(false);
    }
  }

  async function connect() {
    setSyncing(true);
    setError("");
    try {
      const data = await json<{ accessToken: string }>("/api/pluggy/connect-token", { method: "POST" });
      setConnectToken(data.accessToken);
    } catch {
      setError("Configure as credenciais Pluggy para conectar uma instituição.");
    } finally {
      setSyncing(false);
    }
  }

  async function connected(data: { item: { id: string } }) {
    setConnectToken("");
    setSyncing(true);
    try {
      await json("/api/pluggy/items", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ item_id: data.item.id }),
      });
      await load();
    } catch {
      setError("A conta conectou, mas a primeira sincronização falhou. Tente atualizar.");
    } finally {
      setSyncing(false);
    }
  }

  async function loadMore() {
    if (!nextCursor) return;
    const page = await json<TransactionPage>(`/api/transactions?${queryString({ ...transactionParams, cursor: nextCursor })}`);
    setTransactions((current) => [...current, ...page.items]);
    setNextCursor(page.next_cursor);
  }

  async function changeCategory(transactionId: string, categoryId: string) {
    try {
      await json(`/api/transactions/${transactionId}/category`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category_id: categoryId || null }),
      });
      setTransactions((current) => current.map((item) => item.id === transactionId
        ? { ...item, category_id: categoryId || null, category_name: categories.find((candidate) => candidate.id === categoryId)?.name ?? null }
        : item));
    } catch {
      setError("Não foi possível atualizar a categoria.");
    }
  }

  function applySearch(event: FormEvent) {
    event.preventDefault();
    setAppliedSearch(search.trim());
  }

  const lastSync = accounts.reduce<string | null>((latest, item) => !item.last_synced_at
    ? latest
    : !latest || item.last_synced_at > latest ? item.last_synced_at : latest, null);

  return (
    <main className="mx-auto flex min-h-svh w-full max-w-[90rem] flex-col gap-8 px-4 py-6 sm:px-8 sm:py-8">
      <header className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <p className="text-sm font-medium tracking-[0.08em] text-muted-foreground uppercase">Planna · {me.household.name}</p>
          <h1 className="font-heading text-3xl font-semibold tracking-tight">Visão da casa</h1>
        </div>
        <div className="flex flex-wrap gap-2">
          <Button disabled={syncing} onClick={connect} variant="outline"><Landmark data-icon="inline-start" />Conectar instituição</Button>
          <Button disabled={syncing || !accounts.length} onClick={sync} variant="outline"><RefreshCw data-icon="inline-start" />{syncing ? "Sincronizando…" : "Atualizar"}</Button>
          <Button aria-label="Sair" disabled={pendingLogout} onClick={onLogout} variant="ghost"><LogOut /></Button>
        </div>
      </header>

      {connectToken && (
        <PluggyConnect
          connectToken={connectToken}
          includeSandbox={process.env.NODE_ENV !== "production"}
          onClose={() => setConnectToken("")}
          onError={() => setError("A conexão com a instituição não foi concluída.")}
          onSuccess={connected}
        />
      )}

      <section className="flex flex-wrap items-end gap-3" aria-label="Período do painel">
        <Field className="max-w-48">
          <FieldLabel htmlFor="period">Período</FieldLabel>
          <select className="h-11 rounded-lg border border-input bg-card px-3.5 text-sm outline-none focus:border-ring focus:ring-3 focus:ring-ring/50" id="period" onChange={(event) => choosePreset(event.target.value as Preset)} value={preset}>
            <option value="month">Este mês</option>
            <option value="quarter">Este trimestre</option>
            <option value="year">Este ano</option>
            <option value="custom">Personalizado</option>
          </select>
        </Field>
        {preset === "custom" && <>
          <Field className="max-w-44"><FieldLabel htmlFor="date-from">De</FieldLabel><Input id="date-from" max={to} onChange={(event) => setFrom(event.target.value)} type="date" value={from} /></Field>
          <Field className="max-w-44"><FieldLabel htmlFor="date-to">Até</FieldLabel><Input id="date-to" min={from} onChange={(event) => setTo(event.target.value)} type="date" value={to} /></Field>
        </>}
        <p className="ml-auto text-sm text-muted-foreground">
          {lastSync ? `Atualizado em ${new Date(lastSync).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}` : "Nenhuma conta sincronizada"}
        </p>
      </section>

      {error && <p aria-live="polite" className="rounded-lg bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</p>}

      {loading || !kpis ? (
        <Card><CardHeader><CardTitle>Organizando seus números…</CardTitle><CardDescription>Receitas, despesas e contas estão sendo consolidadas.</CardDescription></CardHeader></Card>
      ) : <>
        <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Indicadores financeiros">
          <KpiCard data={kpis.income} label="Receita" />
          <KpiCard data={kpis.expense} expense label="Despesa" />
          <KpiCard data={kpis.balance} label="Saldo do período" />
          <KpiCard data={kpis.net_worth} label="Patrimônio" />
        </section>

        <section className="grid gap-4 xl:grid-cols-[1.6fr_1fr]">
          <Card><CardHeader><CardTitle>Tendência em 12 meses</CardTitle><CardDescription>Receitas e despesas reconhecidas nas contas conectadas.</CardDescription></CardHeader><CardContent><TrendChart values={trends} /></CardContent></Card>
          <Card><CardHeader><CardTitle>Para onde foi o dinheiro</CardTitle><CardDescription>Despesas por categoria no período.</CardDescription></CardHeader><CardContent><ExpenseChart values={expenses} /></CardContent></Card>
        </section>

        <Card>
          <CardHeader>
            <CardTitle>Movimentações</CardTitle>
            <CardDescription>Busque e filtre o extrato compartilhado da casa.</CardDescription>
          </CardHeader>
          <CardContent className="flex flex-col gap-5">
            <form className="flex gap-2" onSubmit={applySearch}>
              <Input aria-label="Buscar movimentação" onChange={(event) => setSearch(event.target.value)} placeholder="Descrição ou estabelecimento" value={search} />
              <Button aria-label="Buscar" type="submit" variant="outline"><Search /></Button>
            </form>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <select aria-label="Filtrar por conta" className="h-11 rounded-lg border border-input bg-card px-3.5 text-sm" onChange={(event) => setAccount(event.target.value)} value={account}><option value="">Todas as contas</option>{accounts.map((item) => <option key={item.id} value={item.id}>{item.institution_name} · {item.name}</option>)}</select>
              <select aria-label="Filtrar por membro" className="h-11 rounded-lg border border-input bg-card px-3.5 text-sm" onChange={(event) => setMember(event.target.value)} value={member}><option value="">Todos os membros</option>{me.household.members.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
              <select aria-label="Filtrar por categoria" className="h-11 rounded-lg border border-input bg-card px-3.5 text-sm" onChange={(event) => setCategory(event.target.value)} value={category}><option value="">Todas as categorias</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
              <select aria-label="Filtrar por tipo" className="h-11 rounded-lg border border-input bg-card px-3.5 text-sm" onChange={(event) => setType(event.target.value)} value={type}><option value="">Receitas e despesas</option><option value="credit">Receitas</option><option value="debit">Despesas</option></select>
            </div>
            <Separator />
            {transactions.length ? (
              <div className="overflow-x-auto">
                <table className="w-full min-w-3xl border-collapse text-left text-sm">
                  <thead><tr className="border-b text-xs text-muted-foreground"><th className="px-3 py-3 font-medium">Data</th><th className="px-3 py-3 font-medium">Movimentação</th><th className="px-3 py-3 font-medium">Categoria</th><th className="px-3 py-3 font-medium">Conta</th><th className="px-3 py-3 font-medium">Membro</th><th className="px-3 py-3 text-right font-medium">Valor</th></tr></thead>
                  <tbody>{transactions.map((item) => (
                    <tr className="border-b border-border/60 last:border-0" key={item.id}>
                      <td className="whitespace-nowrap px-3 py-4 text-muted-foreground">{shortDate.format(new Date(item.date))}</td>
                      <td className="max-w-60 px-3 py-4"><p className="truncate font-medium">{item.merchant_name || item.description}</p><p className="truncate text-xs text-muted-foreground">{item.installment_total ? `${item.installment_current}/${item.installment_total} · ` : ""}{item.status === "pending" ? "Pendente" : item.description}</p></td>
                      <td className="px-3 py-4"><select aria-label={`Categoria de ${item.description}`} className="h-9 max-w-44 rounded-md border border-input bg-card px-2 text-xs" onChange={(event) => void changeCategory(item.id, event.target.value)} value={item.category_id ?? ""}><option value="">Sem categoria</option>{categories.filter((candidate) => candidate.kind === (item.type === "debit" ? "expense" : "income")).map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.name}</option>)}</select></td>
                      <td className="px-3 py-4 text-muted-foreground">{item.account_name}</td>
                      <td className="px-3 py-4 text-muted-foreground">{item.member_name}</td>
                      <td className={`px-3 py-4 text-right font-medium tabular-nums ${item.type === "credit" ? "text-primary" : ""}`}>{money.format(Number(item.amount))}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3 py-12 text-center"><WalletCards className="size-8 text-muted-foreground" aria-hidden="true" /><p className="font-medium">Nenhuma movimentação encontrada</p><p className="max-w-md text-sm text-muted-foreground">Conecte uma instituição ou ajuste os filtros para ver o extrato da casa.</p></div>
            )}
            {nextCursor && <Button className="self-center" onClick={() => void loadMore()} variant="outline">Carregar mais</Button>}
          </CardContent>
        </Card>
      </>}
    </main>
  );
}
