# Validação do repositório

Este arquivo registra os comandos usados para verificar o MVP e separa código
validado de integrações que exigem um processo externo.

## Checks automatizados

Executar na raiz, salvo indicação contrária:

```bash
cd backend
.venv/bin/ruff check app tests
.venv/bin/ruff format --check app tests
.venv/bin/pytest -q

cd ..
PYTHONPATH=. backend/.venv/bin/pytest -q agent/tests
backend/.venv/bin/python -m compileall -q backend/app agent
hermes plugins doctor ./agent --ci

cd frontend
npm run typecheck
npm run build
```

O backend cobre criação de receita/despesa, transferências com duas pernas,
saldo, orçamento, Decimal, timezone, isolamento de usuário, idempotência e
mensagem originada pelo WhatsApp. O plugin cobre o cliente HTTP e a descoberta
das 13 tools no Hermes.

## Milestone comprovado por código

O caminho a seguir está implementado e testado nas fronteiras do repositório:

```text
tool Hermes/smoke runner
  -> BackendFinanceClient
  -> headers X-Agent-Token + X-Agent-Sender-Id + X-Agent-Message-Id
  -> endpoint FastAPI do agente
  -> service financeiro
  -> Transaction/PostgreSQL
```

O teste de serviço comprova que `source` permanece `whatsapp` e que a mesma
mensagem é idempotente. A geração OpenAPI também inclui as rotas de agente,
webhook e CRUD financeiro.

## Validações dependentes do ambiente

- Ollama precisa estar instalado e com um modelo baixado para validar a
  interpretação real em português. O adaptador é local, mas o binário não é
  empacotado neste repositório.
- O pareamento e a entrega efetiva pelo WhatsApp Web precisam de uma sessão
  Hermes/Baileys ativa e de um telefone previamente vinculado.
- Docker Compose precisa de um daemon Docker acessível ao usuário para subir o
  PostgreSQL. A suíte de serviços pode continuar sendo executada com PostgreSQL
  local.

Essas condições não são tratadas como sucesso apenas porque o código foi
escrito. Depois de disponíveis, valide manualmente:

1. vincular o número pela tela Integrações;
2. enviar “Gastei 50 reais de gasolina.”;
3. conferir `source=whatsapp`, categoria e saldo no dashboard;
4. repetir a mesma mensagem/ID e confirmar que não duplica;
5. perguntar “Quanto gastei com transporte este mês?”;
6. conferir que a resposta contém os números devolvidos por
   `get_category_summary`, não um cálculo do modelo.
