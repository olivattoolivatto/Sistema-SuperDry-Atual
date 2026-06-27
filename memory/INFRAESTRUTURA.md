# Infraestrutura — Decisões e Arquitetura

Documento de referência para a infraestrutura de hospedagem do SuperDry e
serviços relacionados. Atualizado em 23/06/2026 (migração Oracle concluída em 12/06/2026,
verificação via SSH/Cloud Shell em 22/06/2026, **correção de paridade de código em 23/06/2026**
— ver seção "Paridade de código (local vs. VM) — ⚠️ CORRIGIDO em 23/06/2026" abaixo. A conclusão
de 22/06 de que local e VM estavam em "commit idêntico/sem drift real" estava **incorreta**.).

---

## Arquitetura decidida (definitiva)

```
Oracle Cloud Free Tier (sempre ligado, IP fixo público)
├── SuperDry — backend FastAPI + MongoDB + frontend React
└── Home Assistant — automações ESP32 via MQTT/ESPHome

Proxmox local (Core 2 Duo, 4GB DDR2) — hospedagem física de arquivos
└── Nextcloud — armazenamento de arquivos (substituto do OneDrive)
    └── acesso remoto via Tailscale (já instalado)
```

### Por que essa divisão

- **Oracle:** SuperDry precisa de IP fixo público para o webhook da InfinitePay
  funcionar sem depender do Tailscale Funnel. Home Assistant vai com ele porque
  os dispositivos são ESP32 (Wi-Fi, conectam pela internet de qualquer lugar —
  não são Zigbee/Z-Wave que precisam de rede local).
- **Proxmox local:** Nextcloud precisa de grande armazenagem sem custo mensal.
  O Proxmox tem HDs físicos locais. A Oracle Free dá apenas 200GB de disco total,
  insuficiente para substituir o OneDrive. O Nextcloud fica local e é acessado
  remotamente via Tailscale (custo zero).
- **Nextcloud como Opção 2:** interface do Nextcloud pode eventualmente ficar na
  Oracle apontando via SFTP para os arquivos no Proxmox — mas por ora fica tudo
  local no Proxmox para simplicidade.

---

## Oracle Cloud Free Tier — especificações

- **Plano:** Always Free (permanente, não expira)
- **VM:** ARM Ampere A1 — 4 OCPUs + 24GB RAM
- **Disco:** 200GB SSD
- **IP público fixo:** `148.116.108.43`
- **Hostname:** `instance-20260611-1911`
- **OS:** Oracle Linux Server 9.7 (aarch64) — confirmado via `/etc/os-release` (VERSION_ID="9.7")
- **Região:** Chile West (Valparaiso) — código real `sa-valparaiso-1` *(corrigido — o nome anterior "mx-queretaro-1" estava errado; confirmado no console OCI e no prompt do Cloud Shell)*
- **Banda:** 10TB saída/mês
- **Custo:** R$0 permanente
- **Status atual:** ✅ **EM PRODUÇÃO desde 12/06/2026 — verificado funcional em 22/06/2026**

### Stack instalada na VM

| Componente | Versão | Porta |
|---|---|---|
| Python | 3.11 (3.11.13) | — |
| FastAPI (Uvicorn) | 0.110.1 | 8001 (interno) |
| MongoDB | 7.0 (v7.0.37 confirmado) | 27017 (interno) |
| Node.js | 20.x (v20.20.2 confirmado) | — |
| Nginx | 1.20.1 | 80 (público) |

### Acesso
- **Sistema:** http://148.116.108.43 (sem VPN, de qualquer lugar) — também respondendo em
  **https://sistema.lavesuperdry.com.br** (ver seção Cloudflare abaixo)
- **SSH:** `ssh -i <caminho-da-chave> opc@148.116.108.43`
  - **Chave atual (válida em 22/06/2026):**
    `E:\OneDrive\SuperDry\EMERGENT - Novo Sistema SD\Oracle\feito daianaolivatto com VM\ssh-key-2026-06-11.key`
    *(caminho antigo `oracle-vm-key.key` na pasta do projeto está obsoleto/não existe mais)*
  - Usuário SSH correto: **`opc`** (Oracle Linux padrão) — `ubuntu` NÃO funciona (dá Permission denied)
  - Acesso alternativo sem chave local: **OCI Console → Cloud Shell** (browser, já tem internet/DNS completos,
    útil quando o sandbox local não tem rede). Usuário pode subir a chave `.key` direto na UI do Cloud Shell
    e então rodar `ssh -i ~/ssh-key-2026-06-11.key opc@148.116.108.43 "<comando>"` de lá.
