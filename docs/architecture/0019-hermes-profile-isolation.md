# ADR 0019 — Isolamento do perfil financeiro no Hermes

## Status

Aceito para desenvolvimento local.

## Contexto

O host já possui um gateway Hermes padrão usado por outras integrações. Esse
gateway estava ativo com o perfil `default` e um provider externo, enquanto o
perfil `personal-finance` permanecia parado e configurado com um modelo menor
que não atende à janela exigida pelo Hermes. Redirecionar ou reiniciar o
gateway padrão para validar o produto financeiro poderia afetar outros agentes
e misturar credenciais, sessões ou canais.

## Decisão

- Manter o gateway padrão fora do escopo da validação financeira.
- Instalar o plugin do monorepo no perfil isolado
  `~/.hermes/profiles/personal-finance` usando a fonte local do repositório.
- Configurar esse perfil com `custom:ollama` e `llama3.2:3b`, sem chave de API.
- Validar o perfil por um comando one-shot de leitura que injeta apenas a
  identidade técnica da sessão e chama a API FastAPI; o perfil não acessa o
  PostgreSQL diretamente.
- Deixar o bridge WhatsApp e o gateway padrão inalterados até existir um número
  controlado, uma allowlist explícita e uma decisão de roteamento do canal.

## Consequências

- A fronteira Hermes → Ollama → tool → FastAPI pode ser comprovada sem
  interromper Telegram ou outros agentes do host.
- O perfil financeiro instalado precisa ser atualizado novamente quando o
  código do plugin mudar; o smoke usa a cópia instalada, não uma importação
  implícita do diretório de trabalho.
- O round trip WhatsApp permanece pendente: perfil isolado não equivale a
  sessão Baileys em modo `bot`, nem autoriza um remetente não verificado.
- O gateway padrão pode continuar usando outro provider; por isso os checks do
  Ciclo 3 devem distinguir o perfil financeiro do status global do Hermes.
