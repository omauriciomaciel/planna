"use client";

import { FormEvent, useEffect, useState } from "react";

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
        body: JSON.stringify({ email: form.get("email") }),
      });
      setView(response.ok ? "requested" : "error");
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
      <main className="flex min-h-svh items-center justify-center px-4 py-12">
        <Card aria-live="polite" className="w-full max-w-md">
          <CardHeader>
            <CardTitle>Verificando acesso</CardTitle>
            <CardDescription>Um instante.</CardDescription>
          </CardHeader>
        </Card>
      </main>
    );
  }

  if (view === "authenticated" && me) {
    return <Dashboard me={me} onLogout={logout} pendingLogout={pending} />;
  }

  return (
    <main className="flex min-h-svh items-center justify-center px-4 py-12 sm:px-8">
      <div className="grid w-full max-w-5xl items-center gap-12 lg:grid-cols-[1fr_26rem]">
        <section className="flex max-w-xl flex-col gap-6">
          <p className="text-sm font-medium tracking-[0.08em] text-muted-foreground uppercase">
            Planna · contas da casa
          </p>
          <h1 className="text-balance text-4xl leading-[1.12] font-semibold tracking-tight sm:text-5xl">
            A vida financeira do casal em um só lugar.
          </h1>
          <p className="max-w-[60ch] text-pretty text-base leading-[1.45] text-muted-foreground sm:text-lg">
            Banco + nota fiscal → uma visão compartilhada, simples e auditável.
          </p>
        </section>
        <Card aria-live="polite">
          <CardHeader>
            <CardTitle>{view === "requested" ? "Confira seu e-mail" : "Entrar"}</CardTitle>
            <CardDescription>
              {view === "requested"
                ? "Enviamos um link de acesso, se este endereço estiver autorizado."
                : "Use um dos e-mails previamente cadastrados para o casal."}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {view === "requested" ? (
              <Button onClick={() => setView("guest")} variant="outline">
                Usar outro e-mail
              </Button>
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
                  <Button disabled={pending} type="submit">
                    {pending ? "Enviando…" : "Enviar link de acesso"}
                  </Button>
                </FieldGroup>
              </form>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}