- **Deploy key GitHub:** `~/.ssh/github_deploy` (ed25519, já adicionada ao repo)

### Domínio / HTTPS via Cloudflare
- `sistema.lavesuperdry.com.br` já está **proxyado pelo Cloudflare** (IPs anycast `2606:4700:...`),
  respondendo com HTTP 200 e TLS terminado na borda da Cloudflare.
- A origem (VM Oracle) **não tem certificado TLS próprio nem túnel `cloudflared`** — o Nginx da VM
  só escuta HTTP na porta 80. O Cloudflare está em modo proxy (`pub80:200` confirmado via Cloud Shell),
  então o tráfego HTTPS externo → Cloudflare → HTTP simples → VM:80.
- Portanto o item "Configurar domínio + HTTPS" abaixo em pendências está **parcialmente resolvido**:
  o domínio já funciona com HTTPS do ponto de vista do usuário final (graças ao Cloudflare), mas não há
  Let's Encrypt/Certbot rodando na própria VM nem túnel oficial — só o proxy DNS da Cloudflare.

### Serviços systemd
- `superdry.service` — backend FastAPI (autostart, restart automático)
- `mongod.service` — MongoDB
- `nginx.service` — servidor web / proxy reverso

### Arquivos importantes na VM
- Código: `~/superdry/` (clone do GitHub)
- Env produção: `/etc/superdry.env`
- Build frontend: `~/superdry/frontend/build/`
- Config Nginx: `/etc/nginx/conf.d/superdry.conf`

### Workflow de deploy
```
Editar código localmente (PC Windows)
  → git push (GitHub)
  → SSH na VM → git pull ~/superdry
  → sudo systemctl restart superdry
```
Para mudanças no frontend, adicionar após o pull:
```
cd ~/superdry/frontend
REACT_APP_BACKEND_URL=http://148.116.108.43:8001 npm run build --legacy-peer-deps
sudo chcon -R -t httpd_sys_content_t ~/superdry/frontend/build
```

### Vantagens sobre o PC Windows atual
- Sempre ligado (sem depender do PC do dono)
- Webhook InfinitePay sem Tailscale Funnel (IP público direto)
- 24GB RAM vs 4GB atual
- CPU ARM moderna vs Core 2 Duo
- Acesso ao sistema de qualquer lugar sem VPN

---

## Proxmox local — especificações

- **Hardware:** Core 2 Duo, 2x2GB DDR2 (4GB total, slots cheios, sem expansão)
- **Memória RAM:** já no limite físico — não dá para expandir
- **Geração:** hardware muito antigo (~15 anos), risco de falha aumenta
- **Uso futuro:** exclusivamente Nextcloud + armazenamento físico dos arquivos
- **Acesso remoto:** Tailscale (já instalado e configurado, nó `pve` no tailnet)

---

## Proxmox — nós no Tailnet (olivatto.olivatto@)

| Nó | IP Tailscale | OS | Uso |
|---|---|---|---|
| `superdry` (pc-casa) | 100.77.51.88 | Windows | Desenvolvimento |
| `pve` | 100.83.4.37 | Proxmox | Servidor local |
| `nextcloud` | 100.97.166.46 | Linux | Nextcloud (em testes) |
| `iphone172` | 100.99.40.93 | iOS | Celular do dono |

---

## Estado atual do desenvolvimento (jun/2026)

**Produção:** Oracle Cloud VM — http://148.116.108.43 (sempre no ar, sem VPN)

**Desenvolvimento local** (PC Windows do dono) — ainda funciona em paralelo:
- Backend: uvicorn na porta 8001 (subir com `autostart.ps1`)
- Frontend: React na porta 3000
- MongoDB: localhost:27017
- Tailscale Funnel: `https://superdry.tail287b6c.ts.net` → porta 8001

