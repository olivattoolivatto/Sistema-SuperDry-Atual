# 📱 MODO TÉCNICO - Especificação Técnica Completa

## 🎯 Visão Geral
Interface mobile-friendly dividida em **2 modos operacionais** para técnicos de campo e empresa.

---

## 🚗 MODO RUA - Atendimento Externo

### 📋 Status Atendidos (Conforme enum ServiceStatus)
- `RETIRAR` - Itens para coleta na casa do cliente
- `EXECUTAR_NO_LOCAL` - Serviços executados na residência
- `ENTREGAR` - Itens para entrega na casa do cliente

### 🏠 Interface Principal - Lista de Clientes
**Layout:** Cards de clientes do dia
```
┌─────────────────────────────────────┐
│ 📍 João Silva - 08:30               │
│ Rua das Flores, 123 - Centro        │
│ 🛋️ Sofá 3 lugares • 🪑 2 Cadeiras   │
│ Status: EXECUTAR_NO_LOCAL           │
│ ──────────────────────────────────  │
│         [ATENDER CLIENTE]           │
└─────────────────────────────────────┘
```

### 📱 Tela do Cliente (Detalhada)
**Seções:**
1. **Dados do Cliente**
   - Nome, telefone, endereço completo
   - Observações internas do orçamento

2. **Lista de Itens/Serviços**
   - Nome do serviço, quantidade, valor
   - Observações específicas de cada item
   - Status atual de cada item

3. **Campo de Observações do Técnico**
   - Texto livre para anotações do técnico
   - Salvo por item ou geral do cliente

### 📸 Fluxo de Fotos Obrigatórias

#### **ANTES do Serviço (Obrigatório)**
```
┌─────────────────────────────────────┐
│ 📸 FOTOS ANTES DO SERVIÇO           │
│                                     │
│ Item: Sofá 3 Lugares                │
│ Mínimo: 2 fotos obrigatórias        │
│                                     │
│ ❓ O item apresenta danos visíveis?  │
│    [ SIM ]  [ NÃO ]                 │
│                                     │
│ Se SIM: Tirar fotos específicas     │
│ dos danos para documentação         │
└─────────────────────────────────────┘
```

#### **DURANTE o Serviço (Opcional)**
- Fotos do processo de execução
- Documentação de progresso

#### **DEPOIS do Serviço (Obrigatório)**
```
┌─────────────────────────────────────┐
│ 📸 FOTOS FINAIS DO SERVIÇO          │
│                                     │
│ Resultado final do trabalho         │
│ Mínimo: 2 fotos do resultado        │
│                                     │
│ ✍️ ASSINATURA DIGITAL               │
│ ──────────────────────────────────  │
│ Nome: ________________________     │
│ Assinatura: [TELA TOUCH]            │
│                                     │
│ 💰 PAGAMENTO                        │
│ Forma: [ PIX ] [ Cartão ] [ $$ ]    │
│ Valor Recebido: R$ _______          │
│ Status: [ Pago ] [ Pendente ]       │
└─────────────────────────────────────┘
```

### 🔄 Evolução de Status (Modo Rua)
```
RETIRAR → COLETADO
EXECUTAR_NO_LOCAL → EXECUTADO  
ENTREGAR → ENTREGUE
```

---

## 🏢 MODO EMPRESA - Operação Interna

### 📋 Status Atendidos (Conforme enum ServiceStatus)
**Entrada:**
- `CLIENTE_TROUXE` - Item trazido pelo cliente
- `COLETADO` - Item coletado pelo técnico

**Em Processo:**
- `EM_LAVAGEM` - Item sendo processado internamente
- `EM_LAVAGEM_PARCEIRO` - Item terceirizado

**Finalizado:**
- `AGUARDANDO_ENTREGA` - Pronto para entrega
- `AGUARDANDO_BUSCAR` - Pronto para busca pelo cliente

**Concluído:**
- `ENTREGUE` - Item entregue ao cliente
- `BUSCOU` - Cliente buscou o item

### 🏭 Interface Principal - Controle Produtivo
**Layout:** Lista por status com contadores
```
┌─────────────────────────────────────┐
│ 📥 ENTRADA (5 itens)                │
│ • CLIENTE_TROUXE (2)                │
│ • COLETADO (3)                      │
├─────────────────────────────────────┤
│ 🔄 EM PROCESSO (8 itens)            │
│ • EM_LAVAGEM (5)                    │
│ • EM_LAVAGEM_PARCEIRO (3)           │
├─────────────────────────────────────┤
│ ✅ FINALIZADO (12 itens)            │
│ • AGUARDANDO_ENTREGA (7)            │
│ • AGUARDANDO_BUSCAR (5)             │
└─────────────────────────────────────┘
```

### 🔄 Evolução de Status (Modo Empresa)
```
CLIENTE_TROUXE → EM_LAVAGEM → AGUARDANDO_BUSCAR → BUSCOU
COLETADO → EM_LAVAGEM → AGUARDANDO_ENTREGA → ENTREGUE

Variação com parceiro:
→ EM_LAVAGEM_PARCEIRO → AGUARDANDO_ENTREGA/BUSCAR
```

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