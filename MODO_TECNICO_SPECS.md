# 📱 MODO TÉCNICO - Especificação Técnica Completa

## 🎯 Visão Geral
Interface mobile-friendly dividida em **2 modos operacionais** para técnicos de campo e empresa.

---

## 🚗 MODO RUA - Atendimento Externo (ATUALIZADO)

### 📋 Status Atendidos (Conforme enum ServiceStatus)
- `RETIRAR` - Itens para coleta na casa do cliente
- `EXECUTAR_NO_LOCAL` - Serviços executados na residência
- `ENTREGAR` - Itens para entrega na casa do cliente

### 🏠 Interface Principal - Agenda Diária
**Layout:** Cards de clientes do dia com acesso rápido
```
┌─────────────────────────────────────┐
│ 📍 João Silva - 08:30               │
│ Rua das Flores, 123 - Centro        │
│ 🛋️ Sofá 3 lugares • 🪑 2 Cadeiras   │
│ Status: EXECUTAR_NO_LOCAL           │
│ ──────────────────────────────────  │
│ [🗺️ WAZE/MAPS] [ATENDER CLIENTE]    │
└─────────────────────────────────────┘
```

### 📱 Tela do Cliente (Completa)

#### **1. Dados do Cliente + Navegação**
- Nome, telefone, endereço completo
- **Link direto Waze/Maps** para navegação
- Observações internas do orçamento

#### **2. Lista de Itens com Seleção Individual**
```
┌─────────────────────────────────────┐
│ ☐ Sofá 3 Lugares - R$ 320,00       │
│   Status: EXECUTAR_NO_LOCAL         │
│   Obs: Mancha no braço direito      │
├─────────────────────────────────────┤
│ ☐ Cadeira Presidencial - R$ 80,00  │
│   Status: EXECUTAR_NO_LOCAL         │
│   Obs: Nenhuma observação          │
└─────────────────────────────────────┘
```

#### **3. Campo de Observações do Técnico**
- Texto livre para anotações do técnico
- Possibilidade de **adicionar novos itens** ao orçamento

### 📸 Fluxo de Fotos Obrigatórias (DETALHADO)

#### **ANTES do Serviço (Obrigatório)**
```
┌─────────────────────────────────────┐
│ 📸 FOTOS ANTES - Sofá 3 Lugares     │
│                                     │
│ Mínimo: 2 fotos obrigatórias        │
│ [📷 Foto 1] [📷 Foto 2]             │
│                                     │
│ ❓ O item apresenta danos visíveis?  │
│    [ SIM ]  [ NÃO ]                 │
│                                     │
│ Se SIM: Fotos específicas dos danos │
│ [📷 Dano 1] [📷 Dano 2] [+ Mais]    │
└─────────────────────────────────────┘
```

#### **DEPOIS do Serviço (Obrigatório + Assinatura)**
```
┌─────────────────────────────────────┐
│ 📸 FOTOS FINAIS DO SERVIÇO          │
│ [📷 Resultado 1] [📷 Resultado 2]   │
│                                     │
│ ✍️ ASSINATURA DIGITAL               │
│ ──────────────────────────────────  │
│ Nome: ________________________     │
│ [    ÁREA DE ASSINATURA TOUCH    ]  │
│                                     │
│ 📄 Comprovante PDF será enviado     │
│    automaticamente via WhatsApp    │
└─────────────────────────────────────┘
```

### 🔄 Botões de Finalização por Item

#### **Botões Específicos por Status:**
```
┌─────────────────────────────────────┐
│ Para itens EXECUTAR_NO_LOCAL:       │
│         [✅ SERVIÇO CONCLUÍDO]       │
│                                     │
│ Para itens RETIRAR:                 │
│         [📦 RETIRADA EFETUADA]       │
│                                     │
│ Para itens ENTREGAR:                │
│         [🚚 ENTREGA EFETUADA]        │
│                                     │
│ Para itens AGUARDANDO_BUSCAR:       │
│         [👤 CLIENTE BUSCOU]          │
│                                     │
│ Opções adicionais:                  │
│ [❌ CANCELADO PELO CLIENTE]         │
│ [📅 REAGENDAR]                      │
└─────────────────────────────────────┘
```

