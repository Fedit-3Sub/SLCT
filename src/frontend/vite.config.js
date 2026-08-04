import path from 'node:path'
import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue2'
import Components from 'unplugin-vue-components/vite'
import Icons from 'unplugin-icons/vite'
import IconsResolver from 'unplugin-icons/resolver'
import AutoImport from 'unplugin-auto-import/vite'
import svgr from 'vite-plugin-svgr';
import react from '@vitejs/plugin-react'
import svgLoader from 'vite-svg-loader'

// .env 파일 값을 먼저 깔고, 실제 프로세스 환경변수로 덮어쓴다.
// (컨테이너/쿠버네티스 배포에서 주입한 VITE_PROXY_URL 이 이미지에 포함된 .env 보다 우선해야 함)
process.env = { ...loadEnv('development', process.cwd()), ...process.env };

// 개발 환경에서 백엔드 프록시 기본값을 안전하게 지정합니다.
// VITE_PROXY_URL 미설정 시 Django 백엔드 기본 포트(1337)로 프록시합니다.
const backendTarget = process.env.VITE_PROXY_URL || 'http://localhost:1337';

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
          // Restrict to MDI to avoid mis-resolving normal components like <Label> to `la/bel`
          enabledCollections: ['mdi'],
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
    port: 9900,
    proxy: {
      '/': {
        target: backendTarget,
        changeOrigin: true,
        rewrite: (path) => path,
        secure: false,
        ws: false,
        bypass: (req) => {
          if(req.url.match(/^\/$/)) {
            return "/default";
          }
          if(req.url.match(/^\/[^/]+$/) || req.url.match(/^\/@/) || req.url.match(/^\/src\//) || req.url.match(/^\/node_modules\//)) {
            //console.log('match', req.url)
            return req.url
          }
          //console.log('notmatch', req.url)
          return null
        }
      }
    }
},
})

export default config
