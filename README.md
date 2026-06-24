# uoma

> *uoma* (finlandês): leito/canal de rio — os fluxos pelos quais a água corre.
> Aqui, os fluxos de usuário que uma aplicação revela quando você a percorre.

Agente que **explora autonomamente uma app web sem documentação**, mapeia seus fluxos com um modelo de visão (UI-TARS), e **cristaliza** o que descobre em testes Playwright determinísticos — *characterization tests* pra blindar regressão.

> **Princípio:** o modelo atua só em *authoring-time* (explora e rascunha). O runtime dos testes é determinístico, **sem modelo no hot path**. Sem documentação não há oráculo de correção → o que se gera é golden master, não validação de correção.

## Arquitetura (host vs container)

No Apple Silicon o Docker roda em VM Linux **sem GPU**, então:

```
        HOST (Mac / Metal)                 CONTAINERS (Docker)
┌──────────────────────────────┐   ┌──────────────────────────────────┐
│ llama-server (UI-TARS) :8080  │◄──┤ harness  → Fase 2 (explora+gera)  │
│ UI-TARS-desktop (Fase 1)      │   │ e2e      → Fase 3 (replay/CI)     │
└──────────────────────────────┘   └──────────────────────────────────┘
        precisa de hardware          host.docker.internal:8080 → modelo
```

## Estrutura

```
uoma/
├── docker-compose.yml      # harness (authoring) + e2e (replay/CI)
├── playwright.config.ts    # config do replay (Fase 3)
├── .env.example            # copie p/ .env e preencha TARGET_URL
├── harness/
│   ├── Dockerfile          # base: Playwright Python
│   ├── requirements.txt
│   └── uoma/
│       └── explore.py      # SKELETON do loop Fase 2
├── artifacts/              # (gerado) flows.json, steps, screenshots
└── tests/                  # (gerado) *.spec.ts pro replay
```

## Como rodar

**1. Host — sobe o modelo (com GPU/Metal):**
```bash
brew install llama.cpp
llama-server -hf Mungert/UI-TARS-1.5-7B-GGUF:Q4_K_M \
  --mmproj <mmproj.gguf> --port 8080 -ngl 999
```

**2. Config:**
```bash
cp .env.example .env   # preencha TARGET_URL (+ login se precisar)
```

**3. Fase 2 — exploração (container fala com o modelo no host):**
```bash
docker compose run --rm harness                      # gera artifacts/steps.json
```

**4. Gera as specs a partir do que foi explorado:**
```bash
docker compose run --rm harness python -m uoma.gen   # gera tests/flow.spec.ts
```

**5. Fase 3 — replay determinístico (sem modelo, igual ao CI):**
```bash
docker compose --profile ci run --rm e2e
```

> **Smoke test / calibração:** no 1º run, abra `artifacts/steps.json` e confira se os
> cliques caíram nos elementos certos. Se errarem em bloco, troque `COORD_SPACE` no
> `.env` (`norm1000` ↔ `absolute`). Passos marcados `via: pixel` não viram spec
> determinístico — só os `via: selector`.

## Notas

- `host.docker.internal` faz o container alcançar o `llama-server` no host.
- Mac 24GB: limite a RAM da VM do Docker Desktop pra não brigar com o modelo (~6GB) no host.
- Fase 1 (UI-TARS-desktop) roda **no host**, fora do Docker — controla o desktop via SO.
- Produção/escala: mover o modelo pra host **Linux + NVIDIA** containeriza tudo (GPU passthrough); este desenho migra limpo.

## Licença

A definir.
