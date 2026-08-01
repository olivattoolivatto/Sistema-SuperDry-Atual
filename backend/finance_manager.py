"""
SuperDry — Gestor Financeiro (Organizze-like) — modelos e helpers
==================================================================

Lado "gestão / contas a pagar" do financeiro: contas bancárias, cartões de
crédito e LANÇAMENTOS que agregam ENTRADAS por categoria (uma compra = soma de
linhas por categoria, espelhando o padrão Orçamento → Itens já existente).

Estado: SCAFFOLD. Modelos definidos; endpoints e wiring no server.py virão
incrementalmente. Ver memory/GESTOR_FINANCEIRO.md para a arquitetura completa.

Coleções:
  financial_accounts     (ACC-XXXX)  contas e cartões
  financial_categories   (CAT-XXXX)  árvore de categorias
  financial_entries      (LCT-XXXX)  lançamentos (agregador) + splits por categoria
  credit_card_invoices   (FAT-XXXX)  faturas (fase 2)
  financial_recurring    (REC-XXXX)  recorrências (fase 3)
"""
from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ── Enums ─────────────────────────────────────────────────────────────────────
class AccountType(str, Enum):
    CONTA_CORRENTE = "CONTA_CORRENTE"
    CARTAO_CREDITO = "CARTAO_CREDITO"
    DINHEIRO = "DINHEIRO"
    POUPANCA = "POUPANCA"
    CONTA_PAGAMENTO = "CONTA_PAGAMENTO"   # ex: InfinitePay


class Scope(str, Enum):
    EMPRESA = "EMPRESA"
    PESSOAL = "PESSOAL"
    AMBOS = "AMBOS"


class CategoryKind(str, Enum):
    DESPESA = "DESPESA"
    RECEITA = "RECEITA"


class EntryKind(str, Enum):
    DESPESA = "DESPESA"
    RECEITA = "RECEITA"
    TRANSFERENCIA = "TRANSFERENCIA"


class EntryStatus(str, Enum):
    A_CATEGORIZAR = "A_CATEGORIZAR"   # soma das splits != total (ou só "Não categorizado")
    PENDENTE = "PENDENTE"             # previsto, ainda não pago
    PAGO = "PAGO"
    CONCILIADO = "CONCILIADO"         # batido com extrato Open Finance


class EntrySource(str, Enum):
    MANUAL = "MANUAL"
    OPENFINANCE = "OPENFINANCE"
    WEBHOOK = "WEBHOOK"               # ponte com cobrança recebida (AR)
    EXTRATO_IMPORT = "EXTRATO_IMPORT"  # importado de arquivo OFX/CSV (manual ou via e-mail)


# ── Modelos ───────────────────────────────────────────────────────────────────
class OpenFinanceLink(BaseModel):
    connected: bool = False
    provider: Optional[str] = None        # PLUGGY | BELVO
    item_id: Optional[str] = None
    account_id: Optional[str] = None
    last_sync: Optional[str] = None


class FinancialAccount(BaseModel):
    id: Optional[str] = None              # ACC-XXXX
    name: str
    type: AccountType
    scope: Scope = Scope.EMPRESA
    institution: Optional[str] = None
    holder_document: Optional[str] = None  # CPF/CNPJ do titular (só dígitos) — usado pra
                                            # detectar transferências entre contas próprias
                                            # na importação de extrato (ver finance_import.py)
    holder_name: Optional[str] = None      # nome do titular como aparece nos extratos (ex:
                                            # "Diego Cesar Gonçalves Olivatto") — fallback de
                                            # matching por nome quando o extrato não traz CPF/
                                            # CNPJ na descrição (caso do BB "Pix enviado", ver
                                            # finance_import._detect_transfer e GESTOR_FINANCEIRO.md §25)
    statement_pdf_password: Optional[str] = None  # senha do extrato em PDF, quando o banco
                                            # protege o arquivo (ex: C6 usa os 6 primeiros
                                            # dígitos do CPF do titular) — usada em
                                            # finance_import.parse_pdf_bytes()
    opening_balance: float = 0.0
    current_balance: float = 0.0          # calculado
    # cartão de crédito:
    credit_limit: Optional[float] = None
    closing_day: Optional[int] = None     # fechamento da fatura
    due_day: Optional[int] = None         # vencimento
    openfinance: OpenFinanceLink = Field(default_factory=OpenFinanceLink)
    color: Optional[str] = None
    icon: Optional[str] = None
    archived: bool = False


