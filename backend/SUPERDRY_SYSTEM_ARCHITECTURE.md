# SUPERDRY LAVANDERIA - ARQUITETURA TÉCNICA DO SISTEMA
## Documento de Referência Completa - Versão 3.0

---

## 📋 VISÃO GERAL DO SISTEMA

**Empresa:** SuperDry Lavanderia de Tapetes & Estofados  
**Tecnologia:** React + FastAPI + MongoDB  
**Módulos:** 10/15 módulos implementados (67% concluído)  
**APIs:** Google Places, Geocoding, Google Calendar, OSRM, OpenStreetMap (Leaflet)  
**Status:** Fase 2 COMPLETA - Rotas e Agenda totalmente funcionais

---

## 🏗️ ESTRUTURA DE MÓDULOS

### ✅ FASE 1 COMPLETA (8 módulos)
1. **✅ Painel Inicial** - Dashboard com resumos e estatísticas
2. **✅ Clientes** - CRUD completo + busca híbrida + mini mapas + adição rápida
3. **✅ Catálogo** - Serviços organizados por 11 categorias + tipos de medição + colunas ordenáveis + status padrão + duplicar e editar
4. **✅ Orçamentos** - Core completo + itens + cálculos + medidas específicas + edição + preços editáveis + lançamento em lote + agrupamento de itens
5. **✅ WhatsApp** - Mensagens formatadas + deeplinks + medidas detalhadas
6. **✅ PDF** - Geração com logo + textos de risco + seções numeradas
7. **✅ Config. Orçamento** - 13 seções editáveis + formatação *negrito* _itálico_
8. **✅ Config. Sistema** - Dados empresa + LGPD + busca híbrida + mini mapa

### ✅ FASE 2 COMPLETA (2 módulos)
9. **✅ Rotas** - Sistema completo de otimização com OSRM + mapa interativo + priorização + salvamento completo
10. **✅ Agenda** - Integração Google Calendar OAuth2 + visualização completa + edição individual + reordenação + horários proporcionais

### 🔄 FASE 3 PLANEJADA (5 módulos)
11. **Lavagem/Execução** - Controle produtivo + status flow
12. **Modo Técnico** - Interface técnicos + fotos + assinaturas
13. **Financeiro** - Controle recebimentos + pagamentos
14. **Gerenciador Financeiro** - Open Finance + categorização
15. **Relatórios** - Analytics + KPIs + comissões

---

## 🚀 IMPLEMENTAÇÕES RECENTES - DETALHAMENTO FASE 2

### 📍 MÓDULO ROTAS - FUNCIONALIDADES IMPLEMENTADAS

#### Interface de 5 Seções
1. **Serviços Disponíveis** - Lista itens com status RETIRAR/EXECUTAR NO LOCAL/CLIENTE_TROUXE
2. **Rota Carro** - Seleção de itens para veículo tipo CARRO
3. **Rota Moto** - Seleção de itens para veículo tipo MOTO  
4. **Priorização de Rota** - Controle de sequência (PRIMEIRA/AUTOMÁTICA/ÚLTIMA)
5. **Visualizar e Salvar** - Mapa otimizado + resumo + persistência

#### Funcionalidades Técnicas
- ✅ **Validação de Cliente Completo** - Verifica dados obrigatórios antes da rota
- ✅ **Otimização OSRM** - Cálculo de rota mais eficiente com timeout de 60s
- ✅ **Loading Modal** - Feedback visual durante otimização 
- ✅ **Mapa Interativo** - Leaflet + markers personalizados por tipo
- ✅ **IDs Sequenciais** - RTE-000000 para rotas, STP-000000 para paradas
- ✅ **Alias Inteligente** - Descrições com bairros + timestamps
- ✅ **Durações Padrão** - 30min (RETIRAR/ENTREGAR), 120min (EXECUTAR NO LOCAL)
- ✅ **Merge de Paradas** - +60min para múltiplos itens no mesmo endereço
- ✅ **Persistência Completa** - Salvamento de rotas otimizadas no MongoDB

### 📅 MÓDULO AGENDA - INTEGRAÇÃO GOOGLE CALENDAR

