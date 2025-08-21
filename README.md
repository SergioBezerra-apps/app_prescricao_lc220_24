# Calculadora de Prescrição — LC-RJ 220/2024 (art. 5º-A)

App Streamlit simples para estimar prazos prescricionais conforme o novo regime da LC-RJ nº 220/2024:
- Enquadramento intertemporal (novo regime vs. transição vs. consumado antes da lei);
- Interrupções (§ 3º) e reinício da contagem;
- Prescrição intercorrente (§ 1º);
- Substituição por prazo penal (se aplicável);
- Geração de texto padrão para colar no parecer.

## Rodar localmente
```bash
pip install -r requirements.txt
streamlit run app_prescricao_lc220_24.py
```

## Deploy no Streamlit Community Cloud
1. Suba estes arquivos para um repositório público do GitHub.
2. Acesse https://share.streamlit.io/ ou https://streamlit.io/cloud e faça login com sua conta GitHub.
3. Clique em **New app** → selecione o repositório, branch e o arquivo principal `app_prescricao_lc220_24.py`.
4. Confirme a criação. A cada `git push`, o Streamlit recompila o app automaticamente.

## Estrutura
```
.
├── app_prescricao_lc220_24.py
├── requirements.txt
└── README.md
```

## Observações
- O app **não usa segredos**. Se futuramente precisar, crie o arquivo `.streamlit/secrets.toml` e configure pelo painel do Streamlit Cloud.
- Se aparecer `ModuleNotFoundError`, confirme se o pacote está listado em `requirements.txt`.
- Datas devem ser inseridas corretamente (AAAA-MM-DD) nos marcos interruptivos.
