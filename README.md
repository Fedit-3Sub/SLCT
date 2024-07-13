# KT-BPMN

curl -fsSL https://fnm.vercel.app/install | bash
fnm use --install-if-missing 20
corepack enable

cd frontend
pnpm i
pnpm dev

cd backend
npm run dev
