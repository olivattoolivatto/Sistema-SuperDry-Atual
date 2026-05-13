# Sistema SuperDry Lavanderia - PRD

## Problema Original
Sistema de gestão de lavanderia com módulo de rotas. O usuário queria integrar a API do Geoapify Route Planner como alternativa ao sistema de rotas existente (que usa OSRM + Leaflet/OpenMaps), mantendo o mesmo fluxo de informações do sistema.

## Arquitetura Técnica
- **Backend**: FastAPI (Python) + MongoDB
- **Frontend**: React.js + Tailwind CSS
- **Otimização OSRM** (aba Rotas existente): OpenStreetMap + Leaflet
- **Otimização Geoapify** (aba nova): API Geoapify Route Planner

## Requisitos Core (Estáticos)
- Receber orçamentos com status EXECUTAR_NO_LOCAL/RETIRAR/ENTREGAR como pontos de rota
- Selecionar veículo: CARRO ou MOTO
- Definir prioridades: PRIMEIRA, AUTOMATICA, ULTIMA
- Calcular rota otimizada
- Salvar rota com alias
- Módulo Agenda lê rotas salvas e cria eventos no Google Calendar

## O que foi implementado

### 2026-02-xx - Integração Geoapify Route Planner
- **Backend**: Adicionado `GEOAPIFY_API_KEY` no .env
- **Backend**: `calculate_route_geoapify()` - chama POST https://api.geoapify.com/v1/routeplanner
- **Backend**: `optimize_route_with_priorities_geoapify()` - respeita prioridades PRIMEIRA/AUTOMATICA/ULTIMA
- **Backend**: Endpoint `POST /api/routes/{id}/optimize-geoapify`
- **Bug fix**: Stop IDs agora usam UUID para garantir unicidade (antes causava "Duplicate id in jobs")
- **Frontend**: `RoutesGeoapify.js` - nova aba sem mapa Leaflet, mesma lógica de seleção/priorização
- **Frontend**: `routesApi.optimizeGeoapify()` adicionado ao api.js
- **Frontend**: Route `/routes-geo` adicionado ao App.js
- **Frontend**: Item "Rotas Geoapify" adicionado ao Layout.js

## Dados de Teste
- Admin: admin@superdry.com / admin123
- 3 clientes criados (CLI-0001, 0002, 0003) com endereços reais em Cuiabá
- 1 serviço (SRV-0001: Higienização Sofá)
- 3 orçamentos (ORC-0000001, 0002, 0003)
- System config: lat=-15.6014, lon=-56.0974

## Backlog / Próximos passos
- [ ] Testar frontend visualmente (usuário solicitou testar por conta própria)
- [ ] Verificar integração completa Rotas Geoapify → Agenda → Google Calendar com dados reais
- [ ] Considerar adicionar mode=motorcycle quando Geoapify implementar (atualmente usa drive para ambos)
- [ ] Remover debug logs do console no Routes.js (produção)

## Chaves e Config
- Geoapify API Key: 01c4cd29f11547d49cbcd136694c775c (no backend/.env)
- Geoapify endpoint: POST https://api.geoapify.com/v1/routeplanner
- Response: features[0].properties.actions (type='job') para ordem otimizada
- Response: features[0].properties.time = total (viagem + serviço) em segundos
- Response: features[0].properties.distance = distância em metros
- Response: features[0].geometry = MultiLineString (geometria da rota)
