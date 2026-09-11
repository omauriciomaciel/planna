"use client";

import { FormEvent, useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
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
      <Card aria-live="polite">
        <CardHeader>
          <CardTitle>Verificando acesso</CardTitle>
          <CardDescription>Um instante.</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  if (view === "authenticated" && me) {
    return (
      <Card>
        <CardHeader>
          <CardDescription>Household compartilhado</CardDescription>
          <CardTitle>{me.household.name}</CardTitle>
        </CardHeader>
        <CardContent>
          <ul className="flex list-none flex-col gap-3 p-0">
            {me.household.members.map((member) => (
              <li className="flex items-baseline justify-between gap-4" key={member.id}>
                <span className="font-medium">{member.name}</span>
                <span className="text-sm text-muted-foreground">
                  {member.role === "owner" ? "Responsável" : "Membro"}
                </span>
              </li>
            ))}
          </ul>
        </CardContent>
        <CardFooter>
          <Button disabled={pending} onClick={logout} variant="outline">
            Sair
          </Button>
        </CardFooter>
      </Card>
    );
  }

  return (
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
  );
}
