# portal-academico-palmas-dados-teste

> **AMBIENTE DE TESTE — DADOS FICTÍCIOS.** Nada aqui é contato real do IFTO. Não use estes dados.

Repositório de **homologação** da publicação de contatos do Portal de Serviços Acadêmicos — IFTO Campus Palmas (etapa R3.20-A1-R3, arquitetura C2):

```
Planilha privada (Google Sheets, conta GEAE) → Apps Script (validação + "Publicar (teste)")
  → este repositório (diretorio.json) → build de PRÉVIA do Cloudflare Pages (valida de novo) → Portal estático
```

## Conteúdo

| Arquivo | Função |
|---|---|
| `diretorio.json` | Contatos publicados no contrato público `diretorio.v1`. Só os campos da lista branca; nenhuma observação interna, situação editorial ou identificador de planilha |
| `validar-diretorio.py` | Validador do contrato (cópia do `scripts/validar-diretorio.py` do Portal). Com `--somente-ficticios`, recusa qualquer contato que não seja `teste-…` / `[TESTE] …` |
| `.github/workflows/validar.yml` | Validação automática a cada envio (somente leitura) |

## Regras

- **Só dados fictícios.** O Apps Script e o build da prévia recusam qualquer contato não marcado como teste.
- **Sem segredos.** Nenhum token, credencial, cookie ou ID de planilha neste repositório. O token de publicação fica só nas propriedades privadas do Apps Script da conta que publica.
- **Não ligado à produção.** O build de produção (`main` do Portal) nunca lê este repositório; o script de build recusa a fonte de teste no ramo de produção.

## Histórico e reversão

Cada publicação é **um commit** ("Publicação via planilha — data — N contatos (TESTE)").

- **Reverter a última publicação:** `git revert <commit>` (ou "Revert" no GitHub) e acionar um novo build da prévia.
- **Voltar a uma versão específica:** restaurar `diretorio.json` daquele commit e publicar.

O build da prévia **valida** o arquivo; se ele estiver inválido, o build falha e a prévia anterior continua no ar.

## Encerramento do teste

Arquivar ou excluir este repositório e revogar o token fine-grained usado. Nada no Portal em produção depende dele.
