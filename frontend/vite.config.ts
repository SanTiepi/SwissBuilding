/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { VitePWA } from 'vite-plugin-pwa';
import path from 'path';

const apiProxyTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000';

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      manifest: {
        name: 'SwissBuildingOS',
        short_name: 'SBO',
        description: 'Swiss National Building Intelligence Platform',
        theme_color: '#dc2626',
        background_color: '#f8fafc',
        display: 'standalone',
        icons: [
          {
            src: '/icon.svg',
            sizes: 'any',
            type: 'image/svg+xml',
          },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,ico,png,svg,woff2}'],
        cleanupOutdatedCaches: true,
        navigateFallback: '/index.html',
        navigateFallbackDenylist: [/^\/api\//],
        runtimeCaching: [
          {
            urlPattern: /^\/api\//,
            handler: 'NetworkFirst',
            options: {
              cacheName: 'api-cache',
              networkTimeoutSeconds: 10,
              expiration: {
                maxEntries: 200,
                maxAgeSeconds: 24 * 60 * 60,
              },
              cacheableResponse: {
                statuses: [0, 200],
              },
            },
          },
        ],
      },
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: apiProxyTarget,
        changeOrigin: true,
        secure: false,
      },
    },
  },
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test/setup.ts',
    css: true,
    fileParallelism: false,
    exclude: ['e2e/**', 'e2e-real/**', 'node_modules/**'],
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // i18n strings (~500 kB raw across 4 langs) are statically imported in main —
    // the index chunk legitimately exceeds 500 kB after minification.
    chunkSizeWarningLimit: 650,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom', 'react-router-dom'],
          query: ['@tanstack/react-query'],
          // Note: mapbox-gl removed — it is only dynamically imported via lazy pages,
          // so the manual chunk was always empty (0 kB).
          // recharts is NOT listed here on purpose: it is only imported from lazy
          // components (DashboardCharts, PortfolioCharts, RiskSimulator) and Rollup
          // already isolates it into its own chunk automatically.
        },
      },
    },
  },
});
