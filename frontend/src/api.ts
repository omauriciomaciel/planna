export async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { credentials: "include", ...init });
  if (!response.ok) {
    const body = await response.text();
    try {
      const detail = JSON.parse(body).detail;
      throw new Error(
        typeof detail === "string"
          ? detail
          : detail?.[0]?.msg || "Não foi possível concluir a solicitação.",
      );
    } catch (error) {
      if (error instanceof SyntaxError) {
        throw new Error("Não foi possível concluir a solicitação.");
      }
      throw error;
    }
  }
  return response.json();
}