### 💰 Sistema de Pagamento Completo

#### **Interface de Pagamento**
```
┌─────────────────────────────────────┐
│ 💰 PAGAMENTO - R$ 400,00            │
│                                     │
│ Valor Restante: R$ 400,00           │
│                                     │
│ Forma de Pagamento:                 │
│ [PIX ▼] [CNPJ: 25995295000104 ▼]   │
│ Valor: R$ [_______] [+ ADICIONAR]   │
│                                     │
│ 💸 DESCONTO (Opcional)              │
│ R$ [_______]                        │
│ ⚠️ Informar desconto à administração │
│                                     │
│ Pagamentos Adicionados:             │
│ • PIX (CNPJ-104) - R$ 300,00       │
│ • DINHEIRO - R$ 100,00              │
│                                     │
│ [💾 CONFIRMAR PAGAMENTO]            │
└─────────────────────────────────────┘
```

#### **Formas de Pagamento Disponíveis:**
- **PIX:** 2 CNPJs (25995295000104 / 30369419000186)
- **DINHEIRO**
- **CRÉDITO:** x1 até x8 parcelas
- **DÉBITO**
- **BOLETO**
- **LINK_PAGAMENTO**
- **TRANSFERÊNCIA**
- **PERMUTA**

### 🎫 Sistema de Chamados/Comunicação
```
┌─────────────────────────────────────┐
│ 📞 CRIAR CHAMADO                    │
│                                     │
│ Tipo: [Manutenção ▼] [Compra ▼]    │
│ Destinatário: [Admin ▼] [João ▼]   │
│                                     │
│ Descrição:                          │
│ ________________________________   │
│ ________________________________   │
│                                     │
│ [📤 ENVIAR CHAMADO]                 │
└─────────────────────────────────────┘
```

### 🔄 Evolução de Status (Modo Rua)
```
RETIRAR → [📦 RETIRADA EFETUADA] → COLETADO
EXECUTAR_NO_LOCAL → [✅ SERVIÇO CONCLUÍDO] → EXECUTADO  
ENTREGAR → [🚚 ENTREGA EFETUADA] → ENTREGUE
AGUARDANDO_BUSCAR → [👤 CLIENTE BUSCOU] → BUSCOU
```

### 🔍 Auditoria de Alterações
**Registra automaticamente:**
- Usuário responsável pela alteração
- Data/hora da modificação
- Valores antes e depois
- Tipo de alteração (pagamento/desconto/reagendamento)

---

## 🏢 MODO EMPRESA - Operação Interna (ATUALIZADO)

### 📋 Status Atendidos (Conforme enum ServiceStatus)

#### **🔄 Fluxo Físico Detalhado:**
```
RECEPÇÃO → LAVAGEM → SECAGEM → MEDIÇÃO → DEPÓSITO SAÍDA → FINALIZAÇÃO
```

**Por Etapa Física:**

**1. 📥 RECEPÇÃO (Armazenamento Inicial)**
- `CLIENTE_TROUXE` - Item trazido pelo cliente
- `COLETADO` - Item coletado pelo técnico

**2. 🧽 LAVAGEM/PROCESSO**
- `EM_LAVAGEM` - Item sendo processado internamente
- `EM_LAVAGEM_PARCEIRO` - Item terceirizado

**3. 📏 MEDIÇÃO E RECOLHIMENTO**
- Status mantém-se durante secagem no varal
- Processo de medição com auditoria
- Recolhimento para depósito de saída

**4. 📦 DEPÓSITO DE SAÍDA (Escritório)**
- `AGUARDANDO_ENTREGA` - Pronto para entrega (itens nossos)
- `AGUARDANDO_BUSCAR` - Pronto para busca (itens de parceiros)