class FinancialCategory(BaseModel):
    id: Optional[str] = None              # CAT-XXXX
    name: str
    kind: CategoryKind
    parent_id: Optional[str] = None       # hierarquia
    scope: Scope = Scope.AMBOS
    color: Optional[str] = None
    icon: Optional[str] = None
    archived: bool = False


class EntrySplit(BaseModel):
    """Uma linha por categoria dentro do lançamento (como um BudgetItem)."""
    category_id: str
    description: Optional[str] = None
    value: float


class Installments(BaseModel):
    n: int = 1
    total: int = 1


class FinancialEntry(BaseModel):
    id: Optional[str] = None              # LCT-XXXX
    kind: EntryKind
    scope: Scope = Scope.EMPRESA
    account_id: str
    date: str                             # competência (ISO)
    paid_date: Optional[str] = None       # caixa
    establishment: Optional[str] = None   # contraparte / estabelecimento
    total_value: float                    # bate com o valor passado no cartão/PIX
    payment_method: Optional[str] = None  # PIX|CREDITO|DEBITO|DINHEIRO|BOLETO|TRANSFERENCIA
    installments: Installments = Field(default_factory=Installments)
    status: EntryStatus = EntryStatus.A_CATEGORIZAR
    splits: List[EntrySplit] = Field(default_factory=list)
    is_internal_transfer: bool = False  # transferência entre contas próprias (detectada na
                                         # importação de extrato) — kind continua RECEITA/DESPESA
                                         # pra não quebrar o cálculo de saldo da conta, mas deve
                                         # ser excluída de relatórios de receita/despesa real
    transfer_match_confidence: Optional[str] = None  # "documento"|"nome"|"valor_data" — como a
                                         # transferência foi identificada (ver finance_import.py)
    transfer_with_account_id: Optional[str] = None    # ACC-XXXX da outra ponta da transferência
    transfer_with_entry_id: Optional[str] = None       # LCT-XXXX do lançamento espelho (só
                                         # preenchido no caso "valor_data", pra confirmar/rejeitar
                                         # o par exato depois)
    transfer_suggested: bool = False    # True = é só sugestão (match por valor+data, baixa
                                         # confiança), aguardando confirmação manual do usuário;
                                         # is_internal_transfer só vira True depois de confirmado
                                         # via POST /api/finance/entries/{id}/confirm-transfer
    source: EntrySource = EntrySource.MANUAL
    openfinance_tx_id: Optional[str] = None   # dedupe da importação
    reconciled: bool = False
    invoice_id: Optional[str] = None      # FAT-XXXX (cartão)
    attachments: List[str] = Field(default_factory=list)
    recurring_id: Optional[str] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None


# ── Helpers ───────────────────────────────────────────────────────────────────
SPLIT_TOLERANCE = 0.01


def splits_total(splits: List[Dict[str, Any]]) -> float:
    return round(sum(float(s.get("value") or 0) for s in (splits or [])), 2)


def splits_balanced(total_value: float, splits: List[Dict[str, Any]]) -> bool:
    """True se a soma das categorias fecha o valor da compra (tolerância 1 centavo)."""
    return abs(splits_total(splits) - round(float(total_value or 0), 2)) <= SPLIT_TOLERANCE


def splits_categorized(splits: List[Dict[str, Any]]) -> bool:
    """True se existe ao menos uma split e TODAS têm category_id preenchido.

    Uma split com valor/descrição mas sem categoria (ex.: usuário digitou um
    nome novo que não existe ainda na árvore e não havia como criá-lo na hora)
    não está, de fato, categorizada — mesmo que a soma dela bata com o total.
    Sem essa checagem o lançamento aparentava "resolvido" (saldo ok) mas as
    categorias reais (o que importa pros relatórios) ficavam órfãs e
    invisíveis em qualquer busca por categoria. Bug relatado pelo Diego em
    2026-06-28 (fracionamento "Lanchinho"/"Gasosa" que não aparecia em
    nenhuma busca).
    """
    return bool(splits) and all(s.get("category_id") for s in splits)


def derive_status(total_value: float, splits: List[Dict[str, Any]],
                  current: str = EntryStatus.PENDENTE.value) -> str:
    """A_CATEGORIZAR enquanto as splits não fecham ou alguma ainda não tem
    categoria definida; senão preserva o status atual."""
    if not splits_balanced(total_value, splits) or not splits_categorized(splits):
        return EntryStatus.A_CATEGORIZAR.value
    return current if current != EntryStatus.A_CATEGORIZAR.value else EntryStatus.PENDENTE.value