### Migração para Oracle — checklist ✅ CONCLUÍDO em 12/06/2026
- [x] Criar conta Oracle Cloud
- [x] Provisionar VM ARM (4 OCPU, 24GB, Oracle Linux 9.7)
- [x] Configurar OCI: internet gateway + security list (portas 22/80/443/8001)
- [x] Configurar firewalld na VM
- [x] Instalar Python 3.11, Node 20, MongoDB 7, Nginx, Git
- [x] Configurar GitHub deploy key (SSH ed25519)
- [x] Clonar repositório em `~/superdry/`
- [x] Instalar dependências Python (`pip3.11 install -r requirements.txt`)
- [x] Criar `/etc/superdry.env` com variáveis de produção
- [x] Criar serviço systemd `superdry.service`
- [x] Build do frontend (248KB gzip)
- [x] Configurar Nginx como proxy reverso
- [x] Ajustar SELinux (httpd_can_network_connect + chcon build/)
- [x] Importar 85 serviços do catálogo
- [x] Testar acesso externo completo

### Pendentes pós-migração
- [ ] Configurar domínio próprio + HTTPS (Let's Encrypt / Certbot)
- [ ] Adicionar IP/domínio Oracle ao Google OAuth (para Agenda funcionar em prod)
- [ ] Atualizar webhook InfinitePay com URL pública Oracle
- [ ] Instalar Home Assistant (Docker) na mesma VM
- [ ] Configurar MQTT broker para ESP32s
- [ ] Migrar dados do MongoDB local para produção (dump/restore)

---

## Ambiente de desenvolvimento (após migração)

Após a migração, o fluxo de trabalho será:
```
Edições no código (PC Windows + Claude Code)
        ↓ deploy manual ou git push
Oracle VM (produção, sempre no ar)
```
O PC Windows vira apenas estação de desenvolvimento — o sistema em produção
fica na Oracle independentemente do PC estar ligado ou não.

---

## Verificação de 22/06/2026 (via SSH direto + Oracle Cloud Shell)

Verificação completa feita logando na VM com a chave SSH (usuário forneceu a chave via
Cloud Shell; Claude nunca leu/digitou o conteúdo da chave privada — apenas referenciou o
caminho do arquivo já carregado pelo usuário). Resultado: **sistema 100% funcional e em
paridade com o código local.**

### Serviços e API
- `superdry.service`, `mongod.service`, `nginx.service` — todos **ativos (active/running)**
- Backend respondendo **HTTP 200** nas rotas testadas
- Portas abertas no firewall confirmadas: **80/tcp, 443/tcp, 8001/tcp**

### Recursos do sistema (snapshot 22/06/2026 21:23)
- **Uptime:** 10 dias, 22:08 — load average 0.13 / 0.15 / 0.27 (ocioso, saudável)
- **Disco (`/`):** 30G total, 18G usados, 12G livres — **61% de uso**
- **Memória:** 22Gi total, 10Gi usados, 2.4Gi livres, **12Gi disponível** (`available`); swap 5.0Gi livre (não usado)

### Backup automático (descoberto nesta verificação — não documentado antes)
- Existe rotina de backup em `/home/opc/backups/` com log próprio (`backup.log`)
- Último backup encontrado: **`superdry_20260622_0300.tar.gz`** (gerado às 03:00 do dia 22/06) —
  ou seja, **backup diário automatizado já está rodando em produção**, mecanismo/agendador
  (cron? systemd timer?) ainda não identificado em detalhe — investigar na próxima sessão
  se for preciso restaurar ou auditar retenção.

### Paridade de código (local vs. VM) — ⚠️ CORRIGIDO em 23/06/2026

A verificação de 22/06 abaixo estava **errada** na conclusão sobre paridade. Ela comparou apenas
o diff do `README.md` e generalizou para todo o repo. Uma comparação real (`git diff -b` arquivo a
arquivo) feita em 23/06 mostrou o seguinte:

- **A VM está rodando exatamente o commit `2fd9f07`** (isso está correto).
- **O working tree local NÃO está nesse commit** — está **~1.700 linhas adiante** em `backend/server.py`
  (e mudanças equivalentes em `backend/auth.py` e dezenas de arquivos do frontend), nunca commitadas
  nem enviadas ao GitHub. Ou seja, a VM não tem drift de código em si — ela está **desatualizada em
  relação ao local**, rodando uma versão sensivelmente mais antiga e com menos funcionalidades.
- **Impacto concreto identificado:** o PDF de orçamento gerado em produção é o template antigo
  (sem a identidade visual SuperDry azul/verde, sem tratamento correto de `service_category` por
  risco) porque essa funcionalidade existe só no código local, nunca deployado. O caminho da logo
  também está hardcoded como `/app/backend/uploads/logo.png` no código antigo da VM — path que não
  existe nessa VM (o deploy usa `~/superdry/`), então a logo provavelmente nem aparece nos PDFs
  gerados em produção.
- **Bugs encontrados e corrigidos em 23/06 no endpoint `/api/automation/execute-budget`:**
  1. Geração de ID por `count_documents()+1` causava colisão de chave duplicada — **isto sim era
     drift real**: o local já tinha a correção (agregação pelo maior ID existente) havia algum
     tempo, só não tinha sido deployada.
  2. Campo `execution_location` ausente no item criado, violando o schema de resposta (Pydantic) —
     **bug latente presente também no código local**, não era drift; corrigido nos dois lados.
  3. `service_id` gravado como `None`/vazio (dependia de um catálogo "matched" que esse endpoint
     nunca preenche) — **mesmo caso**, bug latente nos dois lados, corrigido nos dois.
  Os itens 2 e 3 foram corrigidos na VM via patch direto (sem deploy completo, por urgência) e
  retroativamente também no `backend/server.py` local, para não reaparecerem no próximo deploy.
- **Conclusão prática:** o fluxo de deploy documentado (`git push` → `git pull` na VM) nunca foi
  executado de fato desde 12/06 além do commit inicial. Antes de continuar o desenvolvimento local,
  é necessário **comitar e deployar** o trabalho pendente (ou substituir o arquivo diretamente),
  senão a VM continuará cada vez mais desatualizada.
- **Arquivos existentes só localmente, ainda não versionados/deployados na VM (lista de 22/06,
  ainda válida):** `.claude/`, `CLAUDE.md`, `Invoice-U4IOQSZN-0009.pdf`, `autostart.ps1`,
  `backend/finance_manager.py`, `backend/fix_client_name_backfill.py`, `backend/logs/`,
  `backend/payment_providers.py`, `buscar-eventos.py`, `clientes.json`, `conciliar_junho.py`,
  `eventos_junho.json`, `iniciar_superdry.ps1`, `instalar-tunnel.bat`,
  `memory/AGENDA_PADRAO_EVENTOS.md`, `memory/FLUXO_TRABALHO_E_AUTOMACAO.md`,
  `memory/GESTOR_FINANCEIRO.md`, `memory/INFRAESTRUTURA.md` (este arquivo),
  `memory/INTEGRACOES_PAGAMENTO.md`. `frontend/package-lock.json` também está untracked, mas é
  consistente nos dois lados (não é lacuna).

### Pendências confirmadas como ainda reais (sem mudança)
- Sem certificado TLS próprio na origem / sem `cloudflared` — depende 100% do proxy Cloudflare
- IP/domínio Oracle ainda não adicionado ao Google OAuth (Agenda em prod não testada)
- Webhook InfinitePay ainda não atualizado com URL pública Oracle
- Home Assistant/MQTT ainda não instalados na VM
- Mecanismo exato do backup automático (`/home/opc/backups/`) não documentado/auditado em detalhe
- **[NOVO 23/06]** Deploy do `backend/server.py`/`auth.py`/frontend local (≈1.700 linhas de
  funcionalidades, incl. template de PDF colorido com logo) para a VM — pendente, sandbox sem
  acesso de rede ao GitHub para `git push`; ver opções de transferência na seção abaixo.

### Logo no PDF — tamanho do arquivo (investigado em 23/06)
O PDF "colorido" local não é maior por causa das cores (tabelas/textos coloridos no ReportLab são
comandos vetoriais, custam poucos bytes). O peso extra vem da **imagem da logo embutida em
resolução original** — o ReportLab embute os pixels do arquivo fonte mesmo exibindo em tamanho
pequeno (1,5x1,2 polegada). Corrigido em `backend/server.py` (`POST /api/system-config/logo`):
agora a logo é redimensionada (máx. 600px no lado maior) e recomprimida via Pillow no momento do
upload, antes de salvar — fica nítida no PDF e não infla mais o arquivo.
