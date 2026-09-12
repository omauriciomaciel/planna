"use client";

import { useSyncExternalStore } from "react";
import { Moon, Sun } from "lucide-react";
import { cn } from "cn";

import { Button } from "@/components/ui/button";

const themeEvent = "planna-theme-change";

function subscribe(callback: () => void) {
  window.addEventListener(themeEvent, callback);
  return () => window.removeEventListener(themeEvent, callback);
}

function isDark() {
  return document.documentElement.classList.contains("dark");
}

export function ThemeToggle({ className }: { className?: string }) {
  const dark = useSyncExternalStore(subscribe, isDark, () => false);
  const label = dark ? "Ativar tema claro" : "Ativar tema escuro";

  function toggleTheme() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    try {
      localStorage.setItem("planna-theme", next ? "dark" : "light");
    } catch {}
    window.dispatchEvent(new Event(themeEvent));
  }

  return (
    <Button
      aria-label={label}
      aria-pressed={dark}
      className={cn("size-11", className)}
      onClick={toggleTheme}
      size="icon-lg"
      title={label}
      variant="ghost"
    >
      {dark ? <Sun aria-hidden="true" /> : <Moon aria-hidden="true" />}
    </Button>
  );
}
