/**
 * Constantes compartilhadas para o módulo de Orçamentos
 */
export const EXECUTION_MODES = [
  { value: 'RETIRAR_E_LEVAR', label: 'Retirar e Levar', desc: 'SuperDry busca, leva à empresa, devolve' },
  { value: 'EXECUTAR_NO_LOCAL', label: 'Executar no Local', desc: 'Técnico executa no endereço do cliente' },
  { value: 'CLIENTE_TROUXE', label: 'Cliente Trouxe', desc: 'Cliente entrega, SuperDry devolve' },
  { value: 'CLIENTE_LEVARA', label: 'Cliente Levará', desc: 'Cliente entrega e busca na empresa' },
];

export const EXEC_MODE_TO_STATUS = {
  RETIRAR_E_LEVAR: 'RETIRAR',
  EXECUTAR_NO_LOCAL: 'EXECUTAR_NO_LOCAL',
  CLIENTE_TROUXE: 'CLIENTE_TROUXE',
  CLIENTE_LEVARA: 'CLIENTE_TROUXE',
};

export const PAYMENT_METHODS = [
  { value: 'PIX_CNPJ_25995295000104', label: 'PIX CNPJ 1' },
  { value: 'PIX_CNPJ_30369419000186', label: 'PIX CNPJ 2' },
  { value: 'DINHEIRO', label: 'Dinheiro' },
  { value: 'CREDITO_1X', label: 'Crédito 1x' },
  { value: 'CREDITO_2X', label: 'Crédito 2x' },
  { value: 'CREDITO_3X', label: 'Crédito 3x' },
  { value: 'CREDITO_4X', label: 'Crédito 4x' },
  { value: 'CREDITO_5X', label: 'Crédito 5x' },
  { value: 'CREDITO_6X', label: 'Crédito 6x' },
  { value: 'CREDITO_7X', label: 'Crédito 7x' },
  { value: 'CREDITO_8X', label: 'Crédito 8x' },
  { value: 'DEBITO', label: 'Débito' },
  { value: 'BOLETO', label: 'Boleto' },
  { value: 'LINK_PAGAMENTO', label: 'Link de Pagamento' },
  { value: 'TRANSFERENCIA', label: 'Transferência' },
  { value: 'PERMUTA', label: 'Permuta' },
];

export const SALESPERSONS = [
  'Gabriela Alcântara',
  'Diego Olivatto',
  'Daiana Olivatto',
  'Marcos Anthonio',
];

export const STATUS_COLOR = {
  RETIRAR: 'bg-blue-100 text-blue-700',
  EXECUTAR_NO_LOCAL: 'bg-violet-100 text-violet-700',
  CLIENTE_TROUXE: 'bg-teal-100 text-teal-700',
  COLETADO: 'bg-cyan-100 text-cyan-700',
  EM_LAVAGEM: 'bg-amber-100 text-amber-700',
  EM_LAVAGEM_PARCEIRO: 'bg-amber-100 text-amber-700',
  AGUARDANDO_ENTREGA: 'bg-orange-100 text-orange-700',
  AGUARDANDO_BUSCAR: 'bg-orange-100 text-orange-700',
  ENTREGAR: 'bg-indigo-100 text-indigo-700',
  ENTREGUE: 'bg-emerald-100 text-emerald-700',
  BUSCOU: 'bg-emerald-100 text-emerald-700',
  EXECUTADO: 'bg-emerald-100 text-emerald-700',
  CANCELADO_PELO_CLIENTE: 'bg-rose-100 text-rose-700',
  AGENDADO: 'bg-sky-100 text-sky-700',
  RETOQUE_NECESSARIO: 'bg-yellow-100 text-yellow-700',
  EM_TRANSITO_DEVOLUCAO: 'bg-purple-100 text-purple-700',
  EXECUCAO_PARCIAL: 'bg-yellow-100 text-yellow-700',
};

export const PAYMENT_STATUS_COLOR = {
  PENDENTE: 'bg-amber-100 text-amber-700',
  PARCIAL: 'bg-sky-100 text-sky-700',
  PAGO: 'bg-emerald-100 text-emerald-700',
  CORTESIA: 'bg-violet-100 text-violet-700',
  INADIMPLENTE: 'bg-rose-100 text-rose-700',
};

export const fmtMoney = (n) =>
  (Number(n) || 0).toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' });

export const normalize = (s = '') =>
  String(s || '').normalize('NFD').replace(/[\u0300-\u036f]/g, '').toLowerCase().trim();
