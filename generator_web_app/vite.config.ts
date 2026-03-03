import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import vueDevTools from 'vite-plugin-vue-devtools'
import Components from 'unplugin-vue-components/vite'
import { BootstrapVueNextResolver } from 'bootstrap-vue-next/resolvers'

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),
    vueDevTools(),
    Components({
      resolvers: [BootstrapVueNextResolver()]
    })
  ],
  optimizeDeps: {
    include: [
      'bootstrap-vue-next/components/**/*' ,
      '@vueuse/core'
    ]
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    },
  },
  build: {
    target: 'esnext'
  },
  server: {
    allowedHosts: ['pronghorn-count-dev.arcc.uwyo.edu', 'annotation_software_web-app-dev_1', '127.0.0.1:5173']
  }
})