# ── Seed de categorias padrão (legado — mantido apenas por compatibilidade) ───
DEFAULT_CATEGORIES = [
    # DESPESA — PJ
    {"name": "Insumos/Produtos de lavagem", "kind": "DESPESA", "scope": "EMPRESA"},
    {"name": "Combustível/Veículo",         "kind": "DESPESA", "scope": "EMPRESA"},
    {"name": "Folha/Comissões",             "kind": "DESPESA", "scope": "EMPRESA"},
    {"name": "Impostos/Taxas",              "kind": "DESPESA", "scope": "EMPRESA"},
    {"name": "Marketing",                   "kind": "DESPESA", "scope": "EMPRESA"},
    {"name": "Manutenção/Equipamentos",     "kind": "DESPESA", "scope": "EMPRESA"},
    {"name": "Aluguel",                     "kind": "DESPESA", "scope": "EMPRESA"},
    {"name": "Energia/Água",                "kind": "DESPESA", "scope": "EMPRESA"},
    {"name": "Software/Assinaturas",        "kind": "DESPESA", "scope": "EMPRESA"},
    # DESPESA — PF
    {"name": "Mercado",                     "kind": "DESPESA", "scope": "PESSOAL"},
    {"name": "Produtos de limpeza",         "kind": "DESPESA", "scope": "PESSOAL"},
    {"name": "Comida",                      "kind": "DESPESA", "scope": "PESSOAL"},
    {"name": "Itens para casa",             "kind": "DESPESA", "scope": "PESSOAL"},
    {"name": "Higiene",                     "kind": "DESPESA", "scope": "PESSOAL"},
    {"name": "Saúde",                       "kind": "DESPESA", "scope": "PESSOAL"},
    {"name": "Transporte",                  "kind": "DESPESA", "scope": "PESSOAL"},
    {"name": "Lazer",                       "kind": "DESPESA", "scope": "PESSOAL"},
    {"name": "Moradia",                     "kind": "DESPESA", "scope": "PESSOAL"},
    # RECEITA
    {"name": "Serviços (clientes)",         "kind": "RECEITA", "scope": "EMPRESA"},
    {"name": "Outras receitas",             "kind": "RECEITA", "scope": "AMBOS"},
    {"name": "Aportes",                     "kind": "RECEITA", "scope": "AMBOS"},
]


