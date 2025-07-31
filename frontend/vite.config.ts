import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    
    host: true,
    proxy: {
     '/assistant/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },'/health': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },'/assistant/resume': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      }
    },
  },
});