# ADR 0017 — Preflight do modo efetivo do bridge

## Contexto

O gateway Hermes pode manter uma sessão Baileys conectada em `self-chat` para
desenvolvimento. As variáveis `WHATSAPP_MODE` e `WHATSAPP_ALLOWED_USERS` não
provam, sozinhas, que o processo conectado está aceitando mensagens de usuários
em modo bot.

## Decisão

`agent.integration_check` continua validando backend, Ollama, plugin, sessão,
allowlist E.164 e configuração `WHATSAPP_MODE=bot`. Quando o bridge está em um
endereço local, o preflight também examina somente a linha de comando do
processo `whatsapp-bridge` associado à porta configurada e extrai apenas
`--mode`.

Se o modo observado for `self-chat`, desconhecido ou diferente de `bot`, o
check permanece em warning e o `--strict` falha. O health endpoint continua
sendo consultado para confirmar conectividade. Nenhum conteúdo de sessão,
credencial, QR code, telefone ou mensagem é lido.

## Consequências

- Uma sessão conectada em self-chat não pode ser confundida com o gateway de
  produção/desenvolvimento autorizado para receber mensagens.
- Em bridges remotos, o modo só pode ser aceito quando o próprio health
  endpoint o reporta; o processo remoto não é inspecionado.
- O round trip real continua exigindo um número controlado, allowlist explícita,
  pareamento e confirmação manual dos cenários financeiros.
