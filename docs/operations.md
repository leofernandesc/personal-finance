# Operação local e agendamento

Este documento trata somente de tarefas operacionais do ambiente local ou de
um servidor sob controle do operador. Ele não transforma o projeto em um
serviço gerenciado e não ativa nenhum agendamento automaticamente.

## Limpeza de retenção

A rotina `app.maintenance` remove apenas:

- sessões expiradas ou revogadas;
- desafios de vinculação do WhatsApp vencidos;
- logs técnicos concluídos, sem vínculo financeiro, após
  `AGENT_LOG_RETENTION_DAYS`.

Mensagens e chamadas técnicas ligadas a uma transação ou transferência ficam
preservadas para idempotência e auditoria. Nenhuma linha financeira é alvo da
limpeza.

Antes de agendar a remoção em um ambiente compartilhado:

1. confirme a política de retenção e o responsável pelo banco;
2. confirme que o backup e o teste de restauração estão funcionando;
3. execute `make maintenance-check` e revise as contagens;
4. valide o comando em uma cópia ou banco de homologação;
5. só então instale o timer abaixo.

## Agendamento com systemd do usuário

As unidades em `ops/systemd/` são uma referência para o caminho padrão
`%h/personal-finance`. Edite o caminho se o repositório estiver em outro local.
O serviço exige um `.env` válido, o ambiente virtual do backend e acesso ao
PostgreSQL configurado nesse `.env`.

```bash
mkdir -p ~/.config/systemd/user
cp ops/systemd/personal-finance-maintenance.service ~/.config/systemd/user/
cp ops/systemd/personal-finance-maintenance.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now personal-finance-maintenance.timer
systemctl --user list-timers personal-finance-maintenance.timer
```

O timer executa semanalmente no domingo, com atraso aleatório de até 15
minutos, e recupera uma execução perdida quando o usuário volta a estar
disponível. A execução manual e a simulação continuam disponíveis:

```bash
make maintenance-check
systemctl --user start personal-finance-maintenance.service
journalctl --user -u personal-finance-maintenance.service --since today
```

Para suspender o agendamento sem remover os arquivos:

```bash
systemctl --user disable --now personal-finance-maintenance.timer
```

O timer não faz backup automaticamente porque a estratégia de backup depende
do ambiente (Compose, PostgreSQL local ou armazenamento protegido). O backup
deve ser concluído e verificado antes de habilitar uma limpeza aplicada.
