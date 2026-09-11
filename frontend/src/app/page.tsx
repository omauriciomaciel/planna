import { AuthScreen } from "@/components/auth-screen";

export default function Home() {
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
        <AuthScreen />
      </div>
    </main>
  );
}

