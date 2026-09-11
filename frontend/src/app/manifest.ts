import type { MetadataRoute } from "next";

export default function manifest(): MetadataRoute.Manifest {
  return {
    name: "Planna — contas da casa",
    short_name: "Planna",
    description: "Painel financeiro doméstico compartilhado.",
    start_url: "/",
    display: "standalone",
    background_color: "#f6f3eb",
    theme_color: "#f6f3eb",
    icons: [
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "any",
      },
      {
        src: "/icon.svg",
        sizes: "any",
        type: "image/svg+xml",
        purpose: "maskable",
      },
    ],
  };
}