#### OAuth2 Flow Completo
- ✅ **Autenticação Google** - Flow OAuth2 com redirect para /agenda  
- ✅ **Gerenciamento de Tokens** - Refresh automático + persistência segura
- ✅ **Status de Conexão** - Verificação visual do estado da integração

#### Gestão de Eventos
- ✅ **Criação Automática** - Eventos baseados em rotas salvas
- ✅ **Visualização Completa** - Lista de rotas salvas + eventos associados
- ✅ **Edição Individual** - Horário e duração de cada evento independente
- ✅ **Reordenação Manual** - Botões up/down para qualquer posição na lista
- ✅ **Ajuste Proporcional** - Cascata de horários ao alterar duração/tempo
- ✅ **Reset de Horários** - Volta à sequência original da rota

#### Calendar Grid
- ✅ **Múltiplas Visualizações** - Dia, 3 dias, semana
- ✅ **Navegação de Datas** - Controles anteriores/próximos
- ✅ **Horário Comercial** - Grade de 07:00 às 00:00  
- ✅ **Todos os Eventos** - Exibe eventos do sistema + externos do Google
- ✅ **Tema Google-like** - Cores diferenciadas (azul=sistema, verde=externo)
- ✅ **Edição Completa** - Double-click para editar título, descrição, local, datas
- ✅ **Exclusão Confirmada** - Modal de confirmação para delete

#### Correções de Bugs Críticos
- ✅ **IDs Únicos** - Timestamps + route IDs para evitar conflitos
- ✅ **Deep Copies** - JSON parse/stringify para evitar referências compartilhadas  
- ✅ **Seleção Individual** - Fix no toggle de seleção de eventos
- ✅ **Reordenação Universal** - Permite mover qualquer evento para qualquer posição
- ✅ **Edição Independente** - Cada evento mantém duração/horário próprio

### 🛒 MELHORIAS CATÁLOGO + ORÇAMENTOS

#### Catálogo - Novas Funcionalidades
- ✅ **Colunas Ordenáveis** - Sort por nome, categoria, preço, status
- ✅ **Reordenação de Colunas** - "Ações" na primeira posição
- ✅ **Status Padrão** - Campo `default_service_status` para novos itens
- ✅ **Duplicar e Editar** - Copia serviço + "(Cópia)" no nome + abre edição
- ✅ **Status "Situação"** - Renomeação da coluna is_active

#### Orçamentos - Funcionalidades Avançadas  
- ✅ **Preços Editáveis** - unit_price modificável na adição/edição de itens
- ✅ **Lançamento em Lote** - Seleção múltipla de serviços com quantidades
- ✅ **Medidas Padrão** - area_m2=1 para itens em lote
- ✅ **Agrupamento de Itens** - Exibição "Tapete (3un) R$108,00" nos cards
- ✅ **Fix service_status** - Correção de status baseado no default_service_status

#### Migrações de Dados
- ✅ **Migração Serviços** - Endpoint para adicionar default_service_status em serviços existentes
- ✅ **Correção Itens** - Fix de status em itens baseado no serviço correspondente
- ✅ **Fallback Logic** - Tratamento para serviços sem default_service_status

---

## 🔗 FLUXO PRINCIPAL DE DADOS

```
CLIENTE → ORÇAMENTO → ROTAS → AGENDA → LAVAGEM/EXECUÇÃO → FINANCEIRO
   ↓         ↓          ↓        ↓            ↓              ↓
 CLI-000   ORC-000   RTE-000  Calendar   Status Flow    Pagamento
```

---

## 🆔 SISTEMA DE IDs ÚNICOS

| Entidade | Formato | Exemplo | Descrição |
|----------|---------|---------|-----------|
| Cliente | CLI-0000 | CLI-0001 | Numeração sequencial |
| Serviço | SRV-0000 | SRV-0045 | Catálogo de serviços |
| Orçamento | ORC-0000000 | ORC-0000123 | Orçamentos principais |
| Item | ITM-0000000 | ITM-0005467 | Itens individuais |
| Rota | RTE-000000 | RTE-000012 | Rotas calculadas |
| Parada | STP-000000 | STP-000034 | Paradas nas rotas |
| OS Retoque | OSR-000000 | OSR-000005 | Ordens de retoque |