# ── Árvore de categorias definitiva (2026-06) ─────────────────────────────────
# Substitui DEFAULT_CATEGORIES como fonte real de categorias do sistema.
# Estrutura definida por Diego em "lista de categorias para gerenciador
# financeiro SD.docx": PF/PJ × Receitas/Despesas, cada categoria-pai com suas
# subcategorias. A seção "PJ → Receitas" do documento original é uma lista
# plana, sem categorias-pai — por isso entra aqui como itens de topo
# (parent=None), cada um podendo receber lançamentos diretamente.
# Usado por POST /api/finance/categories/reset-import (ver finance_routes.py).
CATEGORY_TREE = [
    # ── PF — Receitas ──────────────────────────────────────────────────────
    {"scope": "PESSOAL", "kind": "RECEITA", "name": "Salários / Rendimentos", "children": [
        "Retiradas SuperDry Diego", "Retiradas SuperDry Daiana", "Pagamentos Studio Daiana",
        "Aluguéis Daiana", "Rendimentos negócios Diego / Atividades Extras",
        "Presentes / Doações de Outros para Diego", "Presentes / Doações de Outros para Daiana",
        "Presentes / Doações de Outros para Crianças", "Rendimentos de Investimentos / Dividendos / Lucros",
        "Vendas de Doces e outros itens Benjamim",
    ]},
    {"scope": "PESSOAL", "kind": "RECEITA", "name": "Minimalismo", "children": [
        "Venda de Itens Diego", "Venda de itens Daiana", "Venda de Itens Crianças",
    ]},
    {"scope": "PESSOAL", "kind": "RECEITA", "name": "Sorteios e Campanhas", "children": [
        "Premio Diego", "Premio Daiana", "Premio Benjamim", "Premio Yan", "Premios de outros / participação",
    ]},

    # ── PF — Despesas ──────────────────────────────────────────────────────
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Atividades Física e Hobbys", "children": [
        "Conserto Bicicleta Benjamim", "Conserto Bicicleta Yan", "Conserto Bicicleta Diego",
        "Conserto Bicicleta Daiana", "Bicicleta Nova Diego", "Bicicleta Nova Daiana",
        "Bicicleta Nova Benjamim", "Bicicleta Nova Yan", "Acessórios Bicicleta Benjamim",
        "Acessórios Bicicleta Yan", "Acessórios Bicicleta Diego", "Acessórios Bicicleta Daiana",
        "Academia Daiana", "Academia Diego",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Alimentação", "children": [
        "Lanche das Crianças / Escola", "Café da manhã das Crianças", "Lanche da célula",
        "Comida para a família", "Guloseimas e Comer Algo Gostoso", "Hamburguer Diego / Almoço Diego",
        "Hamburgueres Crianças / Almoço Crianças", "Refeições em família fora de casa / na rua",
        "Refeição Diego na rua", "Refeição Daiana na rua", "Eventos com amigos / Cotas",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Combustível", "children": [
        "Yaris Particular", "Kombi Particular", "Opala Particular", "Moto CG-SD Particular",
        "Combustível veículos de outras pessoas",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Lazer / Desfrute / Férias", "children": [
        "Combustível passeio", "Combustível Viagem",
        "Combustível com outras pessoas / Veiculos de outros à passeio", "Hospedagem",
        "Passagens aéreas", "Seguros Viagem", "Custos gerais de viagens",
        "Multas / Infrações de trânsito", "Alimentação em Viagem", "Estacionamento Shopping / Eventos",
        "Pedagio",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Datas Comemorativas", "children": [
        "Aniversários da família", "Aniversários de Amigos", "Presentes para as crianças",
        "Presentes para o casal", "Evento ou jantares de comemoração",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Educação", "children": [
        "Mensalidade Escola Yan", "Mensalidade Escola Benjamim", "Material Didático Yan",
        "Material Didático Benjamim", "Material Escolar Yan", "Material Escolar Benjamim",
        "Passeios Escolares Yan", "Passeios Escolares Benjamim", "Livros Yan", "Livros Benjamim",
        "Atividades Yan", "Atividades Benjamim",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Ministério", "children": [
        "Dízimo Diego", "Dízimo Daiana", "Oferta Diego", "Oferta Daiana", "Livros e Materiais",
        "Cursos e Capacitações", "Eventos Igreja e Ministério",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Saúde", "children": [
        "Plano de Saude", "Remédios Diego", "Remédios Daiana", "Remédios Benjamim", "Remédios Yan",
        "Tratamentos Diego", "Tratamentos Yan", "Tratamentos Benjamim", "Tratamentos Daiana",
        "Procedimentos Diego", "Procedimentos Daiana", "Procedimentos Yan", "Procedimentos Benjamim",
        "Dentista Diego", "Dentista Daiana", "Dentista Benjamim", "Dentista Yan",
        "Consultas Particulares Diego", "Consultas Particulares Daiana", "Consultas Particulares Yan",
        "Consultas Particulares Benjamim", "Terapia Diego", "Terapia Daiana", "Terapia Benjamim", "Terapia Yan",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Veículos", "children": [
        "Manutenção Yaris (RAP-2F89)", "Manutenção Opala", "Manutenção Kombi (JZB-6602)",
        "Manutenção CG-SD (NJP-3J09)", "Documentos Yaris (RAP-2F89)", "Documentos Opala",
        "Documentos Kombi (JZB-6602)", "Documentos CG-SD (NJP-3J09)", "Multas Yaris (RAP-2F89)",
        "Multas Kombi (JZB-6602)", "Multas Opala", "Multas CG-SD (NJP-3J09)",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Financiamento", "children": [
        "Financiamento Casa Canachuê", "Financiamentos em geral",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Pets", "children": [
        "Rações para Peixinhos", "Bombas e filtros para aquário", "Acessórios para aquário", "Novos Peixinhos",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Entretenimento", "children": [
        "Assinatura Netflix", "Assinatura Amazon Prime", "Assinatura HBO", "Assinatura AppleTV",
        "Assinatura Spotify", "Assinatura YouTube Premium", "Assinatura YouTube Music",
        "Assinatura Disney Channel", "Assinatura Paramount", "Assinatura outros Streams / IPTV",
        "Cinema", "Shows", "Eventos e Festas",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Celulares e Comunicação", "children": [
        "Celular Novo Diego", "Celular Novo Daiana", "Celular Novo Benjamim", "Celular Novo Yan",
        "Conserto Celular Diego", "Conserto Celular Daiana", "Conserto Celular Benjamim", "Conserto Celular Yan",
        "Acessórios Celular Diego", "Acessórios Celular Daiana", "Acessórios Celular Benjamim",
        "Acessórios Celular Yan", "Aplicativos Diego", "Aplicativos Daiana", "Aplicativos Benjamim",
        "Aplicativos Yan",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Vestuário e Aparência", "children": [
        "Salão Diego", "Salão Daiana", "Salão Benjamim", "Salão Yan",
        "Roupas Daiana", "Roupas Diego", "Roupas Benjamim", "Roupas Yan",
        "Sapato/Calçado Diego", "Sapato/Calçado Daiana", "Sapato/Calçado Benjamim", "Sapato/Calçado Yan",
        "Acessórios Daiana", "Acessórios Diego", "Acessórios Benjamim", "Acessórios Yan",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Despesas da casa", "children": [
        "Agua", "Telefone / Internet", "Energia Elétrica", "Taxa Condominial", "Gás de Cozinha GLP",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Manutenção da Casa / Reformas e Reparos", "children": [
        "Produtos de Limpeza", "Papel Higiênico", "Água Mineral", "Velas para Filtro de Barro",
        "Material de Limpeza (Vassouras, Rodos, Panos, Acessórios para limpeza)", "Talheres e Copos",
        "Eletrodomésticos", "Móveis", "Lâmpadas",
        "Serviços de reparos (pedreiro, pintor, eletricista, encanador, vidraceiro)",
        "Materiais de Construção e Reforma",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Governo e Burocracia", "children": [
        "Imposto de Renda Daiana", "Imposto de Renda Diego", "Taxas", "Impostos em geral",
    ]},
    {"scope": "PESSOAL", "kind": "DESPESA", "name": "Investimentos / Melhorias e Projetos", "children": [
        "Investimento e Melhoria Yaris", "Investimento e Melhoria Opala", "Investimento e Melhoria Kombi",
        "Investimento e Melhoria CG-SD", "Projetos Eletrônicos", "Projetos Mecânicos e/ou Ferramentas",
        "Novos Eletrodomésticos", "Novos Eletrônicos para Casa", "Novos Móveis para Casa",
        "Novas Utilidades Domésticas para a Casa",
    ]},

    # ── PJ — Receitas (lista plana no documento original; sem categoria-pai) ─
    {"scope": "EMPRESA", "kind": "RECEITA", "name": "Vendas Cartão de Crédito InfinitePay SuperDRY", "children": []},
    {"scope": "EMPRESA", "kind": "RECEITA", "name": "Vendas Cartão de Débito InfinitePay SuperDRY", "children": []},
    {"scope": "EMPRESA", "kind": "RECEITA", "name": "Vendas Pix InfinitePay SuperDRY", "children": []},
    {"scope": "EMPRESA", "kind": "RECEITA", "name": "Vendas Pix NuBank SuperDRY", "children": []},
    {"scope": "EMPRESA", "kind": "RECEITA", "name": "Vendas Pix PagSeguro SuperDRY", "children": []},
    {"scope": "EMPRESA", "kind": "RECEITA", "name": "Prestações de Serviços à Parceiros InfinitePay SuperDRY", "children": []},
    {"scope": "EMPRESA", "kind": "RECEITA", "name": "Prestações de Serviços à Parceiros NuBank SuperDRY", "children": []},
    {"scope": "EMPRESA", "kind": "RECEITA", "name": "Prestações de Serviços à Parceiros Crédito InfinitePay SuperDRY", "children": []},

    # ── PJ — Despesas ──────────────────────────────────────────────────────
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Custos com Equipe", "children": [
        "Salário Marcos", "Vale / Adiantamento Marcos", "Comissão Marcos", "Bônus Marcos",
        "Diária Marcos - Serviços Extras", "13º Marcos", "Férias Marcos",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Parceiros e Terceirizações", "children": [
        "Lavanderia Aeroporto – Seu Vicente", "Terceirizações de tapetes grandes – Agnaldo",
        "Terceirizações de Consertos de Cortinas – Agnaldo", "Consertos de Cortinas – Dona Izabel Costureira",
        "Instalação e Desinstalação de Cortinas - Welton Bastos sobrinho Agnaldo",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Prejuízos e Danos", "children": [
        "Consertos de Itens – Dona Izabel Costureira", "Aquisição de Material para reparos",
        "Aquisição de Itens para Substituição", "Consertos e Terceirizações de reparos para reposição de clientes",
        "Instalação e Desinstalação de Cortinas - Welton Bastos sobrinho Agnaldo",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Governo e Burocracia", "children": [
        "DASMEI – Mensal", "Taxas", "Impostos",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Custos Bancários", "children": [
        "Taxas cartão de Crédito InfinitePay", "Taxas cartão de Débito InfinitePay",
        "Taxas de Transferências", "Cesta / Pacote / Mensalidade Conta",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Juros / Atrasos", "children": [
        "Juros Cartão de Crédito ou Cheque Especial", "Mora diária Cartão de Crédito ou Cheque Especial", "IOF",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Insumos / Matérias Primas", "children": [
        "Peróxido de Hidrogênio", "Hipoclorito de Sódio", "Fita Adesiva", "Sacos / Embalagens",
        "Multi Interiores EasyTech", "OXY4D EasyTech", "Impermeabilizante GS Acqua Pro (base d'agua)",
        "Impermeabilizante EasyTech Pro Imper (base d'agua)", "Impermeabilizante GS Safe (Solvente não inflamável)",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "EPIs", "children": [
        "Botas / Calçados", "Protetores auriculares", "Luvas", "Máscaras", "Protetores Faciais",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Custos Equipe Extra e Serviços Grandes", "children": [
        "Diária Luiz", "Diária Gabriel", "Diária Lucas", "Diária Ajudantes em geral",
        "Alimentação Equipe", "Deslocamento Equipe", "Pedagio",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Equipamentos e Máquinas", "children": [
        "Manutenção Extratora (motores, bombas, mangueiras, bicos, etc)",
        "Manutenção Pulverizador (mangueira, gatilho, bomba, bateria, filtros)", "Manutenção Escova Rotativa",
        "Escova Manual", "Escova para Enceradeira", "Manutenção da Enceradeira",
        "Manutenção da Centrífuga", "Manutenção do Espaço",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Investimentos", "children": [
        "Melhorias no Espaço", "Melhorias nos Equipamentos / Novas idéias", "Equipamentos Novos",
        "Aquisição Equipamentos Usados", "Aquisição Veículo", "Projetos Eletrônicos",
        "Projetos Mecânicos e/ou Ferramentas", "Investimento e Melhoria Yaris",
        "Investimento e Melhoria Opala", "Investimento e Melhoria Kombi",
        "Investimento e Melhoria CG-SD", "Investimento em Softwares e desenvolvimento",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Marketing / Redes Sociais e Fortalecimento de Marca", "children": [
        "Day Marketing", "Campanhas Google", "Campanhas Meta / Instagram / Facebook / Whatsapp",
        "Material Impresso", "Desenvolvimento de Artes e material digital", "Hospedagem site",
        "Registro Domínio", "Registro Marca", "Desenvolvimento de Site ou similares", "Uniforme Equipe",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Combustível", "children": [
        "Yaris - Rota", "Kombi - Rota", "Opala - Rota", "Moto CG-SD – Rota",
        "Combustível veículos de outras pessoas", "Uber e deslocamento por Aplicativo",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Despesas Fixas da Empresa", "children": [
        "Agua", "Celular", "Internet", "Energia Elétrica", "IPTU", "Aluguel", "Recarga Crédito Celular Marcos",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Materiais da Empresa e Reparos", "children": [
        "Produtos de Limpeza", "Papel Higiênico", "Água Mineral", "Velas para Filtro de Barro",
        "Material de Limpeza (Vassouras, Rodos, Panos, Acessórios para limpeza)", "Talheres e Copos",
        "Eletrodomésticos", "Móveis", "Lâmpadas",
        "Serviços de reparos (pedreiro, pintor, eletricista, encanador, vidraceiro)",
        "Materiais de Construção e Reforma", "Ração Gatos",
    ]},
    {"scope": "EMPRESA", "kind": "DESPESA", "name": "Veículos / Transporte", "children": [
        "Manutenção Yaris (RAP-2F89)", "Manutenção Opala", "Manutenção Kombi (JZB-6602)",
        "Manutenção CG-SD (NJP-3J09)", "Documentos Yaris (RAP-2F89)", "Documentos Opala",
        "Documentos Kombi (JZB-6602)", "Documentos CG-SD (NJP-3J09)", "Multas Yaris (RAP-2F89)",
        "Multas Kombi (JZB-6602)", "Multas Opala", "Multas CG-SD (NJP-3J09)",
    ]},
]
