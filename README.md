# KT-BPMN

##

curl -fsSL https://fnm.vercel.app/install | bash
fnm use --install-if-missing 20
corepack enable

##
pip install -r ./processor/requirements.txt

##

cd frontend
pnpm i
pnpm dev

cd backend
npm run develop

cd processor
python3 main.py