---

## 📊 STATUS FLOW - CICLO DE VIDA DOS ITENS

### Fluxo Principal - Retirada
```
RETIRAR → COLETADO → EM LAVAGEM → AGUARDANDO ENTREGA → ENTREGAR → ENTREGUE
```

### Fluxo Execução Local
```
EXECUTAR NO LOCAL → EXECUTADO
```

### Fluxo Cliente Trouxe
```
CLIENTE TROUXE → EM LAVAGEM PARCEIRO → AGUARDANDO BUSCAR → BUSCOU
```

### Status de Cancelamento
```
QUALQUER STATUS → CANCELADO PELO CLIENTE
```

---

## 🏷️ CATEGORIAS DE SERVIÇOS

| Categoria | Tipos de Serviço |
|-----------|------------------|
| **ESTOFADOS** | Sofá, Cadeira, Puff, Poltrona, Chaise, Cabeceira, Almofada |
| **COLCHÕES** | Solteiro, Viúvo, Casal Padrão/Queen/King/Super King, Especial |
| **BOX** | Box Solteiro, Viúvo, Casal Padrão/Queen/King/Super King, Especial |
| **TAPETES** | Tapete na Empresa, Tapete Parceiro |
| **CARPETES_E_TAPETES_NO_LOCAL** | Tapete no Local, Carpete no Local |
| **CORTINAS** | Simples, Pé Direito Duplo, Dupla/Especial |
| **PERSIANAS** | Vertical, Rolô/Romana, Horizontal Alumínio/Madeira |
| **ITENS_INFANTIS** | Carrinho, Cadeirinha, Bebê Conforto |
| **VEÍCULOS** | Bancos, Teto, Carpete, Forrações, Porta Malas, Interior Completo |
| **IMPERMEABILIZAÇÃO** | Sofás, Cadeiras, Poltronas, Almofadas |
| **OUTROS_ITENS** | Itens Diversos |

---

## 📏 TIPOS DE MEDIÇÃO

| Tipo | Campos de Entrada | Cálculo |
|------|------------------|---------|
| **UNITARIO** | Quantidade | Simples |
| **AREA_DE_TAPETE** | Largura × Altura | = Área M² |
| **TAPETE_REDONDO_DIAMETRO** | Diâmetro | = (D/2)² × 3,14 |
| **AREA_PERSIANA** | Largura × Altura | = Área M² |
| **METRAGEM_LINEAR_CORTINA_SIMPLES** | Dobras × Tecido/Dobra ÷ 100 | = Metros Lineares |
| **METRAGEM_LINEAR_PE_DIREITO_DUPLO** | Dobras × Tecido/Dobra ÷ 100 | = Metros Lineares |
| **METRAGEM_LINEAR_ESPECIAL** | Dobras × Tecido/Dobra ÷ 100 | = Metros Lineares |
| **CARPETE_TAPETE_LOCAL** | Largura × Altura | = Área M² |

---

## 🗄️ MODELO DE DADOS - RELACIONAMENTOS

### Cliente
```javascript
{
  id: "CLI-0001",
  name: "string",
  phone_primary: "string",
  phone_alternative: "string?",
  email: "string?",
  cpf_cnpj: "string?",
  instagram: "string?",
  address: {
    full_address: "string",
    complement: "string?",
    neighborhood: "string",
    city: "string", 
    state: "string",
    latitude: float,
    longitude: float
  },
  created_at: datetime,
  updated_at: datetime
}
```

### Orçamento
```javascript
{
  id: "ORC-0000001",
  client_id: "CLI-0001",
  client_name: "string",
  payment_method: enum,
  salesperson: enum,
  internal_observations: "string?",
  budget_observations: "string?",
  items: [ITM-objects],
  total_value: float,
  total_area_m2: float,
  total_linear_meters: float,
  total_units: int,
  created_at: datetime,
  updated_at: datetime
}
```

