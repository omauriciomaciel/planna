"use client";

import { useEffect, useState } from "react";

export function clearPrivateOfflineData() {
  navigator.serviceWorker?.controller?.postMessage({ type: "CLEAR_PRIVATE_DATA" });
}

export function PwaRegistration() {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const updateStatus = () => setOffline(!navigator.onLine);
    updateStatus();
    window.addEventListener("online", updateStatus);
    window.addEventListener("offline", updateStatus);
    if ("serviceWorker" in navigator) {
      void navigator.serviceWorker
        .register("/sw.js", { scope: "/", updateViaCache: "none" })
        .catch(() => undefined);
    }
    return () => {
      window.removeEventListener("online", updateStatus);
      window.removeEventListener("offline", updateStatus);
    };
  }, []);

  return offline ? (
    <p
      aria-live="polite"
      className="fixed inset-x-4 bottom-4 z-50 mx-auto max-w-md rounded-xl border border-border bg-card px-4 py-3 text-center text-sm font-medium text-card-foreground"
      role="status"
    >
      Sem conexão — exibindo os últimos dados salvos neste aparelho.
    </p>
  ) : null;
}
