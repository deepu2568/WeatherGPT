import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import { VitePWA } from "vite-plugin-pwa";

export default defineConfig({
  plugins: [
    react(),

    VitePWA({
      registerType: "autoUpdate",

      devOptions: {
        enabled: true,
      },

      manifest: {
        name: "WeatherGPT",
        short_name: "WeatherGPT",
        description: "Your AI Weather Assistant",
        theme_color: "#0b1020",
        background_color: "#0b1020",
        display: "standalone",
        start_url: "/",

        icons: [
          {
            src: "/weather-icon-192.png",
            sizes: "192x192",
            type: "image/png",
          },
          {
            src: "/weather-icon-512.png",
            sizes: "512x512",
            type: "image/png",
          },
        ],
      },
    }),
  ],
});