### Item de Orçamento
```javascript
{
  id: "ITM-0000001",
  budget_id: "ORC-0000001",
  service_id: "SRV-0001", 
  service_name: "string",
  service_code: "string",
  quantity: float,
  unit_price: float,
  total_value: float,
  area_m2: float?,
  linear_meters: float?,
  diameter: float?,
  width: float?,
  height: float?,
  fabric_folds: int?,
  fabric_per_fold: float?,
  observations: "string?",
  status: enum,
  execution_location: enum,
  is_retoque: boolean,
  original_item_id: "ITM-0000000?",
  created_at: datetime,
  updated_at: datetime
}
```

### Serviço (Catálogo)
```javascript
{
  id: "SRV-0001",
  name: "string",
  category: enum,
  service_type: "string",
  measure_type: enum,
  execution_location: enum,
  cost_price: float,
  sale_price: float,
  default_service_status: enum, // Status inicial para novos itens
  is_active: boolean,
  created_at: datetime,
  updated_at: datetime
}
```

### Rota
```javascript
{
  id: "RTE-000001",
  alias: "string", // Descrição inteligente com bairros + timestamp
  vehicle_type: "CARRO" | "MOTO",
  start_datetime: datetime,
  items: ["ITM-0000001", "ITM-0000002"],
  stops: [STP-objects],
  total_duration: int, // minutos
  total_distance: float, // km
  optimized: boolean,
  route_type: "ROTA_CURTA" | "ROTA_EFICIENTE",
  created_at: datetime,
  updated_at: datetime
}
```

### Parada (Stop)
```javascript
{
  id: "STP-000001",
  route_id: "RTE-000001", 
  client_id: "CLI-0001",
  items: ["ITM-0000001"],
  address: "string",
  latitude: float,
  longitude: float,
  priority: "PRIMEIRA" | "AUTOMATICA" | "ULTIMA",  
  estimated_duration: int, // minutos
  estimated_start_time: "HH:MM", // Horário estimado de chegada
  order_sequence: int,
  status: enum,
  created_at: datetime
}
```

### Evento Google Calendar
```javascript
{
  id: "google-calendar-event-id",
  summary: "string", // Título do evento
  description: "string", // Detalhes do cliente + serviços
  location: "string", // Endereço completo
  start: {
    dateTime: "2025-06-XX T10:00:00-03:00", // ISO format
    timeZone: "America/Cuiaba"
  },
  end: {
    dateTime: "2025-06-XX T11:00:00-03:00", // ISO format  
    timeZone: "America/Cuiaba"
  },
  colorId: "1", // 1=azul (sistema), 2=verde (externo)
  route_id: "RTE-000001", // Referência à rota (eventos do sistema)
  created_at: datetime
}
```

---

## 🔄 INTEGRAÇÃO ENTRE MÓDULOS

### Orçamentos → Rotas
- **Trigger:** Items com status `RETIRAR` ou `EXECUTAR NO LOCAL`
- **Dados:** Cliente, endereço, tipo de serviço, duração estimada
- **Resultado:** Criação de paradas otimizadas

### Rotas → Agenda  
- **Trigger:** Rota otimizada e confirmada
- **Dados:** Horários, durações, endereços, observações
- **Resultado:** Eventos no Google Calendar

### Agenda → Modo Técnico
- **Trigger:** Data atual = data agendada
- **Dados:** Lista de serviços do dia, endereços, observações
- **Resultado:** Interface mobile para técnico

### Modo Técnico → Lavagem/Execução
- **Trigger:** Mudança de status pelo técnico
- **Dados:** Status atualizado, fotos, assinaturas
- **Resultado:** Item segue fluxo produtivo

### Lavagem/Execução → Financeiro
- **Trigger:** Item com status final (ENTREGUE, EXECUTADO, BUSCOU)
- **Dados:** Orçamento completo, valores, formas de pagamento
- **Resultado:** Cobrança disponível

---

## ⚙️ CONFIGURAÇÕES DO SISTEMA

### Formas de Pagamento
```
PIX_CNPJ_25995295000104
PIX_CNPJ_30369419000186  
DINHEIRO
CREDITO_1X...CREDITO_8X
DEBITO
BOLETO
LINK_PAGAMENTO
TRANSFERENCIA
PERMUTA
```

