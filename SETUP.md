# Guia de Configuração — Comparador de Imóveis

## Por que Google Sheets e não Supabase?

Ambas as opções resolvem o problema do file system efêmero do Streamlit
Community Cloud. Optei pelo **Google Sheets** porque, para o seu caso de uso
(2 pessoas, entrada manual, poucas centenas de linhas), ele exige **zero
infraestrutura extra**: não há schema SQL para criar, não há gerenciamento de
tabelas/índices, e vocês ainda conseguem abrir a planilha diretamente no
navegador para dar uma olhada rápida nos dados, editar algo na mão ou tirar
um print para mandar no WhatsApp. O Supabase é mais robusto (Postgres de
verdade, relações, etc.), mas isso é over-engineering para um CRUD de "vamos
comparar 20-30 apartamentos".

A biblioteca usada é a `st-gsheets-connection`, oficial e mantida pelo time
do Streamlit, feita exatamente para este cenário.

---

## Passo 1 — Criar a planilha no Google Sheets

1. Acesse [sheets.google.com](https://sheets.google.com) e crie uma planilha
   nova. Dê o nome que quiser, ex: `imoveis-database`.
2. Renomeie a primeira aba (worksheet) para **`Imoveis`** (exatamente assim,
   é o nome usado no código em `WORKSHEET_NAME`).
3. Na primeira linha, cole os cabeçalhos exatamente nesta ordem:

```
ID	Link	Bairro	Valor_Base	Valor_Condominio	Valor_IPTU	Custo_Total	Area_m2	Vagas_Garagem	Estacao_Proxima	Tempo_Estacao_min	Status	Notas	Data_Cadastro
```

   (Cole essa linha inteira na célula A1 — o Google Sheets separa
   automaticamente por TAB em colunas.)
4. Deixe o resto da planilha vazio. O app vai preencher as linhas conforme
   vocês cadastrarem imóveis.
5. Copie a **URL completa** da planilha (barra de endereço do navegador).
   Você vai precisar dela no Passo 3.

---

## Passo 2 — Criar a Service Account no Google Cloud

Isso é necessário porque, para o app **escrever** na planilha (não só ler),
ele precisa de uma credencial de serviço — não dá para usar apenas
"compartilhamento público".

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/).
2. Crie um projeto novo (ou use um existente). Ex: `comparador-imoveis`.
3. No menu de busca, procure **"Google Drive API"** e clique em **Ativar**.
4. No mesmo menu de busca, procure **"Google Sheets API"** e clique em
   **Ativar** também. (Os dois precisam estar ativos.)
5. Vá em **"APIs e Serviços" → "Credenciais"**.
6. Clique em **"Criar Credenciais" → "Conta de serviço"** (Service Account).
7. Dê um nome (ex: `sheets-imoveis-bot`) e clique em **Concluir** (não
   precisa dar nenhuma role/papel especial de projeto).
8. Na lista de contas de serviço, clique na que você acabou de criar.
9. Vá na aba **"Chaves" ("Keys")** → **"Adicionar chave" → "Criar nova
   chave"** → formato **JSON** → Criar.
10. Um arquivo `.json` será baixado no seu computador. **Guarde-o com
    cuidado, ele é sua credencial de acesso.**
11. Copie o valor do campo `"client_email"` de dentro desse JSON (algo como
    `sheets-imoveis-bot@comparador-imoveis.iam.gserviceaccount.com`).
12. Volte na sua planilha do Google Sheets, clique em **"Compartilhar"** e
    cole esse e-mail, dando permissão de **Editor**. Sem esse passo, a
    Service Account não consegue escrever na planilha.

---

## Passo 3 — Configurar os secrets

O arquivo `.json` baixado tem todos os campos que você precisa. Você vai
transcrever esses valores para o formato `.toml` que o Streamlit usa.

### 3a. Para testar localmente

1. Na pasta do projeto, copie `.streamlit/secrets.toml.example` para
   `.streamlit/secrets.toml` (remova o `.example` do nome).
2. Abra o `.json` baixado no Passo 2 e o `secrets.toml` lado a lado, e
   preencha cada campo:

```toml
[connections.gsheets]
spreadsheet = "https://docs.google.com/spreadsheets/d/SEU_ID_AQUI/edit"
type = "service_account"
project_id = "valor do campo project_id no json"
private_key_id = "valor do campo private_key_id no json"
private_key = "valor do campo private_key no json (mantenha as \n)"
client_email = "valor do campo client_email no json"
client_id = "valor do campo client_id no json"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "valor do campo client_x509_cert_url no json"
```

   > **Atenção ao `private_key`**: no JSON original ele vem como uma única
   > linha com `\n` no meio (representando quebras de linha). Cole o valor
   > exatamente como está no JSON, entre aspas duplas — não precisa
   > reformatar.

3. Rode localmente:

```bash
pip install -r requirements.txt
streamlit run app.py
```

4. **Importante:** adicione `.streamlit/secrets.toml` ao seu `.gitignore`
   para nunca subir essa credencial para o GitHub:

```bash
echo ".streamlit/secrets.toml" >> .gitignore
```

### 3b. Para o deploy no Streamlit Community Cloud

1. Suba o projeto para um repositório no GitHub — **sem o arquivo
   `secrets.toml` real** (só o `.example`, o `app.py` e o
   `requirements.txt`).
2. Acesse [share.streamlit.io](https://share.streamlit.io) e clique em
   **"New app"**, selecionando o repositório e o arquivo `app.py`.
3. Antes (ou depois) de dar deploy, vá em **"Settings" → "Secrets"** da sua
   app no painel do Streamlit Cloud.
4. Cole ali o **mesmo conteúdo** do seu `secrets.toml` local (o bloco
   `[connections.gsheets]` inteiro, com os valores reais).
5. Salve. O Streamlit Cloud reinicia a app automaticamente com as novas
   credenciais.

---

## Passo 4 — Testar

1. Abra o app (local ou já publicado).
2. Vá em **"Cadastrar Imóvel"**, preencha um registro de teste e salve.
3. Volte na planilha do Google Sheets: uma nova linha deve ter aparecido.
4. Vá em **"Comparar Imóveis"**: o registro deve aparecer na tabela, os
   filtros devem funcionar, e você deve conseguir editar Status/Notas ou
   excluir o registro de teste.

---

## Observações finais

- **Concorrência**: como vocês dois vão usar o app ao mesmo tempo, o código
  sempre lê a planilha inteira antes de gravar (`ttl=0`, sem cache). Isso
  evita a maior parte dos conflitos, mas se dois cadastros forem salvos no
  exato mesmo segundo, um pode sobrescrever o outro. Para o volume de uso de
  vocês (cadastro manual, poucas dezenas de imóveis) isso não deve ser um
  problema na prática.
- **Limite gratuito**: a Google Sheets API tem uma cota generosa (60
  requisições de leitura/escrita por minuto por usuário), mais que suficiente
  para esse uso.
- **Backup**: como os dados moram numa planilha normal do Google Sheets,
  vocês sempre podem abrir, exportar como Excel/CSV, ou duplicar a planilha
  como backup manual quando quiserem.