**5. 🚚 ENTREGA/RETIRADA**
- `ENTREGAR` - Item em processo de rota para entrega
- `ENTREGUE` - Item entregue ao cliente
- `BUSCOU` - Cliente buscou o item

### 🏭 Interface Principal - Controle Produtivo por Etapas

#### **Dashboard por Localização Física:**
```
┌─────────────────────────────────────┐
│ 📥 RECEPÇÃO (5 itens)               │
│ • CLIENTE_TROUXE (2) - Parceiros    │
│ • COLETADO (3) - Rota               │
├─────────────────────────────────────┤
│ 🧽 LAVAGEM (8 itens)                │
│ • EM_LAVAGEM (5) - Interno          │
│ • EM_LAVAGEM_PARCEIRO (3) - Tercei. │
├─────────────────────────────────────┤
│ 🌬️ SECAGEM/VARAL (4 itens)          │
│ • Aguardando secagem completa       │
├─────────────────────────────────────┤
│ 📏 MEDIÇÃO PENDENTE (2 itens)       │
│ • Prontos para medição              │
├─────────────────────────────────────┤
│ 📦 DEPÓSITO SAÍDA (12 itens)        │
│ • AGUARDANDO_ENTREGA (7) - Nossos   │
│ • AGUARDANDO_BUSCAR (5) - Parceiros │
└─────────────────────────────────────┘
```

### 🏷️ Sistema de Identificação para Parceiros

#### **Campo Especial para Etiquetas:**
```
┌─────────────────────────────────────┐
│ 🏷️ IDENTIFICAÇÃO DO ITEM            │
│                                     │
│ Cliente: João Silva                 │
│ Item: Tapete Persa 2x3m             │
│                                     │
│ É item de PARCEIRO?                 │
│ [ SIM ] [ NÃO ]                     │
│                                     │
│ Se SIM - Etiqueta:                  │
│ [AZUL-224    ] [🔍 Buscar]          │
│                                     │
│ Exemplos: AZUL-224, ROSA-335,       │
│          VERDE-101, AMAR-067        │
└─────────────────────────────────────┘
```

### 📏 Sistema de Medição com Auditoria

#### **Interface de Medição:**
```
┌─────────────────────────────────────┐
│ 📏 MEDIÇÃO - Tapete Persa           │
│                                     │
│ Medidas Originais (Orçamento):      │
│ • Largura: 2,00m                    │
│ • Altura: 3,00m                     │
│ • Área: 6,00m²                      │
│                                     │
│ Medidas Reais (Pós-Lavagem):        │
│ • Largura: [1,95] m                 │
│ • Altura: [2,98] m                  │
│ • Área: 5,82m² (calc. automático)   │
│                                     │
│ ⚠️ Diferença detectada: -0,18m²      │
│                                     │
│ Motivo da alteração:                │
│ [Encolhimento natural da lavagem]   │
│                                     │
│ [💾 SALVAR COM AUDITORIA]           │
└─────────────────────────────────────┘
```

### 📊 Relatório Mensal para Parceiros

#### **Geração Automática:**
```
┌─────────────────────────────────────┐
│ 📊 RELATÓRIO - Setembro 2025        │
│                                     │
│ Parceiro: Lavanderia Azul           │
│ Etiquetas: AZUL-001 a AZUL-350      │
│                                     │
│ Resumo do Mês:                      │
│ • Itens Recebidos: 45               │
│ • Itens Finalizados: 42             │
│ • Itens Pendentes: 3                │
│ • Valor Total: R$ 2.340,00          │
│                                     │
│ Status Detalhado:                   │
│ • EM_LAVAGEM_PARCEIRO: 3            │
│ • AGUARDANDO_BUSCAR: 0              │
│ • BUSCOU: 42                        │
│                                     │
│ [📄 GERAR PDF] [📧 ENVIAR EMAIL]    │
└─────────────────────────────────────┘
```

### 🔄 Evolução de Status (Modo Empresa)

