# Chat UI

The Next.js front end for the RAG service. Design: [contract-chat-ui.md](../docs/design/contract-chat-ui.md); API side:
[chat-ui-api.md](../docs/contracts/chat-ui-api.md).

Start the service from the repo root, then the UI from here:

```
uv run uvicorn rag.api:app --host 127.0.0.1 --port 8000
npm install
npm run dev -- -p 3100
```

Server settings go in `web/.env.local` (never committed): `RAG_API_URL` (default `http://127.0.0.1:8000`) and
`RAG_API_KEY` (the service's `API_KEY`, when it has one). The browser only calls this app's `/api` routes, so the key
stays on the server.

In development, `/?fixture=answer|thread|refusal|loading|error|busy|offline|library|history` shows a recorded state
(dev-set eval answers) without the service. Production builds ignore it.
