"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  ArrowDownRight,
  ArrowUpRight,
  ChartNoAxesCombined,
  ChevronDown,
  ChevronUp,
  House,
  Landmark,
  LayoutDashboard,
  LogOut,
  Menu,
  ReceiptText,
  RefreshCw,
  Search,
  Sparkles,
  UsersRound,
  WalletCards,
} from "lucide-react";
import { cn } from "cn";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
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
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";
import { InvoiceCapture, InvoiceIngestResult } from "@/components/invoice-capture";
import { InsightsPanel } from "@/components/insights-panel";
import { ThemeToggle } from "@/components/theme-toggle";
import { WealthPanel } from "@/components/wealth-panel";
import { api } from "@/api";

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
  type: "bank" | "credit" | "investment";
  subtype: string | null;
  number_masked: string | null;
  balance: string;
  currency: string;
  credit_limit: string | null;
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
type InstallmentForecast = {
  total_remaining: string;
  monthly_installment_burden: string;
  by_category: { category_name: string; remaining_total: string; monthly_impact: string }[];
};
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
  account_id: string | null;
  account_name: string;
  member_id: string;
  member_name: string;
  installment_current: number | null;
  installment_total: number | null;
  invoice_id: string | null;
  invoice_items: {
    id: string;
    description: string;
    quantity: string;
    unit: string | null;
    unit_price: string;
    total_price: string;
  }[];
};
type TransactionPage = { items: Transaction[]; next_cursor: string | null };
type Preset = "month" | "quarter" | "year" | "custom";
type DashboardView = "overview" | "accounts" | "transactions" | "insights" | "wealth" | "invoices";

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });
const shortDate = new Intl.DateTimeFormat("pt-BR", { day: "2-digit", month: "short" });
const monthName = new Intl.DateTimeFormat("pt-BR", { month: "short" });
const selectClass = "h-12 w-full rounded-xl border border-border bg-input/45 px-4 text-sm outline-none transition-[background-color,border-color,box-shadow] focus:border-ring focus:bg-card focus:ring-3 focus:ring-ring/20";
const navigationItems = [
  { id: "overview", label: "Visão geral", icon: LayoutDashboard },
  { id: "accounts", label: "Contas", icon: Landmark },
  { id: "transactions", label: "Movimentações", icon: WalletCards },
  { id: "insights", label: "Insights", icon: Sparkles },
  { id: "wealth", label: "Patrimônio", icon: ChartNoAxesCombined },
  { id: "invoices", label: "Notas fiscais", icon: ReceiptText },
] as const;
const viewDetails: Record<DashboardView, { title: string; description: string }> = {
  overview: {
    title: "Visão da casa",
    description: "O resumo financeiro do período, sem perder o fio da meada.",
  },
  accounts: {
    title: "Contas conectadas",
    description: "Veja saldos, faturas e quem compartilhou cada conta com a casa.",
  },
  transactions: {
    title: "Movimentações",
    description: "Busque, filtre e categorize o extrato compartilhado da casa.",
  },
  insights: {
    title: "Leitura financeira",
    description: "Entenda o que saiu do padrão e qual ação pode ter mais impacto agora.",
  },
  wealth: {
    title: "Patrimônio",
    description: "Acompanhe ativos, dívidas e a evolução do que vocês construíram.",
  },
  invoices: {
    title: "Notas fiscais",
    description: "Importe uma NFC-e e concilie a compra com a movimentação bancária.",
  },
};

const accountTypeLabels: Record<Account["type"], string> = {
  bank: "Conta bancária",
  credit: "Cartão de crédito",
  investment: "Investimento",
};

function accountMoney(value: string, currency: string) {
  return new Intl.NumberFormat("pt-BR", { style: "currency", currency }).format(Number(value));
}

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
    <span className={cn("text-xs font-medium", favorable ? "text-primary" : "text-destructive")}>
      <Icon className="mr-1 inline size-3.5" aria-hidden="true" />
      {Math.abs(value).toLocaleString("pt-BR", { style: "percent", maximumFractionDigits: 1 })}
      <span className="text-muted-foreground"> vs. período anterior</span>
    </span>
  );
}

