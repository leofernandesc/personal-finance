# ADR 0020 — Regras de cadastro e campos de senha

## Status

Aceito em 22/09/2026.

## Contexto

A revisão das regras do MVP encontrou diferenças entre a tela de cadastro e a
API: o nome podia ser omitido pela API, e a interface não pedia confirmação da
senha nem permitia conferir o texto digitado. Isso aumentava erros de entrada
e deixava uma regra importante dependente somente do navegador.

## Decisões

- O nome é obrigatório, removendo espaços nas extremidades, e aceita de 1 a
  120 caracteres.
- A senha aceita de 8 a 128 caracteres. O cadastro pede a confirmação e a
  compara no navegador e na API; a confirmação nunca é armazenada.
- O controle de mostrar/ocultar senha existe no login e no cadastro, com nome
  acessível, estado anunciado e suporte a teclado.
- E-mail continua validado como endereço e normalizado em minúsculas antes da
  persistência; e-mails duplicados são recusados.
- A confirmação não impõe regras artificiais de composição de senha. O projeto
  usa Argon2 para armazenar hashes, nunca a senha em texto.
- Recuperação de senha, alteração autenticada de senha e verificação de e-mail
  não são simuladas. Precisam de um fluxo próprio e de uma decisão de entrega
  de e-mail antes de oferecer o produto fora do ambiente local.

## Consequências

O contrato de cadastro exige `password_confirmation`, além de `email`,
`password`, `full_name` e `timezone`. Clientes de API também recebem validação
de consistência. Mudanças de senha e recuperação permanecem fora do fluxo
existente até haver política de reautenticação, expiração e entrega segura.