### Vendedores Responsáveis
```
Gabriela Alcântara (3% comissão)
Diego Olivatto
Daiana Olivatto  
Marcos Anthonio (10% comissão)
```

### Tempos de Duração (Rotas)
- **Retirar/Entregar:** 30 minutos
- **Executar no Local:** 120 minutos
- **Múltiplos itens mesmo endereço:** +60 min por item adicional

---

## 🔐 AUDITORIA E LOGS

### Campos Auditáveis
- Alterações em valores/preços
- Mudanças de status de itens
- Descontos aplicados
- Formas de pagamento alteradas
- Edições em medidas

### Estrutura de Log
```javascript
{
  id: "uuid",
  table: "string",
  record_id: "string", 
  field_changed: "string",
  old_value: any,
  new_value: any,
  user_id: "string",
  timestamp: datetime,
  reason: "string?"
}
```

---

## 📱 APIS E INTEGRAÇÕES EXTERNAS

### Google Cloud APIs Habilitadas
- **Maps JavaScript API** - Exibição de mapas
- **Places API** - Busca de endereços  
- **Geocoding API** - Conversão endereço ↔ coordenadas
- **Directions API** - Cálculo de rotas otimizadas
- **Distance Matrix API** - Cálculo de distâncias
- **Google Calendar API** - Integração com agenda

### Chaves API
- **Principal:** AIzaSyBQPia_xVeD9jqnP9kWyi-w66qsLDqy_8U
- **Maps/Rotas:** AIzaSyCh2nGE77H8Iru2hMn5byQ4LJAdzKScKjY

---

## 📋 REGRAS DE NEGÓCIO CRÍTICAS

### 1. Validação de Cliente para Rota
```javascript
// Cliente deve ter dados completos antes de ir para rota
const validateClientForRoute = (client) => {
  return client.phone_primary !== "A COMPLETAR" &&
         client.address.full_address !== "Endereço a completar" &&
         client.address.neighborhood !== "Bairro a completar" &&
         client.address.city !== "Cidade a completar" &&
         client.address.latitude !== 0 &&
         client.address.longitude !== 0;
};
```

### 2. Cálculo de Orçamento  
- Soma automática de valores dos itens
- Recálculo ao adicionar/remover itens
- Consideração de descontos aplicados

### 3. Controle de Status
- Sequência lógica obrigatória
- Impossibilidade de pular etapas críticas
- Logs de todas as mudanças

### 4. Geração de PDFs
- Textos de risco baseados em categoria
- Formatação markdown → HTML
- Assinatura obrigatória do cliente

---

## 🎯 PRÓXIMOS PASSOS - FASE 2

### Rotas
1. Interface de seleção de itens por veículo
2. Integração Directions API para otimização
3. Visualização em mapa interativo
4. Controle de prioridades (PRIMEIRA/AUTOMÁTICA/ÚLTIMA)

### Agenda
1. Integração Google Calendar API
2. Criação automática de eventos
3. Sincronização bidireccional
4. Notificações e lembretes

### WhatsApp  
1. Formatação de mensagens (negrito/itálico)
2. Deeplinks para abertura do app
3. Templates pré-definidos
4. Histórico de envios

---

## 📝 OBSERVAÇÕES TÉCNICAS

### Inconsistências Identificadas e Resolvidas
1. **Padronização:** CARPETE_TAPETE_LOCAL (enum) vs Carpete_Tapete_Local (string)
2. **Status redundantes:** Esclarecido uso de ENTREGUE/BUSCOU e COLETADO/CLIENTE TROUXE
3. **WhatsApp sem API:** Solução por deeplinks aprovada

### Performance e Escalabilidade
- Paginação em listas (10 itens por scroll)
- Índices em campos de busca frequente
- Cache de cálculos complexos de rota
- Otimização de queries MongoDB

---

**Documento criado:** 24/08/2025  
**Última atualização:** 24/08/2025  
**Versão:** 1.0  
**Status:** Fase 1 Completa | Fase 2 Em Desenvolvimento