#### **Fluxo Completo Detalhado:**
```
CLIENTE_TROUXE → EM_LAVAGEM → (Secagem) → (Medição) → AGUARDANDO_BUSCAR → BUSCOU

COLETADO → EM_LAVAGEM → (Secagem) → (Medição) → AGUARDANDO_ENTREGA → ENTREGAR → ENTREGUE

Com Parceiro:
COLETADO → EM_LAVAGEM_PARCEIRO → (Retorno) → AGUARDANDO_ENTREGA → ENTREGAR → ENTREGUE
```

### 🔍 Auditoria Completa

#### **Registro de Alterações:**
- **Medições:** Quem alterou, quando, valores antes/depois, motivo
- **Status:** Transições com timestamp e responsável
- **Localização:** Movimentação física dos itens
- **Parceiros:** Controle de entrada/saída com etiquetas

---

## 🛠️ Especificações Técnicas

### 📊 Estrutura de Dados

#### **TechnicianSession (Nova collection)**
```javascript
{
  id: "TECH-000001",
  technician_id: "USER-001",
  mode: "RUA", // RUA | EMPRESA
  date: "2025-09-15",
  clients_assigned: ["CLI-001", "CLI-002"],
  items_processed: [],
  created_at: "2025-09-15T08:00:00Z"
}
```

#### **ServicePhotos (Nova collection)**
```javascript
{
  id: "PHOTO-000001",
  item_id: "ITM-001",
  technician_id: "USER-001",
  phase: "BEFORE", // BEFORE | DURING | AFTER
  has_damage: true,
  damage_description: "Mancha no braço direito",
  photos: [
    {
      url: "base64_compressed_image",
      timestamp: "2025-09-15T10:30:00Z",
      type: "general" // general | damage_detail
    }
  ]
}
```

#### **DigitalSignature (Nova collection)**
```javascript
{
  id: "SIGN-000001",
  item_id: "ITM-001", 
  client_name: "João Silva",
  signature_data: "base64_svg_signature",
  payment_method: "PIX",
  amount_received: 150.00,
  payment_status: "PAGO",
  signed_at: "2025-09-15T11:45:00Z"
}
```

### 📱 Interface Mobile

#### **Design Responsivo**
- **Viewport:** Mobile-first (375px+)
- **Navegação:** Tab bar inferior
- **Cards:** Touch-friendly (min 44px)
- **Fotos:** Compressão automática (<500KB)

#### **Tabs de Navegação**
```
[ 🏠 Clientes ] [ 📋 Produção ] [ 📊 Status ] [ ⚙️ Config ]
```

### 🔧 APIs Necessárias

#### **GET /api/technician/daily-schedule**
- Retorna clientes do dia com status RUA
- Filtro por técnico e data

#### **GET /api/technician/production-queue**  
- Retorna itens por status EMPRESA
- Contadores por categoria

#### **POST /api/technician/photos**
- Upload de fotos com compressão
- Associação automática com item

#### **POST /api/technician/signature**
- Salva assinatura + dados de pagamento
- Atualiza status do item

#### **PUT /api/technician/item-status**
- Atualiza status conforme modo de operação
- Valida transições permitidas

### 📦 Otimizações Técnicas

#### **Fotos Leves**
- **Formato:** WebP ou JPEG otimizado
- **Resolução:** Máx 1080x720
- **Compressão:** 70-80% quality
- **Tamanho:** < 500KB por foto

#### **Sincronização Offline**
- **localStorage** para dados pendentes
- **IndexedDB** para fotos base64
- **Auto-sync** quando conecta à internet
- **Indicadores visuais** de sync status

---

## 🎯 Próximos Passos de Implementação

1. **Backend APIs** - Endpoints para modo técnico
2. **Upload de Fotos** - Compressão e storage
3. **Interface Mobile** - Layout responsivo  
4. **Assinatura Digital** - Canvas touch
5. **Sincronização** - Offline-first approach
6. **Testes de Campo** - Validação com técnicos reais

---

*Especificação criada: 15/09/2025 - Baseada nos status exatos do sistema*