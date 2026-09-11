"use client";

import { ChangeEvent, FormEvent, useState } from "react";
import { Camera, ReceiptText } from "lucide-react";

import { Badge } from "@/components/ui/badge";
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
  FieldError,
  FieldGroup,
  FieldLabel,
} from "@/components/ui/field";
import { Input } from "@/components/ui/input";

type Invoice = {
  id: string;
  merchant_name: string;
  issue_datetime: string;
  total_amount: string;
  payment_status: "reconciled" | "voucher";
  needs_review: boolean;
  items: { id: string }[];
};

export type InvoiceIngestResult = { invoice: Invoice; created: boolean };

type BarcodeDetectorInstance = {
  detect(source: ImageBitmap): Promise<{ rawValue: string }[]>;
};

type BarcodeDetectorConstructor = new (options: {
  formats: string[];
}) => BarcodeDetectorInstance;

const money = new Intl.NumberFormat("pt-BR", { style: "currency", currency: "BRL" });

export function InvoiceCapture({
  onIngest,
}: {
  onIngest: (url: string) => Promise<InvoiceIngestResult>;
}) {
  const [url, setUrl] = useState("");
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [result, setResult] = useState<InvoiceIngestResult | null>(null);

  async function readQrCode(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setMessage("");
    try {
      const Detector = (window as unknown as { BarcodeDetector?: BarcodeDetectorConstructor })
        .BarcodeDetector;
      if (!Detector) throw new Error("unsupported");
      const image = await createImageBitmap(file);
      const codes = await new Detector({ formats: ["qr_code"] }).detect(image);
      image.close();
      if (!codes[0]?.rawValue) throw new Error("not-found");
      setUrl(codes[0].rawValue);
    } catch {
      setMessage("Não foi possível ler a foto. Cole o link completo da NFC-e.");
    } finally {
      event.target.value = "";
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPending(true);
    setMessage("");
    setResult(null);
    try {
      const nextResult = await onIngest(url.trim());
      setResult(nextResult);
      setUrl("");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Não foi possível importar a nota.");
    } finally {
      setPending(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Adicionar nota fiscal</CardTitle>
        <CardDescription>
          O Planna cruza valor e data com o banco; sem correspondência, registra a compra como vale.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-5">
        <form onSubmit={submit}>
          <FieldGroup>
            <Field data-invalid={!!message || undefined}>
              <FieldLabel htmlFor="invoice-url">Link ou conteúdo do QR code</FieldLabel>
              <Input
                aria-invalid={!!message || undefined}
                autoComplete="off"
                id="invoice-url"
                onChange={(event) => setUrl(event.target.value)}
                placeholder="https://nfce.sefaz.al.gov.br/…"
                required
                type="text"
                value={url}
              />
              <FieldDescription>Apenas notas emitidas pela SEFAZ de Alagoas.</FieldDescription>
              <FieldError>{message}</FieldError>
            </Field>
            <Field>
              <FieldLabel htmlFor="invoice-qr">
                <Camera aria-hidden="true" />
                Fotografar QR code
              </FieldLabel>
              <Input
                accept="image/*"
                capture="environment"
                id="invoice-qr"
                onChange={readQrCode}
                type="file"
              />
              <FieldDescription>
                Se o navegador não reconhecer a imagem, use o campo acima.
              </FieldDescription>
            </Field>
            <Button disabled={pending || !url.trim()} type="submit">
              <ReceiptText data-icon="inline-start" />
              {pending ? "Consultando a SEFAZ…" : "Importar nota"}
            </Button>
          </FieldGroup>
        </form>

        {result && (
          <div aria-live="polite" className="flex flex-col gap-2 rounded-lg bg-muted/60 p-4">
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-medium">{result.invoice.merchant_name}</p>
              <Badge variant={result.invoice.payment_status === "voucher" ? "secondary" : "outline"}>
                {result.invoice.needs_review
                  ? "Revisar correspondência"
                  : result.invoice.payment_status === "voucher"
                    ? "Vale-alimentação"
                    : "Conciliada"}
              </Badge>
            </div>
            <p className="text-sm text-muted-foreground">
              {money.format(Number(result.invoice.total_amount))} · {result.invoice.items.length} itens · {result.created ? "nota adicionada" : "nota já cadastrada"}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
