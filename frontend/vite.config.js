import path from 'node:path'
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue2'
import Components from 'unplugin-vue-components/vite'
import Icons from 'unplugin-icons/vite'
import IconsResolver from 'unplugin-icons/resolver'
import AutoImport from 'unplugin-auto-import/vite'
import svgr from 'vite-plugin-svgr';
import react from '@vitejs/plugin-react'
import svgLoader from 'vite-svg-loader'

const config = defineConfig({
  resolve: {
    alias: {
      '@': `${path.resolve(__dirname, 'src')}`,
      'bpmn-js/lib': `${path.resolve(__dirname, 'src', 'lib', 'bpmn-js')}`,
      "@bpmn-io/properties-panel": `${path.resolve(__dirname, 'src', 'lib', 'bpmn-properties-panel')}`,
      "bpmn-js-properties-panel": `${path.resolve(__dirname, 'src', 'lib', 'bpmn-js-properties-panel')}`,
    },
  },
  build: {
    minify: true,
  },
  plugins: [
    react({ jsxRuntime: 'classic' }),
    vue(),
    Components({
      resolvers: [
        IconsResolver({
          componentPrefix: '',
        }),
      ],
      dts: 'src/components.d.ts',
    }),
    Icons(),
    AutoImport({
      imports: [
        '@vueuse/core',
      ],
      dts: 'src/auto-imports.d.ts',
    }),
    svgr({include: "**/*.svg", exclude: ["src/lib/bpmn-js-token-simulation/**/*.svg"]}),
    svgLoader(),
  ],

  server: {
    port: 3333,
  },
})

export default config
