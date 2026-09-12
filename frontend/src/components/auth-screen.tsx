"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Field,
  FieldDescription,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Dashboard } from "@/components/dashboard";
import { clearPrivateOfflineData } from "@/components/pwa-registration";
import { ThemeToggle } from "@/components/theme-toggle";

type Member = {
  id: string;
  name: string;
  email: string;
  role: "owner" | "member";
};

type Me = {
  id: string;
  name: string;
  email: string;
  household: {
    id: string;
    name: string;
    members: Member[];
  };
};

type View = "checking" | "guest" | "requested" | "authenticated" | "error";

export function AuthScreen() {
  const [view, setView] = useState<View>("checking");
  const [me, setMe] = useState<Me | null>(null);
  const [pending, setPending] = useState(false);
  const [devLink, setDevLink] = useState("");

  useEffect(() => {
    let active = true;
    fetch("/api/auth/me", { credentials: "include" })
      .then(async (response) => {
        if (!active) return;
        if (response.status === 401) {
          setView("guest");
          return;
        }
        if (!response.ok) throw new Error("session");
        setMe(await response.json());
        setView("authenticated");
      })
      .catch(() => active && setView("error"));
    return () => {
      active = false;
    };
  }, []);

  async function requestLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    const form = new FormData(event.currentTarget);
    try {
      const response = await fetch("/api/auth/magic-link", {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: form.get("email"),
          privacy_accepted: form.get("privacy") === "on",
          ai_consent: form.get("ai-consent") === "on",
        }),
      });
      if (!response.ok) throw new Error("magic-link");
      const data = (await response.json()) as { dev_link?: string | null };
      setDevLink(data.dev_link ?? "");
      setView("requested");
    } catch {
      setView("error");
    } finally {
      setPending(false);
    }
  }

  async function logout() {
    setPending(true);
    try {
      const response = await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
      if (!response.ok) throw new Error("logout");
      clearPrivateOfflineData();
      setMe(null);
      setView("guest");
    } catch {
      setView("error");
    } finally {
      setPending(false);
    }
  }

  if (view === "checking") {
    return (
      <main className="flex min-h-svh items-center justify-center bg-background px-4 py-12">
        <ThemeToggle className="absolute top-4 right-4" />
        <Card aria-live="polite" className="w-full max-w-sm">
          <CardHeader>
            <CardTitle>Verificando acesso</CardTitle>
            <CardDescription>Preparando sua visão financeira&hellip;</CardDescription>
          </CardHeader>
        </Card>
      </main>
    );
  }

  if (view === "authenticated" && me) {
    return <Dashboard me={me} onLogout={logout} pendingLogout={pending} />;
  }

  return (
    <main className="relative grid min-h-svh bg-card lg:grid-cols-[1.1fr_0.9fr]">
      <ThemeToggle className="absolute top-4 right-4 z-10" />
      <section className="relative hidden overflow-hidden bg-primary p-12 text-primary-foreground lg:flex lg:flex-col lg:justify-between xl:p-16">
        <div className="flex items-center gap-3 text-sm font-semibold tracking-[0.08em] uppercase">
          <span className="grid size-10 place-items-center rounded-full bg-primary-foreground text-lg font-bold text-primary">P</span>
          Planna
        </div>
        <div className="flex max-w-xl flex-col gap-5">
          <p className="text-sm font-semibold tracking-[0.08em] text-primary-foreground uppercase">Finanças da casa</p>
          <h2 className="text-balance text-5xl leading-[1.04] font-semibold tracking-[-0.04em] xl:text-6xl">
            A vida financeira de vocês, em uma só visão.
          </h2>
          <p className="max-w-[52ch] text-pretty text-lg leading-[1.45] text-primary-foreground">
            Contas, notas fiscais e decisões compartilhadas, sem perder o fio da meada.
          </p>
        </div>
        <p className="text-sm text-primary-foreground">Seguro, simples e feito para a rotina.</p>
      </section>

      <section className="flex items-center justify-center px-5 py-10 sm:px-10">
        <div className="flex w-full max-w-md flex-col gap-10">
          <div className="flex items-center gap-3 lg:hidden">
            <span className="grid size-11 place-items-center rounded-full bg-primary text-lg font-bold text-primary-foreground">P</span>
            <span className="text-sm font-semibold tracking-[0.08em] uppercase">Planna</span>
          </div>

          <div className="flex flex-col gap-3">
            <p className="text-sm font-semibold tracking-[0.08em] text-primary uppercase dark:text-foreground">Bem-vindos</p>
            <h1 className="text-3xl leading-[1.12] font-semibold tracking-[-0.035em]">
              {view === "requested" ? "Confira seu e-mail" : "Acesse a conta da casa"}
            </h1>
            <p className="max-w-[46ch] text-pretty text-base leading-[1.45] text-muted-foreground">
              {view === "requested"
                ? "Enviamos um link de acesso, se este endereço estiver autorizado."
                : "Use um dos e-mails previamente cadastrados para o casal."}
            </p>
          </div>

          <Card aria-live="polite" className="border-0 shadow-none sm:border sm:shadow-[0_12px_32px_rgba(24,24,35,0.05)] sm:dark:shadow-none">
            <CardHeader className="sr-only">
              <CardTitle>{view === "requested" ? "Link enviado" : "Entrar"}</CardTitle>
              <CardDescription>Autenticação do Planna</CardDescription>
            </CardHeader>
            <CardContent>
              {view === "requested" ? (
                <div className="flex flex-col gap-3">
                  {devLink && (
                    <Link
                      className="text-center text-sm font-medium text-foreground underline underline-offset-4"
                      href={devLink}
                    >
                      Abrir link de desenvolvimento
                    </Link>
                  )}
                  <Button className="w-full" onClick={() => setView("guest")} variant="outline">
                    Usar outro e-mail
                  </Button>
                </div>
              ) : (
                <form onSubmit={requestLink}>
                  <FieldGroup>
                    <Field data-invalid={view === "error" || undefined}>
                      <FieldLabel htmlFor="email">E-mail</FieldLabel>
                      <Input
                        aria-invalid={view === "error" || undefined}
                        autoComplete="email"
                        id="email"
                        name="email"
                        placeholder="voce@exemplo.com"
                        required
                        type="email"
                      />
                      <FieldDescription>
                        {view === "error"
                          ? "Não foi possível concluir agora. Tente novamente."
                          : "O link expira em 15 minutos e só pode ser usado uma vez."}
                      </FieldDescription>
                    </Field>
                    <div className="flex items-start gap-3 text-sm leading-[1.4]">
                      <input
                        className="mt-0.5 size-4 shrink-0 accent-primary"
                        id="privacy"
                        name="privacy"
                        required
                        type="checkbox"
                      />
                      <label htmlFor="privacy">
                        Li o aviso de privacidade.{" "}
                        <Link
                          className="font-medium text-foreground underline underline-offset-4"
                          href="/privacidade"
                        >
                          Ver aviso
                        </Link>
                      </label>
                    </div>
                    <div className="flex items-start gap-3 text-sm leading-[1.4] text-muted-foreground">
                      <input
                        className="mt-0.5 size-4 shrink-0 accent-primary"
                        id="ai-consent"
                        name="ai-consent"
                        type="checkbox"
                      />
                      <label htmlFor="ai-consent">
                        Autorizo o envio de sinais financeiros resumidos à OpenAI. Sem esta
                        autorização, os insights continuam sendo calculados localmente.
                      </label>
                    </div>
                    <Button className="w-full" disabled={pending} type="submit">
                      {pending ? "Enviando…" : "Enviar link de acesso"}
                    </Button>
                  </FieldGroup>
                </form>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
