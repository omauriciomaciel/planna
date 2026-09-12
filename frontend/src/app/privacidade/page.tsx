import Link from "next/link";

import { buttonVariants } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export default function PrivacyPage() {
  return (
    <main className="min-h-svh bg-background px-4 py-12 sm:px-8">
      <article className="mx-auto flex max-w-3xl flex-col gap-6">
        <div className="flex flex-col gap-3">
          <p className="text-sm font-semibold tracking-[0.08em] text-foreground uppercase">
            Privacidade e IA
          </p>
          <h1 className="text-3xl font-semibold tracking-[-0.035em] sm:text-4xl">
            Como o Planna cuida dos dados da casa
          </h1>
          <p className="max-w-[65ch] text-muted-foreground">
            Aviso vigente desde 12 de setembro de 2026. O Planna trata dados financeiros apenas
            para organizar e analisar a vida financeira do household compartilhado.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Dados e finalidades</CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="flex list-disc flex-col gap-3 pl-5 text-sm leading-[1.45]">
              <li>Contas, transações, patrimônio e notas fiscais compõem o painel financeiro.</li>
              <li>E-mail e sessões servem somente para autenticação e controle de acesso.</li>
              <li>Logs operacionais não incluem e-mail, consultas ou valores financeiros.</li>
              <li>
                O aparelho guarda uma cópia offline dos dados já consultados. Sair da conta apaga
                essa cópia.
              </li>
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Uso opcional de IA</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm leading-[1.45]">
            <p>
              A OpenAI recebe somente sinais calculados e seu contexto mínimo, sem e-mail,
              credenciais, chave de nota fiscal ou número de conta. A solicitação à API não é
              armazenada pelo Planna.
            </p>
            <p>
              O envio externo só acontece quando todos os membros autorizam. Caso contrário, os
              mesmos sinais são produzidos pelo cálculo determinístico local.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Retenção e exclusão</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-col gap-3 text-sm leading-[1.45]">
            <p>
              Os dados permanecem enquanto o household estiver ativo. Tokens expirados e sessões
              encerradas são removidos automaticamente; backups diários expiram após 30 dias.
            </p>
            <p>
              Para corrigir, exportar ou excluir os dados, solicite ao administrador da instalação.
              A exclusão alcança a base principal imediatamente e os backups ao fim da retenção.
            </p>
          </CardContent>
        </Card>

        <Link className={buttonVariants({ className: "self-start", variant: "outline" })} href="/">
          Voltar ao Planna
        </Link>
      </article>
    </main>
  );
}