function KpiCard({ label, data, expense }: { label: string; data: Kpi; expense?: boolean }) {
  return (
    <Card className="min-h-36 justify-between" size="sm">
      <CardHeader>
        <CardDescription>{label}</CardDescription>
        <CardTitle className="text-2xl font-semibold tracking-[-0.035em] tabular-nums">
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
  const [activeView, setActiveView] = useState<DashboardView>("overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const [preset, setPreset] = useState<Preset>("month");
  const [from, setFrom] = useState(initial.from);
  const [to, setTo] = useState(initial.to);
  const [accounts, setAccounts] = useState<Account[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [kpis, setKpis] = useState<Kpis | null>(null);
  const [trends, setTrends] = useState<Trend[]>([]);
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [installments, setInstallments] = useState<InstallmentForecast | null>(null);
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
  const [expandedTransaction, setExpandedTransaction] = useState("");

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
      const [nextAccounts, nextCategories, nextKpis, nextTrends, nextExpenses, nextInstallments, page] = await Promise.all([
        api<Account[]>("/api/accounts"),
        api<Category[]>("/api/categories"),
        api<Kpis>(`/api/analytics/kpis?${period}`),
        api<Trend[]>(`/api/analytics/trends?${queryString({ date_to: to })}`),
        api<Expense[]>(`/api/analytics/expenses-by-category?${period}`),
        api<InstallmentForecast>("/api/analytics/installments-forecast"),
        api<TransactionPage>(`/api/transactions?${queryString(transactionParams)}`),
      ]);
      setAccounts(nextAccounts);
      setCategories(nextCategories);
      setKpis(nextKpis);
      setTrends(nextTrends);
      setExpenses(nextExpenses);
      setInstallments(nextInstallments);
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
      await api("/api/pluggy/sync", { method: "POST", headers: { "Content-Type": "application/json" }, body: "{}" });
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
      const data = await api<{ accessToken: string }>("/api/pluggy/connect-token", { method: "POST" });
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
      await api("/api/pluggy/items", {
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
    const page = await api<TransactionPage>(`/api/transactions?${queryString({ ...transactionParams, cursor: nextCursor })}`);
    setTransactions((current) => [...current, ...page.items]);
    setNextCursor(page.next_cursor);
  }

  async function ingestInvoice(url: string): Promise<InvoiceIngestResult> {
    const result = await api<InvoiceIngestResult>("/api/invoices/ingest", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    await load();
    return result;
  }

  async function changeCategory(transactionId: string, categoryId: string) {
    try {
      await api(`/api/transactions/${transactionId}/category`, {
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

  function navigate(view: DashboardView) {
    setActiveView(view);
    setMenuOpen(false);
  }

  const navigation = (
    <div className="flex h-full w-full flex-col">
      <div className="flex items-center gap-3 px-5 py-6">
        <span className="grid size-11 place-items-center rounded-full bg-primary text-lg font-bold text-primary-foreground">
          P
        </span>
        <div className="min-w-0 pr-8">
          <p className="text-sm font-semibold tracking-[0.08em] uppercase">Planna</p>
          <p className="truncate text-xs text-muted-foreground">{me.household.name}</p>
        </div>
      </div>

      <nav aria-label="Navegação principal" className="px-3">
        <ul className="flex list-none flex-col gap-1 p-0">
          {navigationItems.map((item) => {
            const Icon = item.icon;
            const active = activeView === item.id;
            return (
              <li key={item.id}>
                <Button
                  aria-current={active ? "page" : undefined}
                  className="w-full justify-start"
                  onClick={() => navigate(item.id)}
                  variant={active ? "secondary" : "ghost"}
                >
                  <Icon data-icon="inline-start" />
                  {item.label}
                </Button>
              </li>
            );
          })}
        </ul>
      </nav>

      <div className="mt-auto flex flex-col gap-3 p-4">
        <div className="rounded-xl bg-muted/60 p-3">
          <p className="text-xs font-medium text-foreground">
            {accounts.length ? `${accounts.length} ${accounts.length === 1 ? "conta conectada" : "contas conectadas"}` : "Nenhuma conta conectada"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">
            {lastSync ? `Atualizado em ${new Date(lastSync).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}` : "Conecte um banco para começar."}
          </p>
        </div>
        <Button disabled={syncing} onClick={connect}>
          <Landmark data-icon="inline-start" />
          Conectar instituição
        </Button>
        <Button disabled={syncing || !accounts.length} onClick={sync} variant="outline">
          <RefreshCw data-icon="inline-start" />
          {syncing ? "Sincronizando…" : "Atualizar dados"}
        </Button>
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <ThemeToggle />
            <Link
              className="inline-flex min-h-11 items-center rounded-lg px-3 text-sm text-muted-foreground hover:text-foreground focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-ring"
              href="/privacidade"
            >
              Privacidade
            </Link>
          </div>
          <Button disabled={pendingLogout} onClick={onLogout} variant="ghost">
            <LogOut data-icon="inline-start" />
            Sair
          </Button>
        </div>
      </div>
    </div>
  );

  return (
    <main className="min-h-svh bg-background md:grid md:grid-cols-[16rem_minmax(0,1fr)]">
      <aside className="sticky top-0 hidden h-svh border-r border-sidebar-border bg-sidebar text-sidebar-foreground md:flex">
        {navigation}
      </aside>

      <section className="min-w-0">
        <header className="sticky top-0 z-40 flex items-center gap-3 border-b border-border bg-background/95 px-4 py-3 backdrop-blur-sm md:static md:border-0 md:bg-transparent md:px-8 md:pt-8 md:pb-0 md:backdrop-blur-none lg:px-10">
          <div className="md:hidden">
            <Sheet onOpenChange={setMenuOpen} open={menuOpen}>
              <SheetTrigger render={<Button aria-label="Abrir menu" size="icon-lg" variant="ghost" />}>
                <Menu />
              </SheetTrigger>
              <SheetContent className="w-[min(20rem,88vw)] gap-0 p-0 md:hidden" side="left">
                <SheetHeader className="sr-only">
                  <SheetTitle>Menu principal</SheetTitle>
                  <SheetDescription>Navegue pelas áreas financeiras da casa.</SheetDescription>
                </SheetHeader>
                {navigation}
              </SheetContent>
            </Sheet>
          </div>
          <div className="min-w-0">
            <p className="text-xs font-semibold tracking-[0.08em] text-muted-foreground uppercase">
              Planna · {me.household.name}
            </p>
            <h1 className="truncate text-xl font-semibold tracking-[-0.025em] sm:text-2xl">
              {viewDetails[activeView].title}
            </h1>
          </div>
        </header>

        {connectToken && (
          <PluggyConnect
            connectToken={connectToken}
            includeSandbox={process.env.NODE_ENV !== "production"}
            onClose={() => setConnectToken("")}
            onError={() => {
              setConnectToken("");
              setError("A conexão não foi concluída. Se a instituição já estiver conectada, use Atualizar dados.");
            }}
            onSuccess={connected}
          />
        )}

        <div className="mx-auto flex w-full max-w-[90rem] flex-col gap-6 px-4 py-6 sm:px-8 md:pt-5 lg:px-10 lg:pb-10">
          <div className="flex flex-col gap-1">
            <p className="max-w-[65ch] text-sm text-muted-foreground">
              {viewDetails[activeView].description}
            </p>
          </div>

          {(activeView === "overview" || activeView === "transactions") && (
            <Card size="sm">
              <CardContent className="flex flex-wrap items-end gap-3">
                <Field className="min-w-44 flex-1 sm:max-w-52">
                  <FieldLabel htmlFor="period">Período</FieldLabel>
                  <select className={selectClass} id="period" onChange={(event) => choosePreset(event.target.value as Preset)} value={preset}>
                    <option value="month">Este mês</option>
                    <option value="quarter">Este trimestre</option>
                    <option value="year">Este ano</option>
                    <option value="custom">Personalizado</option>
                  </select>
                </Field>
                {preset === "custom" && <>
                  <Field className="min-w-40 flex-1 sm:max-w-48"><FieldLabel htmlFor="date-from">De</FieldLabel><Input id="date-from" max={to} onChange={(event) => setFrom(event.target.value)} type="date" value={from} /></Field>
                  <Field className="min-w-40 flex-1 sm:max-w-48"><FieldLabel htmlFor="date-to">Até</FieldLabel><Input id="date-to" min={from} onChange={(event) => setTo(event.target.value)} type="date" value={to} /></Field>
                </>}
              </CardContent>
            </Card>
          )}

          {error && <p aria-live="polite" className="rounded-2xl bg-destructive/10 px-4 py-3 text-sm text-destructive">{error}</p>}

          {(activeView === "overview" || activeView === "transactions") && (loading || !kpis) ? (
            <Card><CardHeader><CardTitle>Organizando seus números…</CardTitle><CardDescription>Receitas, despesas e contas estão sendo consolidadas.</CardDescription></CardHeader></Card>
          ) : null}

          {activeView === "accounts" && loading && (
            <Card aria-live="polite">
              <CardHeader>
                <CardTitle>Buscando contas conectadas…</CardTitle>
                <CardDescription>Saldos, faturas e sincronizações estão sendo organizados.</CardDescription>
              </CardHeader>
            </Card>
          )}

          {activeView === "accounts" && !loading && !error && (
            <Card>
              <CardHeader className="gap-4 sm:grid-cols-[1fr_auto]">
                <div className="flex flex-col gap-1.5">
                  <CardTitle>
                    {accounts.length} {accounts.length === 1 ? "conta compartilhada" : "contas compartilhadas"}
                  </CardTitle>
                  <CardDescription>
                    {lastSync
                      ? `Última atualização em ${new Date(lastSync).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })}.`
                      : "Conecte uma instituição para reunir a vida financeira da casa."}
                  </CardDescription>
                </div>
                <div className="flex flex-wrap gap-2 sm:justify-end">
                  <Button disabled={syncing} onClick={connect}>
                    <Landmark data-icon="inline-start" />
                    Conectar instituição
                  </Button>
                  <Button disabled={syncing || !accounts.length} onClick={sync} variant="outline">
                    <RefreshCw data-icon="inline-start" />
                    {syncing ? "Sincronizando…" : "Atualizar contas"}
                  </Button>
                </div>
              </CardHeader>

              {accounts.length ? (
                <CardContent className="px-0">
                  <div className="hidden grid-cols-[minmax(0,1.5fr)_minmax(9rem,0.6fr)_minmax(10rem,0.7fr)_minmax(10rem,auto)] gap-4 border-b border-border/70 px-5 pb-3 text-xs font-medium text-muted-foreground md:grid">
                    <span>Instituição e conta</span>
                    <span>Titular</span>
                    <span>Sincronização</span>
                    <span className="text-right">Saldo ou fatura</span>
                  </div>
                  <ul className="list-none p-0">
                    {accounts.map((item) => (
                      <li
                        className="grid gap-4 border-b border-border/70 px-5 py-5 last:border-b-0 md:grid-cols-[minmax(0,1.5fr)_minmax(9rem,0.6fr)_minmax(10rem,0.7fr)_minmax(10rem,auto)] md:items-center"
                        key={item.id}
                      >
                        <div className="flex min-w-0 items-start gap-3">
                          <span className="grid size-11 shrink-0 place-items-center rounded-full bg-muted text-muted-foreground">
                            <Landmark className="size-5" aria-hidden="true" />
                          </span>
                          <div className="min-w-0">
                            <p className="truncate font-semibold">{item.name.trim()}</p>
                            <div className="mt-1 flex flex-wrap items-center gap-2">
                              <span className="text-xs text-muted-foreground">{item.institution_name}</span>
                              <Badge variant="outline">{accountTypeLabels[item.type]}</Badge>
                              {item.number_masked && (
                                <span className="text-xs text-muted-foreground tabular-nums">
                                  {item.type === "credit" ? "Final" : "Conta"} {item.number_masked}
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                        <p className="flex items-center gap-2 text-sm">
                          <UsersRound className="size-4 text-muted-foreground" aria-hidden="true" />
                          {item.member_name}
                        </p>
                        <div>
                          <p className="text-sm">
                            {item.last_synced_at
                              ? new Date(item.last_synced_at).toLocaleString("pt-BR", { dateStyle: "short", timeStyle: "short" })
                              : "Aguardando atualização"}
                          </p>
                          <p className="mt-1 text-xs text-muted-foreground">
                            {item.last_synced_at ? "Dados sincronizados" : "Dados ainda não recebidos"}
                          </p>
                        </div>
                        <div className="md:text-right">
                          <p className="text-xs text-muted-foreground md:hidden">
                            {item.type === "credit" ? "Fatura atual" : "Saldo atual"}
                          </p>
                          <p className="text-lg font-semibold tracking-[-0.02em] tabular-nums">
                            {accountMoney(item.balance, item.currency)}
                          </p>
                          {item.type === "credit" && item.credit_limit !== null && (
                            <p className="mt-1 text-xs text-muted-foreground tabular-nums">
                              Limite {accountMoney(item.credit_limit, item.currency)}
                            </p>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              ) : (
                <CardContent className="flex flex-col items-center gap-4 py-12 text-center">
                  <span className="grid size-14 place-items-center rounded-full bg-muted text-muted-foreground">
                    <Landmark className="size-6" aria-hidden="true" />
                  </span>
                  <div className="flex max-w-md flex-col gap-1">
                    <p className="font-semibold">Nenhuma conta conectada</p>
                    <p className="text-sm text-muted-foreground">
                      Conecte uma instituição para trazer saldos e movimentações para a visão da casa.
                    </p>
                  </div>
                  <Button onClick={connect}>
                    <Landmark data-icon="inline-start" />
                    Conectar primeira instituição
                  </Button>
                </CardContent>
              )}
            </Card>
          )}

          {activeView === "overview" && kpis && (
            <>
              <section aria-label="Resumo financeiro">
                <Card className="border-primary bg-primary text-primary-foreground">
                  <CardHeader>
                    <div className="flex items-center justify-between gap-4">
                      <CardDescription className="text-primary-foreground">Patrimônio da casa</CardDescription>
                      <span className="grid size-10 place-items-center rounded-full bg-primary-foreground/12"><House className="size-5" aria-hidden="true" /></span>
                    </div>
                    <CardTitle className="text-4xl font-semibold tracking-[-0.045em] tabular-nums sm:text-5xl">
                      {money.format(Number(kpis.net_worth.value))}
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="mt-auto grid gap-4 border-t border-primary-foreground/15 pt-5 sm:grid-cols-2">
                    <div>
                      <p className="text-xs text-primary-foreground">Contas conectadas</p>
                      <p className="mt-1 font-semibold tabular-nums">{accounts.length}</p>
                    </div>
                    <div>
                      <p className="flex items-center gap-1.5 text-xs text-primary-foreground"><UsersRound className="size-3.5" aria-hidden="true" />Compartilhado com</p>
                      <p className="mt-1 truncate font-semibold">{me.household.members.map((item) => item.name).join(" · ")}</p>
                    </div>
                  </CardContent>
                </Card>
              </section>

              <section className="grid gap-4 sm:grid-cols-3" aria-label="Indicadores financeiros">
                <KpiCard data={kpis.income} label="Receita" />
                <KpiCard data={kpis.expense} expense label="Despesa" />
                <KpiCard data={kpis.balance} label="Saldo do período" />
              </section>

              {installments && Number(installments.total_remaining) > 0 && (
                <Card>
                  <CardHeader>
                    <CardTitle>Parcelas futuras</CardTitle>
                    <CardDescription>Compromissos de cartão ainda não pagos.</CardDescription>
                  </CardHeader>
                  <CardContent className="grid gap-4 sm:grid-cols-2">
                    <div><p className="text-xs text-muted-foreground">Total restante</p><p className="mt-1 text-2xl font-semibold tabular-nums">{money.format(Number(installments.total_remaining))}</p></div>
                    <div><p className="text-xs text-muted-foreground">Próxima fatura</p><p className="mt-1 text-2xl font-semibold tabular-nums">{money.format(Number(installments.monthly_installment_burden))}</p></div>
                  </CardContent>
                </Card>
              )}

              <section className="grid gap-5 xl:grid-cols-[1.6fr_1fr]">
                <Card><CardHeader><CardTitle>Tendência em 12 meses</CardTitle><CardDescription>Receitas e despesas reconhecidas nas contas conectadas.</CardDescription></CardHeader><CardContent><TrendChart values={trends} /></CardContent></Card>
                <Card><CardHeader><CardTitle>Para onde foi o dinheiro</CardTitle><CardDescription>Despesas por categoria no período.</CardDescription></CardHeader><CardContent><ExpenseChart values={expenses} /></CardContent></Card>
              </section>
            </>
          )}

          {activeView === "transactions" && !loading && kpis && (
            <Card>
              <CardHeader>
                <CardTitle>Extrato da casa</CardTitle>
                <CardDescription>Use a busca e os filtros para encontrar uma movimentação.</CardDescription>
              </CardHeader>
              <CardContent className="flex flex-col gap-5 px-0">
                <form className="flex gap-2 px-5" onSubmit={applySearch}>
                  <Input aria-label="Buscar movimentação" onChange={(event) => setSearch(event.target.value)} placeholder="Descrição ou estabelecimento" value={search} />
                  <Button aria-label="Buscar" size="icon-lg" type="submit" variant="outline"><Search /></Button>
                </form>
                <div className="grid gap-3 px-5 sm:grid-cols-2 xl:grid-cols-4">
                  <select aria-label="Filtrar por conta" className={selectClass} onChange={(event) => setAccount(event.target.value)} value={account}><option value="">Todas as contas</option>{accounts.map((item) => <option key={item.id} value={item.id}>{item.institution_name} · {item.name}</option>)}</select>
                  <select aria-label="Filtrar por membro" className={selectClass} onChange={(event) => setMember(event.target.value)} value={member}><option value="">Todos os membros</option>{me.household.members.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
                  <select aria-label="Filtrar por categoria" className={selectClass} onChange={(event) => setCategory(event.target.value)} value={category}><option value="">Todas as categorias</option>{categories.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select>
                  <select aria-label="Filtrar por tipo" className={selectClass} onChange={(event) => setType(event.target.value)} value={type}><option value="">Receitas e despesas</option><option value="credit">Receitas</option><option value="debit">Despesas</option></select>
                </div>
                <Separator />
                {transactions.length ? (
                  <div>
                    <div className="hidden grid-cols-[minmax(0,1fr)_12rem_14rem_8rem] gap-4 border-b border-border/70 px-5 pb-3 text-xs font-medium text-muted-foreground md:grid">
                      <span>Movimentação</span><span>Categoria</span><span>Conta</span><span className="text-right">Valor</span>
                    </div>
                    <ul className="list-none p-0">{transactions.map((item) => {
                      const expanded = expandedTransaction === item.id;
                      return (
                        <li className="grid gap-4 border-b border-border/70 px-5 py-4 last:border-b-0 md:grid-cols-[minmax(0,1fr)_12rem_14rem_8rem] md:items-center" key={item.id}>
                          <div className="min-w-0">
                            <button
                              aria-expanded={item.invoice_id ? expanded : undefined}
                              className="flex min-h-11 w-full items-center gap-2 text-left"
                              disabled={!item.invoice_id}
                              onClick={() => item.invoice_id && setExpandedTransaction(expanded ? "" : item.id)}
                              type="button"
                            >
                              <span className="min-w-0 flex-1">
                                <span className="flex flex-wrap items-center gap-2">
                                  {item.invoice_id && (expanded ? <ChevronUp className="size-4 shrink-0" aria-hidden="true" /> : <ChevronDown className="size-4 shrink-0" aria-hidden="true" />)}
                                  <span className="truncate font-medium">{item.merchant_name || item.description}</span>
                                  {item.source === "voucher" && <Badge variant="secondary">Vale-alimentação</Badge>}
                                </span>
                                <span className="block truncate text-xs text-muted-foreground">{shortDate.format(new Date(item.date))} · {item.member_name}{item.installment_total ? ` · ${item.installment_current}/${item.installment_total}` : ""}{item.status === "pending" ? " · Pendente" : ""}</span>
                              </span>
                            </button>
                          </div>
                          <select aria-label={`Categoria de ${item.description}`} className="h-10 min-w-0 w-full rounded-xl border border-border bg-input/45 pl-3 pr-8 text-xs outline-none focus:border-ring focus:ring-3 focus:ring-ring/20" onChange={(event) => void changeCategory(item.id, event.target.value)} value={item.category_id ?? ""}><option value="">Sem categoria</option>{categories.filter((candidate) => candidate.kind === (item.type === "debit" ? "expense" : "income")).map((candidate) => <option key={candidate.id} value={candidate.id}>{candidate.name}</option>)}</select>
                          <p className="truncate text-sm text-muted-foreground">{item.account_name}</p>
                          <p className={cn("text-right font-semibold tabular-nums", item.type === "credit" && "text-primary")}>{money.format(Number(item.amount))}</p>
                          {expanded && (
                            <div className="rounded-2xl bg-muted/70 p-4 md:col-span-4">
                              <p className="mb-3 text-xs font-semibold tracking-[0.08em] text-muted-foreground uppercase">Itens da nota</p>
                              <ul className="grid list-none gap-2 p-0 sm:grid-cols-2">
                                {item.invoice_items.map((invoiceItem) => (
                                  <li className="grid grid-cols-[1fr_auto] gap-3 text-sm" key={invoiceItem.id}>
                                    <span>{invoiceItem.description} · {Number(invoiceItem.quantity).toLocaleString("pt-BR")} {invoiceItem.unit ?? "un."}</span>
                                    <span className="tabular-nums">{money.format(Number(invoiceItem.total_price))}</span>
                                  </li>
                                ))}
                              </ul>
                            </div>
                          )}
                        </li>
                      );})}
                    </ul>
                  </div>
                ) : (
                  <div className="flex flex-col items-center gap-3 py-12 text-center"><WalletCards className="size-8 text-muted-foreground" aria-hidden="true" /><p className="font-medium">Nenhuma movimentação encontrada</p><p className="max-w-md text-sm text-muted-foreground">Conecte uma instituição ou ajuste os filtros para ver o extrato da casa.</p></div>
                )}
                {nextCursor && <Button className="self-center" onClick={() => void loadMore()} variant="outline">Carregar mais</Button>}
              </CardContent>
            </Card>
          )}

          {activeView === "wealth" && (
            <WealthPanel members={me.household.members} onChanged={load} refreshKey={lastSync ?? ""} />
          )}

          {activeView === "insights" && <InsightsPanel />}

          {activeView === "invoices" && (
            <div className="max-w-2xl">
              <InvoiceCapture onIngest={ingestInvoice} />
            </div>
          )}
        </div>
      </section>
    </main>
  );
}
