import sys as _sys
# Garante UTF-8 no stdout/stderr — evita UnicodeEncodeError com emojis nos logs
# em consoles Windows (cp1252). Sem isto, prints com emoji crasham funções.
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from fastapi import FastAPI, APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, date, timedelta
from enum import Enum
import googlemaps
import json
import asyncio
from io import BytesIO
import aiofiles
import re
import requests
import math
import unicodedata
from typing import Tuple
from xml.sax.saxutils import escape as _xml_escape
from PIL import Image as PILImage
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import os
from reportlab.lib.units import cm
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from fastapi import Depends
from fastapi import Request as HttpRequest
import payment_providers
from finance_manager import DEFAULT_CATEGORIES

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Caminhos de arquivos (portáveis — relativos ao diretório do backend, não /app)
UPLOADS_DIR = ROOT_DIR / "uploads"


def _logo_candidates():
    """Caminhos candidatos da logo, em ordem de preferência (multiplataforma)."""
    return [
        str(UPLOADS_DIR / "logo.png"),
        str(ROOT_DIR / "logo-superdry.png"),
        str(UPLOADS_DIR / "logo-superdry.png"),
    ]


def _find_logo():
    for p in _logo_candidates():
        if os.path.exists(p):
            return p
    return None

# Import auth module (Phase 1)
from auth import (
    User, UserPublic, UserCreate, UserUpdate, UserRole,
    LoginRequest, LoginResponse, AuditLog,
    hash_password, verify_password, create_access_token,
    make_auth_dependencies, ensure_default_admin,
)

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Google Maps client
GOOGLE_MAPS_KEY = "AIzaSyCh2nGE77H8Iru2hMn5byQ4LJAdzKScKjY"
gmaps = googlemaps.Client(key=GOOGLE_MAPS_KEY)

# Condensa o texto de risco para a mensagem do WhatsApp (primeira frase, max 200 chars)
def _condense_risk(text: str, max_len: int = 200) -> str:
    if not text:
        return ""
    text = text.strip()
    # Pega até o primeiro ponto final, exclamação, interrogação ou quebra de linha
    m = re.search(r'[.!?\n]', text[:max_len + 30])
    snippet = text[:m.start()].strip() if m else text[:max_len].strip()
    if len(snippet) > max_len:
        snippet = snippet[:max_len - 3] + '...'
    return snippet


# Textos curtos de aviso por categoria para a mensagem de WhatsApp
_WA_SHORT_RISKS = {
    'ESTOFADOS':
        "🚨 Estofados podem esconder *situações perigosas*: migração de manchas, ferrugem entre outros danos irreversíveis, *não garantimos* remoção delas nem outros tipos de manchas. Leia atentamente o termo de aceite para mais informações.",
    'COLCHOES':
        "🚨 Colchões podem esconder *situações perigosas*: migração de manchas ou cores, ferrugem entre outros danos irreversíveis, *não garantimos* remoção delas nem outros tipos de manchas. Leia atentamente o termo de aceite para mais informações.",
    'BOX':
        "🚨 Colchões/Box podem esconder *situações perigosas*: migração de manchas ou cores, ferrugem entre outros danos irreversíveis, *não garantimos* remoção delas nem outros tipos de manchas. Leia atentamente o termo de aceite para mais informações.",
    'TAPETES':
        "🚨 Felpas amassadas e tapete soltando areia são sinais de desgaste irreversíveis. Não removemos manchas. Tapetes orientais/persas com histórico de urina podem migrar ou variar a cor. Prazo de entrega: até 5 dias úteis. Leia atentamente o termo de aceite para mais informações.",
    'CARPETES_E_TAPETES_NO_LOCAL':
        "🚨 Felpas amassadas por desgaste são irreversíveis. Itens com urina prévia podem migrar ou variar a cor. Secagem: ±12h. Leia atentamente o termo de aceite para mais informações.",
    'CORTINAS':
        "🚨 Cortinas e especialmente *Blackouts podem escurecer ou descolar*. Tecidos nunca lavados podem encolher ou alongar. Materiais com PVC e similares podem colar ou rasgar por enfraquecimento devido à radiação solar. Leia atentamente o termo de aceite para mais informações.",
    'PERSIANAS':
        "🚨 Blackouts podem escurecer ou descolar por desgaste via radiação solar. Materiais com PVC podem colar ou rasgar. Leia atentamente o termo de aceite para mais informações.",
    'ITENS_INFANTIS':
        "🚨 Priorizamos produtos suaves — algumas manchas podem não sair totalmente. Leia atentamente o termo de aceite para mais informações.",
    'VEICULOS':
        "🚨 Risco de descolamento do tecido do teto e forrações — avalie antes. Não garantimos remoção de manchas. Tecidos escuros podem parecer desbotados após limpeza. Leia atentamente o termo de aceite para mais informações.",
    'IMPERMEABILIZACAO':
        "🚨 Não protege contra óleos nem urina por tempo prolongado. Atrito diário reduz a durabilidade. Aguardar 24h para uso após aplicação. Leia atentamente o termo de aceite para mais informações.",
    'OUTROS_ITENS':
        "🚨 Não garantimos remoção de manchas. Peças escuras podem parecer desbotadas após limpeza. Secagem: ±8h. Leia atentamente o termo de aceite para mais informações.",
}

# Ordem de exibição das categorias na mensagem (mantém coerência visual)
_CAT_ORDER = [
    'ESTOFADOS', 'COLCHOES', 'BOX', 'TAPETES', 'CARPETES_E_TAPETES_NO_LOCAL',
    'CORTINAS', 'PERSIANAS', 'ITENS_INFANTIS', 'VEICULOS', 'IMPERMEABILIZACAO', 'OUTROS_ITENS',
]


def _suggest_installments(total: float) -> int:
    """Calcula máximo de parcelas sugerido: ~R$100/parcela, teto 6x."""
    if total <= 200: return 2
    if total <= 300: return 3
    if total <= 400: return 4
    if total <= 500: return 5
    return 6  # R$600+ → 6x (teto)


def _format_payment_wa(total: float) -> str:
    """Formata sugestão de pagamento para WhatsApp."""
    installments = _suggest_installments(total)
    return (
        f"R$ {total:.2f} _à vista no PIX_ ou _em até {installments}x sem juros no cartão de crédito._"
    )


def _make_short_id(length: int = 7) -> str:
    import random, string
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=length))


# Utility functions for text formatting
def format_whatsapp_text(text: str) -> str:
    """Convert markdown-like formatting to WhatsApp format"""
    # *text* -> Bold in WhatsApp
    text = re.sub(r'\*(.*?)\*', r'*\1*', text)
    # _text_ -> Italic in WhatsApp  
    text = re.sub(r'_(.*?)_', r'_\1_', text)
    return text


def normalize_text(s: str) -> str:
    """Normaliza texto para busca: minúsculo, sem acento."""
    if not s:
        return ""
    import unicodedata
    nfkd = unicodedata.normalize("NFD", s)
    only_ascii = "".join(c for c in nfkd if not unicodedata.combining(c))
    return only_ascii.lower().strip()


def only_digits(s: str) -> str:
    """Mantém apenas dígitos (útil para CPF/CNPJ/telefone)."""
    if not s:
        return ""
    return re.sub(r"\D+", "", s)

def format_html_text(text: str) -> str:
    """Convert markdown-like formatting to HTML"""
    # *text* -> <b>text</b>
    text = re.sub(r'\*(.*?)\*', r'<b>\1</b>', text)
    # _text_ -> <i>text</i>
    text = re.sub(r'_(.*?)_', r'<i>\1</i>', text)
    return text

# Google Calendar configuration
GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
GOOGLE_CLIENT_SECRET = os.getenv('GOOGLE_CLIENT_SECRET')
SCOPES = ['https://www.googleapis.com/auth/calendar']
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://lavesuperdry.com.br/agenda')

# Google Calendar helper functions
def get_google_auth_flow():
    """Create Google OAuth flow"""
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    return flow

def get_calendar_service(credentials_dict):
    """Create Google Calendar service from credentials"""
    credentials = Credentials.from_authorized_user_info(credentials_dict, SCOPES)
    service = build('calendar', 'v3', credentials=credentials)
    return service

# Create the main app without a prefix
app = FastAPI(title="SuperDry Lavanderia Management System")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# ============================================================
# AUTH dependencies setup (Phase 1)
# ============================================================
_auth = make_auth_dependencies(db)
get_current_user = _auth["get_current_user"]
get_optional_user = _auth["get_optional_user"]
require_roles = _auth["require_roles"]
log_audit = _auth["log_audit"]
require_admin = require_roles(UserRole.ADMIN)

# Enums
class ServiceCategory(str, Enum):
    ESTOFADOS = "ESTOFADOS"
    COLCHOES = "COLCHOES" 
    BOX = "BOX"
    TAPETES = "TAPETES"
    CARPETES_E_TAPETES_NO_LOCAL = "CARPETES_E_TAPETES_NO_LOCAL"
    CORTINAS = "CORTINAS"
    PERSIANAS = "PERSIANAS"
    ITENS_INFANTIS = "ITENS_INFANTIS"
    VEICULOS = "VEICULOS"
    IMPERMEABILIZACAO = "IMPERMEABILIZACAO"
    OUTROS_ITENS = "OUTROS_ITENS"

class MeasureType(str, Enum):
    UNITARIO = "UNITARIO"
    AREA_DE_TAPETE = "AREA_DE_TAPETE"
    CARPETE_TAPETE_LOCAL = "CARPETE_TAPETE_LOCAL"
    TAPETE_REDONDO_DIAMETRO = "TAPETE_REDONDO_DIAMETRO"
    AREA_PERSIANA = "AREA_PERSIANA"
    METRAGEM_LINEAR_CORTINA_SIMPLES = "METRAGEM_LINEAR_CORTINA_SIMPLES"
    METRAGEM_LINEAR_PE_DIREITO_DUPLO = "METRAGEM_LINEAR_PE_DIREITO_DUPLO"
    METRAGEM_LINEAR_ESPECIAL = "METRAGEM_LINEAR_ESPECIAL"
    TAPETE_A_IDENTIFICAR = "TAPETE_A_IDENTIFICAR"  # placeholder — forma ainda não definida (ajuste 02/10/2026)

class ExecutionLocation(str, Enum):
    RETIRADA = "RETIRADA"
    NO_LOCAL = "NO_LOCAL"
    CLIENTE_TROUXE = "CLIENTE_TROUXE"


class ExecutionMode(str, Enum):
    """Modo de execução logístico de um ITEM (não confundir com ExecutionLocation do Service)."""
    RETIRAR_E_LEVAR = "RETIRAR_E_LEVAR"   # SuperDry busca, leva à empresa, devolve
    EXECUTAR_NO_LOCAL = "EXECUTAR_NO_LOCAL"  # Técnico executa no endereço do cliente
    CLIENTE_TROUXE = "CLIENTE_TROUXE"     # Cliente entrega na empresa, SuperDry devolve
    CLIENTE_LEVARA = "CLIENTE_LEVARA"     # Cliente entrega e busca na empresa


class PaymentStatusItem(str, Enum):
    PENDENTE = "PENDENTE"
    PARCIAL = "PARCIAL"
    PAGO = "PAGO"
    CORTESIA = "CORTESIA"
    INADIMPLENTE = "INADIMPLENTE"

class PaymentMethod(str, Enum):
    PIX_CNPJ_1 = "PIX_CNPJ_25995295000104"
    PIX_CNPJ_2 = "PIX_CNPJ_30369419000186"
    DINHEIRO = "DINHEIRO"
    CREDITO_1X = "CREDITO_1X"
    CREDITO_2X = "CREDITO_2X"
    CREDITO_3X = "CREDITO_3X"
    CREDITO_4X = "CREDITO_4X"
    CREDITO_5X = "CREDITO_5X"
    CREDITO_6X = "CREDITO_6X"
    CREDITO_7X = "CREDITO_7X"
    CREDITO_8X = "CREDITO_8X"
    DEBITO = "DEBITO"
    BOLETO = "BOLETO"
    LINK_PAGAMENTO = "LINK_PAGAMENTO"
    TRANSFERENCIA = "TRANSFERENCIA"
    PERMUTA = "PERMUTA"

class ServiceStatus(str, Enum):
    RETIRAR = "RETIRAR"
    EXECUTAR_NO_LOCAL = "EXECUTAR_NO_LOCAL"
    CLIENTE_TROUXE = "CLIENTE_TROUXE"
    COLETADO = "COLETADO"
    EM_LAVAGEM = "EM_LAVAGEM"
    EM_LAVAGEM_PARCEIRO = "EM_LAVAGEM_PARCEIRO"
    AGUARDANDO_ENTREGA = "AGUARDANDO_ENTREGA"
    AGUARDANDO_BUSCAR = "AGUARDANDO_BUSCAR"
    ENTREGAR = "ENTREGAR"
    ENTREGUE = "ENTREGUE"
    BUSCOU = "BUSCOU"
    EXECUTADO = "EXECUTADO"
    CANCELADO_PELO_CLIENTE = "CANCELADO_PELO_CLIENTE"
    # Novos (standby para fluxos futuros)
    AGENDADO = "AGENDADO"
    RETOQUE_NECESSARIO = "RETOQUE_NECESSARIO"
    EM_TRANSITO_DEVOLUCAO = "EM_TRANSITO_DEVOLUCAO"
    EXECUCAO_PARCIAL = "EXECUCAO_PARCIAL"

class Salesperson(str, Enum):
    GABRIELA_ALCANTARA = "Gabriela Alcântara"
    DIEGO_OLIVATTO = "Diego Olivatto"
    DAIANA_OLIVATTO = "Daiana Olivatto"
    MARCOS_ANTHONIO = "Marcos Anthonio"

# Pydantic Models
class Address(BaseModel):
    full_address: str
    complement: Optional[str] = None
    neighborhood: str
    city: str
    state: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class Client(BaseModel):
    id: str = Field(default_factory=lambda: f"CLI-{str(uuid.uuid4().int)[:4].zfill(4)}")
    name: str
    phone_primary: str  # WhatsApp
    phone_alternative: Optional[str] = None
    email: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    instagram: Optional[str] = None
    address: Address
    # Campos de busca normalizada (não usados pelo front, mas pelo back)
    name_normalized: Optional[str] = None
    phone_digits: Optional[str] = None
    cpf_cnpj_digits: Optional[str] = None
    # Observações livres sobre o cliente
    observations: Optional[str] = None
    # Auditoria
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None
    updated_by: Optional[str] = None
    updated_by_name: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ClientCreate(BaseModel):
    name: str
    phone_primary: str
    phone_alternative: Optional[str] = None
    email: Optional[str] = None
    cpf_cnpj: Optional[str] = None
    instagram: Optional[str] = None
    address: Address

class Service(BaseModel):
    id: str = Field(default_factory=lambda: f"SRV-{str(uuid.uuid4().int)[:4].zfill(4)}")
    name: str
    category: ServiceCategory
    service_type: str
    measure_type: MeasureType
    execution_location: ExecutionLocation
    cost_price: float
    sale_price: float
    is_active: bool = True
    default_service_status: ServiceStatus = ServiceStatus.RETIRAR  # Status padrão quando adicionado a orçamento
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class ServiceCreate(BaseModel):
    name: str
    category: ServiceCategory
    service_type: str
    measure_type: MeasureType
    execution_location: ExecutionLocation
    cost_price: float
    sale_price: float
    default_service_status: ServiceStatus = ServiceStatus.RETIRAR  # Status padrão quando adicionado a orçamento

class BudgetItem(BaseModel):
    id: str = Field(default_factory=lambda: f"ITM-{str(uuid.uuid4().int)[:7].zfill(7)}")
    # FK redundantes (item é o pilar — precisa carregar referência direta)
    budget_id: Optional[str] = None
    client_id: Optional[str] = None
    client_name: Optional[str] = None
    client_phone: Optional[str] = None

    # Serviço
    service_id: Optional[str] = None
    service_name: str = "Tapete"
    service_code: str = "AUTO"
    service_category: Optional[str] = None
    measure_type: Optional[str] = None
    quantity: float = 1.0
    unit_price: float
    area_m2: Optional[float] = None
    linear_meters: Optional[float] = None
    total_value: float
    observations: Optional[str] = None

    # Status atual + histórico
    status: ServiceStatus = ServiceStatus.RETIRAR
    status_history: List[Dict[str, Any]] = Field(default_factory=list)

    # Modo de execução logístico
    execution_mode: ExecutionMode = ExecutionMode.RETIRAR_E_LEVAR
    is_retoque: bool = False
    execution_location: Optional[ExecutionLocation] = ExecutionLocation.CLIENTE_TROUXE

    # Endereços por etapa (override do endereço do cliente)
    pickup_address: Optional[Dict[str, Any]] = None
    execution_address: Optional[Dict[str, Any]] = None
    delivery_address: Optional[Dict[str, Any]] = None

    # Datas planejadas
    scheduled_pickup_date: Optional[str] = None       # "YYYY-MM-DD"
    scheduled_pickup_time: Optional[str] = None       # "HH:MM"
    scheduled_execution_date: Optional[str] = None
    scheduled_execution_time: Optional[str] = None
    scheduled_delivery_date: Optional[str] = None
    scheduled_delivery_time: Optional[str] = None

    # Datas reais
    actual_pickup_at: Optional[datetime] = None
    actual_started_at: Optional[datetime] = None
    actual_finished_at: Optional[datetime] = None
    actual_delivered_at: Optional[datetime] = None

    # Sessões de execução (suporta execução em partes)
    execution_sessions: List[Dict[str, Any]] = Field(default_factory=list)

    # Referências de tráfego
    current_route_id: Optional[str] = None
    current_route_stop_id: Optional[str] = None
    route_history: List[str] = Field(default_factory=list)
    technician_id: Optional[str] = None
    agenda_event_ids: List[str] = Field(default_factory=list)
    assignment_ids: List[str] = Field(default_factory=list)

    # Fotos
    photos_before: List[str] = Field(default_factory=list)
    photos_after: List[str] = Field(default_factory=list)

    # Financeiro do item
    payment_method: Optional[PaymentMethod] = None    # null = herda do orçamento
    payment_status: PaymentStatusItem = PaymentStatusItem.PENDENTE
    paid_value: float = 0.0
    payment_records: List[Dict[str, Any]] = Field(default_factory=list)

    # Medidas específicas para diferentes tipos
    width: Optional[float] = None
    height: Optional[float] = None
    diameter: Optional[float] = None
    fabric_folds: Optional[int] = None
    fabric_per_fold: Optional[float] = None

    # Comissão do técnico
    commission_enabled: bool = False
    commission_user_id: Optional[str] = None
    commission_user_name: Optional[str] = None
    commission_pct: Optional[float] = None

    # Cliente desistiu: mantém no histórico mas sai das rotas
    client_desisted: bool = False

    # Identificação de parceiro (lavanderia parceira)
    partner_label: Optional[Dict[str, Any]] = None
    # ex: {"type":"COLOR_NUM","color":"AZUL","number":"224"} ou {"type":"TEXT","text":"Joao da Silva"}
    confirmed_measures: bool = False

    # Auditoria de medidas
    measures_history: List[Dict[str, Any]] = Field(default_factory=list)

    # Valor original do orçamento antes de ajuste por medição real
    original_total_value: Optional[float] = None

    # Auditoria
    created_by: Optional[str] = None
    updated_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BudgetItemCreate(BaseModel):
    service_id: str
    quantity: float = 1.0
    area_m2: Optional[float] = None
    linear_meters: Optional[float] = None
    observations: Optional[str] = None
    # Medidas específicas para diferentes tipos
    width: Optional[float] = None
    height: Optional[float] = None
    diameter: Optional[float] = None
    fabric_folds: Optional[int] = None
    fabric_per_fold: Optional[float] = 18.0

class Budget(BaseModel):
    id: str = Field(default_factory=lambda: f"ORC-{str(uuid.uuid4().int)[:7].zfill(7)}")
    client_id: str
    client_name: str
    payment_method: PaymentMethod
    salesperson: str                    # nome do vendedor (display_name do usuário)
    internal_observations: Optional[str] = None
    budget_observations: Optional[str] = None
    items: List[BudgetItem] = []
    total_value: float = 0.0
    total_area_m2: float = 0.0
    total_linear_meters: float = 0.0
    total_units: int = 0
    # Condição de pagamento padrão sugerida pelo valor (apenas sugestão; o
    # pagamento real é selecionado no Financeiro). Regra em suggest_credit_installments.
    suggested_payment_method: Optional[str] = "CREDITO"
    suggested_installments: Optional[int] = None
    payment_status: Optional[str] = "PENDENTE"
    # Status administrativo do orçamento (ciclo comercial, independente dos itens)
    # RASCUNHO → ENVIADO → APROVADO → CANCELADO / ARQUIVADO
    # EM_EXECUCAO e CONCLUIDO são derivados dos itens (calculados, não gravados)
    budget_status: Optional[str] = "RASCUNHO"
    budget_status_updated_at: Optional[datetime] = None
    budget_status_updated_by: Optional[str] = None
    source: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BudgetConfig(BaseModel):
    # Risk texts for each category
    risks_estofados: Optional[str] = ""
    risks_colchoes: Optional[str] = ""
    risks_box: Optional[str] = ""
    risks_tapetes: Optional[str] = ""
    risks_carpetes_tapetes_local: Optional[str] = ""
    risks_cortinas: Optional[str] = ""
    risks_persianas: Optional[str] = ""
    risks_itens_infantis: Optional[str] = ""
    risks_veiculos: Optional[str] = ""
    risks_impermeabilizacao: Optional[str] = ""
    risks_outros_itens: Optional[str] = ""
    # General conditions and footer
    general_conditions: Optional[str] = ""
    footer_text: Optional[str] = ""
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Route models
class VehicleType(str, Enum):
    CARRO = "CARRO"
    MOTO = "MOTO"

class Priority(str, Enum):
    PRIMEIRA = "PRIMEIRA"
    AUTOMATICA = "AUTOMATICA"
    ULTIMA = "ULTIMA"

class RouteStatus(str, Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"

class RouteStop(BaseModel):
    id: str = Field(default_factory=lambda: f"STP-{str(uuid.uuid4().int)[:7].zfill(7)}")
    route_id: str
    budget_item_id: str                           # item principal (1º do endereço)
    extra_budget_item_ids: List[str] = []         # demais itens do mesmo endereço (merge)
    client_id: str
    client_name: str
    service_name: str
    service_value: float
    address: dict
    priority: Priority = Priority.AUTOMATICA
    estimated_duration: int = 30
    service_status: ServiceStatus
    order_sequence: int = 0
    delivery_order: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Route(BaseModel):
    id: str = Field(default_factory=lambda: f"RTE-{str(uuid.uuid4().int)[:7].zfill(7)}")
    vehicle_type: VehicleType
    planned_date: str  # Format: "YYYY-MM-DD"
    planned_start_time: str  # Format: "HH:MM"
    alias: Optional[str] = None
    status: RouteStatus = RouteStatus.PLANNED
    stops: List[RouteStop] = []
    total_duration: int = 0  # minutes
    total_distance: float = 0.0  # km — deslocamento total incluindo ida e volta à empresa
    company_address: dict
    route_geometry: Optional[dict] = None
    route_provider: Optional[str] = "OSRM"  # "OSRM" | "GEOAPIFY" — origem do cálculo
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_edited_by: Optional[str] = "Sistema"

# OSRM Integration Functions
OSRM_BASE_URL = "http://router.project-osrm.org"

# ── Geoapify Integration ──────────────────────────────────────────────────────
GEOAPIFY_API_KEY = os.environ.get("GEOAPIFY_API_KEY", "01c4cd29f11547d49cbcd136694c775c")
GEOAPIFY_ROUTE_PLANNER_URL = "https://api.geoapify.com/v1/routeplanner"


async def calculate_route_geoapify(stops: list, company_coords: tuple, vehicle_type: str = "CARRO",
                                   start_coords: tuple = None, end_coords: tuple = None,
                                   use_traffic: bool = False) -> dict:
    """Calculate optimized route using Geoapify Route Planner API.
    start_coords/end_coords (lon, lat) permitem ancorar o início/fim da otimização.
    use_traffic=True considera o tráfego médio/típico da região no cálculo da ORDEM."""
    try:
        mode = "drive"  # Geoapify uses drive for both car and motorcycle
        company_lon, company_lat = company_coords
        s_lon, s_lat = start_coords if start_coords else (company_lon, company_lat)
        e_lon, e_lat = end_coords if end_coords else (company_lon, company_lat)
        jobs = []
        for stop in stops:
            jobs.append({
                "id": stop.id,
                "location": [float(stop.address['longitude']), float(stop.address['latitude'])],
                "duration": int(stop.estimated_duration * 60)
            })
        body = {
            "mode": mode,
            "agents": [{
                "start_location": [s_lon, s_lat],
                "end_location":   [e_lon, e_lat],
                "time_windows":   [[0, 86400]]
            }],
            "jobs": jobs
        }
        if use_traffic:
            body["traffic"] = "approximated"
        print(f"🌍 Geoapify: {len(jobs)} jobs, mode={mode}, vehicle={vehicle_type}")
        print(f"📤 Geoapify request body: {json.dumps(body, indent=2)[:500]}")
        resp = requests.post(
            f"{GEOAPIFY_ROUTE_PLANNER_URL}?apiKey={GEOAPIFY_API_KEY}",
            json=body, timeout=30
        )
        if not resp.ok:
            print(f"❌ Geoapify 4xx/5xx: {resp.status_code} - {resp.text[:500]}")
        resp.raise_for_status()
        result = resp.json()
        print(f"✅ Geoapify response: {len(result.get('features', []))} features")
        return result
    except Exception as e:
        print(f"❌ Geoapify API Error: {e}")
        return {"error": str(e)}


GEOAPIFY_ROUTING_URL = "https://api.geoapify.com/v1/routing"

def get_road_geometry_geoapify(ordered_latlng: list, use_traffic: bool = False):
    """Busca o traçado REAL por ruas para uma sequência de pontos já ordenada.
    ordered_latlng = [(lat, lng), ...] incluindo empresa no início e fim.
    use_traffic=True → tempo reflete o tráfego médio/típico da região.
    Retorna (geometry_dict, distance_km, time_min).
    """
    if len(ordered_latlng) < 2:
        return None, 0.0, 0.0
    try:
        waypoints = "|".join(f"{lat},{lng}" for lat, lng in ordered_latlng)
        params = {"waypoints": waypoints, "mode": "drive", "apiKey": GEOAPIFY_API_KEY}
        if use_traffic:
            params["traffic"] = "approximated"
        resp = requests.get(GEOAPIFY_ROUTING_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        feats = data.get("features", [])
        if not feats:
            return None, 0.0, 0.0
        props = feats[0].get("properties", {})
        geom = feats[0].get("geometry")
        return geom, props.get("distance", 0) / 1000, props.get("time", 0) / 60
    except Exception as e:
        print(f"Geoapify routing geometry error: {e}")
        return None, 0.0, 0.0


async def optimize_route_with_priorities_geoapify(stops: list, company_coords: tuple, vehicle_type: str = "CARRO",
                                                  use_traffic: bool = False):
    """Optimize route using Geoapify, respecting manual priorities.
    use_traffic=True → considera tráfego médio/típico da região (ordem + tempo).
    Returns (final_stops, dist_km, travel_min, geometry).
    """
    if not stops:
        return [], 0.0, 0.0, None

    primeira_stops = [s for s in stops if s.priority == Priority.PRIMEIRA]
    ultima_stops   = [s for s in stops if s.priority == Priority.ULTIMA]
    auto_stops     = [s for s in stops if s.priority == Priority.AUTOMATICA]
    print(f"🎯 Geoapify priorities: {len(primeira_stops)} PRIMEIRA / {len(auto_stops)} AUTO / {len(ultima_stops)} ULTIMA")

    optimized_auto    = list(auto_stops)
    total_distance_km = 0.0
    total_travel_min  = 0.0
    route_geometry    = None

    # Ancoragem: o miolo AUTOMÁTICO começa após a última PRIMEIRA e termina antes
    # da primeira ÚLTIMA, dando ao otimizador o contexto geográfico real.
    # (lon, lat) — default = empresa quando não há prioridade. Sem risco de descartar paradas.
    def _coords(stop):
        a = stop.address or {}
        return (float(a["longitude"]), float(a["latitude"])) if a.get("latitude") and a.get("longitude") else None
    start_anchor = _coords(primeira_stops[-1]) if primeira_stops else None
    end_anchor   = _coords(ultima_stops[0])    if ultima_stops   else None

    if auto_stops:
        try:
            result   = await calculate_route_geoapify(auto_stops, company_coords, vehicle_type,
                                                       start_coords=start_anchor, end_coords=end_anchor,
                                                       use_traffic=use_traffic)
            features = result.get('features', [])
            if features:
                feat  = features[0]
                props = feat.get('properties', {})
                geom  = feat.get('geometry')
                total_distance_km = props.get('distance', 0) / 1000
                total_travel_min  = props.get('time', 0) / 60
                if geom:
                    route_geometry = geom
                # Optimized order lives in 'actions' (type='job')
                actions     = props.get('actions', [])
                ordered_ids = [a.get('job_id') for a in actions if a.get('type') == 'job' and a.get('job_id')]
                print(f"📋 Geoapify optimized order: {ordered_ids}")
                if ordered_ids:
                    stop_map  = {s.id: s for s in auto_stops}
                    new_order = [stop_map[jid] for jid in ordered_ids if jid in stop_map]
                    missing   = [s for s in auto_stops if s.id not in set(ordered_ids)]
                    optimized_auto = new_order + missing
                    print(f"✅ Geoapify optimized {len(optimized_auto)} auto stops")
        except Exception as e:
            print(f"⚠️ Geoapify optimization error: {e}, keeping original order")

    final_order = primeira_stops + optimized_auto + ultima_stops
    for i, stop in enumerate(final_order):
        stop.order_sequence = i + 1
        stop.delivery_order = i + 1

    # Traçado REAL por ruas para a ordem final exata (empresa → paradas → empresa).
    # Garante geometria seguindo as vias e distância/tempo corretos para QUALQUER
    # configuração de prioridade — não apenas as paradas automáticas.
    comp_lng, comp_lat = company_coords
    ordered_latlng = [(comp_lat, comp_lng)]
    for s in final_order:
        a = s.address or {}
        if a.get("latitude") and a.get("longitude"):
            ordered_latlng.append((float(a["latitude"]), float(a["longitude"])))
    ordered_latlng.append((comp_lat, comp_lng))

    geom2, dist2, time2 = get_road_geometry_geoapify(ordered_latlng, use_traffic=use_traffic)
    if geom2:
        route_geometry    = geom2
        total_distance_km = dist2
        total_travel_min  = time2

    return final_order, total_distance_km, total_travel_min, route_geometry

def format_coordinates_for_osrm(coordinates: List[Tuple[float, float]]) -> str:
    """Format coordinates for OSRM API (longitude,latitude)"""
    return ";".join([f"{lng},{lat}" for lng, lat in coordinates])

async def calculate_route_osrm(coordinates: List[Tuple[float, float]], vehicle_type: str = "driving", route_type: str = "CURTA") -> dict:
    """Calculate route using OSRM API with different optimization strategies"""
    try:
        coords_str = format_coordinates_for_osrm(coordinates)
        
        if route_type == "EFICIENTE":
            # For efficient routes, try to get more detailed routing with annotations
            url = f"{OSRM_BASE_URL}/trip/v1/{vehicle_type}/{coords_str}"
            params = {
                'source': 'first',  # Start from first coordinate (company)
                'destination': 'last',  # End at last coordinate (company)
                'roundtrip': 'true',
                'steps': 'true',
                'geometries': 'geojson',
                'overview': 'full',
                'annotations': 'true',  # Get additional info for efficiency
            }
        else:
            # For short routes, optimize for distance
            url = f"{OSRM_BASE_URL}/trip/v1/{vehicle_type}/{coords_str}"
            params = {
                'source': 'first',  # Start from first coordinate (company)
                'destination': 'last',  # End at last coordinate (company)
                'roundtrip': 'true',
                'steps': 'true',
                'geometries': 'geojson',
                'overview': 'full'
            }
        
        print(f"🚗 OSRM request: {url}")
        print(f"📊 Route type: {route_type}")
        print(f"📍 Coordinates: {len(coordinates)} points")
        
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        result = response.json()
        print(f"✅ OSRM response received: {len(result.get('trips', []))} trips")
        
        return result
    except Exception as e:
        print(f"❌ OSRM API Error: {e}")
        return {"error": str(e)}

async def calculate_distance_matrix_osrm(coordinates: List[Tuple[float, float]]) -> dict:
    """Calculate distance matrix using OSRM Table API"""
    try:
        coords_str = format_coordinates_for_osrm(coordinates)
        url = f"{OSRM_BASE_URL}/table/v1/driving/{coords_str}"
        
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        return response.json()
    except Exception as e:
        print(f"OSRM Table API Error: {e}")
        return {"error": str(e)}

async def optimize_route_with_priorities(stops: List[RouteStop], company_coords: Tuple[float, float]) -> List[RouteStop]:
    """Optimize route considering manual priorities"""
    
    if not stops:
        return []
    
    # Separate stops by priority
    primeira_stops = [s for s in stops if s.priority == Priority.PRIMEIRA]
    automatica_stops = [s for s in stops if s.priority == Priority.AUTOMATICA]
    ultima_stops = [s for s in stops if s.priority == Priority.ULTIMA]
    
    print(f"Priority separation: PRIMEIRA={len(primeira_stops)}, AUTOMATICA={len(automatica_stops)}, ULTIMA={len(ultima_stops)}")
    
    # Sort PRIMEIRA by distance from company (closest first)
    if primeira_stops:
        def calc_distance(stop):
            stop_coords = (stop.address['longitude'], stop.address['latitude'])
            return ((company_coords[0] - stop_coords[0])**2 + (company_coords[1] - stop_coords[1])**2)**0.5
        
        primeira_stops.sort(key=calc_distance)
    
    # Use OSRM for AUTOMATICA stops optimization
    optimized_automatica = automatica_stops.copy()  # Start with original order as fallback
    
    if automatica_stops and len(automatica_stops) > 1:
        # Only use OSRM if we have multiple stops to optimize
        try:
            # Prepare coordinates for OSRM (include company at start and end)
            coords = [company_coords]  # Start at company
            coords.extend([(s.address['longitude'], s.address['latitude']) for s in automatica_stops])
            coords.append(company_coords)  # End at company
            
            osrm_result = await calculate_route_osrm(coords)
            
            if 'trips' in osrm_result and len(osrm_result['trips']) > 0:
                # Get the optimized waypoint order from OSRM
                waypoints = osrm_result['waypoints']
                optimized_order = []
                
                print(f"🗺️ OSRM returned {len(waypoints)} waypoints")
                
                # Skip first and last waypoints (company positions) and process intermediate waypoints
                intermediate_waypoints = waypoints[1:-1]  # Remove first and last (company)
                
                for i, waypoint in enumerate(intermediate_waypoints):
                    waypoint_index = waypoint.get('waypoint_index', i + 1)  # +1 because we skipped first
                    adjusted_index = waypoint_index - 1  # Adjust for 0-based array indexing (skip company at index 0)
                    
                    print(f"📍 Processing waypoint {i+1}: OSRM_index={waypoint_index}, adjusted_index={adjusted_index}")
                    
                    if 0 <= adjusted_index < len(automatica_stops):
                        original_stop = automatica_stops[adjusted_index]
                        optimized_order.append(original_stop)
                        print(f"✅ Added stop: {original_stop.client_name} (was position {adjusted_index + 1}, now position {len(optimized_order)})")
                    else:
                        print(f"❌ Invalid waypoint index: {adjusted_index} (max: {len(automatica_stops) - 1})")
                
                if optimized_order:
                    optimized_automatica = optimized_order
                    print(f"🚀 OSRM optimization successful: {len(optimized_order)} stops reordered")
                    
                    # Log the final optimized sequence
                    print("📋 Final optimized sequence:")
                    for idx, stop in enumerate(optimized_automatica):
                        print(f"  Position {idx+1}: {stop.client_name} (Priority: {stop.priority})")
                else:
                    print("❌ OSRM returned empty order, using original")
            else:
                print("❌ OSRM response missing trips data, using original order")
        except Exception as e:
            print(f"OSRM optimization failed: {e}, using original order")
    else:
        print(f"Single or no AUTOMATICA stops, skipping OSRM optimization")
    
    # Sort ULTIMA by distance from company (farthest first)
    if ultima_stops:
        def calc_distance_reverse(stop):
            stop_coords = (stop.address['longitude'], stop.address['latitude'])
            return ((company_coords[0] - stop_coords[0])**2 + (company_coords[1] - stop_coords[1])**2)**0.5
        
        ultima_stops.sort(key=calc_distance_reverse, reverse=True)
    
    # Combine in priority order
    final_order = primeira_stops + optimized_automatica + ultima_stops
    
    # Set sequence numbers
    # order_sequence = OSRM geographic optimization order  
    # delivery_order = actual delivery sequence (with priorities)
    
    print("\n🔢 SETTING SEQUENCE NUMBERS:")
    for i, stop in enumerate(final_order):
        stop.delivery_order = i + 1  # This is the actual delivery sequence
        print(f"  Stop {i+1}: {stop.client_name} - delivery_order: {stop.delivery_order}")
    
    # Now set order_sequence based on pure geographic optimization (ignoring priorities)
    # This shows what OSRM would suggest without priority constraints
    geographic_order = primeira_stops + optimized_automatica + ultima_stops
    
    # Calculate distances from company for geographic ordering
    def calc_company_distance(stop):
        stop_coords = (stop.address['longitude'], stop.address['latitude'])
        return ((company_coords[0] - stop_coords[0])**2 + (company_coords[1] - stop_coords[1])**2)**0.5
    
    # Sort by distance for geographic sequence (closest first, farthest last for return efficiency)  
    all_stops_by_distance = sorted(final_order, key=calc_company_distance)
    
    print("\n🗺️ GEOGRAPHIC ORDER (order_sequence):")
    for i, stop in enumerate(all_stops_by_distance):
        # Find this stop in final_order to get its geographic position
        geographic_position = all_stops_by_distance.index(stop) + 1
        stop.order_sequence = geographic_position
        print(f"  Geographic {geographic_position}: {stop.client_name} - order_sequence: {stop.order_sequence}, delivery_order: {stop.delivery_order}")
    
    print(f"\nFinal order: {len(final_order)} stops")
    print("DIFFERENCE EXPLANATION:")
    print("  - order_sequence = Geographic optimization (shortest route)")  
    print("  - delivery_order = Actual delivery sequence (with user priorities)")
    
    return final_order

class RouteCreate(BaseModel):
    vehicle_type: VehicleType
    planned_date: str  # Format: "YYYY-MM-DD"
    planned_start_time: str
    alias: Optional[str] = None  # Custom route name
    stops: List[dict] = []  # Will contain budget_item_ids and priorities

class RouteUpdate(BaseModel):
    vehicle_type: Optional[VehicleType] = None
    planned_date: Optional[str] = None
    planned_start_time: Optional[str] = None
    alias: Optional[str] = None  # Custom route name

class RouteStopUpdate(BaseModel):
    waypoint_index: int
    order_sequence: int

# Google Calendar Models
class CalendarEvent(BaseModel):
    id: Optional[str] = None
    route_id: Optional[str] = None  # Optional for direct events
    stop_id: Optional[str] = None   # Optional for direct events
    budget_item_ids: List[str] = []  # Vínculo direto com item(ns), sem precisar de Rota
    color_id: Optional[str] = None   # Cor gravada no Google no momento da criação/edição
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_datetime: datetime
    end_datetime: datetime
    attendees: Optional[List[str]] = []
    google_event_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class CalendarEventCreate(BaseModel):
    route_id: str
    stop_ids: List[str]  # IDs dos stops selecionados
    start_date: str  # Data no formato YYYY-MM-DD
    start_time: str  # Horário inicial no formato HH:MM

class CalendarEventUpdate(BaseModel):
    summary: Optional[str] = None
    description: Optional[str] = None
    location: Optional[str] = None
    start_datetime: Optional[str] = None
    end_datetime: Optional[str] = None

class GoogleAuthRequest(BaseModel):
    code: str
    redirect_uri: str

class DirectEventCreate(BaseModel):
    summary: str
    description: Optional[str] = None
    location: Optional[str] = None
    start_datetime: str  # ISO format datetime string
    end_datetime: str    # ISO format datetime string
    budget_item_ids: Optional[List[str]] = None  # Vincula direto ao(s) item(ns), sem exigir Rota
    color_id: Optional[str] = None  # '9' cobalto, '3' uva, '5' banana, '11' tomate — default banana se omitido

# SystemConfig class definition starts here
class SystemConfig(BaseModel):
    # Company data
    company_name: Optional[str] = "SuperDry Lavanderia de Tapetes & Estofados"
    address_full: Optional[str] = ""
    address_complement: Optional[str] = ""
    cnpj: Optional[str] = ""
    cep: Optional[str] = ""
    neighborhood: Optional[str] = ""
    city: Optional[str] = ""
    state: Optional[str] = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: Optional[str] = ""
    email: Optional[str] = ""
    website: Optional[str] = ""
    instagram: Optional[str] = ""
    whatsapp: Optional[str] = ""
    
    # Data retention policy
    retention_photos_years: int = 2
    retention_signatures_years: int = 2
    retention_documents_years: int = 2
    retention_action: str = "ANONYMIZE"  # ANONYMIZE or DELETE
    
    # Future: user management fields
    enable_user_management: bool = False

    # Payment methods (customizable)
    payment_methods: List[Dict[str, str]] = Field(default_factory=lambda: [
        {"value": "PIX_CNPJ_25995295000104", "label": "PIX CNPJ 1"},
        {"value": "PIX_CNPJ_30369419000186", "label": "PIX CNPJ 2"},
        {"value": "DINHEIRO",                "label": "Dinheiro"},
        {"value": "CREDITO_1X",              "label": "Crédito 1x"},
        {"value": "CREDITO_2X",              "label": "Crédito 2x"},
        {"value": "CREDITO_3X",              "label": "Crédito 3x"},
        {"value": "CREDITO_4X",              "label": "Crédito 4x"},
        {"value": "CREDITO_5X",              "label": "Crédito 5x"},
        {"value": "CREDITO_6X",              "label": "Crédito 6x"},
        {"value": "CREDITO_7X",              "label": "Crédito 7x"},
        {"value": "CREDITO_8X",              "label": "Crédito 8x"},
        {"value": "CREDITO_9X",              "label": "Crédito 9x"},
        {"value": "CREDITO_10X",             "label": "Crédito 10x"},
        {"value": "CREDITO_11X",             "label": "Crédito 11x"},
        {"value": "CREDITO_12X",             "label": "Crédito 12x"},
        {"value": "DEBITO",                  "label": "Débito"},
        {"value": "BOLETO",                  "label": "Boleto"},
        {"value": "LINK_PAGAMENTO",          "label": "Link de Pagamento"},
        {"value": "TRANSFERENCIA",           "label": "Transferência"},
        {"value": "PERMUTA",                 "label": "Permuta"},
    ])

    # Taxas (%) por forma de pagamento — para estimar o valor LÍQUIDO a receber.
    # Pré-configurado com as taxas de crédito InfinitePay (1x–12x). Demais = 0
    # (ajustável em Configurações). O líquido é estimativa; o valor real liquidado
    # será confirmado pela integração/Open Finance no futuro.
    payment_fees: Dict[str, float] = Field(default_factory=lambda: {
        "PIX_CNPJ_25995295000104": 0.0,
        "PIX_CNPJ_30369419000186": 0.0,
        "DINHEIRO": 0.0,
        "DEBITO": 0.0,
        "BOLETO": 0.0,
        "TRANSFERENCIA": 0.0,
        "PERMUTA": 0.0,
        "LINK_PAGAMENTO": 0.0,
        "CREDITO_1X": 4.20,  "CREDITO_2X": 6.09,  "CREDITO_3X": 7.01,
        "CREDITO_4X": 7.91,  "CREDITO_5X": 8.80,  "CREDITO_6X": 9.67,
        "CREDITO_7X": 12.59, "CREDITO_8X": 13.42, "CREDITO_9X": 14.25,
        "CREDITO_10X": 15.06, "CREDITO_11X": 15.87, "CREDITO_12X": 16.66,
    })

    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BudgetCreate(BaseModel):
    client_id: str
    payment_method: str
    salesperson: str                 # display_name do usuário vendedor
    internal_observations: Optional[str] = None
    budget_observations: Optional[str] = None
    items: Optional[List[dict]] = []
    discount_type: Optional[str] = None    # "fixed" | "percent"
    discount_value: Optional[float] = 0.0  # valor do desconto (R$ ou %)

class DashboardSummary(BaseModel):
    pending_routes: int
    pending_execution_today: int
    items_in_washing: int
    financial_pending: int
    total_clients: int
    active_budgets: int

# Google Places API integration
@api_router.get("/places/search")
async def search_places(query: str):
    """Hybrid search: Places Autocomplete (endereços) + Text Search (locais por nome)"""
    try:
        results = []
        seen_place_ids = set()

        # 1. Places Autocomplete — melhor para endereços digitados
        try:
            autocomplete = gmaps.places_autocomplete(
                query, language='pt-BR', components=[{'country': 'BR'}]
            )
            if isinstance(autocomplete, list):
                for place in autocomplete:
                    if isinstance(place, dict):
                        pid = place.get('place_id')
                        if pid and pid not in seen_place_ids:
                            seen_place_ids.add(pid)
                            results.append({**place, 'source': 'places'})
        except Exception as e:
            print(f"Places autocomplete error: {e}")

        # 2. Text Search — melhor para nomes de locais, condomínios, edifícios, etc.
        try:
            text_response = gmaps.places(query, language='pt-BR', region='br')
            for place in (text_response.get('results') or [])[:5]:
                pid = place.get('place_id')
                if not pid or pid in seen_place_ids:
                    continue
                seen_place_ids.add(pid)
                geo = place.get('geometry', {}).get('location', {})
                name = place.get('name', '')
                addr = place.get('formatted_address', place.get('vicinity', ''))
                description = f"{name} — {addr}" if name and name.lower() not in addr.lower() else addr
                results.insert(0, {   # coloca no topo pois é match por nome
                    'place_id': pid,
                    'description': description,
                    'structured_formatting': {
                        'main_text': name,
                        'secondary_text': addr,
                    },
                    'geometry': {'location': geo} if geo else None,
                    'source': 'text_search',
                })
        except Exception as e:
            print(f"Text search error: {e}")

        # 3. Geocoding — fallback para endereços completos
        try:
            geocoded = gmaps.geocode(query, language='pt-BR')
            for geocode in (geocoded or []):
                pid = geocode.get('place_id')
                if not pid or pid in seen_place_ids:
                    continue
                seen_place_ids.add(pid)
                formatted_address = geocode.get('formatted_address', '')
                parts = [p.strip() for p in formatted_address.split(',')]
                neighborhood = city = state = None
                if len(parts) >= 2:
                    p1 = parts[1]
                    neighborhood = p1.split('-')[1].strip() if '-' in p1 else p1
                if len(parts) >= 3 and '-' in parts[2]:
                    city  = parts[2].split('-')[0].strip()
                    state = parts[2].split('-')[1].strip()
                geo = geocode.get('geometry', {}).get('location', {})
                results.append({
                    'place_id': pid,
                    'description': formatted_address,
                    'structured_formatting': {
                        'main_text': parts[0] if parts else formatted_address,
                        'secondary_text': ', '.join(parts[1:]) if len(parts) > 1 else '',
                    },
                    'neighborhood': neighborhood,
                    'city': city,
                    'state': state,
                    'geometry': {'location': geo} if geo else None,
                    'source': 'geocoding',
                })
        except Exception as e:
            print(f"Geocoding error: {e}")

        return {"results": results}
    except Exception as e:
        print(f"General search error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error searching places: {str(e)}")

@api_router.get("/places/details")
async def get_place_details(place_id: str):
    """Get detailed information about a place using fallback methods"""
    try:
        # First try the official Places API
        try:
            details = gmaps.place(place_id, language='pt-BR')
            return {"details": details}
        except Exception as places_error:
            print(f"Places API Details error: {places_error}")
            
            # Fallback: Use reverse geocoding to get details
            try:
                # First, we need to find the place by place_id using geocoding
                geocode_results = gmaps.geocode(place_id=place_id, language='pt-BR')
                
                if geocode_results and len(geocode_results) > 0:
                    result = geocode_results[0]
                    
                    # Format the response to match Places API structure
                    fallback_details = {
                        'result': {
                            'place_id': result.get('place_id'),
                            'formatted_address': result.get('formatted_address'),
                            'address_components': result.get('address_components', []),
                            'geometry': result.get('geometry', {}),
                            'types': result.get('types', [])
                        }
                    }
                    
                    return {"details": fallback_details}
                else:
                    raise HTTPException(status_code=404, detail="Place not found")
                    
            except Exception as geocode_error:
                print(f"Geocoding fallback error: {geocode_error}")
                raise HTTPException(status_code=404, detail="Unable to get place details")
                
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting place details: {str(e)}")


@api_router.post("/places/resolve-location")
async def resolve_location(payload: Dict[str, Any]):
    """
    Resolve uma localização compartilhada pelo WhatsApp em coordenadas exatas.
    Aceita:
      - Coordenadas cruas: "-15.5918, -56.0618"
      - Link Google Maps: ...?q=lat,lng  /  ...@lat,lng,17z  /  ...!3dlat!4dlng
      - Link curto: maps.app.goo.gl/... ou goo.gl/maps/... (segue o redirect)
    Retorna lat/lng + endereço legível (reverse geocode).
    """
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Cole o link ou as coordenadas da localização.")

    lat = lng = None

    def _extract_coords(s: str):
        # padrões de lat,lng em URL ou texto (Google Maps, Apple Maps, Waze, coords cruas)
        for pat in [
            r'[?&]q=(-?\d+\.\d+),\s*(-?\d+\.\d+)',
            r'[?&]ll=(-?\d+\.\d+),\s*(-?\d+\.\d+)',
            r'[?&]sll=(-?\d+\.\d+),\s*(-?\d+\.\d+)',
            r'coordinate=(-?\d+\.\d+),\s*(-?\d+\.\d+)',   # Apple Maps
            r'@(-?\d+\.\d+),(-?\d+\.\d+)',
            r'!3d(-?\d+\.\d+)!4d(-?\d+\.\d+)',
            r'destination=(-?\d+\.\d+),\s*(-?\d+\.\d+)',
            r'[?&]daddr=(-?\d+\.\d+),\s*(-?\d+\.\d+)',     # Apple "direções para"
            r'^\s*(-?\d+[.,]?\d*)\s*[,;]\s*(-?\d+[.,]?\d*)\s*$',  # coords cruas (vírgula ou ;)
        ]:
            m = re.search(pat, s)
            if m:
                try:
                    return float(m.group(1)), float(m.group(2))
                except ValueError:
                    continue
        return None, None

    lat, lng = _extract_coords(text)

    # Link curto / Apple place → segue o redirect para obter a URL final com coordenadas
    if lat is None and re.search(r'(maps\.app\.goo\.gl|goo\.gl/maps|maps\.google\.[a-z.]+/url|maps\.apple\.com)', text):
        try:
            url_match = re.search(r'https?://\S+', text)
            short_url = url_match.group(0) if url_match else text
            resp = requests.get(short_url, allow_redirects=True, timeout=10,
                                headers={"User-Agent": "Mozilla/5.0"})
            final_url = resp.url
            lat, lng = _extract_coords(final_url)
            if lat is None:
                lat, lng = _extract_coords(resp.text[:5000])
        except Exception as e:
            print(f"Erro ao resolver link curto: {e}")

    if lat is None or lng is None:
        raise HTTPException(status_code=422,
            detail="Não consegui extrair as coordenadas. Cole o link de localização do WhatsApp ou no formato '-15.59, -56.06'.")

    # Reverse geocode para um endereço legível
    full_address = f"Localização GPS ({lat:.5f}, {lng:.5f})"
    neighborhood = city = state = ""
    try:
        rev = gmaps.reverse_geocode((lat, lng), language='pt-BR')
        if rev:
            r0 = rev[0]
            full_address = r0.get('formatted_address', full_address)
            for c in r0.get('address_components', []):
                t = c.get('types', [])
                if 'sublocality' in t or 'neighborhood' in t or 'sublocality_level_1' in t:
                    neighborhood = c.get('long_name', '')
                if 'administrative_area_level_2' in t or 'locality' in t:
                    city = c.get('long_name', '')
                if 'administrative_area_level_1' in t:
                    state = c.get('short_name') or c.get('long_name', '')
    except Exception as e:
        print(f"Reverse geocode falhou: {e}")

    return {
        "latitude": lat, "longitude": lng,
        "full_address": full_address,
        "neighborhood": neighborhood, "city": city, "state": state,
        "source": "WHATSAPP_GPS",
    }


# Client endpoints
@api_router.post("/clients", response_model=Client)
async def create_client(
    client_data: ClientCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    """Criar um novo cliente"""
    try:
        # Generate sequential ID (CLI-0001, CLI-0002...)
        last_client = await db.clients.find_one(sort=[("created_at", -1)])
        if last_client and last_client.get("id", "").startswith("CLI-"):
            try:
                last_id_num = int(last_client["id"].split("-")[1])
            except Exception:
                last_id_num = await db.clients.count_documents({})
            new_id_num = last_id_num + 1
        else:
            new_id_num = 1

        # Garante unicidade
        while await db.clients.find_one({"id": f"CLI-{str(new_id_num).zfill(4)}"}):
            new_id_num += 1

        client_dict = client_data.dict()
        client_dict["id"] = f"CLI-{str(new_id_num).zfill(4)}"
        client_dict["name_normalized"] = normalize_text(client_data.name)
        client_dict["phone_digits"] = only_digits(client_data.phone_primary or "") + \
            ("|" + only_digits(client_data.phone_alternative) if client_data.phone_alternative else "")
        client_dict["cpf_cnpj_digits"] = only_digits(client_data.cpf_cnpj or "")
        client_dict["created_at"] = datetime.utcnow()
        client_dict["updated_at"] = datetime.utcnow()
        client_dict["created_by"] = current_user.id
        client_dict["created_by_name"] = current_user.name
        client_dict["updated_by"] = current_user.id
        client_dict["updated_by_name"] = current_user.name

        client = Client(**client_dict)
        await db.clients.insert_one(client.dict())
        await log_audit("client", client.id, "CREATE", current_user, {"after": client.dict()})
        return client
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating client: {str(e)}")


@api_router.get("/clients", response_model=List[Client])
async def get_clients(
    skip: int = 0,
    limit: int = 1000,
    search: str = None,
    current_user: UserPublic = Depends(get_current_user),
):
    """Listar clientes com busca abrangente (case + acento insensitive)."""
    try:
        query: Dict[str, Any] = {}
        if search:
            norm = normalize_text(search)
            digits = only_digits(search)
            ors: List[Dict[str, Any]] = [
                {"name_normalized": {"$regex": re.escape(norm), "$options": "i"}},
                {"name": {"$regex": re.escape(search), "$options": "i"}},
                {"id": {"$regex": re.escape(search), "$options": "i"}},
                {"email": {"$regex": re.escape(search), "$options": "i"}},
                {"instagram": {"$regex": re.escape(search), "$options": "i"}},
                # Address fields search
                {"address.city": {"$regex": re.escape(search), "$options": "i"}},
                {"address.neighborhood": {"$regex": re.escape(search), "$options": "i"}},
                {"address.full_address": {"$regex": re.escape(search), "$options": "i"}},
            ]
            if digits:
                ors.append({"phone_digits": {"$regex": re.escape(digits)}})
                ors.append({"cpf_cnpj_digits": {"$regex": re.escape(digits)}})
            query = {"$or": ors}

        cursor = db.clients.find(query).sort("name", 1).skip(skip).limit(limit)
        clients = await cursor.to_list(length=limit)
        return [Client(**c) for c in clients]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting clients: {str(e)}")


@api_router.get("/clients/count")
async def get_clients_count(current_user: UserPublic = Depends(get_current_user)):
    total = await db.clients.count_documents({})
    return {"total": total}


@api_router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str, current_user: UserPublic = Depends(get_current_user)):
    """Obter cliente específico"""
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return Client(**client)


@api_router.get("/clients/{client_id}/history")
async def get_client_history(
    client_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """Retorna histórico de itens (todos os orçamentos) do cliente."""
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    cursor = db.budgets.find({"client_id": client_id}).sort("created_at", -1)
    budgets = await cursor.to_list(length=10000)
    rows = []
    for b in budgets:
        budget_id = b.get("id")
        for it in (b.get("items") or []):
            rows.append({
                "budget_id": budget_id,
                "item_id": it.get("id"),
                "service_code": it.get("service_code"),
                "service_name": it.get("service_name"),
                "description": it.get("description") or it.get("observations") or "",
                "measure_type": it.get("measure_type"),
                "quantity": it.get("quantity"),
                "area_m2": it.get("area_m2") or it.get("total_area") or 0,
                "linear_meters": it.get("linear_meters") or 0,
                "unit_value": it.get("unit_value"),
                "total_value": it.get("total_value"),
                "status": it.get("status"),
                "created_at": it.get("created_at") or b.get("created_at"),
            })
    return {"client_id": client_id, "items": rows, "total_items": len(rows)}


@api_router.put("/clients/{client_id}", response_model=Client)
async def update_client(
    client_id: str,
    client_data: ClientCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    """Atualizar cliente"""
    existing = await db.clients.find_one({"id": client_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    update_data = client_data.dict()
    update_data["name_normalized"] = normalize_text(client_data.name)
    update_data["phone_digits"] = only_digits(client_data.phone_primary or "") + \
        ("|" + only_digits(client_data.phone_alternative) if client_data.phone_alternative else "")
    update_data["cpf_cnpj_digits"] = only_digits(client_data.cpf_cnpj or "")
    update_data["updated_at"] = datetime.utcnow()
    update_data["updated_by"] = current_user.id
    update_data["updated_by_name"] = current_user.name

    await db.clients.update_one({"id": client_id}, {"$set": update_data})

    # Capture diff (apenas dos campos relevantes)
    diff = {}
    for k, v in update_data.items():
        if existing.get(k) != v:
            diff[k] = {"before": existing.get(k), "after": v}
    await log_audit("client", client_id, "UPDATE", current_user, {"diff": diff})

    updated_client = await db.clients.find_one({"id": client_id})
    return Client(**updated_client)


@api_router.delete("/clients/{client_id}")
async def delete_client(
    client_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """Excluir cliente (apenas admin/atendente)."""
    if current_user.role not in (UserRole.ADMIN, UserRole.ATENDENTE):
        raise HTTPException(status_code=403, detail="Sem permissão para excluir clientes")
    existing = await db.clients.find_one({"id": client_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Client not found")

    # Bloqueio se houver orçamentos vinculados
    bcount = await db.budgets.count_documents({"client_id": client_id})
    if bcount > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cliente possui {bcount} orçamento(s) vinculado(s) e não pode ser excluído.",
        )

    result = await db.clients.delete_one({"id": client_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
    await log_audit("client", client_id, "DELETE", current_user, {"before": existing})
    return {"message": "Client deleted successfully"}

# Service catalog endpoints
@api_router.post("/services", response_model=Service)
async def create_service(service_data: ServiceCreate):
    """Criar um novo serviço"""
    try:
        # Generate sequential ID: busca o maior número já usado, não apenas o último inserido
        # Isso evita colisão quando o created_at mais recente não é o de maior ID
        all_services = await db.services.find(
            {"id": {"$regex": r"^SRV-\d+$"}}, {"id": 1}
        ).to_list(length=None)
        if all_services:
            max_num = max(int(s["id"].split("-")[1]) for s in all_services if s.get("id", "").startswith("SRV-"))
            new_id_num = max_num + 1
        else:
            new_id_num = 1

        # Garante unicidade (igual ao endpoint de clientes)
        while await db.services.find_one({"id": f"SRV-{str(new_id_num).zfill(4)}"}):
            new_id_num += 1

        service_dict = service_data.dict()
        service_dict["id"] = f"SRV-{str(new_id_num).zfill(4)}"
        service_dict["created_at"] = datetime.utcnow()
        service_dict["updated_at"] = datetime.utcnow()

        service = Service(**service_dict)

        await db.services.insert_one(service.dict())
        return service
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating service: {str(e)}")

@api_router.get("/services", response_model=List[Service])
async def get_services(
    skip: int = 0, 
    limit: int = 100, 
    category: Optional[ServiceCategory] = None,
    search: str = None,
    include_inactive: bool = False
):
    """Listar serviços"""
    try:
        query = {}
        if not include_inactive:
            query["is_active"] = True
        if category:
            query["category"] = category
        if search:
            query["$or"] = [
                {"name": {"$regex": search, "$options": "i"}},
                {"id": {"$regex": search, "$options": "i"}}
            ]
        
        cursor = db.services.find(query).skip(skip).limit(limit)
        services = await cursor.to_list(length=limit)
        return [Service(**service) for service in services]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting services: {str(e)}")

@api_router.get("/services/{service_id}", response_model=Service)
async def get_service(service_id: str):
    """Obter serviço específico"""
    service = await db.services.find_one({"id": service_id})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return Service(**service)

@api_router.put("/services/{service_id}", response_model=Service)
async def update_service(service_id: str, service_data: ServiceCreate):
    """Atualizar serviço"""
    service = await db.services.find_one({"id": service_id})
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    
    update_data = service_data.dict()
    update_data["updated_at"] = datetime.utcnow()
    
    await db.services.update_one({"id": service_id}, {"$set": update_data})
    
    updated_service = await db.services.find_one({"id": service_id})
    return Service(**updated_service)

@api_router.put("/services/{service_id}/deactivate")
async def deactivate_service(service_id: str):
    """Inativar serviço"""
    result = await db.services.update_one(
        {"id": service_id}, 
        {"$set": {"is_active": False, "updated_at": datetime.utcnow()}}
    )
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Service not found")
    return {"message": "Service deactivated successfully"}

@api_router.post("/services/migrate-default-status")
async def migrate_services_default_status():
    """Migrate existing services to add default_service_status field"""
    try:
        # Find services without default_service_status field
        services_to_update = await db.services.find({"default_service_status": {"$exists": False}}).to_list(None)
        
        updated_count = 0
        for service in services_to_update:
            # Apply same logic as before: RETIRADA -> RETIRAR, others -> EXECUTAR_NO_LOCAL
            default_status = ServiceStatus.RETIRAR if service.get("execution_location") == ExecutionLocation.RETIRADA else ServiceStatus.EXECUTAR_NO_LOCAL
            
            await db.services.update_one(
                {"id": service["id"]},
                {"$set": {"default_service_status": default_status, "updated_at": datetime.utcnow()}}
            )
            updated_count += 1
        
        return {
            "message": f"Migration completed successfully", 
            "updated_services": updated_count
        }
    except Exception as e:
        logger.error(f"Error migrating services: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/budget-items/fix-status")
async def fix_budget_items_status():
    """Fix status of existing budget items based on service default_service_status"""
    try:
        # Get all budgets with items
        budgets = await db.budgets.find({}).to_list(None)
        
        total_items_fixed = 0
        budgets_updated = 0
        
        for budget in budgets:
            items = budget.get('items', [])
            items_updated = False
            
            for item in items:
                service_id = item.get('service_id')
                if not service_id:
                    continue
                
                # Get the service to check its default_service_status
                service = await db.services.find_one({"id": service_id})
                if not service:
                    logger.warning(f"Service {service_id} not found for item {item.get('id')}")
                    continue
                
                service_default_status = service.get('default_service_status')
                current_item_status = item.get('status')
                
                # Only update if status is different and service has default_service_status
                if service_default_status and current_item_status != service_default_status:
                    item['status'] = service_default_status
                    items_updated = True
                    total_items_fixed += 1
                    logger.info(f"Fixed item {item.get('id')} status: {current_item_status} -> {service_default_status}")
            
            # Update budget if any items were changed
            if items_updated:
                await db.budgets.update_one(
                    {"id": budget["id"]},
                    {"$set": {"items": items, "updated_at": datetime.utcnow()}}
                )
                budgets_updated += 1
        
        return {
            "message": f"Status fix completed successfully",
            "items_fixed": total_items_fixed,
            "budgets_updated": budgets_updated
        }
    except Exception as e:
        logger.error(f"Error fixing budget items status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Google Calendar endpoints
@api_router.get("/calendar/auth-url")
async def get_google_auth_url(app_url: str = ""):
    """Get Google OAuth authorization URL. app_url is the frontend origin (passed as state)."""
    try:
        flow = get_google_auth_flow()
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',
            state=app_url  # relay page uses this to redirect back to the correct app
        )
        return {"auth_url": authorization_url}
    except Exception as e:
        logger.error(f"Error generating auth URL: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/calendar/auth")
async def authenticate_google_calendar(auth_request: GoogleAuthRequest):
    """Exchange authorization code for credentials"""
    try:
        flow = get_google_auth_flow()
        flow.redirect_uri = auth_request.redirect_uri
        
        # Exchange authorization code for credentials
        flow.fetch_token(code=auth_request.code)
        credentials = flow.credentials
        
        # Store credentials in database (in a real app, you'd want to encrypt these)
        credentials_dict = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        
        # For simplicity, storing in a simple collection - in production, associate with user
        await db.calendar_credentials.delete_many({})  # Remove old credentials
        await db.calendar_credentials.insert_one({
            "credentials": credentials_dict,
            "created_at": datetime.utcnow()
        })
        
        return {"message": "Calendar authentication successful"}
    except Exception as e:
        logger.error(f"Error authenticating calendar: {e}")
        raise HTTPException(status_code=500, detail=str(e))

def calculate_optimized_durations(stops):
    """
    Calcula durações otimizadas considerando múltiplos itens no mesmo local
    - EXECUTAR_NO_LOCAL: 90 minutos (1h30m)
    - RETIRAR/ENTREGAR: 30 minutos
    - Arredondamentos de 10 em 10 minutos, sempre para cima
    """
    if not stops:
        return {}
    
    def round_up_to_tens(minutes):
        """Arredonda para cima de 10 em 10 minutos"""
        return int(math.ceil(minutes / 10) * 10)
    
    # Agrupar stops por localização (coordenadas ou endereço)
    location_groups = {}
    
    for stop in stops:
        address = stop.get("address", {})
        lat = address.get("latitude")
        lng = address.get("longitude")
        
        # Usar coordenadas se disponíveis, senão usar endereço completo
        if lat and lng:
            location_key = f"{lat},{lng}"
        else:
            location_key = address.get("full_address", f"stop_{stop['id']}")
        
        if location_key not in location_groups:
            location_groups[location_key] = []
        location_groups[location_key].append(stop)
    
    # Calcular durações otimizadas para cada grupo
    duration_map = {}
    
    for location_key, location_stops in location_groups.items():
        if len(location_stops) == 1:
            # Item único no local - usar duração padrão
            stop = location_stops[0]
            if stop["service_status"] == "EXECUTAR_NO_LOCAL":
                duration_map[stop["id"]] = 90  # 1h30m (90 minutes)
            else:
                duration_map[stop["id"]] = 30   # 30 minutes
        else:
            # Múltiplos itens no mesmo local - aplicar otimização
            base_duration = 0
            has_execution = False
            
            for stop in location_stops:
                if stop["service_status"] == "EXECUTAR_NO_LOCAL":
                    base_duration += 90  # Atualizado para 90 minutos
                    has_execution = True
                else:
                    base_duration += 30
            
            # Aplicar redução por eficiência quando há múltiplos itens
            if len(location_stops) >= 2:
                if has_execution:
                    # Se há execução no local, reduzir menos (15%)
                    optimized_duration = base_duration * 0.85
                else:
                    # Apenas coletas/entregas, reduzir mais (25%)
                    optimized_duration = base_duration * 0.75
                
                # Arredondar para cima de 10 em 10 minutos
                optimized_duration = round_up_to_tens(optimized_duration)
            else:
                optimized_duration = base_duration
            
            # Distribuir duração otimizada proporcionalmente
            total_base = sum(90 if s["service_status"] == "EXECUTAR_NO_LOCAL" else 30 for s in location_stops)
            
            for stop in location_stops:
                individual_base = 90 if stop["service_status"] == "EXECUTAR_NO_LOCAL" else 30
                proportional_duration = (individual_base / total_base) * optimized_duration
                # Arredondar para cima de 10 em 10 minutos, mínimo 20 minutos
                duration_map[stop["id"]] = max(round_up_to_tens(proportional_duration), 20)
    
    return duration_map

# -- Geracao automatica de titulo/emoji de eventos de agenda ------------------
def _emoji_categoria_servico(service_category: str, service_name: str) -> str:
    """Emoji principal pelo tipo de item (tapete tem prioridade sobre a categoria)."""
    cat = (service_category or "").upper()
    nome = (service_name or "").lower()

    if cat in ("TAPETES", "CARPETES_E_TAPETES_NO_LOCAL") or "tapete" in nome or "carpete" in nome:
        return "🗞️"
    if "edredom" in nome or "edredon" in nome or "colcha" in nome:
        return "🧺"
    if cat == "COLCHOES" or cat == "BOX" or "colch" in nome or "pillowtop" in nome or "box" in nome:
        return "🛏️"
    if cat == "CORTINAS" or "cortina" in nome:
        return "📜"
    if cat == "PERSIANAS" or "persiana" in nome:
        return "📜"
    if cat == "VEICULOS" or "veiculo" in nome or "banco de carro" in nome:
        return "🚘"
    if cat == "ITENS_INFANTIS" or "carrinho" in nome or "bebe conforto" in nome or "cadeirinha" in nome:
        return "🛒"
    if cat == "ESTOFADOS":
        if "sofa" in nome:
            return "🛋️"
        if "cadeira" in nome:
            return "🪑"
        if "poltrona" in nome:
            return "💺"
        return "🛋️"
    return ""


def _palavra_acao(service_status: str) -> Optional[str]:
    """Palavra de acao exibida no titulo -- so pra retirada/entrega separada."""
    if service_status == "RETIRAR":
        return "Retirar"
    if service_status == "ENTREGAR":
        return "Entregar"
    return None


def _eh_venda_proprietario(salesperson: Optional[str]) -> bool:
    """Marcador de venda feita diretamente por Diego ou Daiana (so identificacao visual)."""
    sp = (salesperson or "").lower()
    return "diego" in sp or "daiana" in sp


async def _montar_titulo_evento(budget_item_id: str, client_name: str, service_status: str,
                                  service_name_fallback: str = "") -> str:
    """
    Monta o titulo do evento de agenda no padrao da empresa:
    {emojis}{acao opcional} {cliente}
    Busca o item/orcamento pra achar categoria, nome do servico e vendedor.
    """
    emojis = []
    palavra_acao = _palavra_acao(service_status)
    service_name = service_name_fallback
    observations = ""
    salesperson = None

    if budget_item_id:
        budget = await db.budgets.find_one(
            {"items.id": budget_item_id}, {"items.$": 1, "salesperson": 1}
        )
        if budget:
            salesperson = budget.get("salesperson")
            items = budget.get("items") or []
            if items:
                item = items[0]
                service_name = item.get("service_name") or service_name_fallback
                observations = item.get("observations") or ""

    cat_emoji = _emoji_categoria_servico(None, service_name)
    if cat_emoji:
        emojis.append(cat_emoji)

    nome_lower = (service_name or "").lower()
    obs_lower = (observations or "").lower()
    if "imperm" in nome_lower or "imperm" in obs_lower:
        emojis.append("💦")

    if _eh_venda_proprietario(salesperson):
        emojis.append("🏷️")

    prefixo = "".join(emojis)
    partes = [p for p in (prefixo, palavra_acao, client_name) if p]
    return " ".join(partes)


def _build_event_summary_and_description(
    items: list,
    client_name: str,
    client_phone: str,
    salesperson: str,
    budget_id: str,
    payment_method: str,
    notes: str,
    complement: str,
    location_text: str,
    sched_fmt: str,
    item_status: str,
) -> tuple:
    """
    Gera título (com emoji) + descrição (emojizada) + duração em minutos pra um
    evento de agenda criado a partir de um orçamento inteiro -- mesmo padrão
    visual usado no lançamento em lote da Agenda (generateEventTitle /
    formatEventDescription no frontend), só que em Python, pra ser usado por
    qualquer caminho que crie eventos no backend (hoje: automação com IA com
    launch_agenda=true). Existir só uma vez aqui evita ter um 3º padrão
    diferente de título/descrição cada vez que um novo caminho de criação
    de evento for escrito.
    """
    emojis = []
    seen = set()
    for it in items:
        e = _emoji_categoria_servico(it.get("service_category"), it.get("service_name", ""))
        if e and e not in seen:
            emojis.append(e)
            seen.add(e)
        nome_lower = (it.get("service_name") or "").lower()
        obs_lower = (it.get("observations") or "").lower()
        if ("imperm" in nome_lower or "imperm" in obs_lower) and "💦" not in seen:
            emojis.append("💦")
            seen.add("💦")

    if _eh_venda_proprietario(salesperson):
        emojis.insert(0, "🏷️")

    palavra_acao = _palavra_acao(item_status)
    prefixo = "".join(emojis)
    summary = " ".join(p for p in (prefixo, palavra_acao, client_name) if p)

    duration_minutes = 90 if item_status == "EXECUTAR_NO_LOCAL" else 30

    total_val = sum(float(it.get("value", 0)) for it in items)
    desc_lines = [
        f"🧾 Código do Orçamento: {budget_id}",
        f"👤 Cliente: {client_name}" + (f" | {client_phone}" if client_phone else ""),
        f"🧑‍💼 Atendente: {salesperson}",
        f"📍 Endereço: {location_text or 'Não informado'}",
        f"🏠 Complemento: {complement or 'NENHUM'}",
        f"📅 Data do Orçamento: {sched_fmt or datetime.utcnow().strftime('%d/%m/%Y')}",
        f"💳 Forma de Pagamento: {payment_method}",
        f"📝 Observações Internas: {notes or 'Nenhuma observação'}",
        "",
        f"📦 Quantidade de Itens: {len(items)}",
    ]
    for it in items:
        emoji = _emoji_categoria_servico(it.get("service_category"), it.get("service_name", ""))
        qty = int(it.get("quantity") or 1)
        val = float(it.get("value") or 0)
        line = f"- {emoji} {it.get('service_name', 'Serviço')} - {qty} unid. - R$ {val:.2f}"
        obs = (it.get("observations") or "").strip()
        if obs:
            line += f" (Obs: {obs})"
        desc_lines.append(line)
    desc_lines.append("")
    desc_lines.append(f"💰 VALOR TOTAL: R$ {total_val:.2f}")

    description = "\n".join(desc_lines)
    return summary, description, duration_minutes


@api_router.post("/calendar/events")
async def create_calendar_events(event_request: CalendarEventCreate):
    """Create calendar events from route stops"""
    try:
        # Get credentials from database
        creds_doc = await db.calendar_credentials.find_one({})
        if not creds_doc:
            raise HTTPException(status_code=400, detail="Google Calendar not authenticated")
        
        # Get route details
        route = await db.routes.find_one({"id": event_request.route_id})
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Create calendar service
        service = get_calendar_service(creds_doc["credentials"])
        
        # Parse start date and time
        start_date = datetime.strptime(event_request.start_date, "%Y-%m-%d").date()
        start_time = datetime.strptime(event_request.start_time, "%H:%M").time()
        current_datetime = datetime.combine(start_date, start_time)
        
        # Get selected stops
        selected_stops = [s for s in route.get("stops", []) if s["id"] in event_request.stop_ids]
        
        # Calculate optimized durations considering multiple items at same location
        duration_map = calculate_optimized_durations(selected_stops)
        
        created_events = []
        
        # Create events for selected stops
        for stop_id in event_request.stop_ids:
            # Find the stop in route
            stop = next((s for s in route.get("stops", []) if s["id"] == stop_id), None)
            if not stop:
                continue
            
            # Use optimized duration
            duration_minutes = duration_map.get(stop_id, 30)  # Fallback to 30 minutes
            
            end_datetime = current_datetime + timedelta(minutes=duration_minutes)
            
            # Create Google Calendar event
            titulo_evento = await _montar_titulo_evento(
                budget_item_id=stop.get("budget_item_id"),
                client_name=stop["client_name"],
                service_status=stop["service_status"],
                service_name_fallback=stop.get("service_name", ""),
            )
            event = {
                'summary': titulo_evento,
                'description': f'Serviço: {stop["service_name"]}\nValor: R$ {stop["service_value"]:.2f}\nVeículo: {route.get("vehicle_type", "N/A")}',
                'location': stop.get("address", {}).get("full_address", ""),
                'start': {
                    'dateTime': current_datetime.isoformat(),
                    'timeZone': 'America/Cuiaba',
                },
                'end': {
                    'dateTime': end_datetime.isoformat(),
                    'timeZone': 'America/Cuiaba',
                },
                'colorId': '5'  # Amarelo banana para eventos do sistema SuperDry
            }
            
            # Create event in Google Calendar
            google_event = service.events().insert(calendarId='primary', body=event).execute()
            
            # Store event in database
            calendar_event = CalendarEvent(
                id=f"CAL-{str(uuid.uuid4().int)[:7].zfill(7)}",
                route_id=event_request.route_id,
                stop_id=stop_id,
                summary=event['summary'],
                description=event['description'],
                location=event.get('location'),
                start_datetime=current_datetime,
                end_datetime=end_datetime,
                google_event_id=google_event['id']
            )
            
            await db.calendar_events.insert_one(calendar_event.dict())
            created_events.append(calendar_event.dict())
            
            # Update current time for next event (add travel time)
            current_datetime = end_datetime + timedelta(minutes=15)  # 15 min travel time
        
        return {
            "message": f"Created {len(created_events)} calendar events",
            "events": created_events
        }
        
    except Exception as e:
        logger.error(f"Error creating calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Additional endpoint for updating budget item status
class TechnicianAssignment(BaseModel):
    id: str = Field(default_factory=lambda: f"TASS-{str(uuid.uuid4())[:8]}")
    route_id: Optional[str] = None
    event_ids: List[str] = []
    technician_id: str
    assigned_date: str
    assignment_type: str = "AGENDA"  # "AGENDA" | "STATUS_BASED" | "MANUAL"
    status: str = "ASSIGNED"  # "ASSIGNED" | "IN_PROGRESS" | "COMPLETED"
    # item_schedule: ordem/prioridade que o técnico vê, por item (event_id -> dados).
    # scheduled_time ("HH:MM") vem automático de onde o item foi originado (rota calculada
    # pela Geoapify, ou horário do evento na Agenda) quando existir; manual_priority é a
    # edição rápida do Diego que, quando preenchida, tem autoridade sobre o horário.
    # Resolução de ordem (ver get_technician_daily_tasks): manual_priority > scheduled_time
    # > ordem de chegada (fallback de sempre, sem quebrar nada que já funcionava).
    item_schedule: Dict[str, Dict[str, Any]] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

@api_router.patch("/items/{item_id}/desist")
async def mark_client_desisted(item_id: str, current_user: UserPublic = Depends(get_current_user)):
    """Marca item como 'cliente desistiu' — mantém no histórico, sai das rotas."""
    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    await _update_item_fields(item_id, {"client_desisted": True}, current_user)
    await _append_to_item_array(item_id, "status_history", {
        "status": item.get("status"), "at": datetime.utcnow().isoformat(),
        "by_user_id": current_user.id, "by_user_name": current_user.name,
        "notes": "Cliente desistiu — item inabilitado para rota"
    })
    await log_audit("item", item_id, "CLIENT_DESISTED", current_user, {})
    return {"success": True}


@api_router.patch("/items/{item_id}/reactivate")
async def reactivate_item(item_id: str, current_user: UserPublic = Depends(get_current_user)):
    """Reativa item que estava marcado como desistência — volta a aparecer nas rotas."""
    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    if not item.get("client_desisted"):
        raise HTTPException(status_code=400, detail="Item não está marcado como desistência.")
    await _update_item_fields(item_id, {"client_desisted": False}, current_user)
    await _append_to_item_array(item_id, "status_history", {
        "status": item.get("status"), "at": datetime.utcnow().isoformat(),
        "by_user_id": current_user.id, "by_user_name": current_user.name,
        "notes": "Item reativado — voltou a aparecer nas rotas"
    })
    await log_audit("item", item_id, "ITEM_REACTIVATED", current_user, {})
    return {"success": True}


@api_router.post("/technician/finalize-today")
async def finalize_today_agenda(
    date: str = Query(default=None),
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Finaliza a agenda de uma data (padrão = hoje):
    - Itens finalizados (EXECUTADO/ENTREGUE/BUSCOU) → já no fluxo financeiro
    - Itens coletados (COLETADO/EM_LAVAGEM*) → já no modo empresa
    - Itens sem execução → libera rota para reagendamento
    - Cancelados → mantém status, libera rota
    Assignments da data → marcados como COMPLETED
    """
    from datetime import date as _date
    today = date or _date.today().isoformat()

    FINAL_STATUSES   = {"EXECUTADO", "ENTREGUE", "BUSCOU", "ENTREGUE"}
    EMPRESA_STATUSES = {"COLETADO", "EM_LAVAGEM", "EM_LAVAGEM_PARCEIRO",
                        "AGUARDANDO_ENTREGA", "AGUARDANDO_BUSCAR"}
    PENDING_STATUSES = {"RETIRAR", "EXECUTAR_NO_LOCAL", "ENTREGAR",
                        "AGUARDANDO_ENTREGA", "AGENDADO"}

    results = {"rescheduled": 0, "finalized": 0, "empresa": 0,
               "cancelled": 0, "assignments_completed": 0}

    # Busca assignments de hoje
    assignments = await db.technician_assignments.find(
        {"assigned_date": today, "status": {"$ne": "CANCELLED"}}
    ).to_list(None)

    processed_items: set = set()

    for asgn in assignments:
        for item_id in (asgn.get("event_ids") or []):
            if item_id in processed_items:
                continue
            processed_items.add(item_id)

            budget, item = await _find_budget_and_item(item_id)
            if not item:
                continue

            status = item.get("status", "")

            if status in FINAL_STATUSES:
                results["finalized"] += 1
                # Já está no fluxo correto, sem ação

            elif status in EMPRESA_STATUSES:
                results["empresa"] += 1
                # Já está no modo empresa, sem ação

            elif status == "CANCELADO_PELO_CLIENTE":
                results["cancelled"] += 1
                # Libera vínculo de rota
                await _update_item_fields(item_id, {
                    "current_route_id": None,
                    "current_route_stop_id": None
                }, current_user)

            else:
                # Não executado → reagendar (volta para disponibilidade de rota)
                await _update_item_fields(item_id, {
                    "current_route_id": None,
                    "current_route_stop_id": None
                }, current_user)
                await _append_to_item_array(item_id, "status_history", {
                    "status": status,
                    "at": datetime.utcnow().isoformat(),
                    "by_user_id": current_user.id,
                    "by_user_name": current_user.name,
                    "notes": "Reagendado automaticamente ao finalizar agenda do dia"
                })
                results["rescheduled"] += 1

        # Marca assignment como COMPLETED
        await db.technician_assignments.update_one(
            {"id": asgn["id"]},
            {"$set": {"status": "COMPLETED", "updated_at": datetime.utcnow()}}
        )
        results["assignments_completed"] += 1

    await log_audit("system", "FINALIZE_TODAY", "FINALIZE_TODAY", current_user, {
        "date": today, "results": results
    })
    return {"success": True, "date": today, "results": results}


@api_router.post("/technician/assign-events")
async def assign_events_to_technician(assignment: TechnicianAssignment):
    """Assign events/items to technician"""
    try:
        # Salvar assignment no MongoDB
        assignment_dict = assignment.dict()
        assignment_dict['created_at'] = assignment.created_at.isoformat()
        assignment_dict['updated_at'] = assignment.updated_at.isoformat()
        
        result = await db.technician_assignments.insert_one(assignment_dict)
        
        return {
            "success": True,
            "assignment_id": assignment.id,
            "events_assigned": len(assignment.event_ids),
            "technician_id": assignment.technician_id
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error assigning events: {str(e)}")

@api_router.get("/technician/{technician_id}/daily-tasks")
async def get_technician_daily_tasks(
    technician_id: str,
    date: str = Query(default=datetime.now().strftime('%Y-%m-%d')),
    all: bool = Query(default=False)
):
    """Get hybrid tasks for technician (agenda + status-based).
    Pass all=true to return every pending assignment regardless of date."""
    try:
        tasks = {"agenda_events": [], "status_items": [], "assignments": []}

        # Build query — when all=true skip date filter
        query: dict = {
            "technician_id": technician_id,
            "status": {"$in": ["ASSIGNED", "IN_PROGRESS"]}
        }
        if not all:
            query["assigned_date"] = date

        assignments_cursor = await db.technician_assignments.find(query).to_list(None)

        assignments = []
        for assignment in assignments_cursor:
            assignment_dict = {
                "id": assignment.get("id"),
                "route_id": assignment.get("route_id"),
                "event_ids": assignment.get("event_ids", []),
                "technician_id": assignment.get("technician_id"),
                "assigned_date": assignment.get("assigned_date"),
                "assignment_type": assignment.get("assignment_type", "AGENDA"),
                "status": assignment.get("status"),
                "created_at": assignment.get("created_at"),
                "updated_at": assignment.get("updated_at")
            }
            assignments.append(assignment_dict)

        tasks["assignments"] = assignments

        # Desencapsular assignments em itens individuais (apenas ITM-* válidos)
        for assignment in assignments:
            for event_id in assignment.get("event_ids", []):
                if not event_id.startswith('ITM-'):
                    continue
                budget_found = None
                item_found = None
                async for budget in db.budgets.find({"items.id": event_id}):
                    for item in budget.get("items", []):
                        if item.get("id") == event_id:
                            budget_found = budget
                            item_found = item
                            break
                    if item_found:
                        break

                if budget_found and item_found:
                    client = await db.clients.find_one({"id": budget_found.get("client_id")})
                    item_sched = (assignment.get("item_schedule") or {}).get(event_id, {}) or {}
                    tasks["status_items"].append({
                        "id": item_found.get("id"),
                        "budget_id": budget_found.get("id"),
                        "client_id": budget_found.get("client_id"),
                        "client_name": client.get("name") if client else "Cliente não encontrado",
                        "client_address": client.get("address") if client else {},
                        "client_phone": client.get("phone_primary") if client else "",
                        "service_name": item_found.get("service_name"),
                        "service_value": item_found.get("total_value", 0),
                        "status": item_found.get("status"),
                        "observations": item_found.get("observations", ""),
                        "internal_observations": budget_found.get("internal_observations", ""),
                        "budget_observations": budget_found.get("budget_observations", ""),
                        "assignment_id": assignment.get("id"),
                        "assignment_type": assignment.get("assignment_type"),
                        "assignment_status": assignment.get("status"),
                        "assigned_date": assignment.get("assigned_date"),
                        "route_id": assignment.get("route_id"),
                        "scheduled_time": item_sched.get("scheduled_time"),
                        "manual_priority": item_sched.get("manual_priority"),
                    })
                # ITM não encontrado → ignora silenciosamente (não gera ÓRFÃO)

        # Ordem final: manual_priority (menor primeiro) > scheduled_time (HH:MM) >
        # ordem de chegada (posição original — mesma lógica que já existia, preservada
        # como fallback pra não quebrar nada que já funcionava sem essas infos novas).
        for idx, it in enumerate(tasks["status_items"]):
            it["_arrival_order"] = idx
        def _sort_key(it):
            mp = it.get("manual_priority")
            st = it.get("scheduled_time")
            if mp is not None:
                return (0, mp, it["_arrival_order"])
            if st:
                return (1, st, it["_arrival_order"])
            return (2, "", it["_arrival_order"])
        tasks["status_items"].sort(key=_sort_key)
        for idx, it in enumerate(tasks["status_items"]):
            it["order_index"] = idx
            it.pop("_arrival_order", None)

        return tasks

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting technician tasks: {str(e)}")

@api_router.patch("/technician/assignment/{assignment_id}/item-schedule")
async def update_assignment_item_schedule(
    assignment_id: str,
    body: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user),
):
    """Edição rápida de horário previsto / prioridade manual de 1 item dentro de uma
    assignment já enviada ao técnico — não precisa reenviar a lista toda.
    Body: {item_id, scheduled_time?: "HH:MM"|None, manual_priority?: int|None}
    manual_priority=None volta ao neutro (passa a obedecer scheduled_time/ordem de chegada).
    """
    item_id = body.get("item_id")
    if not item_id:
        raise HTTPException(status_code=400, detail="item_id é obrigatório")

    asgn = await db.technician_assignments.find_one({"id": assignment_id})
    if not asgn:
        raise HTTPException(status_code=404, detail="Assignment não encontrada")

    fields = {}
    if "scheduled_time" in body:
        fields["scheduled_time"] = body["scheduled_time"]
    if "manual_priority" in body:
        fields["manual_priority"] = body["manual_priority"]

    await db.technician_assignments.update_one(
        {"id": assignment_id},
        {"$set": {f"item_schedule.{item_id}": {
            **(asgn.get("item_schedule", {}).get(item_id, {})), **fields,
        }, "updated_at": datetime.utcnow()}},
    )
    return {"success": True}


@api_router.put("/technician/assignment/{assignment_id}/status")
async def update_assignment_status(assignment_id: str, status: str):
    """Update technician assignment status"""
    try:
        result = await db.technician_assignments.update_one(
            {"id": assignment_id},
            {"$set": {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Assignment not found")
        
        return {"success": True, "assignment_id": assignment_id, "new_status": status}
        
    except HTTPException:
        # Re-raise HTTPExceptions (like 404) without wrapping them
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating assignment: {str(e)}")

@api_router.post("/technician/create-test-assignments")
async def create_test_assignments_for_tech001():
    """Criar assignments de teste para TECH-001 para demonstrar funcionalidade"""
    try:
        # Buscar budget items válidos para criar assignments
        budgets = await db.budgets.find({}).to_list(None)
        
        valid_items = []
        for budget in budgets:
            if budget.get('items'):
                for item in budget['items']:
                    if item.get('status') in ['RETIRAR', 'EXECUTAR_NO_LOCAL', 'ENTREGAR']:
                        valid_items.append({
                            'budget_item_id': item.get('id'),
                            'budget_id': budget.get('id'),
                            'client_name': budget.get('client_name', 'Cliente'),
                            'service_name': item.get('service_name', 'Serviço')
                        })
        
        if len(valid_items) < 1:
            raise HTTPException(status_code=400, detail="Não há itens suficientes para criar assignments de teste")
        
        # Criar assignments de teste para hoje
        today = datetime.now().strftime('%Y-%m-%d')
        created_assignments = []
        
        # Assignment 1: Com item disponível
        assignment1 = TechnicianAssignment(
            route_id="RTE-TEST001",
            event_ids=[valid_items[0]['budget_item_id']],
            technician_id="TECH-001",
            assigned_date=today,
            assignment_type="AGENDA",
            status="ASSIGNED"
        )
        
        # Se há mais de 1 item, criar segundo assignment
        assignments_to_create = [assignment1]
        if len(valid_items) > 1:
            assignment2 = TechnicianAssignment(
                route_id="RTE-TEST002", 
                event_ids=[valid_items[1]['budget_item_id']],
                technician_id="TECH-001",
                assigned_date=today,
                assignment_type="MANUAL",
                status="ASSIGNED"
            )
            assignments_to_create.append(assignment2)
        
        # Salvar assignments no banco
        for assignment in assignments_to_create:
            assignment_dict = assignment.dict()
            assignment_dict['created_at'] = assignment.created_at.isoformat()
            assignment_dict['updated_at'] = assignment.updated_at.isoformat()
            
            await db.technician_assignments.insert_one(assignment_dict)
            created_assignments.append(assignment.id)
        
        return {
            "success": True,
            "message": f"Criados {len(created_assignments)} assignments de teste para TECH-001",
            "assignment_ids": created_assignments,
            "date": today,
            "items_used": [item['budget_item_id'] for item in valid_items[:len(assignments_to_create)]]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao criar assignments de teste: {str(e)}")

VALID_CALENDAR_COLOR_IDS = {'1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11'}

@api_router.post("/calendar/events/direct")
async def create_direct_calendar_event(event_request: DirectEventCreate):
    """Create a direct calendar event (not from route).

    Suporta vínculo direto com budget_item_ids, sem exigir Rota — evita a
    burocracia de montar uma Rota só pra colocar um compromisso avulso na Agenda
    (caso comum: estofado de 1 deslocamento, azul/cobalto).
    """
    try:
        # Get credentials from database
        creds_doc = await db.calendar_credentials.find_one({})
        if not creds_doc:
            raise HTTPException(status_code=400, detail="Google Calendar not authenticated")

        # Valida os itens informados (se houver) — evita vínculo com ITM inexistente/typo
        budget_item_ids = event_request.budget_item_ids or []
        if budget_item_ids:
            found_ids = set()
            for iid in budget_item_ids:
                bud = await db.budgets.find_one({"items.id": iid}, {"items.$": 1})
                if bud and bud.get("items"):
                    found_ids.add(iid)
            missing = [iid for iid in budget_item_ids if iid not in found_ids]
            if missing:
                raise HTTPException(
                    status_code=404,
                    detail=f"budget_item_id(s) não encontrado(s): {', '.join(missing)}"
                )

        color_id = event_request.color_id or '5'  # Amarelo banana é o default (reservado/não confirmado)
        if color_id not in VALID_CALENDAR_COLOR_IDS:
            raise HTTPException(status_code=400, detail=f"color_id inválido: {color_id}")

        # Create calendar service
        service = get_calendar_service(creds_doc["credentials"])

        # Parse datetime strings
        start_datetime = datetime.fromisoformat(event_request.start_datetime.replace('Z', '+00:00'))
        end_datetime = datetime.fromisoformat(event_request.end_datetime.replace('Z', '+00:00'))

        # Create Google Calendar event
        event = {
            'summary': event_request.summary,
            'description': event_request.description,
            'location': event_request.location,
            'start': {
                'dateTime': start_datetime.isoformat(),
                'timeZone': 'America/Cuiaba',
            },
            'end': {
                'dateTime': end_datetime.isoformat(),
                'timeZone': 'America/Cuiaba',
            },
            'colorId': color_id
        }

        # Create event in Google Calendar
        google_event = service.events().insert(calendarId='primary', body=event).execute()

        # Store event in database
        calendar_event = CalendarEvent(
            id=f"CAL-{str(uuid.uuid4().int)[:7].zfill(7)}",
            route_id=None,  # Não associado a uma rota
            stop_id=None,   # Não associado a um stop
            budget_item_ids=budget_item_ids,
            color_id=color_id,
            summary=event['summary'],
            description=event.get('description'),
            location=event.get('location'),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            google_event_id=google_event['id']
        )

        await db.calendar_events.insert_one(calendar_event.dict())

        # Vínculo reverso: cada item passa a saber que tem esse evento na Agenda
        # (campo agenda_event_ids já existia no modelo BudgetItem, nunca era preenchido).
        for iid in budget_item_ids:
            await _append_to_item_array(iid, "agenda_event_ids", calendar_event.id)

        return {
            "message": "Direct calendar event created successfully",
            "event": calendar_event.dict(),
            "google_event_id": google_event['id']
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating direct calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/calendar/events/{route_id}")
async def get_calendar_events_by_route(route_id: str):
    """Get calendar events for a specific route"""
    try:
        events = await db.calendar_events.find({"route_id": route_id}).to_list(None)
        return {"events": events}
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.get("/calendar/events")
async def get_all_calendar_events(start_date: str, end_date: str):
    """Get all events from Google Calendar in a date range"""
    try:
        # Get credentials from database
        creds_doc = await db.calendar_credentials.find_one({})
        if not creds_doc:
            raise HTTPException(status_code=400, detail="Google Calendar not authenticated")
        
        # Create calendar service
        service = get_calendar_service(creds_doc["credentials"])
        
        # Format dates for Google Calendar API (RFC3339)
        start_datetime = f"{start_date}T00:00:00-04:00"  # GMT-4 Cuiabá
        end_datetime = f"{end_date}T23:59:59-04:00"
        
        # Get events from Google Calendar
        events_result = service.events().list(
            calendarId='primary',
            timeMin=start_datetime,
            timeMax=end_datetime,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        google_events = events_result.get('items', [])

        # Busca vínculos locais (budget_item_ids + color_id salvo) pra enriquecer
        # a resposta — uma única query em lote, não uma por evento. Esse é também
        # o ponto de "polling leve" da sincronia mão-dupla cor↔status: acontece
        # sempre que a Agenda é aberta/atualizada, sem cron nem infra extra.
        google_ids = [e.get('id') for e in google_events if e.get('id')]
        linked_docs = await db.calendar_events.find(
            {"google_event_id": {"$in": google_ids}}
        ).to_list(None) if google_ids else []
        linked_map = {d["google_event_id"]: d for d in linked_docs}

        # Format events for frontend
        formatted_events = []
        for event in google_events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            end = event['end'].get('dateTime', event['end'].get('date'))

            # Parse datetime strings
            if 'T' in start:  # DateTime format
                start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
                end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
            else:  # Date format (all-day event)
                start_dt = datetime.strptime(start, '%Y-%m-%d')
                end_dt = datetime.strptime(end, '%Y-%m-%d')

            live_color = event.get('colorId')
            local_doc = linked_map.get(event.get('id'))
            budget_item_ids = local_doc.get("budget_item_ids", []) if local_doc else []
            stored_color = local_doc.get("color_id") if local_doc else None
            # Diverge = você mudou a cor manualmente no Google desde a última vez
            # que o sistema gravou/leu. Só sinaliza pra evento vinculado a item —
            # evento solto/manual não tem baseline pra comparar, então não se aplica.
            color_diverged = bool(
                budget_item_ids and stored_color and live_color and stored_color != live_color
            )

            formatted_events.append({
                'id': event.get('id'),
                'summary': event.get('summary', 'Sem título'),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'start_datetime': start_dt.isoformat(),
                'end_datetime': end_dt.isoformat(),
                'color_id': live_color,  # Cor do evento no Google Calendar (ao vivo)
                'budget_item_ids': budget_item_ids,  # Vínculo local, se houver
                'stored_color_id': stored_color,  # Última cor que o sistema conhecia
                'color_diverged': color_diverged,  # True = mudou no Google, sistema ainda não sabe
                'is_system_event': False,  # Evento externo (não criado pelo sistema)
                'google_event_id': event.get('id')
            })

        return {"events": formatted_events}

    except Exception as e:
        logger.error(f"Error fetching Google Calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.post("/calendar/events/{event_id}/acknowledge-color")
async def acknowledge_calendar_event_color(event_id: str, current_user: UserPublic = Depends(get_current_user)):
    """Confirma uma mudança de cor feita manualmente no Google Calendar.

    `event_id` aqui é o ID do evento no GOOGLE (mesmo padrão do PUT/DELETE de
    `/calendar/events/{event_id}` já existentes), não o CAL-XXXXXXX interno —
    o frontend só tem o id do Google disponível na tela de edição do evento.

    Só atualiza a baseline local (`color_id` salvo) pra parar de sinalizar
    divergência — NÃO grava pagamento nem muda status do item. A regra
    combinada é: o sistema sinaliza, você decide e lança o pagamento de
    verdade no Financeiro (a cor sozinha não é confiável o bastante pra isso,
    por sua própria observação de que a regra do vermelho às vezes falha).
    """
    cal_doc = await db.calendar_events.find_one({"google_event_id": event_id})
    if not cal_doc:
        raise HTTPException(status_code=404, detail="Evento não encontrado (sem vínculo local)")

    creds_doc = await db.calendar_credentials.find_one({})
    if not creds_doc:
        raise HTTPException(status_code=400, detail="Google Calendar not authenticated")
    service = get_calendar_service(creds_doc["credentials"])

    google_event = service.events().get(calendarId='primary', eventId=event_id).execute()
    live_color = google_event.get('colorId', '1')

    await db.calendar_events.update_one(
        {"google_event_id": event_id},
        {"$set": {"color_id": live_color, "updated_at": datetime.utcnow()}}
    )
    await log_audit("calendar_event", cal_doc["id"], "COLOR_ACKNOWLEDGED", current_user, {
        "color_id": live_color, "budget_item_ids": cal_doc.get("budget_item_ids", []),
    })
    return {"success": True, "color_id": live_color}

@api_router.get("/calendar/status")
async def check_calendar_auth_status():
    """Check if Google Calendar is authenticated"""
    try:
        # Check if we have valid credentials in database
        creds_doc = await db.calendar_credentials.find_one({})
        if not creds_doc:
            return {"authenticated": False, "message": "No credentials found"}
        
        # Try to create a calendar service to test credentials
        try:
            service = get_calendar_service(creds_doc["credentials"])
            # Test with a simple API call
            calendars = service.calendarList().list(maxResults=1).execute()
            return {"authenticated": True, "message": "Google Calendar connected"}
        except Exception as cred_error:
            logger.error(f"Invalid credentials: {cred_error}")
            return {"authenticated": False, "message": "Invalid credentials"}
            
    except Exception as e:
        logger.error(f"Error checking calendar status: {e}")
        return {"authenticated": False, "message": "Error checking status"}

@api_router.get("/calendar/events/detail/{event_id}")
async def get_calendar_event_detail(event_id: str):
    """Get detailed information of a specific calendar event"""
    try:
        # Get credentials from database
        creds_doc = await db.calendar_credentials.find_one({})
        if not creds_doc:
            raise HTTPException(status_code=400, detail="Google Calendar not authenticated")
        
        # Create calendar service
        service = get_calendar_service(creds_doc["credentials"])
        
        # Get event from Google Calendar
        event = service.events().get(calendarId='primary', eventId=event_id).execute()

        start = event['start'].get('dateTime', event['start'].get('date'))
        end = event['end'].get('dateTime', event['end'].get('date'))

        # Parse datetime strings
        if 'T' in start:  # DateTime format
            start_dt = datetime.fromisoformat(start.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end.replace('Z', '+00:00'))
        else:  # Date format (all-day event)
            start_dt = datetime.strptime(start, '%Y-%m-%d')
            end_dt = datetime.strptime(end, '%Y-%m-%d')

        linked_doc = await db.calendar_events.find_one({"google_event_id": event.get('id')})

        return {
            "id": event.get('id'),
            "summary": event.get('summary', ''),
            "description": event.get('description', ''),
            "location": event.get('location', ''),
            "start_datetime": start_dt.isoformat(),
            "end_datetime": end_dt.isoformat(),
            "color_id": event.get('colorId'),  # Cor do evento no Google Calendar
            "budget_item_ids": (linked_doc or {}).get("budget_item_ids", []),  # Vínculo local, se houver
            "google_event_id": event.get('id')
        }
        
    except Exception as e:
        logger.error(f"Error fetching event detail: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.put("/calendar/events/{event_id}")
async def update_calendar_event(event_id: str, event_update: CalendarEventUpdate):
    """Update an existing calendar event"""
    try:
        # Get credentials from database
        creds_doc = await db.calendar_credentials.find_one({})
        if not creds_doc:
            raise HTTPException(status_code=400, detail="Google Calendar not authenticated")
        
        # Create calendar service
        service = get_calendar_service(creds_doc["credentials"])
        
        # Get current event
        current_event = service.events().get(calendarId='primary', eventId=event_id).execute()
        
        # Update only provided fields
        if event_update.summary is not None:
            current_event['summary'] = event_update.summary
        if event_update.description is not None:
            current_event['description'] = event_update.description
        if event_update.location is not None:
            current_event['location'] = event_update.location
        
        if event_update.start_datetime and event_update.end_datetime:
            # Parse new datetime
            start_dt = datetime.fromisoformat(event_update.start_datetime)
            end_dt = datetime.fromisoformat(event_update.end_datetime)
            
            current_event['start'] = {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'America/Cuiaba',
            }
            current_event['end'] = {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'America/Cuiaba',
            }
        
        # Update event in Google Calendar
        updated_event = service.events().update(
            calendarId='primary', 
            eventId=event_id, 
            body=current_event
        ).execute()
        
        return {"message": "Event updated successfully", "event": updated_event}
        
    except Exception as e:
        logger.error(f"Error updating calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@api_router.delete("/calendar/events/{event_id}")
async def delete_calendar_event(event_id: str):
    """Delete a calendar event"""
    try:
        # Get credentials from database
        creds_doc = await db.calendar_credentials.find_one({})
        if not creds_doc:
            raise HTTPException(status_code=400, detail="Google Calendar not authenticated")
        
        # Create calendar service
        service = get_calendar_service(creds_doc["credentials"])
        
        # Delete event from Google Calendar
        service.events().delete(calendarId='primary', eventId=event_id).execute()
        
        # Also remove from our database if it exists
        await db.calendar_events.delete_many({"google_event_id": event_id})
        
        return {"message": "Event deleted successfully"}
        
    except Exception as e:
        logger.error(f"Error deleting calendar event: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Budget endpoints

EXEC_LOCATION_TO_MODE = {
    "RETIRADA": "RETIRAR_E_LEVAR",
    "NO_LOCAL": "EXECUTAR_NO_LOCAL",
    "CLIENTE_TROUXE": "CLIENTE_TROUXE",
}


async def enrich_budget_item(
    item_data: dict,
    budget_id: str,
    client_doc: dict,
    user: Optional[UserPublic] = None,
    is_new: bool = True,
) -> dict:
    """
    Garante que todo BudgetItem tenha os campos necessários para ser
    pilar do sistema (FK redundantes, snapshot de cliente, defaults).
    """
    now = datetime.utcnow()
    item = dict(item_data)

    # ID
    if not item.get("id"):
        item["id"] = f"ITM-{str(uuid.uuid4().int)[:7].zfill(7)}"

    # FK + snapshot de cliente
    item["budget_id"] = budget_id
    item["client_id"] = client_doc.get("id")
    item["client_name"] = client_doc.get("name")
    item["client_phone"] = client_doc.get("phone_primary")

    # Enriquecer com dados do serviço se faltar
    if item.get("service_id"):
        srv = await db.services.find_one({"id": item["service_id"]})
        if srv:
            item.setdefault("service_name", srv.get("name"))
            item.setdefault("service_code", srv.get("id"))
            item.setdefault("service_category", srv.get("category"))
            item.setdefault("measure_type", srv.get("measure_type"))
            item.setdefault("execution_location", srv.get("execution_location", "RETIRADA"))
            # Status padrão derivado do serviço
            if not item.get("status"):
                item["status"] = srv.get("default_service_status") or "RETIRAR"

    # Execution mode default (derivado da execution_location)
    if not item.get("execution_mode"):
        exec_loc = item.get("execution_location", "RETIRADA")
        item["execution_mode"] = EXEC_LOCATION_TO_MODE.get(exec_loc, "RETIRAR_E_LEVAR")

    # Defaults para coleções/refs
    item.setdefault("status_history", [])
    item.setdefault("execution_sessions", [])
    item.setdefault("route_history", [])
    item.setdefault("agenda_event_ids", [])
    item.setdefault("assignment_ids", [])
    item.setdefault("photos_before", [])
    item.setdefault("photos_after", [])
    item.setdefault("payment_records", [])
    item.setdefault("payment_status", "PENDENTE")
    item.setdefault("paid_value", 0.0)
    item.setdefault("status", "RETIRAR")

    # Status history inicial
    if is_new and not item.get("status_history"):
        item["status_history"] = [{
            "status": item["status"],
            "at": now.isoformat(),
            "by_user_id": user.id if user else None,
            "by_user_name": user.name if user else None,
            "notes": "Item criado",
        }]

    # Auditoria + timestamps
    if is_new:
        item["created_at"] = item.get("created_at") or now
        item["created_by"] = user.id if user else None
    item["updated_at"] = now
    item["updated_by"] = user.id if user else None

    return item


def suggest_credit_installments(total) -> int:
    """
    Sugestão de parcelamento padrão (cartão de crédito) pelo valor do orçamento:
      até R$200 → 2x | até R$300 → 3x | até R$400 → 4x | até R$500 → 5x | R$600+ → 6x (teto).
    É apenas uma sugestão exibida no orçamento; o pagamento real é definido no Financeiro.
    """
    t = round(float(total or 0), 2)
    if t <= 0:
        return 1
    return min(6, max(2, math.ceil(t / 100)))


async def get_payment_fees() -> Dict[str, float]:
    """Tabela de taxas (%) por forma de pagamento (system_config)."""
    cfg = await db.system_config.find_one({}) or {}
    fees = cfg.get("payment_fees")
    if not fees:
        fees = SystemConfig().payment_fees
    return fees


def compute_net(gross, fee_pct) -> dict:
    """Calcula taxa e líquido a partir do bruto e do percentual."""
    gross = round(float(gross or 0), 2)
    pct = float(fee_pct or 0)
    fee = round(gross * pct / 100.0, 2)
    return {"fee_pct": pct, "fee_amount": fee, "net_value": round(gross - fee, 2)}


def calc_budget_totals(items: List[dict], discount_type: str = None, discount_value: float = 0.0) -> dict:
    subtotal = sum(float(i.get("total_value", 0) or 0) for i in items)
    dv = float(discount_value or 0)
    if discount_type == "percent":
        discount_amount = round(subtotal * dv / 100, 2)
    elif discount_type == "fixed":
        discount_amount = round(min(dv, subtotal), 2)
    else:
        discount_amount = 0.0
    final_value = round(max(subtotal - discount_amount, 0), 2)
    return {
        "subtotal_value": subtotal,
        "discount_type": discount_type or None,
        "discount_value": dv if discount_type else 0.0,
        "discount_amount": discount_amount,
        "total_value": final_value,          # total_value = valor final (com desconto)
        "total_area_m2": sum(float(i.get("area_m2", 0) or 0) for i in items),
        "total_linear_meters": sum(float(i.get("linear_meters", 0) or 0) for i in items),
        "total_units": len(items),
        # Condição de pagamento padrão sugerida (não vincula o pagamento real)
        "suggested_payment_method": "CREDITO",
        "suggested_installments": suggest_credit_installments(final_value),
    }


@api_router.post("/budgets", response_model=Budget)
async def create_budget(
    budget_data: BudgetCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    """Criar um novo orçamento"""
    try:
        client = await db.clients.find_one({"id": budget_data.client_id})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # ID sequencial
        last_budget = await db.budgets.find_one(sort=[("created_at", -1)])
        if last_budget and last_budget.get("id", "").startswith("ORC-"):
            try:
                last_id_num = int(last_budget["id"].split("-")[1])
            except Exception:
                last_id_num = await db.budgets.count_documents({})
            new_id_num = last_id_num + 1
        else:
            new_id_num = 1
        while await db.budgets.find_one({"id": f"ORC-{str(new_id_num).zfill(7)}"}):
            new_id_num += 1
        new_budget_id = f"ORC-{str(new_id_num).zfill(7)}"

        budget_dict = budget_data.dict()
        budget_dict["id"] = new_budget_id
        budget_dict["client_name"] = client["name"]
        budget_dict["created_at"] = datetime.utcnow()
        budget_dict["updated_at"] = datetime.utcnow()
        budget_dict["created_by"] = current_user.id
        budget_dict["created_by_name"] = current_user.name
        budget_dict["payment_received"] = False

        # Items enriquecidos
        processed_items = []
        for item_data in (budget_data.items or []):
            enriched = await enrich_budget_item(item_data, new_budget_id, client, current_user, is_new=True)
            processed_items.append(enriched)
        budget_dict["items"] = processed_items
        budget_dict.update(calc_budget_totals(
            processed_items,
            discount_type=budget_data.discount_type,
            discount_value=budget_data.discount_value or 0.0,
        ))

        await db.budgets.insert_one(budget_dict)
        await log_audit("budget", new_budget_id, "CREATE", current_user, {
            "items": len(processed_items),
            "total_value": budget_dict["total_value"],
        })

        # Re-fetch para garantir conversão correta
        saved = await db.budgets.find_one({"id": new_budget_id})
        saved.pop("_id", None)
        return Budget(**saved)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating budget: {str(e)}")


@api_router.get("/budgets", response_model=List[Budget])
async def get_budgets(
    skip: int = 0,
    limit: int = 200,
    search: str = None,
    current_user: UserPublic = Depends(get_current_user),
):
    """Listar orçamentos com busca abrangente."""
    try:
        query: Dict[str, Any] = {}
        if search:
            ors = [
                {"id": {"$regex": re.escape(search), "$options": "i"}},
                {"client_name": {"$regex": re.escape(search), "$options": "i"}},
                {"items.id": {"$regex": re.escape(search), "$options": "i"}},
            ]
            query = {"$or": ors}
        cursor = db.budgets.find(query).sort("created_at", -1).skip(skip).limit(limit)
        budgets = await cursor.to_list(length=limit)
        result = []
        for b in budgets:
            b.pop("_id", None)
            try:
                result.append(Budget(**b))
            except Exception as parse_err:
                print(f"[budgets] parse error {b.get('id')}: {parse_err}")
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting budgets: {str(e)}")


@api_router.get("/budgets/{budget_id}", response_model=Budget)
async def get_budget(budget_id: str, current_user: UserPublic = Depends(get_current_user)):
    """Obter orçamento específico"""
    budget = await db.budgets.find_one({"id": budget_id})
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    budget.pop("_id", None)
    return Budget(**budget)


@api_router.put("/budgets/{budget_id}", response_model=Budget)
async def update_budget(
    budget_id: str,
    budget_data: BudgetCreate,
    current_user: UserPublic = Depends(get_current_user),
):
    """Atualizar orçamento (mantém referências e auditoria por item)."""
    try:
        budget = await db.budgets.find_one({"id": budget_id})
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        client = await db.clients.find_one({"id": budget_data.client_id})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Map dos itens existentes por id (para preservar histórico/refs)
        existing_items = {it.get("id"): it for it in (budget.get("items") or [])}

        update_data = budget_data.dict()
        update_data["client_name"] = client["name"]
        update_data["updated_at"] = datetime.utcnow()
        update_data["updated_by"] = current_user.id
        update_data["updated_by_name"] = current_user.name

        processed_items = []
        for item_data in (budget_data.items or []):
            iid = item_data.get("id")
            is_new = not iid or iid not in existing_items
            base = {} if is_new else existing_items[iid]
            # merge: campos enviados sobrepõem, mas preservamos histórico/refs/audit
            merged = {**base, **item_data}
            # Garantir preservação de campos críticos
            for key in ("status_history", "execution_sessions", "route_history",
                        "agenda_event_ids", "assignment_ids", "photos_before",
                        "photos_after", "payment_records", "paid_value",
                        "payment_status", "current_route_id", "current_route_stop_id",
                        "technician_id", "created_at", "created_by"):
                if key in base and key not in item_data:
                    merged[key] = base[key]
            enriched = await enrich_budget_item(merged, budget_id, client, current_user, is_new=is_new)
            # Se status mudou em relação ao base, append em status_history
            if not is_new and base.get("status") != enriched.get("status"):
                enriched["status_history"] = list(enriched.get("status_history") or [])
                enriched["status_history"].append({
                    "status": enriched["status"],
                    "at": datetime.utcnow().isoformat(),
                    "by_user_id": current_user.id,
                    "by_user_name": current_user.name,
                    "notes": "Status atualizado via edição do orçamento",
                })
            processed_items.append(enriched)

        update_data["items"] = processed_items
        update_data.update(calc_budget_totals(
            processed_items,
            discount_type=budget_data.discount_type,
            discount_value=budget_data.discount_value or 0.0,
        ))

        await db.budgets.update_one({"id": budget_id}, {"$set": update_data})
        await log_audit("budget", budget_id, "UPDATE", current_user, {
            "items": len(processed_items), "total_value": update_data["total_value"]
        })
        saved = await db.budgets.find_one({"id": budget_id})
        saved.pop("_id", None)
        return Budget(**saved)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating budget: {str(e)}")


@api_router.delete("/budgets/{budget_id}/force")
async def force_delete_budget(budget_id: str, current_user: UserPublic = Depends(get_current_user)):
    """Exclusão TOTAL (ADMIN): remove orçamento + todos os rastros no sistema
    (rotas, paradas, assignments, eventos de calendário, audit logs)."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Apenas administradores podem forçar exclusão.")
    budget = await db.budgets.find_one({"id": budget_id})
    if not budget:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")

    item_ids = [it["id"] for it in (budget.get("items") or [])]
    removed = {}

    # 1. Remover paradas das rotas + limpar current_route_id
    for it in (budget.get("items") or []):
        route_id = it.get("current_route_id")
        if route_id:
            r = await db.routes.update_one(
                {"id": route_id},
                {"$pull": {"stops": {"budget_item_id": it["id"]}}}
            )
            removed.setdefault("route_stops", 0)
            removed["route_stops"] += r.modified_count

    # 2. Excluir rotas que ficaram sem paradas E foram geradas só por este orçamento
    #    (rotas onde TODOS os stops eram deste orçamento)
    async for route in db.routes.find({"stops": {"$size": 0}}):
        await db.routes.delete_one({"id": route["id"]})
        removed.setdefault("empty_routes", 0)
        removed["empty_routes"] += 1

    # 3. Cancelar / excluir assignments de técnico que referenciam os itens deste orçamento
    if item_ids:
        # Assignments que têm event_ids com qualquer item deste orçamento
        asgn_result = await db.technician_assignments.delete_many(
            {"event_ids": {"$in": item_ids}}
        )
        removed["assignments"] = asgn_result.deleted_count

    # 4. Remover eventos de calendário vinculados
    cal_result = await db.calendar_events.delete_many(
        {"$or": [{"budget_id": budget_id}, {"event_ids": {"$in": item_ids}}]}
    )
    removed["calendar_events"] = cal_result.deleted_count

    # 5. Excluir audit_logs relacionados
    audit_result = await db.audit_logs.delete_many(
        {"$or": [{"entity_id": budget_id}, {"entity_id": {"$in": item_ids}}]}
    )
    removed["audit_logs"] = audit_result.deleted_count

    # 6. Excluir o orçamento
    await db.budgets.delete_one({"id": budget_id})
    removed["budget"] = 1

    print(f"[FORCE_DELETE] {budget_id} by {current_user.email}: {removed}")
    return {
        "message": f"Orçamento {budget_id} e todos os rastros excluídos.",
        "removed": removed
    }


@api_router.delete("/automation/measures/cleanup")
async def cleanup_automation_measures(current_user: UserPublic = Depends(get_current_user)):
    """Remove apenas os orçamentos criados pela automação de medidas (source=AUTOMATION_MEASURES).
    NÃO remove clientes — preserva todos os cadastros."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Apenas administradores.")
    r = await db.budgets.delete_many({"source": "AUTOMATION_MEASURES"})
    return {"message": f"{r.deleted_count} orçamento(s) de automação removidos. Clientes preservados."}

@api_router.put("/budgets/{budget_id}/budget-status")
async def update_budget_status(
    budget_id: str,
    body: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user),
):
    """Atualiza o status administrativo do orçamento.
    Valores válidos: RASCUNHO, ENVIADO, APROVADO, CANCELADO, ARQUIVADO
    """
    VALID_STATUSES = {"RASCUNHO", "ENVIADO", "APROVADO", "CANCELADO", "ARQUIVADO"}
    new_status = (body.get("budget_status") or "").upper()
    if new_status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Status inválido. Use: {', '.join(VALID_STATUSES)}")

    budget = await db.budgets.find_one({"id": budget_id})
    if not budget:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    # Trava de aceite — fase de testes do sistema (01/10/2026): aprovar sem o cliente
    # ter aceitado os termos só é permitido para ADMIN (override manual e consciente).
    # Atendentes/outros usuários precisam que o aceite já esteja confirmado antes de aprovar.
    if (
        new_status == "APROVADO"
        and budget.get("budget_status") != "APROVADO"
        and budget.get("acceptance_status") != "ACCEPTED"
        and current_user.role != "ADMIN"
    ):
        raise HTTPException(
            status_code=403,
            detail="Este orçamento ainda não tem o Termo de Ciência aceito pelo cliente. "
                   "Gere o link de aceite e aguarde a confirmação, ou peça a um administrador "
                   "para aprovar manualmente.",
        )

    now = datetime.utcnow()
    admin_override = (
        new_status == "APROVADO"
        and budget.get("acceptance_status") != "ACCEPTED"
        and current_user.role == "ADMIN"
    )
    try:
        update_fields = {
            "budget_status": new_status,
            "budget_status_updated_at": now,
            "budget_status_updated_by": current_user.name or current_user.username or "admin",
            "updated_at": now,
        }
        await db.budgets.update_one({"id": budget_id}, {"$set": update_fields})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao salvar no banco: {str(e)}")

    if admin_override:
        await log_audit("budget", budget_id, "APROVADO_SEM_ACEITE_ADMIN", current_user, {
            "note": "Admin aprovou orçamento sem aceite confirmado do cliente (fase de testes).",
        })

    try:
        await log_audit("budget", budget_id, "STATUS_CHANGED", current_user, {
            "from": budget.get("budget_status", "RASCUNHO"),
            "to": new_status,
        })
    except Exception:
        pass  # auditoria não pode derrubar a operação principal

    return {"success": True, "budget_id": budget_id, "budget_status": new_status}


@api_router.post("/budgets/migrate-status")
async def migrate_budget_statuses(current_user: UserPublic = Depends(get_current_user)):
    """Admin — define budget_status='APROVADO' em todos os orçamentos que ainda não têm o campo.
    Executar uma única vez após o deploy desta versão.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Apenas administradores")

    result = await db.budgets.update_many(
        {"budget_status": {"$exists": False}},
        {"$set": {"budget_status": "APROVADO", "budget_status_updated_at": datetime.utcnow(), "budget_status_updated_by": "migration"}}
    )
    # Também cobre documentos com budget_status=null
    result2 = await db.budgets.update_many(
        {"budget_status": None},
        {"$set": {"budget_status": "APROVADO", "budget_status_updated_at": datetime.utcnow(), "budget_status_updated_by": "migration"}}
    )
    total = result.modified_count + result2.modified_count
    return {"success": True, "migrated": total, "message": f"{total} orçamento(s) receberam status APROVADO"}


@api_router.post("/budgets/migrate-partner-execution-mode")
async def migrate_partner_execution_mode(current_user: UserPublic = Depends(get_current_user)):
    """Admin — corrige execution_mode de itens de parceiro criados antes do deploy 2025-07.
    Itens cujo service_id está no mapeamento de parceiros devem ter execution_mode=CLIENTE_TROUXE
    para não aparecer na tela de rotas.
    """
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Apenas administradores")

    partner_service_ids: list = []
    for sq, sr in _PARTNER_SERVICE_MAP.values():
        partner_service_ids.append(sq)
        partner_service_ids.append(sr)

    result = await db.budgets.update_many(
        {"items": {"$elemMatch": {
            "service_id": {"$in": partner_service_ids},
            "execution_mode": {"$ne": "CLIENTE_TROUXE"},
        }}},
        {"$set": {
            "items.$[elem].execution_mode": "CLIENTE_TROUXE",
            "items.$[elem].is_partner_item": True,
            "items.$[elem].updated_at": datetime.utcnow(),
        }},
        array_filters=[{
            "elem.service_id": {"$in": partner_service_ids},
            "elem.execution_mode": {"$ne": "CLIENTE_TROUXE"},
        }],
    )
    return {
        "success": True,
        "budgets_touched": result.modified_count,
        "message": f"{result.modified_count} orçamento(s) com itens de parceiro corrigidos",
    }


@api_router.delete("/budgets/{budget_id}")
async def delete_budget(budget_id: str, current_user: UserPublic = Depends(get_current_user)):
    """Excluir orçamento (bloqueia se algum item já está em rota ou executado)."""
    budget = await db.budgets.find_one({"id": budget_id})
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    locked = [
        it for it in (budget.get("items") or [])
        if it.get("current_route_id") or it.get("status") in (
            ServiceStatus.EXECUTADO.value, ServiceStatus.ENTREGUE.value,
            ServiceStatus.EM_LAVAGEM.value, ServiceStatus.COLETADO.value,
        )
    ]
    if locked:
        raise HTTPException(
            status_code=400,
            detail=f"Não é possível excluir: {len(locked)} item(ns) já em rota ou execução.",
        )
    await db.budgets.delete_one({"id": budget_id})
    await log_audit("budget", budget_id, "DELETE", current_user, {"before": budget})
    return {"message": "Budget deleted successfully"}

@api_router.get("/budgets/{budget_id}/whatsapp")
async def generate_whatsapp_message(budget_id: str):
    """Gerar mensagem formatada para WhatsApp."""
    try:
        budget = await db.budgets.find_one({"id": budget_id})
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")

        client = await db.clients.find_one({"id": budget.get("client_id")})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")

        # Data do orçamento: prefere created_at, cai em updated_at
        orc_date = budget.get("created_at") or budget.get("updated_at") or datetime.utcnow()
        if isinstance(orc_date, str):
            orc_date = datetime.fromisoformat(orc_date.replace('Z', '+00:00'))
        formatted_date = orc_date.strftime("%d/%m/%Y")

        items = budget.get("items") or []
        total_value = float(budget.get("total_value") or 0)

        # ── Cabeçalho ──────────────────────────────────────────────────────────
        message = (
            "🔸*ORÇAMENTO PERSONALIZADO*🔸\n"
            "                     💙_SuperDry®_💚\n"
            "  _Lavanderia de Tapetes e Estofados_\n\n"
            f"🏷️ *Código do Orçamento:* {budget_id}\n"
            f"👨‍👩‍👦 *Cliente:* {budget.get('client_name', 'N/A')}\n"
            f"🗣️ *Atendente:* {budget.get('salesperson', 'N/A')}\n"
            f"📅 *Data do Orçamento:* {formatted_date}\n\n"
            f"📄 *Quantidade de Itens:* {len(items)}"
        )

        # ── Itens ──────────────────────────────────────────────────────────────
        for item in items:
            item_line = f"💧 {item.get('service_name', 'N/A')}"
            area_m2       = float(item.get('area_m2')       or 0)
            linear_meters = float(item.get('linear_meters') or 0)
            if area_m2 > 0:
                diameter = item.get('diameter')
                width    = item.get('width')
                height   = item.get('height')
                if diameter:
                    item_line += f" - Ø{float(diameter):.1f}m - {area_m2:.1f} m²"
                elif width and height:
                    item_line += f" - {float(width):.1f} x {float(height):.1f} - {area_m2:.1f} m²"
                else:
                    item_line += f" - {area_m2:.1f} m²"
            elif linear_meters > 0:
                ff = item.get('fabric_folds')
                fp = item.get('fabric_per_fold')
                if ff and fp:
                    item_line += f" - {float(ff):.0f} dobras x {float(fp):.0f}cm - {linear_meters:.1f}m lineares"
                else:
                    item_line += f" - {linear_meters:.1f}m lineares"
            else:
                qty = float(item.get('quantity') or 1)
                item_line += f" - {qty:.0f} unid." if qty > 1 else " - 1 unid."
            item_line += f" - R$ {float(item.get('total_value') or 0):.2f}"
            message += f"\n_{item_line}_"

        # ── Total + desconto + pagamento ───────────────────────────────────────
        _disc_amt  = float(budget.get("discount_amount") or 0)
        _subtotal  = float(budget.get("subtotal_value")  or total_value)
        if _disc_amt > 0:
            _disc_type  = budget.get("discount_type", "fixed")
            _disc_val   = float(budget.get("discount_value") or 0)
            _disc_label = f"{_disc_val:.0f}%" if _disc_type == "percent" else f"R$ {_disc_val:.2f}"
            message += f"\n\n📝 *Subtotal:* R$ {_subtotal:.2f}"
            message += f"\n🏷️ *Desconto ({_disc_label}):* -R$ {_disc_amt:.2f}"
        message += f"\n\n📝*VALOR TOTAL:* R$ {total_value:.2f}"
        message += f"\n💳*FORMAS DE PAGAMENTO:* {_format_payment_wa(total_value)}"

        # ── Avisos por categoria (textos curtos fixos) ─────────────────────────
        cats_seen = [
            cat for cat in _CAT_ORDER
            if any(itm.get('service_category') == cat for itm in items)
        ]
        if cats_seen:
            message += "\n\n*⚠️ Avisos importantes:*"
            for cat in cats_seen:
                risk_txt = _WA_SHORT_RISKS.get(cat)
                if risk_txt:
                    message += f"\n{risk_txt}"

        # ── Links: aceite + PDF ────────────────────────────────────────────────
        public_url = (
            os.environ.get("PUBLIC_WEBHOOK_URL", "")
            .replace("/api/webhooks/payment", "")
            .strip("/")
        )

        acceptance = await db.service_acceptances.find_one({"budget_id": budget_id})
        if not acceptance and public_url:
            _wa_term = await _get_current_term_version()
            new_acc = ServiceAcceptance(
                budget_id=budget_id,
                client_id=budget.get("client_id"),
                client_name_on_budget=budget.get("client_name"),
                client_phone=budget.get("client_phone"),
                term_version_id=_wa_term["id"] if _wa_term else None,
                term_text_snapshot=_wa_term["text"] if _wa_term else None,
            )
            await db.service_acceptances.insert_one(new_acc.dict())
            acceptance_short = new_acc.short_id
            acceptance_token = new_acc.token
        elif acceptance:
            # garante short_id para aceites antigos
            if not acceptance.get("short_id"):
                sid = _make_short_id()
                await db.service_acceptances.update_one(
                    {"budget_id": budget_id}, {"$set": {"short_id": sid}}
                )
                acceptance_short = sid
            else:
                acceptance_short = acceptance["short_id"]
            acceptance_token = acceptance.get("token")
        else:
            acceptance_short = None
            acceptance_token = None

        if public_url and acceptance_short:
            message += (
                f"\n\n✅ *Para autorizar a execução leia e confirme os termos do serviço:*\n"
                f"{public_url}/api/s/{acceptance_short}"
            )

        # ── Rodapé ─────────────────────────────────────────────────────────────
        message += (
            "\n\n😁_Caso tenha dúvidas, estou à disposição!_"
            "\n💡_Orçamento válido por *30 dias*._"
        )

        # ── URL WhatsApp ───────────────────────────────────────────────────────
        phone_raw = (client.get('phone_primary') or '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
        phone_clean = phone_raw if phone_raw.startswith('55') else f"55{phone_raw}"

        import urllib.parse
        message_encoded = urllib.parse.quote(message, safe='')
        whatsapp_url = f"https://wa.me/{phone_clean}"
        whatsapp_url_with_text = f"https://wa.me/{phone_clean}?text={message_encoded}"

        if len(whatsapp_url_with_text) > 2000:
            return {
                "message": message,
                "phone": client.get("phone_primary", ""),
                "whatsapp_url": whatsapp_url,
                "whatsapp_url_with_text": None,
                "note": "Mensagem muito longa para URL automática. Copie e cole manualmente.",
            }
        return {
            "message": message,
            "phone": client.get("phone_primary", ""),
            "whatsapp_url": whatsapp_url_with_text,
            "whatsapp_url_simple": whatsapp_url,
            "note": "Mensagem incluída na URL automaticamente.",
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generating WhatsApp message: {str(e)}")

@api_router.get("/budgets/{budget_id}/pdf")
async def generate_pdf_budget(budget_id: str):
    """Gerar PDF do orçamento"""
    try:
        budget = await db.budgets.find_one({"id": budget_id})
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        client = await db.clients.find_one({"id": budget.get("client_id")})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        config = await db.budget_config.find_one({})
        if not config:
            config = BudgetConfig().dict()
            await db.budget_config.insert_one(config)
        
        # Create PDF — margens reduzidas: top menor, esquerda mais próxima da borda
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer, pagesize=A4,
            leftMargin=2*cm,     # margem esquerda padrão
            rightMargin=1.8*cm,
            topMargin=0.8*cm,    # margem superior compacta
            bottomMargin=1.5*cm,
        )
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles — seções com spaceBefore/spaceAfter reduzidos em ~40%
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            spaceAfter=6,
            alignment=1
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=6,   # era 12 → 40% menos
            spaceBefore=12, # era 20 → 40% menos
            textColor=colors.black
        )

        big_style = ParagraphStyle(
            'BigNormal',
            parent=styles['Normal'],
            fontSize=11,
            leading=13,
            alignment=1
        )
        
        # ── Paleta da marca SuperDry (extraída da logo) ──────────────────────
        BLUE        = colors.HexColor("#1F4E8C")
        GREEN       = colors.HexColor("#8CC63F")
        BLUE_LIGHT  = colors.HexColor("#EAF0F8")
        GREEN_LIGHT = colors.HexColor("#F1F7E6")
        GREY_TXT    = colors.HexColor("#444444")
        usable = A4[0] - 2*cm - 1.8*cm   # largura útil (margens do doc)

        # Helper: cabeçalho de seção em barra azul com texto branco
        def section(num, title):
            t = Table([[Paragraph(
                f"<font color='white'><b>{num}. {title}</b></font>",
                styles['Normal'])]], colWidths=[usable])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), BLUE),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('TOPPADDING', (0, 0), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ]))
            return t

        # ── Cabeçalho com marca + logo ───────────────────────────────────────
        brand_block = Paragraph(
            f"<font color='#1F4E8C' size=22><b>ORÇAMENTO</b></font> "
            f"<font color='#8CC63F' size=22><b>{budget_id}</b></font><br/>"
            f"<font color='#444444' size=9>SuperDry · Lavanderia de Tapetes e Estofados Especializada</font>",
            styles['Normal'])
        logo_file = _find_logo()
        if logo_file:
            logo_el = Image(logo_file, width=1.5*inch, height=1.2*inch)
            header = Table([[brand_block, logo_el]], colWidths=[usable - 1.6*inch, 1.6*inch])
            header.setStyle(TableStyle([
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (1, 0), (1, 0), 0),
            ]))
            story.append(header)
        else:
            story.append(brand_block)

        # Régua bicolor azul/verde
        rule = Table([['', '']], colWidths=[usable * 0.62, usable * 0.38], rowHeights=[3])
        rule.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, 0), BLUE),
            ('BACKGROUND', (1, 0), (1, 0), GREEN),
            ('LEFTPADDING', (0, 0), (-1, -1), 0), ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ]))
        story.append(rule)
        story.append(Spacer(1, 10))

        # ── Card de dados do cliente ─────────────────────────────────────────
        updated_date = budget.get("updated_at", datetime.utcnow())
        if isinstance(updated_date, str):
            updated_date = datetime.fromisoformat(updated_date.replace('Z', '+00:00'))
        formatted_date = updated_date.strftime("%d/%m/%Y")

        pm_raw = budget.get('payment_method', 'N/A') or 'N/A'
        pm_label = pm_raw.replace('CREDITO_', 'Crédito ').replace('PIX_CNPJ_', 'PIX ').replace('_', ' ')

        addr_obj = client.get('address') or {}
        addr_str = addr_obj.get('full_address') or ''
        addr_line = (
            f"<br/><font color='#1F4E8C'><b>Endereço:</b></font> {addr_str}"
            if addr_str else ""
        )
        client_card_html = (
            f"<font color='#1F4E8C'><b>Cliente:</b></font> {budget.get('client_name', 'N/A')}&nbsp;&nbsp;&nbsp;"
            f"<font color='#1F4E8C'><b>Telefone:</b></font> {client.get('phone_primary', 'N/A')}"
            f"{addr_line}<br/>"
            f"<font color='#1F4E8C'><b>Vendedor:</b></font> {budget.get('salesperson', 'N/A')}&nbsp;&nbsp;&nbsp;"
            f"<font color='#1F4E8C'><b>Pagamento:</b></font> {pm_label}&nbsp;&nbsp;&nbsp;"
            f"<font color='#1F4E8C'><b>Data:</b></font> {formatted_date}"
        )
        client_card = Table([[Paragraph(client_card_html, styles['Normal'])]], colWidths=[usable])
        client_card.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), BLUE_LIGHT),
            ('LEFTPADDING', (0, 0), (-1, -1), 10), ('RIGHTPADDING', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8), ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -1), 2, GREEN),
        ]))
        story.append(client_card)
        
        # Budget observations
        if budget.get('budget_observations'):
            story.append(Spacer(1, 6))
            story.append(Paragraph(f"<b>Observações:</b> {budget.get('budget_observations')}", styles['Normal']))
        
        story.append(Spacer(1, 10))  # era 20 → compacto
        
        # Section 1: Services table
        story.append(Spacer(1, 12))
        story.append(section("1", "SERVIÇOS"))
        story.append(Spacer(1, 4))

        # Create centered style for table content
        centered_style = ParagraphStyle(
                'CenteredCell',
                parent=styles['Normal'],
                fontSize=9,
                alignment=1  # Center
        )

        # Cabeçalho da tabela com quebra de linha usando <br/>
        table_data = [[
                Paragraph("<b><font color='white'>Descrição</font></b>", centered_style),
                Paragraph("<b><font color='white'>Medidas</font></b>", centered_style),
                Paragraph("<b><font color='white'>Área M²</font></b>", centered_style),
                Paragraph("<b><font color='white'>Metragem<br/>Linear</font></b>", centered_style),
                Paragraph("<b><font color='white'>Unidade</font></b>", centered_style),
                Paragraph("<b><font color='white'>Valor</font></b>", centered_style)
        ]]

        total_value = 0
        service_categories = set()  # Track categories for risk texts

        for item in budget.get('items', []):
                measures = ""
                width = item.get('width')
                height = item.get('height')
                diameter = item.get('diameter')

                if width and height:
                        measures = f"{width} x {height}"
                elif diameter:
                        measures = f"Ø {diameter}m"

                area_m2 = item.get('area_m2') or 0
                linear_meters = item.get('linear_meters') or 0
                quantity_val = item.get('quantity') or 1
                total_val = item.get('total_value') or 0

                area_m2_str = f"{area_m2:.1f}" if area_m2 > 0 else "-"
                linear_meters_str = f"{linear_meters:.1f}" if linear_meters > 0 else "-"
                quantity = f"{quantity_val:.0f}"
                value = f"R$ {total_val:.2f}"

                total_value += total_val

                # Categoria de risco: usa o service_category REAL do item (vindo do
                # catálogo) — corrige o caso "Impermeabilização de Sofá" cair em ESTOFADOS.
                CAT_TO_RISK = {
                        'ESTOFADOS': 'risks_estofados',
                        'COLCHOES': 'risks_colchoes',
                        'BOX': 'risks_box',
                        'TAPETES': 'risks_tapetes',
                        'CARPETES_E_TAPETES_NO_LOCAL': 'risks_carpetes_tapetes_local',
                        'CORTINAS': 'risks_cortinas',
                        'PERSIANAS': 'risks_persianas',
                        'ITENS_INFANTIS': 'risks_itens_infantis',
                        'VEICULOS': 'risks_veiculos',
                        'IMPERMEABILIZACAO': 'risks_impermeabilizacao',
                        'OUTROS_ITENS': 'risks_outros_itens',
                }
                risk_key = CAT_TO_RISK.get(item.get('service_category'))
                if not risk_key:
                        # Fallback por palavra-chave — IMPERMEABILIZAÇÃO checada ANTES de estofado
                        sn = (item.get('service_name') or '').upper()
                        if 'IMPERMEAB' in sn:
                                risk_key = 'risks_impermeabilizacao'
                        elif any(w in sn for w in ['SOFÁ', 'SOFA', 'CADEIRA', 'POLTRONA', 'ALMOFADA', 'ESTOFADO', 'PUFF']):
                                risk_key = 'risks_estofados'
                        elif 'COLCH' in sn:
                                risk_key = 'risks_colchoes'
                        elif 'BOX' in sn:
                                risk_key = 'risks_box'
                        elif ('TAPETE' in sn or 'CARPETE' in sn) and 'LOCAL' in sn:
                                risk_key = 'risks_carpetes_tapetes_local'
                        elif 'TAPETE' in sn or 'CARPETE' in sn:
                                risk_key = 'risks_tapetes'
                        elif 'CORTINA' in sn:
                                risk_key = 'risks_cortinas'
                        elif 'PERSIANA' in sn:
                                risk_key = 'risks_persianas'
                        elif any(w in sn for w in ['CARRINHO', 'CADEIRINHA', 'BEBÊ', 'BEBE', 'INFANTIL']):
                                risk_key = 'risks_itens_infantis'
                        elif any(w in sn for w in ['VEÍCULO', 'VEICULO', 'BANCO', 'CARRO']):
                                risk_key = 'risks_veiculos'
                        else:
                                risk_key = 'risks_outros_itens'
                service_categories.add(risk_key)

                desc_text = item.get('service_name') or 'N/A'
                item_obs = (item.get('observations') or '').strip()
                if item_obs:
                        desc_text = (
                                f"{desc_text}<br/>"
                                f"<font size='7' color='#666666'><i>{_xml_escape(item_obs)}</i></font>"
                        )

                table_data.append([
                        Paragraph(desc_text, centered_style),
                        Paragraph(measures, centered_style),
                        Paragraph(area_m2_str, centered_style),
                        Paragraph(linear_meters_str, centered_style),
                        Paragraph(quantity, centered_style),
                        Paragraph(value, centered_style)
                ])

        # Total row
        table_data.append([
                Paragraph("", centered_style),
                Paragraph("", centered_style),
                Paragraph("", centered_style),
                Paragraph("", centered_style),
                Paragraph("<b>TOTAL</b>", centered_style),
                Paragraph(f"<b>R$ {total_value:.2f}</b>", centered_style)
        ])

        # Adjusted column widths to fit A4 page
        col_widths = [3.5*inch, 1*inch, 0.9*inch, 0.9*inch, 0.7*inch, 1*inch]

        table = Table(table_data, colWidths=col_widths)
        table.setStyle(TableStyle([
                # Cabeçalho azul da marca
                ('BACKGROUND', (0, 0), (-1, 0), BLUE),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 7),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 7),
                # Linhas do corpo: alternância branco / azul claro
                ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, BLUE_LIGHT]),
                ('TOPPADDING', (0, 1), (-1, -2), 5),
                ('BOTTOMPADDING', (0, 1), (-1, -2), 5),
                # Linha do TOTAL em verde
                ('BACKGROUND', (0, -1), (-1, -1), GREEN_LIGHT),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('TEXTCOLOR', (0, -1), (-1, -1), BLUE),
                ('LINEABOVE', (0, -1), (-1, -1), 1.5, GREEN),
                ('TOPPADDING', (0, -1), (-1, -1), 7),
                ('BOTTOMPADDING', (0, -1), (-1, -1), 7),
                # Grade sutil
                ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor("#D8DEE8")),
                ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#C7CEDA")),
        ]))

        story.append(table)
        story.append(Spacer(1, 18))  # era 30 → compacto
        
        # Section 2: Risk texts based on service categories
        if service_categories:
            story.append(Spacer(1, 14))
            story.append(section("2", "RISCOS E ADVERTÊNCIAS"))
            story.append(Spacer(1, 4))
            
            category_labels = {
                'risks_estofados': 'ESTOFADOS',
                'risks_colchoes': 'COLCHÕES', 
                'risks_box': 'BOX',
                'risks_tapetes': 'TAPETES',
                'risks_carpetes_tapetes_local': 'CARPETES E TAPETES NO LOCAL',
                'risks_cortinas': 'CORTINAS',
                'risks_persianas': 'PERSIANAS',
                'risks_itens_infantis': 'ITENS INFANTIS',
                'risks_veiculos': 'VEÍCULOS',
                'risks_impermeabilizacao': 'IMPERMEABILIZAÇÃO',
                'risks_outros_itens': 'OUTROS ITENS'
            }
            
            for category in sorted(service_categories):
                risk_text = config.get(category, '')
                if risk_text:
                    # Convert WhatsApp formatting to HTML
                    formatted_text = format_html_text(risk_text)
                    category_name = category_labels.get(category, category.replace('risks_', '').upper())
                    story.append(Paragraph(f"<font color='#1F4E8C'><b>{category_name}</b></font>", styles['Normal']))
                    story.append(Paragraph(formatted_text, styles['Normal']))
                    story.append(Spacer(1, 6))   # era 10 → compacto
        
        # Section 3: General conditions
        general_conditions = config.get('general_conditions', '')
        if general_conditions:
            story.append(Spacer(1, 14))
            story.append(section("3", "CONDIÇÕES GERAIS"))
            story.append(Spacer(1, 4))
            formatted_conditions = format_html_text(general_conditions)
            story.append(Paragraph(formatted_conditions, styles['Normal']))
            story.append(Spacer(1, 12))  # era 20 → compacto
        
        # Signature section — centralizada
        sig_style = ParagraphStyle('SigStyle', parent=styles['Normal'], alignment=1)
        story.append(Spacer(1, 28))
        story.append(Paragraph("_" * 55, sig_style))
        story.append(Spacer(1, 4))
        story.append(Paragraph(
            "<font color='#1F4E8C'>Assinatura do cliente</font>", sig_style))
        
        # Footer
        footer_text = config.get('footer_text', '')
        if footer_text:
            story.append(Spacer(1, 20))
            formatted_footer = format_html_text(footer_text)
            story.append(Paragraph(formatted_footer, styles['Normal']))
        
        # Build PDF
        doc.build(story)
        
        # Return PDF as response
        buffer.seek(0)
        return StreamingResponse(
            BytesIO(buffer.read()),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=orcamento_{budget_id}.pdf"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generating PDF: {str(e)}")

@api_router.get("/budget-config", response_model=BudgetConfig)
async def get_budget_config():
    """Obter configurações do orçamento"""
    try:
        config = await db.budget_config.find_one({})
        if not config:
            # Create default config if doesn't exist
            default_config = BudgetConfig()
            await db.budget_config.insert_one(default_config.dict())
            return default_config
        return BudgetConfig(**config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching budget config: {str(e)}")

@api_router.put("/budget-config", response_model=BudgetConfig)
async def update_budget_config(config: BudgetConfig):
    """Atualizar configurações do orçamento"""
    try:
        config.updated_at = datetime.utcnow()
        config_dict = config.dict()
        
        # Upsert - update if exists, insert if doesn't
        await db.budget_config.replace_one({}, config_dict, upsert=True)
        
        return config
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating budget config: {str(e)}")

# ── Automações ────────────────────────────────────────────────────────────────
#
# Dois fluxos independentes:
#   1. auto-budget  → texto com dados do cliente + itens → cria cliente + orçamento
#   2. auto-measures → texto com medidas de tapetes → preenche Identificação e Medidas
#
# O formato das mensagens será definido pelo usuário.
# Por enquanto o parser aceita linhas separadas por \n.
# Cada automação retorna um "preview" antes de confirmar a criação.
#

class AutoBudgetLine(BaseModel):
    raw_text: str          # texto bruto (uma linha por dado)
    # campos interpretados pelo parser (preenchidos pelo backend)
    client_name:      Optional[str] = None
    client_phone:     Optional[str] = None
    client_address:   Optional[str] = None
    client_complement:Optional[str] = None  # Apto, bloco, etc.
    scheduled_date:   Optional[str] = None  # "YYYY-MM-DD"
    scheduled_time:   Optional[str] = None  # "HH:MM"
    total_pix:        Optional[float] = None
    total_cash:       Optional[float] = None
    items:            List[Dict[str, Any]] = []
    notes:            Optional[str] = None

class AutoMeasureLine(BaseModel):
    raw_text: str
    items: List[Dict[str, Any]] = []  # [{client_name, service_name, width, height, diameter, partner_label}]


# ── Casamento de item com o catálogo (Camada A da automação de orçamento) ──────
# Recebe uma descrição livre ("sofá 3 lugares", "tapete 2x3") e encontra o serviço
# mais provável no catálogo, trazendo preço e tipo de medida. Apenas sugestão — o
# preview é confirmável. Ver memory/FLUXO_TRABALHO_E_AUTOMACAO.md (§2 Camada A).
import unicodedata as _ud

_SVC_STOP = {'de', 'da', 'do', 'e', 'ou', 'com', 'a', 'o', 'para', 'no', 'na', 'dos', 'das'}


def _svc_norm(s: str) -> str:
    return _ud.normalize('NFKD', s or '').encode('ascii', 'ignore').decode().lower()


def _svc_strip_measures(q: str) -> str:
    """Remove medidas da query (NxM, decimais, m²) — elas são tratadas à parte.
    Bug corrigido: a unidade (m/cm/mm) costuma vir colada no número (ex: "3,5m x 4,0m"),
    e as regexes antigas só reconheciam "3,5 x 4,0" (sem unidade colada). Quando a unidade
    vinha colada, a limpeza falhava e os dígitos da medida sobravam como "token" da busca,
    podendo bater por coincidência com um número dentro do NOME de outro serviço do catálogo
    (ex: o "3" de "3,5m" batendo com o "3" de "Lavagem de Sofá 3 Lugares") e desviando o
    casamento pro serviço errado.
    """
    unit_opt = r'(?:(?:m|cm|mm)\.?)?'
    q = re.sub(r'\d+[.,]?\d*\s*' + unit_opt + r'\s*[xX×]\s*\d+[.,]?\d*\s*' + unit_opt, ' ', q)
    q = re.sub(r'\b\d+[.,]\d+\s*' + unit_opt + r'\b', ' ', q, flags=re.IGNORECASE)
    q = re.sub(r'\b\d+\s*(?:m|cm|mm)\.?\b', ' ', q, flags=re.IGNORECASE)
    q = re.sub(r'm²|\bm2\b', ' ', q, flags=re.IGNORECASE)
    q = re.sub(r'\(\s*\d+[.,]?\d*\s*\)', ' ', q)
    return q


def _svc_tokens(s: str):
    return [t for t in re.findall(r'[a-z]+|\d+', _svc_norm(s))
            if t not in _SVC_STOP and (len(t) >= 2 or t.isdigit())]


def _svc_tok_match(q: str, s: str) -> bool:
    if q.isdigit() or s.isdigit():
        return q == s
    if q == s:
        return True
    short, long = sorted([q, s], key=len)
    if len(short) >= 4 and long.startswith(short):
        return True
    c = 0
    for a, b in zip(q, s):
        if a == b:
            c += 1
        else:
            break
    return c >= 6


def _svc_score(query: str, svc: dict) -> float:
    qt = _svc_tokens(_svc_strip_measures(query))
    nt = _svc_tokens(svc.get('name', ''))
    if not qt or not nt:
        return -99.0
    matched = sum(1 for q in qt if any(_svc_tok_match(q, n) for n in nt))
    extras = sum(1 for n in nt if not any(_svc_tok_match(q, n) for q in qt))
    cov = matched / len(qt)
    sc = cov * 2 + matched * 0.2 - 0.15 * extras - 0.03 * len(nt)
    qn = _svc_norm(query)
    if 'imperme' not in qn and svc.get('category') == 'IMPERMEABILIZACAO':
        sc -= 1.2  # sem "imperme" na query, prioriza lavagem
    if 'local' not in qn and 'local' in _svc_norm(svc.get('name', '')):
        sc -= 0.6  # prefere a variante padrão (na empresa) à "no local"
    return sc


async def match_service_in_catalog(query: str, services=None):
    """Melhor serviço do catálogo para a descrição. None se nada razoável."""
    if not (query or '').strip():
        return None
    if services is None:
        services = await db.services.find({"is_active": True}).to_list(length=1000)
    if not services:
        return None
    best = max(services, key=lambda s: _svc_score(query, s))
    sc = _svc_score(query, best)
    if sc <= -1:
        return None
    return {
        "service_id": best["id"],
        "service_name": best["name"],
        "service_code": best["id"],
        "category": best.get("category"),
        "measure_type": best.get("measure_type"),
        "sale_price": best.get("sale_price"),
        "match_score": round(sc, 2),
        "low_confidence": sc < 1.3,
    }


_ADDR_KW = re.compile(
    r'\b(rua|r\.|av\.?|avenida|alameda|al\.|travessa|tv\.|rodovia|estrada|'
    r'pra[çc]a|bairro|quadra|lote|condom[ií]nio|cep|apto|apartamento|bloco|'
    r'casa\s*\d|n[º°]|setor|jardim|jd\.|res\.|residencial|edif[ií]cio)\b', re.IGNORECASE)

# Palavras que indicam complemento de endereço (tratado separado do logradouro)
_COMPLEMENT_KW = re.compile(
    r'^\s*(apartamento|apto|apt\.?|bloco\s+\w|andar|sala\s+\d)', re.IGNORECASE)

# Padrão de agendamento embutido: "Horário 20/7 9:00" ou "Horario 20/7/2026 09:00"
_SCHEDULE_RE = re.compile(
    r'^[Hh]or[aá]rio\s+(\d{1,2}/\d{1,2})(?:/\d{2,4})?\s+(\d{1,2}:\d{2})')

# Marcadores de fim do bloco de orçamento (termos e condições)
_TERMS_BLOCK_RE = re.compile(
    r'^[▪•–]\s*|📍\s*🛋|📍\s*🪟|'
    r'\b(atendimento\s+[eé]\s+em\s+domicílio|responsabilidade|'
    r'garantimos|garantia\s+de|termos\s+e\s+condi[çc][oõ]es|'
    r'n[aã]o\s+nos\s+responsabilizamos)\b',
    re.IGNORECASE)

# Linhas de total / pagamento (não devem virar itens)
_PAYMENT_LINE_RE = re.compile(
    r'total\s+dos\s+servi[çc]os|'
    r'fechando\s+(todos|o\s+or[çc]amento)|'
    r'pagamento\s+em\s+dinheiro|'
    r'[àa]\s+vista\s+em\s+dinheiro|'
    r'total\s+pix|'
    r'em\s+até\s+\d+x\s+sem\s+juros',
    re.IGNORECASE)

# Regex para extrair valor total (pix/cartão) e dinheiro
_TOTAL_PIX_RE = re.compile(r'R\$\s*([\d.,]+)', re.IGNORECASE)
_CASH_LINE_RE = re.compile(
    r'(?:dinheiro|à\s+vista)[^R]*R\$\s*([\d.,]+)', re.IGNORECASE)


def _extract_value(line: str) -> float:
    """Extrai um valor explícito de 'serviço - 350' / 'serviço: 350'. 0 se não houver."""
    parts = re.split(r'\s[-:]\s|\s[-:]\s?|[-:]\s', line, maxsplit=1)
    if len(parts) == 2:
        try:
            return float(re.sub(r'[^\d.,]', '', parts[1]).replace('.', '').replace(',', '.')
                         if parts[1].count(',') else re.sub(r'[^\d.]', '', parts[1]))
        except Exception:
            return 0.0
    return 0.0


def _smart_extract_value(line: str) -> float:
    """
    Extração de valor melhorada para linhas de orçamento WhatsApp (Bug 2, 3, 4).

    Prioridades:
      1. Padrão R$X.XXX,XX ou R$X,XX (valor monetário explícito)
      2. Padrão 'R$X,XXun (Nun = R$Y,YY)' → total Y
      3. Padrão '= R$X,XX' ao final da linha
      4. Fallback para _extract_value legado (linhas simples 'serviço - valor')
    """
    # 1. Procura todos os padrões R$ na linha
    money_re = re.compile(r'R\$\s*([\d.,]+)', re.IGNORECASE)
    # 2. Padrão de preço por unidade: R$X,XXun (Nun = R$Y,YY) ou (Nun R$Y,YY)
    unit_total_re = re.compile(
        r'R\$\s*[\d.,]+\s*un.*?\(\s*\d+\s*un[^)]*R\$\s*([\d.,]+)',
        re.IGNORECASE | re.DOTALL)

    def br_float(s: str) -> float:
        s = s.strip().rstrip('.')
        if not s:
            return 0.0
        try:
            if ',' in s and '.' in s:
                return float(s.replace('.', '').replace(',', '.'))
            elif ',' in s:
                return float(s.replace(',', '.'))
            else:
                return float(s)
        except ValueError:
            return 0.0

    # Prioridade 2: padrão unitário → pega o total entre parênteses
    um = unit_total_re.search(line)
    if um:
        return br_float(um.group(1))

    # Prioridade 1: último R$ na linha (evita sangrar dígitos da descrição)
    all_money = money_re.findall(line)
    if all_money:
        return br_float(all_money[-1])

    # Fallback legado para linhas simples
    return _extract_value(line)


def _smart_extract_unit_qty(line: str) -> tuple:
    """
    Para linhas com 'R$X,XXun (Nun = R$Y,YY)' extrai (unit_price, quantity, total).
    Retorna (None, None, None) se padrão não encontrado.
    """
    pat = re.compile(
        r'R\$\s*([\d.,]+)\s*un.*?\(\s*(\d+)\s*un[^)]*R\$\s*([\d.,]+)',
        re.IGNORECASE | re.DOTALL)
    m = pat.search(line)
    if not m:
        return None, None, None

    def bf(s):
        s = s.strip()
        try:
            if ',' in s and '.' in s:
                return float(s.replace('.', '').replace(',', '.'))
            return float(s.replace(',', '.'))
        except ValueError:
            return 0.0

    return bf(m.group(1)), int(m.group(2)), bf(m.group(3))


def _item_name_only(line: str) -> str:
    """Remove um eventual ' - valor' do fim, deixando só a descrição do item."""
    return re.split(r'\s[-:]\s|\s[-:]\s?|[-:]\s', line, maxsplit=1)[0].strip()


def _parse_line_measures(line: str) -> dict:
    """
    Extrai medidas de uma linha de item: NxM → largura×altura (área);
    número único com 'redondo'/Ø → diâmetro. Aplica heurística cm/m (>10 = cm).
    Ex: 'Persiana rolo 2.1x3.5' → {width:2.1, height:3.5, area_m2:7.35}
    """
    res = {}

    def to_f(s):
        try:
            return float(str(s).replace(',', '.'))
        except Exception:
            return 0.0

    # Unidade (m/cm/mm) costuma vir colada no número (ex: "3,5m x 4,0m") — sem o 
    # \.? opcional abaixo, essa forma não batia e a medida ficava sem width/height/area_m2.
    dim = re.search(
        r'(\d+(?:[.,]\d+)?)\s*(?:(?:m|cm|mm)\.?)?\s*[xX×]\s*(\d+(?:[.,]\d+)?)\s*(?:(?:m|cm|mm)\.?)?',
        line,
    )
    # Bug similar ao já corrigido em _parse_measures_text: "redondo" ANTES do número
    # (ex: "redondo 0,8") tem prioridade sobre número-antes-de-"redondo" (ex: "599 redondo"),
    # senão um código/etiqueta que aparece antes de "redondo" na mesma linha (ex: "Azul 599
    # redondo 0,8") é confundido com o diâmetro em vez do número que realmente é a medida.
    circ_after = re.search(r'redondo\s+(\d+(?:[.,]\d+)?)', line, re.IGNORECASE)
    circ_before = re.search(r'(\d+(?:[.,]\d+)?)\s*redondo', line, re.IGNORECASE)
    circ_sym = re.search(r'[Øø]\s*(\d+(?:[.,]\d+)?)', line)
    circ = circ_after or circ_before or circ_sym
    if dim:
        w, h = to_f(dim.group(1)), to_f(dim.group(2))
        if w > 10 and h > 10:
            w, h = w / 100, h / 100
        elif w > 10:
            w = w / 100
        elif h > 10:
            h = h / 100
        res['width'] = round(w, 4)
        res['height'] = round(h, 4)
        res['area_m2'] = round(w * h, 4)
    elif circ:
        d = to_f(circ.group(1))
        if d > 10:
            d = d / 100
        res['diameter'] = round(d, 4)
        res['area_m2'] = round(3.14159 * (d / 2) ** 2, 4)
    return res


def _smart_parse_budget(text: str, services: list) -> AutoBudgetLine:
    """
    Parser por CONTEÚDO (não posicional). Classifica cada linha:
      - 'obs:' → observações
      - telefone (8–13 dígitos, quase só dígitos)
      - agendamento ("Horário DD/M HH:MM") → scheduled_date / scheduled_time (Bug 10)
      - item (casa com o catálogo) — caso da maioria das linhas do dono
      - endereço (palavras-chave de logradouro) — costuma vir depois, mas se aparecer
      - complemento ("Apartamento", "Apto", etc.) → client_complement (Bug 12)
      - 1ª linha sem classificação → nome do cliente
      - fim do bloco (▪, •, "atendimento é em domicílio", ...) → para (Bug 11)
      - linha de total/pagamento → extrai total_pix / total_cash (Bug 5)
    Adequado ao fluxo do dono: nome + telefone + itens (endereço normalmente ausente).

    Trata chars Unicode invisíveis que o WhatsApp injeta nos números copiados.
    """
    import re as _re
    _INVIS = _re.compile(r'[​-‏‪-‮⁠-⁯﻿]')
    _EMOJI_STRIP = _re.compile(r'[\U0001F300-\U0001FAFF\U00002600-\U000027FF\U0001FA00-\U0001FA6F]')

    def _clean(s: str) -> str:
        return _INVIS.sub('', s).strip()

    def _br_float(s: str) -> float:
        """Converte string brasileira de valor (1.234,56 ou 1234.56) para float."""
        s = _re.sub(r'[^\d.,]', '', s)
        if not s:
            return 0.0
        try:
            if ',' in s and '.' in s:
                # formato 1.234,56
                return float(s.replace('.', '').replace(',', '.'))
            elif ',' in s:
                return float(s.replace(',', '.'))
            else:
                return float(s)
        except ValueError:
            return 0.0

    lines = [_clean(l) for l in text.split('\n')]
    lines = [l for l in lines if l]
    res = AutoBudgetLine(raw_text=text)
    items = []
    payment_block_seen = False  # já vimos linha de total/pagamento?

    for i, line in enumerate(lines):
        low = line.lower()

        # Bug 11: cortar ao encontrar marcador de termos e condições
        if _TERMS_BLOCK_RE.search(line):
            break

        # obs:
        if low.startswith('obs:'):
            res.notes = line[4:].strip()
            continue

        # telefone
        digits = _re.sub(r'\D', '', line)
        non_phone = _re.sub(r'[\d\s()+\-.]', '', line)
        if not res.client_phone and 8 <= len(digits) <= 13 and len(non_phone) <= 2:
            res.client_phone = line
            continue

        # Bug 10: agendamento "Horário DD/M HH:MM"
        sched = _SCHEDULE_RE.match(line)
        if sched:
            from datetime import date as _date
            date_part = sched.group(1)   # "20/7"
            time_part = sched.group(2)   # "9:00"
            dd, mm = date_part.split('/')
            year = _date.today().year
            res.scheduled_date = f"{year}-{int(mm):02d}-{int(dd):02d}"
            h, mn = time_part.split(':')
            res.scheduled_time = f"{int(h):02d}:{mn}"
            continue

        # cabeçalho decorativo do orçamento (🔶 Orçamento - ... 🔶)
        if _re.search(r'[🔶]\s*[Oo]r[çc]amento', line):
            continue

        # Bug 5: linha de total / pagamento → extrair valores, não virar item
        if _PAYMENT_LINE_RE.search(line):
            payment_block_seen = True
            # tentar extrair total_pix (primeira ocorrência de R$)
            vals = _TOTAL_PIX_RE.findall(line)
            if vals and res.total_pix is None and not _CASH_LINE_RE.search(line):
                res.total_pix = _br_float(vals[0])
            # linha de dinheiro
            cash_m = _CASH_LINE_RE.search(line)
            if cash_m:
                res.total_cash = _br_float(cash_m.group(1))
            continue

        # nome do cliente (sempre 1ª linha classificável)
        if i == 0 and not res.client_name:
            res.client_name = line
            continue

        # Bug 12: complemento de endereço — linha que começa com Apartamento/Apto/apt
        if _COMPLEMENT_KW.match(line):
            if not res.client_complement:
                res.client_complement = line
            elif res.client_complement:
                res.client_complement += ', ' + line
            continue

        # classificação normal: endereço vs. item
        clean_name = _EMOJI_STRIP.sub('', line).strip()
        name = _item_name_only(clean_name)
        m = match_score_sync(name, services)
        sc = m[1] if m else -99
        looks_addr = bool(_ADDR_KW.search(line))

        def _mk_item(n=name, ln=line):
            unit_p, qty, total = _smart_extract_unit_qty(ln)
            if unit_p is not None:
                it = {"service_name": n, "value": total, "unit_price": unit_p, "quantity": qty}
            else:
                it = {"service_name": n, "value": _smart_extract_value(ln)}
            it.update(_parse_line_measures(ln))
            return it

        if sc >= 1.0 and not (looks_addr and sc < 1.3):
            items.append(_mk_item())
        elif looks_addr and not res.client_address:
            res.client_address = line
        elif sc >= 0:
            items.append(_mk_item())
        elif not res.client_address:
            res.client_address = line
        else:
            items.append(_mk_item())

    res.items = items
    return res


def match_score_sync(query: str, services: list):
    """(serviço, score) do melhor match — versão síncrona para o classificador."""
    if not (query or '').strip() or not services:
        return None
    best = max(services, key=lambda s: _svc_score(query, s))
    return (best, _svc_score(query, best))


def _parse_budget_text(text: str) -> AutoBudgetLine:
    """
    Parser para automação de orçamento — tolerante ao formato do WhatsApp.

    Detecta dinamicamente (sem assumir posições fixas):
      - Nome:     primeira linha que não seja telefone
      - Telefone: linha com 8–13 dígitos e poucos caracteres não-numéricos
      - Endereço: linha com palavras típicas de logradouro (opcional)
      - Itens:    demais linhas
      - obs:      linha iniciada com "obs:"

    Trata chars Unicode invisíveis que o WhatsApp injeta nos números copiados
    (U+202A LEFT-TO-RIGHT EMBEDDING, U+202C POP DIRECTIONAL FORMATTING,
     U+2011 NON-BREAKING HYPHEN, etc.), que antes quebravam a detecção de telefone.
    """
    import re

    # Remove caracteres Unicode invisíveis/direcionais (comuns em cópias do WhatsApp)
    _INVIS = re.compile(r'[​-‏‪-‮⁠-⁯﻿]')

    def _clean(s: str) -> str:
        return _INVIS.sub('', s).strip()

    def _is_phone(s: str) -> bool:
        digits = re.sub(r'\D', '', s)
        non_phone = re.sub(r'[\d\s()+\-.]', '', s)
        return 8 <= len(digits) <= 13 and len(non_phone) <= 2

    lines = [_clean(l) for l in text.split('\n')]
    lines = [l for l in lines if l]           # remove linhas vazias após limpeza
    result = AutoBudgetLine(raw_text=text)
    if not lines:
        return result

    # Primeira linha = nome do cliente
    result.client_name = lines[0]

    for line in lines[1:]:
        if line.lower().startswith('obs:'):
            result.notes = line[4:].strip()
            continue

        # Telefone detectado por conteúdo, não por posição
        if not result.client_phone and _is_phone(line):
            result.client_phone = line
            continue

        # Tenta separar "serviço - valor" ou "serviço: valor"
        match = re.split(r'\s[-:]\s|\s[-:]\s?|[-:]\s', line, maxsplit=1)
        if len(match) == 2:
            service_name = match[0].strip()
            try:
                value = float(re.sub(r'[^\d.,]', '', match[1]).replace(',', '.'))
            except Exception:
                value = 0.0
            result.items.append({"service_name": service_name, "value": value})
        elif line:
            result.items.append({"service_name": line, "value": 0.0})

    return result


def _parse_measures_text(text: str) -> AutoMeasureLine:
    """
    Parser de medidas de tapetes para mensagens do WhatsApp.

    Parceiros cadastrados (nomes canônicos = nome exato no banco):
      CLI-0006  Leonardo - Dry Clean USA  → cores+código numérico, ou sem identificação
      CLI-0009  Forma Clean               → forma clean/clan, maika, renan
      CLI-0010  Higia Service             → higia, vinicius (ambíguo), lucas
      CLI-0011  Wesley Higienização       → parceiro wesley, wesley
      CLI-0016  Felipe Gonçalves / João Farias → parceiro joao/felipe/domus, domus decor
    Regras de medidas (sempre em metros):
      - Formato NxM → largura x comprimento; vírgula ou ponto como decimal
      - Valor único > 10 isolado → converte de cm para metros
      - Se ambos > 10 → ambos em cm; se só um > 10 → só esse em cm
      - "redondo" ou "Ø" → tapete circular, medida = diâmetro
    Cabeçalhos WhatsApp ([DD/MM/AAAA, HH:MM:SS] Nome:) têm a data extraída como
    reference_date (propagada aos itens das linhas seguintes) e depois são
    removidos do texto da linha.
    """
    # Nomes canônicos exatos conforme cadastro no banco
    PARTNER_LEONARDO   = "Leonardo - Dry Clean USA"
    PARTNER_FORMACLEAN = "Forma Clean"
    PARTNER_HIGIA      = "Higia Service"
    PARTNER_WESLEY     = "Wesley Higienização"
    PARTNER_DOMUS      = "Felipe Gonçalves / João Farias"

    def _to_float(s: str) -> float:
        try:
            return float(s.replace(',', '.'))
        except (ValueError, AttributeError):
            return 0.0

    def _normalize_dims(w: float, h: float):
        # Heurística: se o maior valor é > 10 mas o menor <= 10,
        # só o maior está em cm (ex: 80x1.5 → 0.80x1.5).
        # Se ambos > 10, ambos em cm (ex: 60x70 → 0.60x0.70).
        if w > 10 and h > 10:
            w, h = round(w / 100, 4), round(h / 100, 4)
        elif w > 10:
            w = round(w / 100, 4)
        elif h > 10:
            h = round(h / 100, 4)
        return round(w, 4), round(h, 4)

    # Emoji usados por alguns técnicos (ex: Marcos) no lugar da palavra da cor,
    # sempre coladas ou seguidas do código numérico (ex: "💛059", "🩶 870").
    EMOJI_COLOR_MAP = {
        '💛': 'AMARELO', '🟡': 'AMARELO',
        '🩷': 'ROSA', '💗': 'ROSA', '💖': 'ROSA',
        '🩶': 'CINZA', '⚪': 'CINZA', '🤍': 'CINZA',
        '🧡': 'LARANJA', '🟠': 'LARANJA',
        '💙': 'AZUL', '🔵': 'AZUL',
        '💜': 'ROXO', '🟣': 'ROXO',
        '💚': 'VERDE', '🟢': 'VERDE',
    }
    EMOJI_CODE_RE = re.compile(r'^([\U0001F300-\U0001FAFF☀-➿])\s*(\d{2,3})$')

    def _classify_partner(identifier: str):
        """
        Retorna (client_name, partner_name, is_ambiguous, partner_label).
        partner_name = None se for cliente comum.
        """
        idn = identifier.strip()
        idn_lower = idn.lower()

        # Sem identificação, variantes, ou tag "dry"/"dry2"/"dry clean" (bag/lote sem
        # etiqueta individual do Leonardo) → Leonardo, sem etiqueta cor+número.
        sem_nome_pattern = r'^(sem\s*nome|s/?n|sem\s*identifica[çc][aã]o|n[aã]o\s*identificado|desconhecido)$'
        dry_pattern = r'\bdry\s*\d*\b'
        if not idn or re.match(sem_nome_pattern, idn_lower) or re.search(dry_pattern, idn_lower):
            return None, PARTNER_LEONARDO, False, None

        # Dhiego (motorista da empresa Leonardo Dry Clean USA) e variantes.
        # No contexto de mensagens de medida de tapetes, toda referência a
        # "Dhiego", "Parceiro Diego" ou "Diego" identifica o motorista do Leonardo —
        # NÃO o dono da SuperDry (Diego Olivatto) nem um parceiro separado.
        # Regra confirmada pelo dono em 19/07/2026.
        if re.search(r'\bdhiego\b|parceiro\s+diego|\bdiego\b', idn_lower):
            return None, PARTNER_LEONARDO, False, None

        # Emoji de cor + código 2-3 dígitos (ex: "💛059", "🩶870") → mesma regra
        # do texto, traduzindo o emoji pra cor equivalente.
        emoji_match = EMOJI_CODE_RE.match(idn)
        if emoji_match and emoji_match.group(1) in EMOJI_COLOR_MAP:
            return None, PARTNER_LEONARDO, False, {
                "type": "COLOR_NUM",
                "color": EMOJI_COLOR_MAP[emoji_match.group(1)],
                "number": emoji_match.group(2),
            }

        # Cor + código 2-3 dígitos → Leonardo Dry Clean
        # Aceita com ou sem espaço entre cor e número (Rosa856 ou Rosa 856)
        color_match = re.match(
            r'^(azul|amarelo|cinza|laranja|roxo|rosa|verde)\s*(\d{2,3})$',
            idn_lower
        )
        if color_match:
            return None, PARTNER_LEONARDO, False, {
                "type": "COLOR_NUM",
                "color": color_match.group(1).upper(),
                "number": color_match.group(2),
            }

        # Higia Service: higia, lucas — aceita com ou sem o prefixo "parceiro "
        # (ajuste 02/10/2026: antes só reconhecia a palavra isolada; "Parceiro
        # Higia", mesmo escrito certo, não batia — Wesley/Domus já aceitavam o prefixo).
        if re.fullmatch(r'(parceiro\s+)?(higia|lucas)', idn_lower):
            return None, PARTNER_HIGIA, False, None

        # Vinicius: ambíguo (pode ser cliente comum ou parceiro Higia)
        if re.fullmatch(r'vin[ií]cius', idn_lower):
            return None, PARTNER_HIGIA, True, None

        # Forma Clean: forma clean/clan, maika, renan
        if re.search(r'forma\s*(clean|clan)|maika|renan', idn_lower):
            return None, PARTNER_FORMACLEAN, False, None

        # Wesley Higienização: "parceiro wesley" ou só "wesley"
        if re.search(r'parceiro\s+wesley|^wesley$', idn_lower):
            return None, PARTNER_WESLEY, False, None

        # Felipe / João / Domus Decor
        if re.search(r'parceiro\s+(felipe|jo[aã]o)|domus', idn_lower):
            return None, PARTNER_DOMUS, False, None

        # Normaliza o nome do cliente: Title Case para padronizar maiúsculas/minúsculas
        normalized = ' '.join(w.capitalize() for w in idn.split())
        return normalized, None, False, None  # cliente comum

    lines = [l.strip() for l in text.strip().split('\n')]
    result = AutoMeasureLine(raw_text=text)

    # Data de referência corrente — extraída do último cabeçalho WhatsApp visto
    # ([DD/MM/AAAA, HH:MM:SS] Nome:). Propagada para todos os itens das linhas
    # seguintes até aparecer um novo cabeçalho. Usada como "data de recolhimento/
    # medição" do tapete (quando o técnico envia a mensagem, o item já foi lavado).
    current_ref_date = None

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        # Cabeçalho WhatsApp: [22/05/2026, 16:13:38] Nome:  → captura a data e
        # segue processando o conteúdo após o ":" (não descarta mais a data).
        header_match = re.match(r'^\[(\d{2})/(\d{2})/(\d{4}),\s*(\d{2}:\d{2}:\d{2})\]', line)
        if header_match:
            day, month, year, time_str = header_match.groups()
            try:
                current_ref_date = f"{year}-{month}-{day}T{time_str}"
            except Exception:
                pass
            content_after = re.sub(r'^\[.+?\]\s*[^:]+:\s*', '', line).strip()
            if not content_after:
                continue
            line = content_after

        item: Dict[str, Any] = {"raw": raw_line}

        # ── Detectar medidas ──────────────────────────────────────────────────

        # Redondo / circular — dois formatos possíveis:
        #   Formato A: "redondo 0,8"  → diâmetro vem DEPOIS de "redondo" (ex: "Azul 599 redondo 0,8")
        #   Formato B: "1.60 redondo" → diâmetro vem ANTES  de "redondo" (ex: "Azul 495 1.60 redondo")
        #   Formato C: "Ø1.5"         → símbolo de diâmetro
        # Priorizamos Formato A para evitar que o código de etiqueta (ex: 599) seja confundido com diâmetro
        circ_after  = re.search(r'redondo\s+([\d.,]+)', line, re.IGNORECASE)   # A: diâmetro após "redondo"
        circ_before = re.search(r'([\d.,]+)\s+redondo', line, re.IGNORECASE)   # B: diâmetro antes de "redondo"
        circ_sym    = re.search(r'[ØDd]\s*([\d.,]+)', line)                    # C: símbolo Ø

        if circ_after:
            circ_match = circ_after
            _circ_d_group = 1
            _circ_measure_start = circ_after.start()   # tudo antes de "redondo" é o identificador
        elif circ_before:
            circ_match = circ_before
            _circ_d_group = 1
            _circ_measure_start = circ_before.start()
        elif circ_sym:
            circ_match = circ_sym
            _circ_d_group = 1
            _circ_measure_start = circ_sym.start()
        else:
            circ_match = None
            _circ_d_group = 1
            _circ_measure_start = None

        # Dimensões NxM — unidade (m/cm/mm) costuma vir colada no número ("3,5m x 4,0m"),
        # por isso o (?:(?:m|cm|mm)\.?)? opcional entre o número e o 'x'/depois do 2º número.
        dim_match = re.search(
            r'([\d.,]+)\s*(?:(?:m|cm|mm)\.?)?\s*[xX×]\s*([\d.,]+)\s*(?:(?:m|cm|mm)\.?)?', line
        )

        # Número único (possível diâmetro): ex "FormaClean Thais 2,4" ou "2,4m"
        # Exige pelo menos um dígito antes e depois de eventual separador decimal
        single_match = re.search(r'\b(\d+[.,]\d+|\d{1,3})(?:(?:m|cm|mm)\.?)?\b(?!\s*[xX×])', line) if not dim_match and not circ_match else None

        if circ_match:
            d_str = circ_match.group(_circ_d_group)
            d = _to_float(d_str)
            if d > 10:
                d = round(d / 100, 4)
            item["diameter"] = d
            item["area_m2"]  = round(3.14159 * (d / 2) ** 2, 4)
        elif dim_match:
            w = _to_float(dim_match.group(1))
            h = _to_float(dim_match.group(2))
            w, h = _normalize_dims(w, h)
            item["width"]   = w
            item["height"]  = h
            item["area_m2"] = round(w * h, 4)
        elif single_match:
            # Número inteiro pequeno (1-9) sem decimal = contagem de tapetes prontos → ignora
            raw_num = single_match.group(1)
            if re.fullmatch(r'\d', raw_num) and int(raw_num) <= 9:
                continue
            # Número único com decimal → diâmetro
            d = _to_float(raw_num)
            if d > 10:
                d = round(d / 100, 4)
            item["diameter"] = d
            item["area_m2"]  = round(3.14159 * (d / 2) ** 2, 4)
        else:
            # Linha sem medida reconhecível — ignora
            continue

        # ── Detectar identificador (tudo antes da medida) ────────────────────
        if circ_match and _circ_measure_start is not None:
            measure_start = _circ_measure_start
        else:
            measure_start = (dim_match or single_match).start()
        identifier_raw = line[:measure_start].strip()

        # Remove sufixos extras após a medida (ex: " redondo", texto residual)
        # Limpa pontuação final do identificador
        identifier_raw = re.sub(r'[\s,;:]+$', '', identifier_raw)

        client_name, partner_name, is_ambiguous, label = _classify_partner(identifier_raw)

        # Se o identificador ficou vazio (linha começa direto com medida) → Leonardo
        if not identifier_raw and not partner_name:
            partner_name = PARTNER_LEONARDO

        item["service_name"] = "Tapete"
        if current_ref_date:
            item["reference_date"] = current_ref_date

        if partner_name:
            item["client_name"]   = partner_name
            item["is_partner"]    = True
            item["is_ambiguous"]  = is_ambiguous  # True apenas para "Vinicius"
            if label:
                item["partner_label"] = label
            else:
                item["partner_label"] = {"type": "TEXT", "text": partner_name}
        else:
            item["client_name"]  = client_name
            item["is_partner"]   = False
            item["is_ambiguous"] = False

        result.items.append(item)

    return result


async def _next_id(collection, prefix: str, zfill: int) -> str:
    """Gera o próximo ID sequencial baseado no maior ID existente na coleção."""
    pattern = f"^{re.escape(prefix)}(\\d+)$"
    pipeline = [
        {"$match": {"id": {"$regex": pattern}}},
        {"$project": {"num": {"$toInt": {"$arrayElemAt": [{"$split": ["$id", "-"]}, -1]}}}},
        {"$sort": {"num": -1}},
        {"$limit": 1},
    ]
    cursor = collection.aggregate(pipeline)
    docs = await cursor.to_list(1)
    next_num = (docs[0]["num"] + 1) if docs else 1
    return f"{prefix}{str(next_num).zfill(zfill)}"


@api_router.post("/automation/preview-budget")
async def preview_budget(payload: Dict[str, Any], current_user: UserPublic = Depends(get_current_user)):
    """Preview do que será criado a partir do texto de automação de orçamento."""
    text = payload.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Texto vazio.")
    # Casa cada item com o catálogo → sugere serviço, preço e tipo de medida.
    services = await db.services.find({"is_active": True}).to_list(length=1000)
    parsed = _smart_parse_budget(text, services)
    AREA_TYPES = {"AREA_DE_TAPETE", "AREA_PERSIANA", "CARPETE_TAPETE_LOCAL",
                  "TAPETE_REDONDO_DIAMETRO"}
    enriched = []
    for it in parsed.items:
        item = dict(it)
        m = await match_service_in_catalog(it.get("service_name", ""), services)
        explicit_value = float(it.get("value") or 0)
        if m:
            mtype = m["measure_type"]
            price = float(m["sale_price"] or 0)
            item["matched"] = m
            item["measure_type"] = mtype
            item["unit_price"] = price
            area = float(it.get("area_m2") or 0)

            if mtype in AREA_TYPES:
                # Item por área: se as medidas vieram no texto, já calcula o valor
                if explicit_value:
                    item["value"] = explicit_value
                    item["needs_measure"] = False
                elif area > 0:
                    item["value"] = round(area * price, 2)
                    item["needs_measure"] = False
                else:
                    item["value"] = 0
                    item["needs_measure"] = True      # falta medida → UI abre campos
            else:
                # UNITARIO: valor = preço × quantidade (qtd ajustável na UI, ex.: filetes)
                qty = int(it.get("quantity") or 1)
                item["quantity"] = qty
                item["value"] = explicit_value or round(price * qty, 2)
                item["needs_measure"] = False
                item["needs_quantity"] = True         # UI mostra campo de quantidade
        else:
            item["needs_measure"] = False
        enriched.append(item)

    # Verifica se cliente já existe
    existing_client = None
    if parsed.client_phone:
        phone_clean = re.sub(r'\D', '', parsed.client_phone)
        existing_client = await db.clients.find_one({"phone_primary": {"$regex": phone_clean[-8:]}})
    return {
        "client_name":    parsed.client_name,
        "client_phone":   parsed.client_phone,
        "client_address": parsed.client_address,
        "items":          enriched,
        "notes":          parsed.notes,
        "client_exists":  bool(existing_client),
        "existing_client_id": existing_client.get("id") if existing_client else None,
    }


_OPENAI_API_SKIP = False  # True após receber 400/401/403 — evita chamadas desnecessárias na sessão


@api_router.post("/automation/interpret-message")
async def interpret_message(payload: Dict[str, Any], current_user: UserPublic = Depends(get_current_user)):
    """
    Interpreta mensagem WhatsApp colada pelo atendente.

    Fluxo (três camadas de retaguarda):
      1. OpenAI API (OPENAI_API_KEY no .env, modelo gpt-5.6-luna) — melhor qualidade
      2. Ollama local (llama3.2:3b em localhost:11434) — sem custo, sem internet
      3. Parser Python — fallback sempre disponível
    Após extração: matching de catálogo + verificação de cliente existente.
    """
    import httpx as _httpx
    import json as _json

    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texto vazio.")

    services = await db.services.find({"is_active": True}).to_list(length=1000)

    # ── Catálogo resumido para o prompt ──────────────────────────────────────
    catalog_lines = "\n".join(
        f"- {s.get('name')} ({s.get('category', '')}, R${float(s.get('sale_price') or 0):.0f})"
        for s in services[:80]
    ) if services else "(catálogo vazio)"

    # ── 1. Tentar OpenAI API (GPT-5.6 Luna) ──────────────────────────────────
    global _OPENAI_API_SKIP
    openai_key = os.getenv("OPENAI_API_KEY", "")
    raw_parsed = None
    source = "python_parser"

    if openai_key and not _OPENAI_API_SKIP:
        try:
            prompt = (
                "Você é o assistente da SuperDry Lavanderia em Cuiabá-MT.\n"
                "Analise a conversa/mensagem de WhatsApp abaixo e extraia os dados estruturados.\n\n"
                f"CATÁLOGO DE SERVIÇOS:\n{catalog_lines}\n\n"
                f"MENSAGEM:\n{text[:4000]}\n\n"
                "Retorne SOMENTE um JSON válido (sem markdown, sem explicação) com este schema:\n"
                "{\n"
                '  "client_name": "nome real do cliente (sem timestamps, sem prefixos de grupo)",\n'
                '  "phone": "telefone com DDD, ex: +55 65 99973-1235",\n'
                '  "address": "PRIORIDADE 1: nome do edifício/condomínio (para busca automática no mapa). PRIORIDADE 2 (só se não houver prédio/condomínio): endereço completo (rua, número, bairro) ou ponto de referência (ex: perto de tal parque/shopping)",\n'
                '  "complement": "TODOS os identificadores internos juntos numa string: nome do edifício/condomínio + apartamento + bloco/torre + quadra/lote/casa + nome de rua interna do condomínio, quando existirem. Ex: Edifício Sofisticato, Torre A, Apto 302 | Condomínio Belvedere, Rua das Tesourinhas Qd 02 Lt 12",\n'
                '  "scheduled_date": "YYYY-MM-DD ou null",\n'
                '  "scheduled_time": "HH:MM ou null",\n'
                '  "total_pix": numero ou null,\n'
                '  "total_cash": numero ou null,\n'
                '  "notes": "observações ou null — inclua aqui pontos de referência (perto de tal lugar) quando já houver nome de prédio/condomínio no campo address",\n'
                '  "items": [\n'
                '    {\n'
                '      "service_name": "descrição completa do item (ex: Sofá 2 lugares, Cadeira Tipo Poltrona)",\n'
                '      "quantity": 1,\n'
                '      "unit_price": 0.0,\n'
                '      "value": 0.0\n'
                '    }\n'
                '  ]\n'
                "}\n\n"
                "REGRAS:\n"
                "- O CLIENTE é quem enviou a primeira mensagem (não a SuperDry/Daiana)\n"
                "- Extraia apenas o nome real do cliente, sem timestamp do WhatsApp nem nome do grupo\n"
                "- Para cada item, use o nome descritivo do produto (ex: 'Sofá 2 lugares'), não o tipo do serviço\n"
                "- Itens com quantidade >1 listados juntos (ex: '2un = R$100'): crie um único item com qty=2\n"
                "- Se a mensagem contém um orçamento formatado, extraia os itens com preços\n"
                "- Ignore parágrafos de condições, riscos e rodapé — só extraia serviços com preços\n"
                "- total_pix = valor à vista (pix/dinheiro mais barato) ou o total principal\n"
                "- total_cash = valor em dinheiro se diferente do PIX, ou null\n"
                "- ENDEREÇO/CONDOMÍNIO — regra importante: se a mensagem citar nome de edifício/condomínio, esse nome vai SOZINHO no campo address (é usado pra busca automática no mapa — não misture com ponto de referência). Se também houver ponto de referência (ex: 'perto do parque X'), esse ponto de referência vai para notes, não para address.\n"
                "- No campo complement, quando houver condomínio, junte TODOS os identificadores internos disponíveis numa única string: nome do condomínio/edifício + apartamento + bloco/torre + quadra/lote/casa + rua interna. Reconheça variações e abreviações comuns: Qd/Quadra, Lt/Lote, Cs/Casa, Bl/Bloco, T1/TA/Torre A/Torre 1, Ap/Apto/Apartamento — mantenha a forma como veio na mensagem, sem precisar expandir a abreviação.\n"
                "- Nunca invente dado de endereço que não esteja explícito na mensagem (nem bairro, nem ponto de referência, nem número)\n"
            )
            async with _httpx.AsyncClient(timeout=12.0) as hc:
                r = await hc.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {openai_key}",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "gpt-5.6-luna",
                        "max_completion_tokens": 1500,
                        "response_format": {"type": "json_object"},
                        "messages": [{"role": "user", "content": prompt}],
                    },
                )
            if r.status_code == 200:
                content = r.json().get("choices", [{}])[0].get("message", {}).get("content", "")
                json_match = re.search(r'\{.*\}', content, re.DOTALL)
                if json_match:
                    raw_parsed = _json.loads(json_match.group())
                    source = "openai"
            elif r.status_code in (400, 401, 403):
                _OPENAI_API_SKIP = True
                logging.info(f"OpenAI API retornou {r.status_code} — desabilitando para esta sessão do servidor.")
        except Exception as _ex:
            logging.warning(f"OpenAI API falhou no interpret-message: {_ex}")

    # ── 2. Fallback: Ollama local (llama3.2:3b) ──────────────────────────────
    if raw_parsed is None:
        try:
            async with _httpx.AsyncClient(timeout=10.0) as hc:
                hcheck = await hc.get("http://localhost:11434/api/tags")
            if hcheck.status_code == 200:
                catalog_short = "; ".join(s.get("name", "") for s in services[:40])
                ollama_prompt = (
                    "Você é assistente de atendimento da SuperDry Lavanderia (Cuiabá-MT).\n"
                    "Analise o texto abaixo — pode ser uma mensagem do WhatsApp OU um pedido rápido digitado pela atendente — e extraia os dados para criar um orçamento.\n\n"
                    f"CATÁLOGO DE SERVIÇOS DISPONÍVEIS: {catalog_short}\n\n"
                    f"TEXTO:\n{text[:2500]}\n\n"
                    "REGRAS:\n"
                    "1. client_name = nome do cliente (sem timestamps, sem prefixos como '20/07 10:30 -')\n"
                    "2. phone = telefone, apenas DDD+número sem +55 (ex: '65 99973-1235')\n"
                    "3. address = nome do edifício/condomínio se houver (prioridade, usado pra busca no mapa); senão, rua/bairro ou ponto de referência. Nunca copie instruções como texto do endereço. Se não houver, null\n"
                    "4. complement = junte tudo: edifício/condomínio + apto/bloco/torre/quadra/lote/casa, ex: 'Edifício Sofisticato, Apto 302' ou 'Condomínio Belvedere, Qd 02 Lt 12'. Se não houver, null\n"
                    "5. items = lista de serviços. CADA serviço diferente = item SEPARADO:\n"
                    "   - service_name = nome mais próximo do catálogo disponível\n"
                    "   - quantity = quantidade de peças/unidades (ex: '2 sofás' → quantity:2)\n"
                    "   - SE o texto tiver preço (R$XX): unit_price=XX, value=unit_price×quantity\n"
                    "   - SE não tiver preço (pedido rápido): unit_price=0, value=0 (o sistema busca no catálogo)\n"
                    "   Exemplos:\n"
                    "   'sofá 2 lugares' → [{\"service_name\":\"Lavagem Sofá 2 Lugares\",\"quantity\":1,\"unit_price\":0,\"value\":0}]\n"
                    "   'sofá R$290,00 e 2 poltronas R$60un' → [{\"service_name\":\"Sofá\",\"quantity\":1,\"unit_price\":290,\"value\":290},{\"service_name\":\"Poltrona\",\"quantity\":2,\"unit_price\":60,\"value\":120}]\n"
                    "   'Cadeira R$50un (2un=R$100)' → [{\"service_name\":\"Cadeira\",\"quantity\":2,\"unit_price\":50,\"value\":100}]\n"
                    "6. scheduled_date = YYYY-MM-DD ou null; scheduled_time = HH:MM ou null\n"
                    "7. total_pix = valor total PIX/à vista se mencionado, senão null\n"
                    "8. notes = observações úteis ou null\n\n"
                    "Responda SOMENTE com JSON válido, sem markdown, sem explicações:\n"
                    '{"client_name":"","phone":"","address":null,"complement":null,'
                    '"scheduled_date":null,"scheduled_time":null,'
                    '"total_pix":null,"total_cash":null,"notes":null,'
                    '"items":[{"service_name":"","quantity":1,"unit_price":0.0,"value":0.0}]}'
                )
                async with _httpx.AsyncClient(timeout=150.0) as hc2:
                    ollama_r = await hc2.post("http://localhost:11434/api/generate", json={
                        "model": "llama3.2:3b",
                        "prompt": ollama_prompt,
                        "stream": False,
                        "keep_alive": -1,
                        "options": {"temperature": 0.1},
                    })
                logging.info(f"[OLLAMA] generate status: {ollama_r.status_code}")
                if ollama_r.status_code != 200:
                    logging.warning(f"[OLLAMA] error body: {ollama_r.text[:500]}")
                if ollama_r.status_code == 200:
                    ollama_text = ollama_r.json().get("response", "")
                    logging.info(f"[OLLAMA] response preview: {repr(ollama_text[:300])}")
                    jm = re.search(r'\{.*\}', ollama_text, re.DOTALL)
                    if jm:
                        try:
                            raw_parsed = _json.loads(jm.group())
                            source = "ollama"
                            logging.info("[OLLAMA] JSON parsed OK")
                        except Exception as _je:
                            logging.warning(f"[OLLAMA] JSON parse error: {_je} — text: {repr(jm.group()[:200])}")
                    else:
                        logging.warning(f"[OLLAMA] No JSON found in response: {repr(ollama_text[:300])}")
        except Exception as _ox:
            logging.warning(f"Ollama falhou no interpret-message: {_ox}")

    # ── 3. Fallback final: parser Python ─────────────────────────────────────
    if raw_parsed is None:
        parsed = _smart_parse_budget(text, services)
        raw_parsed = {
            "client_name":    parsed.client_name,
            "phone":          parsed.client_phone,
            "address":        parsed.client_address,
            "complement":     parsed.client_complement,
            "scheduled_date": parsed.scheduled_date,
            "scheduled_time": parsed.scheduled_time,
            "total_pix":      parsed.total_pix,
            "total_cash":     parsed.total_cash,
            "notes":          parsed.notes,
            "items":          [dict(it) for it in (parsed.items or [])],
        }

    # ── Pós-processo: extrai complemento do address se complement estiver vazio ──
    if not (raw_parsed.get("complement") or "").strip():
        _addr_for_comp = (raw_parsed.get("address") or "").strip()
        _comp_extract = [
            (r'\b(apart(?:amento)?|apto?|ap)\s*\.?\s*(\d+\w*)', 'Apto'),
            (r'\b(bloco|bl)\s*\.?\s*([A-Za-z0-9]+)', 'Bloco'),
            (r'\b(sala|sl)\s*\.?\s*([A-Za-z0-9]+)', 'Sala'),
            (r'\b(quadra|qd)\s*\.?\s*([A-Za-z0-9]+)', 'Quadra'),
            (r'\b(lote|lt)\s*\.?\s*([A-Za-z0-9]+)', 'Lote'),
            (r'\b(casa)\s+([A-Za-z0-9]+)', 'Casa'),
            (r'\b(torre)\s+([A-Za-z0-9]+)', 'Torre'),
        ]
        for _cp, _pfx in _comp_extract:
            _cm = re.search(_cp, _addr_for_comp, re.IGNORECASE)
            if _cm:
                raw_parsed["complement"] = f'{_pfx} {_cm.group(2)}'
                raw_parsed["address"] = re.sub(_cp, '', _addr_for_comp, flags=re.IGNORECASE).strip().strip(',- ').strip()
                break

    # ── Pós-processo: normaliza complemento (adiciona prefixo se ausente) ────
    _comp = (raw_parsed.get("complement") or "").strip()
    if _comp and not re.match(
        r'^(apto?|apartamento|bloco|bl|sala|sl|quadra|qd|lote|lt|casa|torre|andar)\b',
        _comp, re.IGNORECASE
    ):
        _pfx_map = [
            (r'(?:apartamento|apto?)\s*\.?\s*' + re.escape(_comp), 'Apto'),
            (r'(?:bloco|bl)\s*\.?\s*' + re.escape(_comp), 'Bloco'),
            (r'(?:sala|sl)\s*\.?\s*' + re.escape(_comp), 'Sala'),
            (r'(?:quadra|qd)\s*\.?\s*' + re.escape(_comp), 'Quadra'),
            (r'(?:lote|lt)\s*\.?\s*' + re.escape(_comp), 'Lote'),
            (r'(?:casa)\s+' + re.escape(_comp), 'Casa'),
            (r'(?:torre)\s+' + re.escape(_comp), 'Torre'),
            (r'(?:andar)\s+' + re.escape(_comp), 'Andar'),
        ]
        for _pat, _pfx in _pfx_map:
            if re.search(_pat, text, re.IGNORECASE):
                raw_parsed["complement"] = f'{_pfx} {_comp}'
                break

    # ── Pós-processo: corrige qtd/valor de itens via padrão "(Nun = R$YY)" ──
    try:
        _qty_re = re.compile(r'R\$\s*([\d,.]+)\s*un\s*\((\d+)\s*un\s*=\s*R\$\s*([\d,.]+)\)', re.IGNORECASE)
        for _m in _qty_re.finditer(text):
            _unit = float(_m.group(1).replace(',', '.'))
            _qty  = int(_m.group(2))
            _tot  = float(_m.group(3).replace(',', '.'))
            for _it in (raw_parsed.get("items") or []):
                _iu = float(_it.get("unit_price") or 0)
                _iv = float(_it.get("value") or 0)
                if abs(_iu - _unit) < 0.5 and abs(_iv - _tot) > 0.5:
                    _it["quantity"] = _qty
                    _it["value"]    = _tot
                    break
    except Exception:
        pass

    # ── 3. Enriquecer itens com matching de catálogo ──────────────────────────
    AREA_TYPES = {"AREA_DE_TAPETE", "AREA_PERSIANA", "CARPETE_TAPETE_LOCAL", "TAPETE_REDONDO_DIAMETRO"}
    enriched_items = []
    for it in (raw_parsed.get("items") or []):
        item = dict(it)
        # Normaliza campos (LLM às vezes usa qty/total em vez de quantity/value)
        if "qty" in item and "quantity" not in item:
            item["quantity"] = item.pop("qty")
        if "total" in item and "value" not in item:
            item["value"] = item.pop("total")
        if "unit_value" in item and "unit_price" not in item:
            item["unit_price"] = item.pop("unit_value")

        m = await match_service_in_catalog(item.get("service_name", ""), services)
        explicit_value = float(item.get("value") or 0)
        if m:
            mtype = m.get("measure_type", "UNITARIO")
            price = float(m.get("sale_price") or 0)
            item["matched_service"] = {
                # BUG histórico: usava m.get("id")/m.get("name"), chaves que não existem no
                # retorno de match_service_in_catalog (é "service_id"/"service_name") --
                # isso fazia matched_service.id vir sempre None, e o item nunca ficava
                # vinculado ao catálogo mesmo com um bom match.
                "id": m.get("service_id"), "name": m.get("service_name"),
                "category": m.get("category"),
                "measure_type": mtype, "sale_price": price,
                "match_score": m.get("match_score"),
                "low_confidence": m.get("low_confidence", False),
            }
            area = float(item.get("area_m2") or 0)
            if mtype in AREA_TYPES:
                item["unit_price"] = price
                item["value"] = explicit_value or (round(area * price, 2) if area > 0 else 0)
                item["needs_measure"] = area == 0 and explicit_value == 0
            else:
                qty = int(item.get("quantity") or 1)
                item["quantity"] = qty
                item["unit_price"] = float(item.get("unit_price") or price)
                item["value"] = explicit_value or round(price * qty, 2)
                item["needs_measure"] = False
        enriched_items.append(item)

    # ── 4. Verificar cliente existente pelo telefone ──────────────────────────
    existing_client = None
    phone_raw = (raw_parsed.get("phone") or "").strip()
    # Remove prefixo +55 — sistema usa DDD + número (ex: 65 99973-1235)
    if phone_raw.startswith("+55 "):
        phone_raw = phone_raw[4:]
    elif phone_raw.startswith("+55"):
        phone_raw = phone_raw[3:].lstrip()
    if phone_raw:
        phone_digits = re.sub(r'\D', '', phone_raw)
        if phone_digits:
            existing_client = await db.clients.find_one(
                {"phone_primary": {"$regex": phone_digits[-8:]}})

    return {
        "client_name":        raw_parsed.get("client_name"),
        "phone":              phone_raw,
        "address":            raw_parsed.get("address"),
        "complement":         raw_parsed.get("complement"),
        "scheduled_date":     raw_parsed.get("scheduled_date"),
        "scheduled_time":     raw_parsed.get("scheduled_time"),
        "items":              enriched_items,
        "total_pix":          raw_parsed.get("total_pix"),
        "total_cash":         raw_parsed.get("total_cash"),
        "notes":              raw_parsed.get("notes"),
        "client_exists":      bool(existing_client),
        "existing_client_id": existing_client.get("id") if existing_client else None,
        "source":             source,
        "raw_text_truncated": text[:500] if len(text) > 500 else text,
    }


@api_router.post("/automation/execute-budget")
async def execute_budget_automation(payload: Dict[str, Any], current_user: UserPublic = Depends(get_current_user)):
    """
    Executa a automação de orçamento:
    1. Cria ou usa cliente existente
    2. Cria orçamento com os itens fornecidos
    3. Opcionalmente lança na Agenda (launch_agenda=true)
    4. Retorna IDs criados
    """
    import re as re2

    client_name    = (payload.get("client_name") or "").strip()
    client_phone   = (payload.get("client_phone") or "").strip()
    client_address = (payload.get("client_address") or "").strip()
    client_address_obj = payload.get("client_address_obj")  # endereço com lat/lng da busca
    # Endereço de execução (diferente do cliente — ex: escritório, condomínio diferente)
    exec_address_obj = payload.get("execution_address_obj")
    exec_address_text = (payload.get("execution_address") or "").strip()
    exec_complement  = (payload.get("execution_complement") or "").strip()
    has_exec_addr    = bool(exec_address_obj or exec_address_text)
    items          = payload.get("items", [])
    notes          = payload.get("notes", "")
    existing_id    = payload.get("existing_client_id")
    payment_method = payload.get("payment_method", "PIX_CNPJ_25995295000104")
    salesperson    = payload.get("salesperson", current_user.display_name or current_user.name)
    launch_agenda  = bool(payload.get("launch_agenda", False))
    scheduled_date = payload.get("scheduled_date") or ""   # "YYYY-MM-DD"
    scheduled_time = payload.get("scheduled_time") or ""   # "HH:MM"

    if not client_name:
        raise HTTPException(status_code=400, detail="Nome do cliente obrigatório.")

    # 1. Cliente
    if existing_id:
        client = await db.clients.find_one({"id": existing_id})
        client_id = existing_id
    else:
        client_id = await _next_id(db.clients, "CLI-", 4)
        # Usa endereço com coordenadas se disponível, senão usa texto simples
        if client_address_obj and client_address_obj.get("latitude"):
            addr_obj = client_address_obj
        else:
            addr_obj = {
                "full_address": client_address,
                "neighborhood": "",
                "city": "",
                "state": "",
                "latitude": None,
                "longitude": None,
            }
        # Complemento (condomínio/quadra/lote/apto) — preservado mesmo após busca Google
        complement = (payload.get("complement") or (client_address_obj or {}).get("complement") or "").strip()
        if complement:
            addr_obj["complement"] = complement
        new_client = {
            "id": client_id,
            "name": client_name,
            "phone_primary": client_phone,
            "email": "",
            "address": addr_obj,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        await db.clients.insert_one(new_client)
        await log_audit("client", client_id, "AUTO_CREATE", current_user, {"source": "automation"})

    # 2. Orçamento
    sys_cfg = await db.system_config.find_one({}) or {}
    salesperson_val = salesperson or sys_cfg.get("salesperson_default", "Sistema")

    budget_id = await _next_id(db.budgets, "ORC-", 7)

    # Endereço secundário resolvido (pode não ser usado por nenhum item, ou só
    # por alguns — decidido item a item mais abaixo, via "use_secondary_address").
    if has_exec_addr:
        resolved_exec_addr = exec_address_obj or {
            "full_address": exec_address_text,
            "neighborhood": "", "city": "", "state": "",
            "latitude": None, "longitude": None,
        }
        if exec_complement:
            resolved_exec_addr["complement"] = exec_complement
    else:
        resolved_exec_addr = None

    # ── Trava anti-item-orfao: nenhum item pode virar orcamento sem estar
    # vinculado a um servico real do catalogo. Se o frontend nao mandou
    # matched_service_id (usuario nao selecionou/nao criou o servico), tenta
    # um ultimo match automatico por texto; se ainda assim nao achar nada
    # razoavel, recusa a requisicao inteira (nada e criado pela metade) e diz
    # exatamente quais itens precisam ser resolvidos manualmente.
    resolved_services = []
    unresolved_names = []
    for raw_item in items:
        _msvc_id = raw_item.get("matched_service_id")
        _svc = (await db.services.find_one({"id": _msvc_id})) if _msvc_id else None
        if not _svc:
            _fallback = await match_service_in_catalog(raw_item.get("service_name", ""))
            if _fallback and not _fallback.get("low_confidence"):
                _svc = await db.services.find_one({"id": _fallback["service_id"]})
        if not _svc:
            unresolved_names.append(raw_item.get("service_name") or "(sem nome)")
        resolved_services.append(_svc)

    if unresolved_names:
        raise HTTPException(
            status_code=400,
            detail=(
                "Os seguintes itens não foram vinculados a nenhum serviço do catálogo: "
                + ", ".join(unresolved_names)
                + ". Selecione um serviço existente na busca ou cadastre um novo antes de confirmar."
            ),
        )

    budget_items = []
    for _idx, raw_item in enumerate(items):
        item_counter = len(budget_items) + 1
        item_id = f"ITM-AUTO-{budget_id}-{item_counter}"
        _svc = resolved_services[_idx]
        val = float(raw_item.get("value") or 0)
        qty = int(raw_item.get("quantity") or 1)

        # Endereço/modo por item — cada item decide se vai pro endereço
        # secundário (execução no local) ou pro fluxo padrão (retirar e levar).
        # Ajuste 03/10/2026: antes era um único modo pra TODOS os itens do
        # orçamento; agora cada item pode ir pro endereço do cliente ou pro
        # secundário, no mesmo orçamento.
        item_uses_secondary = bool(resolved_exec_addr) and bool(raw_item.get("use_secondary_address"))
        if item_uses_secondary:
            exec_mode     = "EXECUTAR_NO_LOCAL"
            exec_location = "NO_LOCAL"
            item_status   = "EXECUTAR_NO_LOCAL"
            item_exec_addr = resolved_exec_addr
        else:
            exec_mode     = "RETIRAR_E_LEVAR"
            exec_location = "RETIRADA"
            item_status   = "RETIRAR"
            item_exec_addr = None

        item_doc = {
            "id": item_id,
            "budget_id": budget_id,
            "client_id": client_id,
            "client_name": client_name,        # essencial para o Financeiro agrupar por cliente
            "service_id": (_svc or {}).get("id") or item_id,
            "service_name": (_svc or {}).get("name") or raw_item.get("service_name", "Serviço"),
            "service_code": (_svc or {}).get("code") or "AUTO",
            "service_category": (_svc or {}).get("category"),
            "measure_type": (_svc or {}).get("measure_type"),
            "quantity": qty,
            "unit_price": float(raw_item.get("unit_price") or val),
            "total_value": val,
            # medidas vindas do texto / preview (persianas, tapetes)
            "width": raw_item.get("width"),
            "height": raw_item.get("height"),
            "diameter": raw_item.get("diameter"),
            "area_m2": raw_item.get("area_m2"),
            "status": item_status,
            "payment_status": "PENDENTE",
            "paid_value": 0.0,
            "execution_mode": exec_mode,
            "execution_location": exec_location,
            "current_route_id": None,
        }
        if item_exec_addr:
            item_doc["execution_address"] = item_exec_addr
        budget_items.append(item_doc)

    budget_doc = {
        "id": budget_id,
        "client_id": client_id,
        "client_name": client_name,
        "payment_method": payment_method,
        "salesperson": salesperson_val,
        "budget_observations": notes or "",
        "internal_observations": "Criado via Automação" + (" + Agenda" if launch_agenda else ""),
        "items": budget_items,
        "total_value": sum(float(i.get("value", 0)) for i in items),
        "payment_status": "PENDENTE",
        "budget_status": "APROVADO",  # automação = serviço já confirmado
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "source": "AUTOMATION",
    }
    await db.budgets.insert_one(budget_doc)
    await log_audit("budget", budget_id, "AUTO_CREATE", current_user, {"source": "automation"})

    # 3. Lançar na Agenda (opcional)
    calendar_event_id = None
    google_event_id   = None
    agenda_error      = None
    if launch_agenda:
        try:
            creds_doc = await db.calendar_credentials.find_one({})
            if not creds_doc:
                agenda_error = "Google Calendar não autenticado"
            else:
                service = get_calendar_service(creds_doc["credentials"])

                # Local: endereço secundário se houver pelo menos um item usando ele,
                # senão endereço do cliente. Ajuste 03/10/2026: antes exec_mode/
                # item_status eram globais (um por orçamento); agora são por item,
                # então o evento único da Agenda usa um resumo: se ALGUM item vai
                # pro endereço secundário, o evento reflete isso.
                any_item_secondary = bool(resolved_exec_addr) and any(
                    bool(ri.get("use_secondary_address")) for ri in items
                )
                location_text = ""
                if any_item_secondary:
                    location_text = resolved_exec_addr.get("full_address", "")
                    if exec_complement:
                        location_text += f" - {exec_complement}"
                elif client_address:
                    location_text = client_address
                    comp = (payload.get("complement") or "").strip()
                    if comp:
                        location_text += f" - {comp}"
                agenda_item_status = "EXECUTAR_NO_LOCAL" if any_item_secondary else "RETIRAR"

                _desc_complement = (payload.get("complement") or "").strip()
                _sched_fmt = ""
                if scheduled_date:
                    try:
                        from datetime import datetime as _dt2
                        _sched_fmt = _dt2.strptime(scheduled_date, "%Y-%m-%d").strftime("%d/%m/%Y")
                    except Exception:
                        _sched_fmt = scheduled_date

                # Título com emoji + descrição emojizada + duração real do serviço
                # (30min retirada/entrega, 90min execução no local) -- mesmo padrão
                # usado no lançamento em lote da Agenda, pra ficar igual não
                # importa se o orçamento nasceu pelo caminho manual ou pela
                # automação com IA.
                summary, description, duration_minutes = _build_event_summary_and_description(
                    items=items,
                    client_name=client_name,
                    client_phone=client_phone,
                    salesperson=salesperson_val,
                    budget_id=budget_id,
                    payment_method=payment_method,
                    notes=notes,
                    complement=_desc_complement,
                    location_text=location_text,
                    sched_fmt=_sched_fmt,
                    item_status=agenda_item_status,
                )

                # Data/hora do evento
                from datetime import datetime as dt2, timedelta
                tz = "America/Cuiaba"
                if scheduled_date:
                    start_str = scheduled_date
                    time_part = scheduled_time or "09:00"
                    try:
                        start_dt = dt2.fromisoformat(f"{start_str}T{time_part}:00")
                        end_dt   = start_dt + timedelta(minutes=duration_minutes)
                        start_iso = start_dt.isoformat()
                        end_iso   = end_dt.isoformat()
                    except Exception:
                        start_iso = f"{start_str}T{time_part}:00"
                        _end_dt_fallback = dt2.strptime(time_part, "%H:%M") + timedelta(minutes=duration_minutes)
                        end_iso = f"{start_str}T{_end_dt_fallback.strftime('%H:%M')}:00"
                else:
                    # Sem data: evento de hoje às 09:00
                    today = datetime.utcnow().strftime("%Y-%m-%d")
                    start_dt = dt2.fromisoformat(f"{today}T09:00:00")
                    end_dt = start_dt + timedelta(minutes=duration_minutes)
                    start_iso = start_dt.isoformat()
                    end_iso = end_dt.isoformat()

                google_ev = {
                    "summary": summary,
                    "description": description,
                    "location": location_text,
                    "start": {"dateTime": start_iso, "timeZone": tz},
                    "end":   {"dateTime": end_iso,   "timeZone": tz},
                    "colorId": "5",  # amarelo = agendado/não confirmado
                }
                created_ev = service.events().insert(calendarId="primary", body=google_ev).execute()
                google_event_id = created_ev.get("id")

                # Salva no MongoDB
                item_ids = [it["id"] for it in budget_items]
                cal_doc = {
                    "id": f"CAL-{str(uuid.uuid4().int)[:7].zfill(7)}",
                    "route_id": None,
                    "stop_id": None,
                    "budget_item_ids": item_ids,
                    "color_id": "5",
                    "summary": summary,
                    "description": description,
                    "location": location_text,
                    "start_datetime": start_iso,
                    "end_datetime": end_iso,
                    "google_event_id": google_event_id,
                    "created_at": datetime.utcnow(),
                }
                await db.calendar_events.insert_one(cal_doc)
                calendar_event_id = cal_doc["id"]

                # Vínculo reverso nos itens
                for iid in item_ids:
                    await _append_to_item_array(iid, "agenda_event_ids", calendar_event_id)

        except Exception as ex:
            agenda_error = str(ex)

    return {
        "success": True,
        "client_id": client_id,
        "budget_id": budget_id,
        "items_created": len(budget_items),
        "client_created": not bool(existing_id),
        "calendar_event_id": calendar_event_id,
        "google_event_id": google_event_id,
        "agenda_error": agenda_error,
    }


ACTIVE_STATUSES = ["COLETADO", "EM_LAVAGEM", "EM_LAVAGEM_PARCEIRO", "CLIENTE_TROUXE"]


async def _find_active_items(client_id: str) -> List[Dict[str, Any]]:
    """Retorna itens em status ativo sem medidas confirmadas para um cliente."""
    budgets = await db.budgets.find(
        {"client_id": client_id, "items.status": {"$in": ACTIVE_STATUSES}}
    ).to_list(None)
    items = []
    for bud in budgets:
        for it in bud.get("items", []):
            if it.get("status") in ACTIVE_STATUSES and not it.get("confirmed_measures"):
                items.append({
                    "item_id": it["id"],
                    "budget_id": bud["id"],
                    "service_name": it.get("service_name", "Tapete"),
                    "status": it.get("status"),
                    "width": it.get("width"),
                    "height": it.get("height"),
                    "diameter": it.get("diameter"),
                    "measure_type": it.get("measure_type"),
                })
    return items


def _shape_of_measure_type(mt: Optional[str]) -> str:
    """'square' | 'round' | 'unknown' — unknown inclui TAPETE_A_IDENTIFICAR e None.
    Ajuste 02/10/2026 (conciliação de medidas por forma)."""
    if mt == "TAPETE_REDONDO_DIAMETRO":
        return "round"
    if mt in ("AREA_DE_TAPETE", "CARPETE_TAPETE_LOCAL"):
        return "square"
    return "unknown"


def _shape_of_parsed_item(item: Dict[str, Any]) -> str:
    """Forma detectada na linha da mensagem colada (diâmetro = redondo)."""
    return "round" if item.get("diameter") else "square"


def _reconcile_measures_with_items(
    parsed_items: List[Dict[str, Any]], indices: List[int], active_items: List[Dict[str, Any]],
) -> Dict[int, Dict[str, Any]]:
    """Casa cada medida recebida (por índice no texto) com o item pendente certo,
    por FORMA (quadrado/redondo), não por posição na mensagem.
      1. Tenta casar com um item pendente da MESMA forma.
      2. Se não achar, tenta um item "a identificar" (forma ainda não definida).
      3. Se ainda não achar E existir item pendente de OUTRA forma não usado,
         não decide sozinho — sinaliza shape_conflict pra conferência manual.
    Ajuste 02/10/2026."""
    pool_square  = [ai for ai in active_items if _shape_of_measure_type(ai.get("measure_type")) == "square"]
    pool_round   = [ai for ai in active_items if _shape_of_measure_type(ai.get("measure_type")) == "round"]
    pool_unknown = [ai for ai in active_items if _shape_of_measure_type(ai.get("measure_type")) == "unknown"]

    resolution: Dict[int, Dict[str, Any]] = {}
    pending: List[int] = []
    for i in indices:
        shape = _shape_of_parsed_item(parsed_items[i])
        pool = pool_square if shape == "square" else pool_round
        if pool:
            resolution[i] = {"target": pool.pop(0), "shape_conflict": False}
        else:
            pending.append(i)

    for i in pending:
        if pool_unknown:
            resolution[i] = {"target": pool_unknown.pop(0), "shape_conflict": False}
        else:
            leftover = pool_square + pool_round  # forma diferente, ainda sem uso
            resolution[i] = {"target": None, "shape_conflict": bool(leftover)}

    return resolution


# Mapeamento parceiro → (serviço_quadrado, serviço_redondo)
# Chave = client_id canônico do banco
_PARTNER_SERVICE_MAP: Dict[str, tuple] = {
    "CLI-0006": ("SRV-0036", "SRV-0037"),  # Leonardo - Dry Clean USA
    "CLI-0009": ("SRV-0040", "SRV-0041"),  # Forma Clean (Maika/Renan)
    "CLI-0010": ("SRV-0038", "SRV-0039"),  # Higia Service (Vinícius/Lucas)
    "CLI-0011": ("SRV-0042", "SRV-0043"),  # Wesley Higienização
    "CLI-0016": ("SRV-0044", "SRV-0045"),  # Felipe Gonçalves / João Farias
}
# Serviços genéricos para clientes comuns (CLIENTE_TROUXE + lavagem na empresa)
_GENERIC_SERVICE_MAP = ("SRV-0032", "SRV-0033")  # quadrado, redondo


async def _resolve_service_for_item(client_id: str, is_round: bool) -> Optional[Dict[str, Any]]:
    """Retorna o documento de serviço do catálogo adequado para o item."""
    pair = _PARTNER_SERVICE_MAP.get(client_id, _GENERIC_SERVICE_MAP)
    srv_id = pair[1] if is_round else pair[0]
    return await db.services.find_one({"id": srv_id})


async def _resolve_measure_update_fields(
    measures: Dict[str, Any], target_doc: Optional[Dict[str, Any]], client_id: str,
) -> Dict[str, Any]:
    """Prepara os campos pra atualizar a medida de um item existente:
      1. Limpa o campo da forma anterior (não deixa largura/altura velha junto
         com diâmetro novo, ou vice-versa, quando a forma real muda).
      2. Se o item era um placeholder "a identificar" (ou sem medida_type),
         resolve o serviço/preço reais pela forma que chegou — item só fica
         com preço e catálogo corretos depois que a forma é conhecida.
    Ajuste 02/10/2026."""
    fields = dict(measures)
    is_round = fields.get("diameter") is not None
    if is_round:
        fields.setdefault("width", None)
        fields.setdefault("height", None)
    elif fields.get("width") is not None or fields.get("height") is not None:
        fields.setdefault("diameter", None)

    current_mtype = (target_doc or {}).get("measure_type")
    if current_mtype in (None, "", "TAPETE_A_IDENTIFICAR"):
        svc = await _resolve_service_for_item(client_id, is_round)
        if svc:
            unit_price = float(svc.get("sale_price") or 0)
            area = fields.get("area_m2") or 0
            fields["service_id"] = svc["id"]
            fields["service_name"] = svc["name"]
            fields["service_code"] = svc.get("id")
            fields["service_category"] = svc.get("category")
            fields["measure_type"] = svc.get("measure_type")
            fields["unit_price"] = unit_price
            fields["total_value"] = round(unit_price * area, 2) if area else 0.0
    return fields


def _strip_accents(s: str) -> str:
    """Remove acentos: 'Katia' == 'Kátia', 'Jose' == 'José'."""
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode('ascii')

def _norm_client_name(s: str) -> str:
    """Minúsculo + sem acentos + espaços normalizados."""
    return ' '.join(_strip_accents(s).lower().split())

async def _resolve_client_fuzzy(name: str) -> List[Dict[str, Any]]:
    """Busca clientes tolerando apelidos, acentos errados, espaços extras e nomes compostos.

    Estratégia de score (maior = melhor match):
      100 — exato normalizado                     "Katia Salles" → "Katia Salles"
       95 — sem espaços igual (nome colado)       "Jose Lito"    → "Joselito"
       90 — digitado é prefixo do cadastrado      "Katia"        → "Katia Salles"
       85 — cadastrado é prefixo do digitado      "Katia Salles" → "Katia" (cadastrado assim)
       75 — todos os tokens digitados (≥3 chars)
             estão presentes no nome cadastrado   "Katia Carvalho" → "Ana Katia Carvalho"
       60 — primeiro token longo (≥4 chars) está
             no início do nome cadastrado         "Katia" → "Katia Maria..."
       40 — algum token longo (≥5 chars) aparece
             em qualquer posição do nome          "Salles" dentro de "Jose Salles"

    Desempate: clientes com orçamento mais recente sobem (tapeteiro recorrente).
    """
    name_norm     = _norm_client_name(name)
    name_nospace  = name_norm.replace(' ', '')
    tokens        = [t for t in name_norm.split() if len(t) >= 3]
    long_tokens   = [t for t in tokens if len(t) >= 4]
    first_token   = tokens[0] if tokens else ""

    # Traz todos os clientes (coleção pequena; full scan é ok)
    all_clients = await db.clients.find(
        {}, {"id": 1, "name": 1, "updated_at": 1, "created_at": 1}
    ).to_list(None)

    scored: List[tuple] = []
    for c in all_clients:
        cn         = _norm_client_name(c.get("name", ""))
        cn_nospace = cn.replace(' ', '')
        cn_tokens  = cn.split()

        if cn == name_norm:
            score = 100
        elif cn_nospace == name_nospace:
            score = 95
        elif cn.startswith(name_norm + ' ') or cn == name_norm:
            score = 90
        elif name_norm.startswith(cn + ' ') or name_norm == cn:
            score = 85
        elif tokens and all(t in cn_tokens for t in tokens):
            score = 75
        elif first_token and len(first_token) >= 4 and cn.startswith(first_token):
            score = 60
        elif any(t in cn for t in long_tokens if len(t) >= 5):
            score = 40
        else:
            continue

        # Tiebreaker: data mais recente sobe (usa updated_at ou created_at)
        ts_raw = c.get("updated_at") or c.get("created_at")
        ts = ts_raw.timestamp() if isinstance(ts_raw, datetime) else 0
        scored.append((score, ts, c))

    if not scored:
        return []

    scored.sort(key=lambda x: (-x[0], -x[1]))

    # Só retorna candidatos no mesmo nível de score do melhor
    best_score = scored[0][0]
    # Threshold: se o melhor é ≥75 retorna apenas esse tier; senão o melhor disponível
    tier_min = 75 if best_score >= 75 else best_score
    result = [c for s, _, c in scored if s >= tier_min]

    return result[:5]


@api_router.post("/automation/preview-measures")
async def preview_measures(payload: Dict[str, Any], current_user: UserPublic = Depends(get_current_user)):
    """Preview do que será preenchido a partir do texto de medidas."""
    text = payload.get("text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Texto vazio.")
    parsed = _parse_measures_text(text)

    # Para cada cliente único: busca candidatos no banco + itens ativos sem medida
    unique_names = {item.get("client_name", "") for item in parsed.items if item.get("client_name")}
    client_info: Dict[str, Any] = {}
    for name in unique_names:
        candidates = await _resolve_client_fuzzy(name)
        if not candidates:
            client_info[name] = {"exists": False, "client_id": None, "canonical_name": None,
                                 "active_items": [], "ambiguous": False, "candidates": []}
            continue

        ambiguous = len(candidates) > 1
        # Para cada candidato, busca itens ativos
        all_active = []
        for c in candidates:
            active = await _find_active_items(c["id"])
            for ai in active:
                ai["client_id"]   = c["id"]
                ai["client_name"] = c["name"]
            all_active.extend(active)

        client_info[name] = {
            "exists":         True,
            "client_id":      candidates[0]["id"] if not ambiguous else None,
            "canonical_name": candidates[0]["name"] if not ambiguous else None,
            "active_items":   all_active,
            "ambiguous":      ambiguous,
            "candidates":     [{"id": c["id"], "name": c["name"]} for c in candidates],
        }

    # Conciliação por cliente: casa cada medida com o item pendente certo pela
    # FORMA (quadrado/redondo), não pela posição na mensagem — ver
    # _reconcile_measures_with_items. Ajuste 02/10/2026.
    by_client_idx: Dict[str, List[int]] = {}
    for i, item in enumerate(parsed.items):
        by_client_idx.setdefault(item.get("client_name", ""), []).append(i)

    resolution: Dict[int, Dict[str, Any]] = {}
    for cname, idxs in by_client_idx.items():
        info = client_info.get(cname, {"active_items": []})
        resolution.update(
            _reconcile_measures_with_items(parsed.items, idxs, list(info.get("active_items", [])))
        )

    annotated = []
    for i, item in enumerate(parsed.items):
        cname = item.get("client_name", "")
        info  = client_info.get(cname, {"exists": False, "client_id": None, "active_items": [],
                                        "ambiguous": False, "candidates": [], "canonical_name": None})
        active_items = info.get("active_items", [])
        res    = resolution.get(i, {"target": None, "shape_conflict": False})
        target = res["target"]

        annotated.append({
            **item,
            "client_exists":      info["exists"],
            "existing_client_id": info["client_id"],
            "canonical_name":     info["canonical_name"],
            "ambiguous":          info["ambiguous"],
            "candidates":         info["candidates"],
            "active_items":       active_items,
            "target_item_id":     target["item_id"] if target else None,
            "target_budget_id":   target["budget_id"] if target else None,
            "action":             "update" if target else "create",
            "shape_conflict":     res["shape_conflict"],
        })

    return {"items": annotated, "count": len(annotated), "clients_summary": client_info}


def _dims_key(item: Dict[str, Any]) -> tuple:
    """Chave de identidade de um tapete para deduplicação interna.
    Para parceiros com etiqueta cor+número, inclui a etiqueta na chave
    pois dois tapetes do mesmo tamanho com etiquetas diferentes são peças distintas.
    """
    pl = item.get("partner_label") or {}
    label_key = (pl.get("color", ""), pl.get("number", "")) if pl.get("type") == "COLOR_NUM" else ("", "")
    return (
        (item.get("client_name") or "").strip().lower(),
        round(item.get("width") or 0, 2),
        round(item.get("height") or 0, 2),
        round(item.get("diameter") or 0, 2),
        label_key,
    )


def _dims_match(item_data: Dict[str, Any], db_item: Dict[str, Any], tol: float = 0.02) -> bool:
    """Retorna True se as dimensões e etiqueta do item são iguais (tolerância de 2cm).
    Para tapetes com etiqueta cor+número, a etiqueta também precisa bater."""
    def close(a, b): return abs((a or 0) - (b or 0)) <= tol

    # Se tem etiqueta cor+número, compara a etiqueta também
    pl_new = (item_data.get("partner_label") or {})
    pl_db  = (db_item.get("partner_label") or {})
    if pl_new.get("type") == "COLOR_NUM" or pl_db.get("type") == "COLOR_NUM":
        if pl_new.get("color") != pl_db.get("color") or pl_new.get("number") != pl_db.get("number"):
            return False

    if item_data.get("diameter") or db_item.get("diameter"):
        return close(item_data.get("diameter"), db_item.get("diameter"))
    return close(item_data.get("width"), db_item.get("width")) and \
           close(item_data.get("height"), db_item.get("height"))


@api_router.post("/automation/execute-measures")
async def execute_measures_automation(payload: Dict[str, Any], current_user: UserPublic = Depends(get_current_user)):
    """
    Para cada item de medida:
    1. Deduplicação interna — ignora linhas repetidas na mesma execução
    2. Deduplicação no banco — ignora se já existe item com mesmas dimensões
       e confirmed_measures=True nos últimos 60 dias para o mesmo cliente
    3. Cria novo orçamento/item se não houver duplicata
    """
    from datetime import timedelta
    items          = payload.get("items", [])
    client_extras  = payload.get("client_extras", {})  # { clientName: {name, phone, address, skip} }
    payment_method = payload.get("payment_method", "PIX_CNPJ_25995295000104")
    results = []
    cutoff = datetime.utcnow() - timedelta(days=60)

    # ── Nível 1: deduplicação interna (mesma colagem) ──────────────────────────
    # Apenas para tapetes COM etiqueta cor+número (ex: Rosa-856).
    # Tapetes de cliente sem etiqueta passam todos — dois tapetes do mesmo
    # tamanho para o mesmo cliente podem ser peças distintas.
    seen_labeled: set = set()
    deduped_items = []
    for item_data in items:
        pl = (item_data.get("partner_label") or {})
        is_labeled = pl.get("type") == "COLOR_NUM"
        if is_labeled:
            key = _dims_key(item_data)
            if key in seen_labeled:
                results.append({
                    "status": "duplicate",
                    "reason": f"etiqueta repetida na mesma colagem ({pl.get('color')}-{pl.get('number')})",
                })
                continue
            seen_labeled.add(key)
        deduped_items.append(item_data)

    # ── Nível 2: processa itens únicos ─────────────────────────────────────────
    for item_data in deduped_items:
        client_name  = (item_data.get("client_name") or "").strip()
        service_name = (item_data.get("service_name") or "Tapete").strip()
        if not client_name:
            results.append({"status": "skipped", "reason": "sem nome"})
            continue

        # Resolve cliente — 3 tentativas em ordem de precisão:
        # 1. Correspondência exata (case-insensitive)
        # 2. Nome digitado é prefixo do nome cadastrado (ex: "Ronimar" → "Ronimar Cruz")
        # 3. Nome cadastrado é prefixo do digitado (ex: "Ronimar Cruz" → "Ronimar")
        client = await db.clients.find_one(
            {"name": {"$regex": f"^{re.escape(client_name)}$", "$options": "i"}}
        )
        if not client:
            client = await db.clients.find_one(
                {"name": {"$regex": f"^{re.escape(client_name)}\\b", "$options": "i"}}
            )
        if not client:
            # Verifica se algum token do nome digitado bate com início do nome cadastrado
            first_token = re.escape(client_name.split()[0]) if client_name.split() else None
            if first_token and len(first_token) >= 4:  # mínimo 4 chars para evitar falsos positivos
                client = await db.clients.find_one(
                    {"name": {"$regex": f"^{first_token}", "$options": "i"}}
                )

        if not client:
            # Usa dados extras fornecidos pelo frontend (nome, telefone, endereço)
            extra = client_extras.get(client_name) or client_extras.get(
                next((k for k in client_extras if k.lower() == client_name.lower()), None), {}
            ) or {}
            final_name  = (extra.get("name") or client_name).strip()
            final_phone = (extra.get("phone") or "").strip()
            addr_obj    = extra.get("address") or {}
            complement  = (extra.get("complement") or "").strip()
            final_addr  = {
                "full_address": addr_obj.get("full_address", ""),
                "complement":   complement,
                "neighborhood": addr_obj.get("neighborhood", ""),
                "city":         addr_obj.get("city", ""),
                "state":        addr_obj.get("state", ""),
                "latitude":     addr_obj.get("latitude"),
                "longitude":    addr_obj.get("longitude"),
            }
            observations = (extra.get("observations") or "").strip()
            cid = await _next_id(db.clients, "CLI-", 4)
            await db.clients.insert_one({
                "id": cid, "name": final_name, "phone_primary": final_phone,
                "address": final_addr,
                "observations": observations or None,
                "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
            })
            client_name = final_name
            client_id = cid
        else:
            client_id = client["id"]
            client_name = client["name"]  # usa o nome canônico do banco

        # ── Deduplicação no banco (60 dias) — apenas para itens com etiqueta COLOR_NUM ──
        # Para clientes sem etiqueta, dois tapetes do mesmo tamanho podem ser peças distintas.
        # Para o Leonardo (e outros parceiros com etiqueta), a etiqueta garante unicidade.
        pl_check = (item_data.get("partner_label") or {})
        if pl_check.get("type") == "COLOR_NUM":
            recent_budgets = await db.budgets.find(
                {"client_id": client_id, "created_at": {"$gte": cutoff}}
            ).to_list(None)
            already_exists = False
            for bud in recent_budgets:
                for it in bud.get("items", []):
                    if it.get("confirmed_measures") and _dims_match(item_data, it):
                        results.append({
                            "status": "duplicate",
                            "reason": f"já lançado em {bud['id']} ({it['id']})",
                            "budget_id": bud["id"], "item_id": it["id"],
                        })
                        already_exists = True
                        break
                if already_exists:
                    break
            if already_exists:
                continue

        measures = {k: item_data[k] for k in ["width", "height", "diameter", "area_m2", "linear_meters"]
                    if k in item_data and item_data[k] is not None}
        measures["confirmed_measures"] = True
        if item_data.get("partner_label"):
            measures["partner_label"] = item_data["partner_label"]
        if item_data.get("reference_date"):
            # Data extraída do cabeçalho da mensagem de WhatsApp — dia em que o
            # tapete foi de fato recolhido/medido (usada no relatório de parceiros).
            measures["reference_date"] = item_data["reference_date"]

        # A medida chegando pela mensagem colada significa que o tapete JÁ foi
        # recolhido, lavado e medido — não é mais "em andamento". Avança o status
        # pro último estágio antes da finalização, pra ficar disponível pra rota
        # de entrega (própria) ou de busca (parceiro) assim que o item já estava
        # ativo (COLETADO/EM_LAVAGEM/EM_LAVAGEM_PARCEIRO/CLIENTE_TROUXE).
        is_partner_item = bool(pl_check.get("type"))
        ready_status = "AGUARDANDO_BUSCAR" if is_partner_item else "AGUARDANDO_ENTREGA"

        # ── Atualiza item existente se o frontend indicou qual é ───────────────
        target_item_id = item_data.get("target_item_id")
        if target_item_id and item_data.get("action") == "update":
            target_doc = None
            async for bud_lookup in db.budgets.find({"items.id": target_item_id}):
                for it_lookup in bud_lookup.get("items", []):
                    if it_lookup.get("id") == target_item_id:
                        target_doc = it_lookup
                        break
                if target_doc:
                    break
            update_fields = await _resolve_measure_update_fields(measures, target_doc, client_id)
            status_advanced = bool(target_doc and target_doc.get("status") in ACTIVE_STATUSES)
            if status_advanced:
                update_fields["status"] = ready_status
            updated = await _update_item_fields(target_item_id, update_fields, current_user)
            if updated:
                if status_advanced:
                    await _append_to_item_array(target_item_id, "status_history", {
                        "status": ready_status, "at": datetime.utcnow().isoformat(),
                        "by_user_id": current_user.id, "by_user_name": current_user.name,
                        "notes": "Medidas confirmadas via automação (mensagem de WhatsApp) — pronto",
                    })
                bud = await db.budgets.find_one({"items.id": target_item_id}, {"id": 1})
                results.append({
                    "status": "updated",
                    "item_id": target_item_id,
                    "budget_id": bud["id"] if bud else "?",
                    "client": client_name,
                })
                continue

        # ── Tenta encontrar item ativo sem medida automaticamente ──────────────
        active_items = await _find_active_items(client_id)
        if len(active_items) == 1:
            # Só um candidato → atualiza sem ambiguidade (sempre ACTIVE_STATUSES por
            # construção de _find_active_items, então sempre avança pro status "pronto")
            ai = active_items[0]
            ai_update_fields = await _resolve_measure_update_fields(measures, ai, client_id)
            ai_update_fields["status"] = ready_status
            await _update_item_fields(ai["item_id"], ai_update_fields, current_user)
            await _append_to_item_array(ai["item_id"], "status_history", {
                "status": ready_status, "at": datetime.utcnow().isoformat(),
                "by_user_id": current_user.id, "by_user_name": current_user.name,
                "notes": "Medidas confirmadas via automação (mensagem de WhatsApp) — pronto",
            })
            results.append({
                "status": "updated", "item_id": ai["item_id"],
                "budget_id": ai["budget_id"], "client": client_name,
            })
            continue

        # ── Cria novo orçamento com o item ────────────────────────────────────
        bid = await _next_id(db.budgets, "ORC-", 7)
        iid = f"ITM-{bid}-1"
        # Itens de parceiro (com etiqueta cor+número) chegam pela mensagem de medidas
        # já LAVADOS e guardados, aguardando o parceiro buscar — não "CLIENTE_TROUXE"
        # (que significa recém-chegado, ainda por lavar). Default por tipo:
        is_partner_item = bool(pl_check.get("type"))
        default_status = "AGUARDANDO_BUSCAR" if is_partner_item else "CLIENTE_TROUXE"
        item_status = item_data.get("status") or default_status

        # Resolve serviço do catálogo
        is_round = bool(measures.get("diameter"))
        svc = await _resolve_service_for_item(client_id, is_round)
        if svc:
            svc_id   = svc["id"]
            svc_name = svc["name"]
            svc_code = svc.get("service_code", svc["id"])
            svc_cat  = svc.get("category", "TAPETES")
            svc_mtype = svc.get("measure_type")          # ← tipo de medida do serviço
            svc_exloc = svc.get("execution_location", "CLIENTE_TROUXE")
            unit_price = float(svc.get("sale_price") or 0)
            cost_price = float(svc.get("cost_price") or 0)
            area = measures.get("area_m2") or 0
            total_val = round(unit_price * area, 2) if area else 0.0
        else:
            svc_id = None; svc_name = service_name; svc_code = "AUTO-MEASURES"
            svc_cat = "TAPETES"; svc_mtype = None; svc_exloc = "CLIENTE_TROUXE"
            unit_price = 0.0; cost_price = 0.0; total_val = 0.0

        budget_item = {
            "id": iid,
            "client_id": client_id,        # essencial para o Financeiro agrupar por cliente
            "client_name": client_name,    # essencial para o Financeiro agrupar por cliente
            "service_id": svc_id, "service_name": svc_name,
            "service_code": svc_code, "service_category": svc_cat,
            "measure_type": svc_mtype,     # essencial p/ editor mostrar medidas
            "quantity": 1,
            "unit_price": unit_price, "cost_price": cost_price, "total_value": total_val,
            "status": item_status, "payment_status": "PENDENTE", "paid_value": 0.0,
            # Parceiro: item já chegou lavado, cliente/parceiro vem buscar — não é rota nossa
            "execution_mode": "CLIENTE_TROUXE" if is_partner_item else "RETIRAR_E_LEVAR",
            "is_partner_item": is_partner_item,  # flag explícita para filtros futuros
            "execution_location": svc_exloc,
            # Histórico de status sintetizado — sem isso o item nasce "órfão" de
            # histórico (este endpoint insere direto no Mongo, sem passar pelo
            # normalizador que outros fluxos usam para inicializar status_history).
            "status_history": [{
                "status": item_status,
                "at": (item_data.get("reference_date") or datetime.utcnow().isoformat()),
                "by_user_id": current_user.id,
                "by_user_name": current_user.display_name or current_user.name,
                "notes": "Item criado via Automação de Medidas"
                         + (" (parceiro — já lavado, aguardando retirada)" if is_partner_item else ""),
            }],
            **measures,
        }
        await db.budgets.insert_one({
            "id": bid, "client_id": client_id, "client_name": client_name,
            "payment_method": payment_method,
            "salesperson": current_user.display_name or current_user.name,
            "budget_observations": "", "internal_observations": "Criado via Automação de Medidas",
            "items": [budget_item], "total_value": total_val, "payment_status": "PENDENTE",
            "budget_status": "APROVADO",  # automação já é confirmação implícita do serviço
            "created_at": datetime.utcnow(), "updated_at": datetime.utcnow(),
            "source": "AUTOMATION_MEASURES",
        })
        results.append({"status": "created", "budget_id": bid, "item_id": iid})

    created  = sum(1 for r in results if r["status"] == "created")
    dupes    = sum(1 for r in results if r["status"] == "duplicate")
    skipped  = sum(1 for r in results if r["status"] == "skipped")
    return {"success": True, "processed": created, "duplicates": dupes, "skipped": skipped, "results": results}


def _format_service_name(service_name: str) -> str:
    """Remove o sufixo com o nome do parceiro do nome do serviço para exibição no
    relatório (todos os parceiros têm essa descrição completa, mas o nome do parceiro
    já aparece na coluna 'Parceiro' — não precisa repetir). Corta tanto em ' - ...'
    quanto a partir da palavra 'Parceiro' (ex: 'Lavagem de Cortinas / Blackouts
    Parceiro Leonardo Dry Clean' -> 'Lavagem de Cortinas / Blackouts')."""
    name = service_name or "Tapete"
    name = name.split(" - ", 1)[0]
    name = re.split(r'\bParceiro\b', name, maxsplit=1, flags=re.IGNORECASE)[0]
    return name.strip()


def _format_partner_tag(item: Dict[str, Any], partner_name: str = "") -> str:
    """Formata a etiqueta do parceiro (cor+número ou texto livre) para exibição no relatório.
    Quando o texto livre é apenas o nome do próprio parceiro/cliente (sem identificação real
    do item, ex: "Leonardo - Dry Clean USA"), trata como ausente -> aparece "sem nome"."""
    label = item.get("partner_label") or {}
    if label.get("type") == "COLOR_NUM":
        return f"{label.get('color', '')} {label.get('number', '')}".strip()
    if label.get("type") == "TEXT":
        text = (label.get("text") or "").strip()
        pname = (partner_name or "").strip().lower()
        if text and pname and (text.lower() == pname or text.lower() in pname or pname in text.lower()):
            return ""
        return text
    return ""


# ─────────────────────────────────────────────────────────────────────────────
# MARKETING — Remarketing & Reativação
# ─────────────────────────────────────────────────────────────────────────────

@api_router.get("/marketing/remarketing")
async def get_remarketing_budgets(
    days: int = 7,
    current_user: dict = Depends(get_current_user)
):
    """Orçamentos PENDENTE/ENVIADO sem movimento por X dias (remarketing)."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    pipeline = [
        {"$match": {
            "status": {"$in": ["PENDENTE", "ENVIADO"]},
            "updated_at": {"$lt": cutoff}
        }},
        {"$lookup": {
            "from": "clients",
            "localField": "client_id",
            "foreignField": "id",
            "as": "_client"
        }},
        {"$project": {
            "_id": 0,
            "id": 1,
            "client_id": 1,
            "client_name": 1,
            "total_value": 1,
            "updated_at": 1,
            "created_at": 1,
            "status": 1,
            "items": {"$slice": ["$items", 3]},
            "phone": {"$arrayElemAt": ["$_client.phone_primary", 0]}
        }},
        {"$sort": {"updated_at": 1}},
        {"$limit": 200}
    ]
    results = await db.budgets.aggregate(pipeline).to_list(200)
    now = datetime.utcnow()
    for r in results:
        upd = r.get("updated_at")
        if isinstance(upd, str):
            try:
                upd = datetime.fromisoformat(upd.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                upd = None
        r["days_since"] = (now - upd).days if upd else 0
    return results


@api_router.get("/marketing/reactivation")
async def get_reactivation_clients(
    days: int = 30,
    current_user: dict = Depends(get_current_user)
):
    """Clientes com último serviço concluído há mais de X dias — candidatos a reativação."""
    cutoff = datetime.utcnow() - timedelta(days=days)
    pipeline = [
        {"$match": {
            "status": {"$in": ["ENTREGUE", "EXECUTADO", "BUSCOU"]},
        }},
        {"$group": {
            "_id": {"client_id": "$client_id", "service_category": "$service_category"},
            "last_date": {"$max": "$updated_at"},
            "client_name": {"$first": "$client_name"},
            "client_id": {"$first": "$client_id"},
            "service_name": {"$first": "$service_name"},
            "last_value": {"$last": "$total_value"},
        }},
        {"$match": {"last_date": {"$lt": cutoff}}},
        {"$lookup": {
            "from": "clients",
            "localField": "client_id",
            "foreignField": "id",
            "as": "_client"
        }},
        {"$project": {
            "_id": 0,
            "client_id": 1,
            "client_name": 1,
            "service_category": "$_id.service_category",
            "service_name": 1,
            "last_date": 1,
            "last_value": 1,
            "phone": {"$arrayElemAt": ["$_client.phone_primary", 0]}
        }},
        {"$sort": {"last_date": 1}},
        {"$limit": 200}
    ]
    results = await db.budget_items.aggregate(pipeline).to_list(200)
    now = datetime.utcnow()
    for r in results:
        last = r.get("last_date")
        if isinstance(last, str):
            try:
                last = datetime.fromisoformat(last.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                last = None
        r["days_since"] = (now - last).days if last else 0
        if last:
            r["last_date"] = last.isoformat()
    return results


@api_router.get("/reports/partner-items")
async def partner_items_report(
    partner_client_id: Optional[str] = None,
    start_date: Optional[str] = None,   # YYYY-MM-DD
    end_date: Optional[str] = None,     # YYYY-MM-DD
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Relatório de conferência/fechamento de tapetes de parceiros — substitui a
    planilha externa (Google Sheets) usada hoje para faturar Leonardo, Higia,
    Forma Clean, Wesley e João/Felipe. Campo genérico de parceiro (não fixo
    em um único parceiro) para poder gerar a conferência de qualquer um deles.

    Filtra por data de referência do item (data extraída do cabeçalho da
    mensagem do WhatsApp em que o tapete foi recolhido/medido — quando ausente,
    cai no fallback da data de criação do orçamento).
    """
    partner_ids = [partner_client_id] if partner_client_id else list(_PARTNER_SERVICE_MAP.keys())
    cursor = db.budgets.find({"client_id": {"$in": partner_ids}})
    budgets = await cursor.to_list(None)

    def _row_date(item: Dict[str, Any], budget: Dict[str, Any]) -> str:
        ref = item.get("reference_date")
        if ref:
            return ref[:10]
        created = budget.get("created_at")
        if isinstance(created, datetime):
            return created.strftime("%Y-%m-%d")
        return str(created or "")[:10]

    rows: List[Dict[str, Any]] = []
    totals_by_partner: Dict[str, Dict[str, float]] = {}

    for bud in budgets:
        partner_name = bud.get("client_name", "")
        for it in bud.get("items", []):
            row_date = _row_date(it, bud)
            if start_date and row_date and row_date < start_date:
                continue
            if end_date and row_date and row_date > end_date:
                continue
            valor = float(it.get("total_value") or 0)
            area = float(it.get("area_m2") or 0)
            rows.append({
                "parceiro": partner_name,
                "objeto": _format_service_name(it.get("service_name")),
                "etiqueta": _format_partner_tag(it, partner_name),
                "largura": it.get("width"),
                "comprimento": it.get("height"),
                "diametro": it.get("diameter"),
                "area_m2": round(area, 2) if area else None,
                "valor": round(valor, 2),
                "data_referencia": row_date,
                "status": it.get("status"),
                "budget_id": bud.get("id"),
                "item_id": it.get("id"),
            })
            tot = totals_by_partner.setdefault(partner_name, {"area_m2": 0.0, "valor": 0.0, "qtd": 0})
            tot["area_m2"] += area
            tot["valor"] += valor
            tot["qtd"] += 1

    rows.sort(key=lambda r: (r["parceiro"], r["data_referencia"]))
    for t in totals_by_partner.values():
        t["area_m2"] = round(t["area_m2"], 2)
        t["valor"] = round(t["valor"], 2)

    return {"rows": rows, "totals_by_partner": totals_by_partner}


@api_router.get("/payment-methods")
async def get_payment_methods():
    """Retorna lista de formas de pagamento configuradas no sistema."""
    config = await db.system_config.find_one({})
    default = SystemConfig()
    if config and config.get("payment_methods"):
        return {
            "payment_methods": config["payment_methods"],
            "payment_fees": config.get("payment_fees") or default.payment_fees,
        }
    # fallback padrão
    return {"payment_methods": default.payment_methods, "payment_fees": default.payment_fees}

@api_router.post("/system-config/logo")
async def upload_company_logo(
    file: UploadFile = File(...),
    current_user: UserPublic = Depends(get_current_user)
):
    """Upload/troca da logo da empresa usada no PDF."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Apenas administradores podem alterar a logo.")
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Apenas imagens são aceitas.")
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    contents = await file.read()
    logo_path = str(UPLOADS_DIR / "logo.png")

    # Redimensiona/recomprime a logo para não inflar o tamanho do PDF gerado.
    # No PDF a logo é exibida a 1.5x1.2 polegadas — 600px no lado maior já é
    # nitidez de sobra (>200dpi nesse tamanho de exibição) e mantém o arquivo leve.
    try:
        img = PILImage.open(BytesIO(contents))
        img.load()
        MAX_SIDE = 600
        if max(img.size) > MAX_SIDE:
            img.thumbnail((MAX_SIDE, MAX_SIDE), PILImage.LANCZOS)
        # Preserva transparência se houver (RGBA/P), senão converte para RGB
        if img.mode not in ("RGBA", "RGB", "P"):
            img = img.convert("RGBA" if "A" in img.getbands() else "RGB")
        buf = BytesIO()
        img.save(buf, format="PNG", optimize=True)
        final_bytes = buf.getvalue()
    except Exception as e:
        logging.warning(f"Falha ao redimensionar logo, salvando original: {e}")
        final_bytes = contents

    with open(logo_path, "wb") as f:
        f.write(final_bytes)
    return {
        "message": "Logo atualizada com sucesso.",
        "path": logo_path,
        "size_bytes": len(final_bytes),
        "size_bytes_original": len(contents),
    }


@api_router.get("/system-config/logo")
async def get_logo_status():
    """Verifica se existe logo personalizada."""
    found = _find_logo()
    return {
        "has_custom_logo": bool(found),
        "has_fallback_logo": bool(found),
        "logo_url": "/api/system-config/logo/file" if found else None
    }


@api_router.get("/system-config/logo/file")
async def serve_logo():
    """Serve o arquivo de logo atual."""
    path = _find_logo()
    if path:
        return FileResponse(path, media_type="image/png")
    raise HTTPException(status_code=404, detail="Logo não encontrada.")


@api_router.get("/system-config", response_model=SystemConfig)
async def get_system_config():
    """Obter configurações do sistema"""
    try:
        config = await db.system_config.find_one({})
        if not config:
            # Create default config if doesn't exist
            default_config = SystemConfig()
            await db.system_config.insert_one(default_config.dict())
            return default_config
        return SystemConfig(**config)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching system config: {str(e)}")

@api_router.put("/system-config", response_model=SystemConfig)
async def update_system_config(config: SystemConfig):
    """Atualizar configurações do sistema"""
    try:
        config.updated_at = datetime.utcnow()
        config_dict = config.dict()
        
        # Upsert - update if exists, insert if doesn't
        await db.system_config.replace_one({}, config_dict, upsert=True)
        
        return config
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating system config: {str(e)}")

@api_router.post("/budgets/{budget_id}/items", response_model=BudgetItem)
async def add_budget_item(budget_id: str, item_data: BudgetItemCreate):
    """Adicionar item ao orçamento"""
    try:
        budget = await db.budgets.find_one({"id": budget_id})
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        service = await db.services.find_one({"id": item_data.service_id})
        if not service:
            raise HTTPException(status_code=404, detail="Service not found")
        
        # Calculate measurements and total based on service type
        item_dict = item_data.dict()
        service_obj = Service(**service)
        
        # Add measurement fields to item dict
        item_dict["width"] = item_data.width
        item_dict["height"] = item_data.height
        item_dict["diameter"] = item_data.diameter
        item_dict["fabric_folds"] = item_data.fabric_folds
        item_dict["fabric_per_fold"] = item_data.fabric_per_fold
        
        # Calculate area and linear meters based on measure type
        if service_obj.measure_type == MeasureType.AREA_DE_TAPETE or service_obj.measure_type == MeasureType.CARPETE_TAPETE_LOCAL:
            if item_data.width and item_data.height:
                item_dict["area_m2"] = item_data.width * item_data.height
                item_dict["quantity"] = item_dict["area_m2"]
        elif service_obj.measure_type == MeasureType.TAPETE_REDONDO_DIAMETRO:
            if item_data.diameter:
                radius = item_data.diameter / 2
                item_dict["area_m2"] = radius * radius * 3.14
                item_dict["quantity"] = item_dict["area_m2"]
        elif service_obj.measure_type == MeasureType.AREA_PERSIANA:
            if item_data.width and item_data.height:
                item_dict["area_m2"] = item_data.width * item_data.height
                item_dict["quantity"] = item_dict["area_m2"]
        elif service_obj.measure_type in [MeasureType.METRAGEM_LINEAR_CORTINA_SIMPLES, MeasureType.METRAGEM_LINEAR_PE_DIREITO_DUPLO, MeasureType.METRAGEM_LINEAR_ESPECIAL]:
            if item_data.fabric_folds and item_data.fabric_per_fold:
                item_dict["linear_meters"] = (item_data.fabric_folds * item_data.fabric_per_fold) / 100
                item_dict["quantity"] = item_dict["linear_meters"]
            elif item_data.linear_meters:
                item_dict["linear_meters"] = item_data.linear_meters
                item_dict["quantity"] = item_dict["linear_meters"]
        
        # Generate item ID
        last_item = await db.budget_items.find_one(sort=[("created_at", -1)])
        if last_item:
            last_id_num = int(last_item["id"].split("-")[1])
            new_id_num = last_id_num + 1
        else:
            new_id_num = 1
        
        item_dict["id"] = f"ITM-{str(new_id_num).zfill(7)}"
        item_dict["service_name"] = service_obj.name
        item_dict["service_code"] = service_obj.id
        item_dict["unit_price"] = service_obj.sale_price
        item_dict["total_value"] = item_dict["quantity"] * service_obj.sale_price
        item_dict["execution_location"] = service_obj.execution_location
        # Usar status padrão do serviço ou fallback para lógica anterior se não existir
        service_dict = service_obj.dict() if hasattr(service_obj, 'dict') else service_obj
        default_status = service_dict.get('default_service_status')
        
        # 🔍 LOG DE MONITORAMENTO - Adicionado para rastrear herança de status
        logger.info(f"💾 HERANÇA DE STATUS - Item: {item_dict['id']}, Service: {service_obj.id}, Herança: {default_status}")
        
        if default_status:
            item_dict["status"] = default_status
            logger.info(f"✅ HERANÇA APLICADA - Item {item_dict['id']} recebeu status '{default_status}' do service {service_obj.id}")
        else:
            # Fallback para lógica anterior (serviços antigos sem o campo)
            fallback_status = ServiceStatus.RETIRAR if service_obj.execution_location == ExecutionLocation.RETIRADA else ServiceStatus.EXECUTAR_NO_LOCAL
            item_dict["status"] = fallback_status
            logger.warning(f"⚠️ FALLBACK APLICADO - Item {item_dict['id']} do service {service_obj.id} sem default_service_status, aplicado fallback: {fallback_status}")
        
        # 🔍 LOG FINAL DE CONFIRMAÇÃO
        logger.info(f"🎯 STATUS FINAL - Item {item_dict['id']}: {item_dict['status']} (Service: {service_obj.id}, Nome: {service_obj.name})")
        item_dict["created_at"] = datetime.utcnow()
        
        budget_item = BudgetItem(**item_dict)
        
        # Add item to budget
        await db.budgets.update_one(
            {"id": budget_id},
            {
                "$push": {"items": budget_item.dict()},
                "$set": {"updated_at": datetime.utcnow()}
            }
        )
        
        # Recalculate totals
        await recalculate_budget_totals(budget_id)
        
        return budget_item
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error adding item to budget: {str(e)}")

async def recalculate_budget_totals(budget_id: str):
    """Recalcular totais do orçamento"""
    budget = await db.budgets.find_one({"id": budget_id})
    if not budget:
        return
    
    total_value = sum(item["total_value"] for item in budget["items"])
    total_area_m2 = sum(item.get("area_m2", 0) or 0 for item in budget["items"])
    total_linear_meters = sum(item.get("linear_meters", 0) or 0 for item in budget["items"])
    total_units = len(budget["items"])
    
    await db.budgets.update_one(
        {"id": budget_id},
        {
            "$set": {
                "total_value": total_value,
                "total_area_m2": total_area_m2,
                "total_linear_meters": total_linear_meters,
                "total_units": total_units,
                "updated_at": datetime.utcnow()
            }
        }
    )

# Dashboard endpoint
@api_router.get("/dashboard", response_model=DashboardSummary)
async def get_dashboard():
    """Obter resumo do dashboard"""
    try:
        total_clients = await db.clients.count_documents({})
        active_budgets = await db.budgets.count_documents({})
        
        # These would need more complex queries based on actual business logic
        pending_routes = 0  # Items with status RETIRAR, EXECUTAR_NO_LOCAL, ENTREGAR
        pending_execution_today = 0  # Items scheduled for today
        items_in_washing = 0  # Items with status EM_LAVAGEM, EM_LAVAGEM_PARCEIRO
        financial_pending = 0  # Unpaid budgets
        
        return DashboardSummary(
            pending_routes=pending_routes,
            pending_execution_today=pending_execution_today,
            items_in_washing=items_in_washing,
            financial_pending=financial_pending,
            total_clients=total_clients,
            active_budgets=active_budgets
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting dashboard data: {str(e)}")

# Routes endpoints
# ── Company Mode endpoints ──────────────────────────────────────────────────

COMPANY_STATUSES = [
    "CLIENTE_TROUXE", "COLETADO",
    "EM_LAVAGEM", "EM_LAVAGEM_PARCEIRO",
    "AGUARDANDO_ENTREGA", "AGUARDANDO_BUSCAR", "ENTREGAR"
]

@api_router.get("/items/company-mode")
async def get_company_mode_items(current_user: UserPublic = Depends(get_current_user)):
    """Todos os itens nas etapas do processo interno da empresa."""
    pipeline = [
        {"$unwind": "$items"},
        {"$match": {"items.status": {"$in": COMPANY_STATUSES}}},
        {"$lookup": {"from": "clients", "localField": "client_id", "foreignField": "id", "as": "client_info"}},
        {"$unwind": {"path": "$client_info", "preserveNullAndEmptyArrays": True}},
        {"$project": {
            "_id": 0,
            "item":           "$items",
            "budget_id":      "$id",
            "client_name":    "$client_name",
            "salesperson":    "$salesperson",
            "neighborhood":   "$client_info.address.neighborhood",
            "city":           "$client_info.address.city",
        }}
    ]
    results = []
    async for doc in db.budgets.aggregate(pipeline):
        item = doc["item"]
        results.append({
            "id":                   item.get("id"),
            "budget_id":            doc["budget_id"],
            "client_name":          doc["client_name"] or item.get("client_name"),
            "salesperson":          doc.get("salesperson"),
            "neighborhood":         doc.get("neighborhood", ""),
            "city":                 doc.get("city", ""),
            "service_name":         item.get("service_name"),
            "service_code":         item.get("service_code"),
            "service_category":     item.get("service_category"),
            "measure_type":         item.get("measure_type"),
            "status":               item.get("status"),
            "total_value":          item.get("total_value", 0),
            "original_total_value": item.get("original_total_value"),
            "quantity":             item.get("quantity", 1),
            "area_m2":              item.get("area_m2"),
            "linear_meters":        item.get("linear_meters"),
            "width":                item.get("width"),
            "height":               item.get("height"),
            "diameter":             item.get("diameter"),
            "fabric_folds":         item.get("fabric_folds"),
            "fabric_per_fold":      item.get("fabric_per_fold"),
            "partner_label":        item.get("partner_label"),
            "confirmed_measures":   item.get("confirmed_measures", False),
            "execution_mode":       item.get("execution_mode"),
            "payment_status":       item.get("payment_status"),
            "observations":         item.get("observations"),
        })
    return results


@api_router.post("/items/bulk-status")
async def bulk_change_status(
    payload: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user)
):
    """Alterar status de vários itens de uma vez. Body: {item_ids: [...], status: '...', notes: ''}"""
    item_ids  = payload.get("item_ids", [])
    new_status = payload.get("status")
    notes     = payload.get("notes", "")
    if not item_ids or not new_status:
        raise HTTPException(status_code=400, detail="item_ids e status são obrigatórios.")
    valid = {s.value for s in ServiceStatus}
    if new_status not in valid:
        raise HTTPException(status_code=400, detail=f"Status inválido: {new_status}")
    CLEAR_ROUTE_ON = {
        ServiceStatus.COLETADO.value, ServiceStatus.EM_LAVAGEM.value,
        ServiceStatus.EM_LAVAGEM_PARCEIRO.value, ServiceStatus.AGUARDANDO_ENTREGA.value,
        ServiceStatus.AGUARDANDO_BUSCAR.value, ServiceStatus.ENTREGUE.value,
        ServiceStatus.EXECUTADO.value, ServiceStatus.BUSCOU.value,
        ServiceStatus.CANCELADO_PELO_CLIENTE.value,
    }
    updated = 0
    for item_id in item_ids:
        budget, item = await _find_budget_and_item(item_id)
        if not item or item.get("status") == new_status:
            continue
        entry = {"status": new_status, "at": datetime.utcnow().isoformat(),
                 "by_user_id": current_user.id, "by_user_name": current_user.name, "notes": notes}
        update_fields: Dict[str, Any] = {"status": new_status}
        if new_status in CLEAR_ROUTE_ON and item.get("current_route_id"):
            update_fields["current_route_id"] = None
            update_fields["current_route_stop_id"] = None
        await _update_item_fields(item_id, update_fields, current_user)
        await _append_to_item_array(item_id, "status_history", entry)
        updated += 1
    return {"updated": updated, "status": new_status}


@api_router.patch("/items/{item_id}/measures")
async def update_item_measures(
    item_id: str,
    payload: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user)
):
    """Atualizar medidas e identificação de parceiro, com auditoria e recálculo de valor."""
    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    measure_fields = ["width","height","diameter","area_m2","linear_meters",
                      "fabric_folds","fabric_per_fold","quantity"]
    before = {f: item.get(f) for f in measure_fields}

    update: Dict[str, Any] = {}

    # Medidas
    for f in measure_fields:
        if f in payload:
            update[f] = payload[f]

    # Recalcular area_m2 se width/height fornecidos
    w = payload.get("width", item.get("width"))
    h = payload.get("height", item.get("height"))
    if w and h and "width" in payload or "height" in payload:
        update["area_m2"] = round(float(w) * float(h), 4)

    # Recalcular valor se houver mudança de área/metragem
    new_area = update.get("area_m2", item.get("area_m2"))
    new_linear = update.get("linear_meters", item.get("linear_meters"))
    if (new_area or new_linear) and item.get("unit_price"):
        qty = update.get("quantity", item.get("quantity", 1))
        base = float(new_area or new_linear or qty)
        new_value = round(float(item["unit_price"]) * base, 2)
        if new_value != item.get("total_value"):
            if not item.get("original_total_value"):
                update["original_total_value"] = item.get("total_value")
            update["total_value"] = new_value

    # Partner label
    if "partner_label" in payload:
        update["partner_label"] = payload["partner_label"]

    # Confirmação de medidas
    if "confirmed_measures" in payload:
        update["confirmed_measures"] = bool(payload["confirmed_measures"])

    # Auditoria de medidas
    after = {f: update.get(f, item.get(f)) for f in measure_fields}
    history_entry = {
        "at": datetime.utcnow().isoformat(),
        "by_user_id": current_user.id,
        "by_user_name": current_user.name,
        "before": before,
        "after": after,
        "notes": payload.get("notes", ""),
    }

    await _update_item_fields(item_id, update, current_user)
    await _append_to_item_array(item_id, "measures_history", history_entry)
    await log_audit("item", item_id, "MEASURES_UPDATE", current_user, {"before": before, "after": after})

    return {"success": True, "updated_fields": list(update.keys()),
            "new_value": update.get("total_value"), "original_value": update.get("original_total_value")}


@api_router.get("/budget-items/available-for-routes")
async def get_available_budget_items_for_routes(current_user: UserPublic = Depends(get_current_user)):
    """Itens disponíveis para rota: status route-eligible + sem rota corrente."""
    try:
        route_statuses = [
            ServiceStatus.RETIRAR.value,
            ServiceStatus.EXECUTAR_NO_LOCAL.value,
            ServiceStatus.ENTREGAR.value,
            ServiceStatus.AGUARDANDO_ENTREGA.value,  # Pronto para rota de entrega
        ]
        pipeline = [
            {"$unwind": "$items"},
            {"$match": {
                # Só orçamentos aprovados (ou legado sem campo = APROVADO implícito)
                "$or": [
                    {"budget_status": "APROVADO"},
                    {"budget_status": {"$exists": False}},
                    {"budget_status": None},
                ],
                "items.status": {"$in": route_statuses},
                "items.client_desisted": {"$ne": True},   # exclui desistências
                # Itens de parceiro (client trouxe / client leva) não geram rota de técnico
                "items.execution_mode": {"$nin": ["CLIENTE_TROUXE", "CLIENTE_LEVARA"]},
                "$and": [{"$or": [
                    {"items.current_route_id": None},
                    {"items.current_route_id": {"$exists": False}},
                ]}],
            }},
            {"$lookup": {
                "from": "clients",
                "localField": "client_id",
                "foreignField": "id",
                "as": "client_info",
            }},
            {"$unwind": {"path": "$client_info", "preserveNullAndEmptyArrays": True}},
            {"$project": {
                "_id": 0,
                "budget_id": "$id",
                "client_id": "$client_id",
                "client_name": "$client_name",
                "item": "$items",
                "client_address": "$client_info.address",
            }},
        ]
        cursor = db.budgets.aggregate(pipeline)
        results = []
        async for doc in cursor:
            item = doc["item"]
            # Ignora itens sem ID válido (criados antes do sistema de IDs)
            if not item.get("id"):
                continue
            status = item.get("status")
            # Endereço específico por etapa, com fallback no cliente
            if status == ServiceStatus.RETIRAR.value:
                addr = item.get("pickup_address") or doc.get("client_address") or {}
            elif status in (ServiceStatus.ENTREGAR.value, ServiceStatus.AGUARDANDO_ENTREGA.value):
                addr = item.get("delivery_address") or doc.get("client_address") or {}
            else:
                addr = item.get("execution_address") or doc.get("client_address") or {}
            results.append({
                "budget_item_id": item["id"],
                "budget_id": doc["budget_id"],
                "client_id": doc["client_id"],
                "client_name": item.get("client_name") or doc["client_name"],
                "service_name": item.get("service_name"),
                "service_code": item.get("service_code"),
                "service_value": item.get("total_value"),
                "status": status,
                "execution_mode": item.get("execution_mode"),
                "payment_status": item.get("payment_status"),
                "neighborhood": (addr or {}).get("neighborhood", ""),
                "address": addr,
                "scheduled_date": (
                    item.get("scheduled_pickup_date") if status == ServiceStatus.RETIRAR.value
                    else item.get("scheduled_delivery_date") if status in (ServiceStatus.ENTREGAR.value, ServiceStatus.AGUARDANDO_ENTREGA.value)
                    else item.get("scheduled_execution_date")
                ),
            })
        return {"available_items": results}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching available items: {str(e)}")

@api_router.post("/routes", response_model=Route)
async def create_route(route_data: RouteCreate):
    """Create a new route"""
    try:
        # Get company address from system config
        system_config = await db.system_config.find_one({})
        if not system_config or not system_config.get('latitude') or not system_config.get('longitude'):
            raise HTTPException(status_code=400, detail="Company GPS coordinates not configured")
        
        company_address = {
            "full_address": system_config.get('address_full', ''),
            "latitude": system_config['latitude'],
            "longitude": system_config['longitude'],
            "neighborhood": system_config.get('neighborhood', ''),
            "city": system_config.get('city', ''),
            "state": system_config.get('state', '')
        }
        
        # Generate route ID
        last_route = await db.routes.find_one(sort=[("created_at", -1)])
        if last_route:
            last_id_num = int(last_route["id"].split("-")[1])
            new_id_num = last_id_num + 1
        else:
            new_id_num = 1
        
        route_id = f"RTE-{str(new_id_num).zfill(7)}"
        
        # Create route
        route = Route(
            id=route_id,
            vehicle_type=route_data.vehicle_type,
            planned_date=route_data.planned_date,
            planned_start_time=route_data.planned_start_time,
            alias=route_data.alias,  # Custom route name
            company_address=company_address,
            stops=[]
        )
        
        # Insert route
        await db.routes.insert_one(route.dict())
        return route
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating route: {str(e)}")

@api_router.get("/routes", response_model=List[Route])
async def get_routes(limit: int = 20):
    """Get routes (limited to 20 most recent)"""
    try:
        cursor = db.routes.find().sort("created_at", -1).limit(limit)
        routes = []
        async for route in cursor:
            routes.append(Route(**route))
        return routes
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching routes: {str(e)}")

@api_router.get("/routes/{route_id}", response_model=Route)
async def get_route(route_id: str):
    """Get specific route by ID"""
    try:
        route = await db.routes.find_one({"id": route_id})
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        return Route(**route)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error fetching route: {str(e)}")

@api_router.put("/routes/{route_id}", response_model=Route)
async def update_route(route_id: str, route_update: RouteUpdate):
    """Update route information"""
    try:
        # Check if route exists
        existing_route = await db.routes.find_one({"id": route_id})
        if not existing_route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Prepare update data
        update_data = {}
        if route_update.vehicle_type is not None:
            update_data["vehicle_type"] = route_update.vehicle_type
        if route_update.planned_date is not None:
            update_data["planned_date"] = route_update.planned_date
        if route_update.planned_start_time is not None:
            update_data["planned_start_time"] = route_update.planned_start_time
        if route_update.alias is not None:
            update_data["alias"] = route_update.alias
        
        # Add updated timestamp
        update_data["updated_at"] = datetime.utcnow()
        
        # Update route
        await db.routes.update_one(
            {"id": route_id},
            {"$set": update_data}
        )
        
        # Return updated route
        updated_route = await db.routes.find_one({"id": route_id})
        return Route(**updated_route)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating route: {str(e)}")

@api_router.put("/routes/{route_id}/stops")
async def update_route_stops(route_id: str, stops_data: List[dict]):
    """Update route stops with priorities"""
    try:
        route = await db.routes.find_one({"id": route_id})
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        # Process stops data
        stops = []
        for stop_data in stops_data:
            # Get budget item details
            budget = await db.budgets.find_one({"items.id": stop_data["budget_item_id"]})
            if not budget:
                continue
                
            # Find the specific item
            budget_item = None
            for item in budget["items"]:
                if item["id"] == stop_data["budget_item_id"]:
                    budget_item = item
                    break
            
            if not budget_item:
                continue
            
            # Get client details
            client = await db.clients.find_one({"id": budget["client_id"]})
            if not client:
                continue
            
            # Generate stop ID - use uuid to guarantee uniqueness per batch
            stop_id = f"STP-{str(uuid.uuid4().int)[:7].zfill(7)}"
            
            # Calculate estimated duration based on status
            estimated_duration = 30  # Default for RETIRAR/ENTREGAR
            if budget_item["status"] == ServiceStatus.EXECUTAR_NO_LOCAL:
                estimated_duration = 120
            
            stop = RouteStop(
                id=stop_id,
                route_id=route_id,
                budget_item_id=stop_data["budget_item_id"],
                client_id=budget["client_id"],
                client_name=budget["client_name"],
                service_name=budget_item["service_name"],
                service_value=budget_item["total_value"],
                address=client["address"],
                priority=Priority(stop_data.get("priority", "AUTOMATICA")),
                estimated_duration=estimated_duration,
                service_status=ServiceStatus(budget_item["status"]),
                order_sequence=len(stops) + 1,  # Initial sequence
                delivery_order=len(stops) + 1   # Will be updated after optimization
            )
            stops.append(stop)
        
        # Update route with stops
        await db.routes.update_one(
            {"id": route_id},
            {
                "$set": {
                    "stops": [stop.dict() for stop in stops],
                    "updated_at": datetime.utcnow()
                }
            }
        )

        # Atualiza cada item para refletir current_route_id (ITEM como pilar)
        new_item_ids = [s.budget_item_id for s in stops]
        for s in stops:
            try:
                await db.budgets.update_one(
                    {"items.id": s.budget_item_id},
                    {"$set": {
                        "items.$.current_route_id": route_id,
                        "items.$.current_route_stop_id": s.id,
                        "items.$.updated_at": datetime.utcnow(),
                    },
                    "$addToSet": {"items.$.route_history": route_id}},
                )
            except Exception as ex:
                print(f"[routes/stops] erro atualizando item {s.budget_item_id}: {ex}")

        # Reconciliação: itens que estavam vinculados a ESTA rota mas saíram da
        # nova lista de paradas (removidos/reordenados) precisam ter o vínculo
        # limpo. Sem isso o item fica órfão — some de available-for-routes (pois
        # ainda tem current_route_id) sem estar em rota nenhuma nem ser entregue.
        try:
            await db.budgets.update_many(
                {"items": {"$elemMatch": {
                    "current_route_id": route_id,
                    "id": {"$nin": new_item_ids},
                }}},
                {"$set": {
                    "items.$[elem].current_route_id": None,
                    "items.$[elem].current_route_stop_id": None,
                    "items.$[elem].updated_at": datetime.utcnow(),
                }},
                array_filters=[{
                    "elem.current_route_id": route_id,
                    "elem.id": {"$nin": new_item_ids},
                }],
            )
        except Exception as ex:
            print(f"[routes/stops] erro limpando itens removidos da rota {route_id}: {ex}")

        return {"message": "Route stops updated successfully", "stops_count": len(stops)}
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating route stops: {str(e)}")

@api_router.post("/routes/{route_id}/optimize")
async def optimize_route(route_id: str, route_type: str = "CURTA"):
    """Optimize route using OSRM with priorities and route type"""
    try:
        route = await db.routes.find_one({"id": route_id})
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        
        if not route.get("stops"):
            raise HTTPException(status_code=400, detail="Route has no stops to optimize")
        
        # Convert dict stops to RouteStop objects
        stops = []
        for stop_dict in route["stops"]:
            print(f"Converting stop: {stop_dict.get('id', 'NO_ID')} - {stop_dict.get('client_name', 'NO_NAME')}")
            try:
                stop_obj = RouteStop(**stop_dict)
                stops.append(stop_obj)
                print(f"Successfully converted stop: {stop_obj.id}")
            except Exception as e:
                print(f"Error converting stop: {e}")
        
        print(f"Total stops converted: {len(stops)}")
        
        # Get company coordinates
        company_coords = (
            route["company_address"]["longitude"],
            route["company_address"]["latitude"]
        )
        
        # Optimize stops with priorities
        optimized_stops = await optimize_route_with_priorities(stops, company_coords)
        
        # Merge stops at same address (same lat/lng) — preserva TODOS os budget_item_ids
        merged_stops = []
        address_groups = {}
        
        for stop in optimized_stops:
            address_key = f"{stop.address['latitude']},{stop.address['longitude']}"
            if address_key in address_groups:
                existing_stop = address_groups[address_key]
                existing_stop.estimated_duration += 60
                existing_stop.service_name += f" + {stop.service_name}"
                existing_stop.service_value += stop.service_value
                # Preserva o budget_item_id do stop mesclado
                if stop.budget_item_id not in existing_stop.extra_budget_item_ids:
                    existing_stop.extra_budget_item_ids.append(stop.budget_item_id)
            else:
                stop.extra_budget_item_ids = []
                address_groups[address_key] = stop
                merged_stops.append(stop)
        
        # Calculate route geometry and totals using OSRM
        all_coords = [company_coords]
        all_coords.extend([(s.address['longitude'], s.address['latitude']) for s in merged_stops])
        all_coords.append(company_coords)
        
        print(f"🎯 Calculating {route_type} route with {len(all_coords)} coordinates")
        osrm_result = await calculate_route_osrm(all_coords, "driving", route_type)
        
        total_duration = sum(stop.estimated_duration for stop in merged_stops)
        total_distance = 0.0
        route_geometry = None
        
        if 'trips' in osrm_result and len(osrm_result['trips']) > 0:
            trip = osrm_result['trips'][0]
            total_distance = trip.get('distance', 0) / 1000  # Convert to km
            total_duration += trip.get('duration', 0) / 60  # Add travel time in minutes
            route_geometry = trip.get('geometry')
        
        # Update route with optimization results
        await db.routes.update_one(
            {"id": route_id},
            {
                "$set": {
                    "stops": [stop.dict() for stop in merged_stops],
                    "total_duration": int(total_duration),
                    "total_distance": round(total_distance, 2),
                    "route_geometry": route_geometry,
                    "updated_at": datetime.utcnow(),
                    "last_edited_by": "Sistema"  # Future: replace with actual user
                }
            }
        )
        
        return {
            "message": "Route optimized successfully",
            "total_stops": len(merged_stops),
            "total_duration_minutes": int(total_duration),
            "total_distance_km": round(total_distance, 2),
            "osrm_status": "success" if 'trips' in osrm_result else "fallback"
        }
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error optimizing route: {str(e)}")


@api_router.post("/routes/{route_id}/optimize-geoapify")
async def optimize_route_geoapify_endpoint(route_id: str, traffic: bool = Query(default=False)):
    """Optimize route using Geoapify Route Planner API.
    traffic=true → considera o tráfego médio/típico da região (afeta ordem e tempo)."""
    try:
        route = await db.routes.find_one({"id": route_id})
        if not route:
            raise HTTPException(status_code=404, detail="Route not found")
        if not route.get("stops"):
            raise HTTPException(status_code=400, detail="Route has no stops to optimize")

        stops = []
        for stop_dict in route["stops"]:
            try:
                stops.append(RouteStop(**stop_dict))
            except Exception as e:
                print(f"Error converting stop: {e}")

        print(f"🌍 Geoapify optimizing {len(stops)} stops for route {route_id}")
        company_coords = (
            route["company_address"]["longitude"],
            route["company_address"]["latitude"]
        )
        vehicle_type = route.get("vehicle_type", "CARRO")

        optimized_stops, dist_km, travel_min, route_geometry = \
            await optimize_route_with_priorities_geoapify(stops, company_coords, vehicle_type, use_traffic=traffic)

        # Merge stops at same address — preserva TODOS os budget_item_ids
        merged_stops    = []
        address_groups  = {}
        for stop in optimized_stops:
            key = f"{stop.address['latitude']},{stop.address['longitude']}"
            if key in address_groups:
                address_groups[key].estimated_duration += 60
                address_groups[key].service_name       += f" + {stop.service_name}"
                address_groups[key].service_value      += stop.service_value
                if stop.budget_item_id not in address_groups[key].extra_budget_item_ids:
                    address_groups[key].extra_budget_item_ids.append(stop.budget_item_id)
            else:
                stop.extra_budget_item_ids = []
                address_groups[key] = stop
                merged_stops.append(stop)

        # Geoapify 'time' already includes service time at stops + travel time
        # Use it directly; fallback to service time sum if Geoapify had no data
        if travel_min > 0:
            total_min = int(travel_min)
        else:
            total_min = sum(s.estimated_duration for s in merged_stops)

        # Calcula AMBOS os tempos (livre e com trânsito) para a ordem final,
        # permitindo mostrar "Sem trânsito: Xmin · Com trânsito: Ymin".
        comp_lng, comp_lat = company_coords
        ordered_ll = [(comp_lat, comp_lng)]
        for s in merged_stops:
            a = s.address or {}
            if a.get("latitude") and a.get("longitude"):
                ordered_ll.append((float(a["latitude"]), float(a["longitude"])))
        ordered_ll.append((comp_lat, comp_lng))
        _, _, time_free    = get_road_geometry_geoapify(ordered_ll, use_traffic=False)
        _, _, time_traffic = get_road_geometry_geoapify(ordered_ll, use_traffic=True)
        duration_free    = int(time_free)    if time_free    else total_min
        duration_traffic = int(time_traffic) if time_traffic else total_min

        await db.routes.update_one(
            {"id": route_id},
            {"$set": {
                "stops":          [s.dict() for s in merged_stops],
                "total_duration": total_min,
                "total_duration_free":    duration_free,
                "total_duration_traffic": duration_traffic,
                "total_distance": round(dist_km, 2),
                "route_geometry": route_geometry,
                "route_provider": "GEOAPIFY",
                "considered_traffic": bool(traffic),
                "updated_at":     datetime.utcnow(),
                "last_edited_by": "Geoapify"
            }}
        )
        return {
            "message":                "Route optimized successfully with Geoapify",
            "total_stops":            len(merged_stops),
            "total_duration_minutes": total_min,
            "total_duration_free":    duration_free,
            "total_duration_traffic": duration_traffic,
            "total_distance_km":      round(dist_km, 2),
            "considered_traffic":     bool(traffic),
            "geoapify_status":        "success" if dist_km > 0 else "fallback"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error optimizing route with Geoapify: {str(e)}")


@api_router.get("/routes/stats/monthly-distance")
async def get_monthly_distance_stats(
    year: Optional[int] = None,
    current_user: UserPublic = Depends(get_current_user)
):
    """
    Estatísticas mensais de deslocamento.
    Agrega total_distance por mês/ano, separado por veículo e provedor.
    Base para futuro relatório de quilometragem mensal.
    """
    try:
        target_year = year or datetime.utcnow().year
        pipeline = [
            {
                "$match": {
                    "planned_date": {"$regex": f"^{target_year}"},
                    "total_distance": {"$gt": 0}
                }
            },
            {
                "$addFields": {
                    "month": {"$substr": ["$planned_date", 5, 2]}
                }
            },
            {
                "$group": {
                    "_id": {
                        "month":    "$month",
                        "vehicle":  "$vehicle_type",
                        "provider": "$route_provider"
                    },
                    "total_km":     {"$sum": "$total_distance"},
                    "routes_count": {"$sum": 1},
                    "stops_total":  {"$sum": {"$size": {"$ifNull": ["$stops", []]}}}
                }
            },
            {"$sort": {"_id.month": 1, "_id.vehicle": 1}}
        ]

        cursor = db.routes.aggregate(pipeline)
        rows = []
        async for doc in cursor:
            rows.append({
                "year":         target_year,
                "month":        int(doc["_id"]["month"]),
                "vehicle_type": doc["_id"]["vehicle"],
                "provider":     doc["_id"].get("provider", "OSRM"),
                "total_km":     round(doc["total_km"], 2),
                "routes_count": doc["routes_count"],
                "stops_total":  doc["stops_total"],
            })

        # Totais gerais por mês (soma de todos os veículos)
        monthly_totals: dict = {}
        for r in rows:
            m = r["month"]
            if m not in monthly_totals:
                monthly_totals[m] = {"month": m, "year": target_year, "total_km": 0.0, "routes_count": 0, "stops_total": 0}
            monthly_totals[m]["total_km"]     = round(monthly_totals[m]["total_km"] + r["total_km"], 2)
            monthly_totals[m]["routes_count"] += r["routes_count"]
            monthly_totals[m]["stops_total"]  += r["stops_total"]

        return {
            "year":           target_year,
            "detail":         rows,
            "monthly_totals": sorted(monthly_totals.values(), key=lambda x: x["month"]),
            "annual_km":      round(sum(v["total_km"] for v in monthly_totals.values()), 2),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao calcular estatísticas: {str(e)}")


@api_router.delete("/routes/{route_id}")
async def delete_route(route_id: str, current_user: UserPublic = Depends(get_current_user)):
    """Delete a route and clear current_route_id on its items."""
    try:
        # Limpa current_route_id dos itens vinculados a esta rota
        await db.budgets.update_many(
            {"items.current_route_id": route_id},
            {"$set": {
                "items.$[elem].current_route_id": None,
                "items.$[elem].current_route_stop_id": None,
            }},
            array_filters=[{"elem.current_route_id": route_id}],
        )
        result = await db.routes.delete_one({"id": route_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Route not found")
        return {"message": "Route deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error deleting route: {str(e)}")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@api_router.post("/admin/migrate-budget-item-status")
async def migrate_budget_item_status():
    """
    Migração para corrigir status dos budget items existentes
    Atualiza budget items para herdar default_service_status dos serviços
    """
    try:
        # Get all budgets with items
        budgets = await db.budgets.find({}).to_list(length=None)
        print(f"📋 Found {len(budgets)} budgets to check")
        
        # Get all services for reference
        services = await db.services.find({}).to_list(length=None)
        service_map = {s["id"]: s for s in services}
        
        updated_count = 0
        total_items = 0
        budgets_updated = 0
        
        for budget in budgets:
            items = budget.get('items', [])
            items_updated = False
            
            for item in items:
                total_items += 1
                service_id = item.get('service_id')
                current_status = item.get('status')
                
                if service_id in service_map:
                    service = service_map[service_id]
                    correct_status = service.get('default_service_status')
                    
                    # Update if status is different
                    if current_status != correct_status:
                        item['status'] = correct_status
                        items_updated = True
                        updated_count += 1
                        print(f"✅ Updated {item['id']}: {current_status} -> {correct_status}")
            
            # Update budget if any items were changed
            if items_updated:
                await db.budgets.update_one(
                    {"id": budget["id"]},
                    {"$set": {"items": items, "updated_at": datetime.utcnow()}}
                )
                budgets_updated += 1
        
        return {
            "message": f"Migration completed successfully",
            "total_items": total_items,
            "updated_items": updated_count,
            "budgets_updated": budgets_updated
        }
        
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Additional endpoint for updating budget item status
@api_router.put("/budget-items/{item_id}/status")
async def update_budget_item_status(
    item_id: str,
    status: str = Query(...),
    current_user: UserPublic = Depends(get_current_user),
):
    """Update the status of a specific budget item (compat — também grava em status_history)."""
    try:
        if status not in [s.value for s in ServiceStatus]:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid options: {[s.value for s in ServiceStatus]}")

        budget = await db.budgets.find_one({"items.id": item_id})
        if not budget:
            raise HTTPException(status_code=404, detail="Budget item not found")

        current_item = next((it for it in (budget.get("items") or []) if it.get("id") == item_id), None)
        old_status = current_item.get("status") if current_item else None

        await db.budgets.update_one(
            {"items.id": item_id},
            {"$set": {
                "items.$.status": status,
                "items.$.updated_at": datetime.utcnow(),
                "items.$.updated_by": current_user.id,
            }},
        )

        if old_status != status:
            entry = {
                "status": status,
                "at": datetime.utcnow().isoformat(),
                "by_user_id": current_user.id,
                "by_user_name": current_user.name,
                "notes": "Atualizado via endpoint legacy",
            }
            await db.budgets.update_one(
                {"items.id": item_id},
                {"$push": {"items.$.status_history": entry}},
            )
            await log_audit("item", item_id, "STATUS_CHANGE", current_user,
                            {"from": old_status, "to": status, "via": "legacy"})
            await _sync_linked_events_color(item_id)

        return {"success": True, "item_id": item_id, "new_status": status}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating budget item status: {str(e)}")

@api_router.get("/service-status/options")
async def get_service_status_options():
    """Get all available service status options"""
    return {"status_options": [{"value": status.value, "label": status.value} for status in ServiceStatus]}

# Photo upload model
class PhotoUpload(BaseModel):
    id: str = Field(default_factory=lambda: f"PHT-{str(uuid.uuid4().int)[:7].zfill(7)}")
    assignment_id: Optional[str] = None
    item_id: str
    technician_id: str
    filename: str
    file_size: int
    file_type: str
    photo_type: str = "BEFORE"  # "BEFORE", "AFTER", "DAMAGE"
    uploaded_at: datetime = Field(default_factory=datetime.utcnow)

@api_router.post("/technician/upload-photos")
async def upload_technician_photos(
    item_id: str = Form(...),
    technician_id: str = Form(...),
    assignment_id: Optional[str] = Form(None),
    photo_type: str = Form("BEFORE"),
    files: List[UploadFile] = File(...)
):
    """Upload photos for technician service items"""
    try:
        # Create uploads directory if it doesn't exist
        upload_dir = Path("/app/uploads/photos")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        uploaded_photos = []
        
        for file in files:
            # Validate file type
            if not file.content_type.startswith('image/'):
                raise HTTPException(status_code=400, detail=f"File {file.filename} is not an image")
            
            # Generate unique filename
            file_extension = Path(file.filename).suffix.lower()
            unique_filename = f"{item_id}_{photo_type}_{uuid.uuid4().hex[:8]}{file_extension}"
            file_path = upload_dir / unique_filename
            
            # Save file
            file_content = await file.read()
            with open(file_path, "wb") as f:
                f.write(file_content)
            
            # Create photo record
            photo = PhotoUpload(
                assignment_id=assignment_id,
                item_id=item_id,
                technician_id=technician_id,
                filename=unique_filename,
                file_size=len(file_content),
                file_type=file.content_type,
                photo_type=photo_type
            )
            
            # Save to database
            await db.technician_photos.insert_one(photo.dict())
            uploaded_photos.append(photo.dict())
        
        return {
            "success": True,
            "uploaded_count": len(uploaded_photos),
            "photos": uploaded_photos
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error uploading photos: {str(e)}")

@api_router.get("/technician/photos/{item_id}")
async def get_technician_photos(item_id: str):
    """Get all photos for a specific item"""
    try:
        photos = await db.technician_photos.find({"item_id": item_id}).to_list(None)
        return {"photos": photos}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting photos: {str(e)}")

@api_router.get("/technician/photos/file/{filename}")
async def get_photo_file(filename: str):
    """Serve photo files"""
    try:
        file_path = Path(f"/app/uploads/photos/{filename}")
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="Photo not found")
        
        return FileResponse(
            path=file_path,
            media_type="image/jpeg",
            filename=filename
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error serving photo: {str(e)}")

@api_router.delete("/technician/photos/{photo_id}")
async def delete_technician_photo(photo_id: str):
    """Delete a technician photo"""
    try:
        # Find photo in database
        photo = await db.technician_photos.find_one({"id": photo_id})
        if not photo:
            raise HTTPException(status_code=404, detail="Photo not found")
        
        # Delete file from filesystem
        file_path = Path(f"/app/uploads/photos/{photo['filename']}")
        if file_path.exists():
            file_path.unlink()
        
        # Delete from database
        result = await db.technician_photos.delete_one({"id": photo_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Photo not found in database")
        
        return {"success": True, "message": "Photo deleted successfully"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting photo: {str(e)}")


# ============================================================
# ACEITE VIRTUAL — modelos e endpoints públicos
# ============================================================

class TermVersion(BaseModel):
    """Versão imutável do Termo de Ciência. Nunca sobrescreve versões antigas."""
    id: str = Field(default_factory=lambda: f"TRM-{str(uuid.uuid4().int)[:4].zfill(4)}")
    version_number: int
    text: str
    is_active: bool = True
    label: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None
    created_by_name: Optional[str] = None


async def _get_current_term_version() -> Optional[Dict]:
    """Retorna a versão ativa do Termo de Ciência.
    Na primeira chamada (sem versões), migra general_conditions do budget_config como v1."""
    tv = await db.term_versions.find_one({"is_active": True}, sort=[("version_number", -1)])
    if tv:
        tv.pop("_id", None)
        return tv
    # Migração automática: usa general_conditions de budget_config como v1
    budget_cfg = await db.budget_config.find_one({}) or {}
    gc = budget_cfg.get("general_conditions", "")
    if gc:
        v1 = TermVersion(version_number=1, text=gc, is_active=True, label="v1 — migrado")
        await db.term_versions.insert_one(v1.dict())
        d = v1.dict()
        d.pop("_id", None)
        return d
    return None


@api_router.get("/term-versions")
async def list_term_versions(current_user: UserPublic = Depends(get_current_user)):
    """Lista todas as versões do Termo de Ciência (mais recente primeiro)."""
    versions = await db.term_versions.find({}).sort("version_number", -1).to_list(200)
    for v in versions:
        v.pop("_id", None)
    return {"versions": versions}


@api_router.get("/term-versions/current")
async def get_current_term_version_endpoint(current_user: UserPublic = Depends(get_current_user)):
    """Retorna a versão ativa atual do Termo de Ciência."""
    v = await _get_current_term_version()
    if not v:
        raise HTTPException(status_code=404, detail="Nenhum termo cadastrado")
    return v


@api_router.post("/term-versions")
async def create_term_version(body: Dict[str, Any], current_user: UserPublic = Depends(get_current_user)):
    """Cria nova versão do Termo (não apaga as antigas). Apenas ADMIN."""
    if current_user.role not in ("ADMIN",):
        raise HTTPException(status_code=403, detail="Apenas administradores podem criar versões do termo")
    text = (body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="Texto do termo é obrigatório")
    label = (body.get("label") or "").strip() or None

    latest = await db.term_versions.find_one({}, sort=[("version_number", -1)])
    next_num = (latest["version_number"] + 1) if latest else 1

    # Desativa todas as anteriores
    await db.term_versions.update_many({}, {"$set": {"is_active": False}})

    new_version = TermVersion(
        version_number=next_num,
        text=text,
        is_active=True,
        created_by=current_user.id,
        created_by_name=current_user.name,
        label=label or f"v{next_num}",
    )
    await db.term_versions.insert_one(new_version.dict())

    await log_audit(
        db=db, action="TERM_VERSION_CREATED", entity_type="term_version",
        entity_id=new_version.id, user_id=current_user.id, user_name=current_user.name,
        details={"version_number": next_num, "label": new_version.label}
    )

    d = new_version.dict()
    d.pop("_id", None)
    return d


class ServiceAcceptance(BaseModel):
    id: str = Field(default_factory=lambda: f"ACE-{str(uuid.uuid4().int)[:7].zfill(7)}")
    token: str = Field(default_factory=lambda: uuid.uuid4().hex + uuid.uuid4().hex)
    short_id: str = Field(default_factory=_make_short_id)
    budget_id: str
    client_id: Optional[str] = None
    client_name_on_budget: Optional[str] = None
    client_phone: Optional[str] = None
    status: str = "PENDING"  # PENDING | ACCEPTED
    accepted_at: Optional[datetime] = None
    accepted_ip: Optional[str] = None
    accepted_user_agent: Optional[str] = None
    accepted_name: Optional[str] = None
    accepted_checkboxes: Dict[str, bool] = {}
    gallery_token: Optional[str] = None
    # Versionamento do termo — snapshot imutável no momento da criação do aceite
    term_version_id: Optional[str] = None
    term_text_snapshot: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


@api_router.post("/budgets/{budget_id}/acceptance/generate")
async def generate_acceptance_link(
    budget_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """Gera (ou retorna existente) o token de aceite para um orçamento."""
    budget = await db.budgets.find_one({"id": budget_id})
    if not budget:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    existing = await db.service_acceptances.find_one({"budget_id": budget_id})
    if existing:
        public_url = (
            os.environ.get("PUBLIC_WEBHOOK_URL", "")
            .replace("/api/webhooks/payment", "")
            .strip("/")
        )
        return {
            "acceptance_id": existing["id"],
            "token": existing["token"],
            "status": existing.get("status", "PENDING"),
            "link": f"{public_url}/aceite/{existing['token']}",
        }

    # Amarra o aceite à versão atual do termo (snapshot imutável)
    current_term = await _get_current_term_version()
    acceptance = ServiceAcceptance(
        budget_id=budget_id,
        client_id=budget.get("client_id"),
        client_name_on_budget=budget.get("client_name"),
        client_phone=budget.get("client_phone"),
        term_version_id=current_term["id"] if current_term else None,
        term_text_snapshot=current_term["text"] if current_term else None,
    )
    await db.service_acceptances.insert_one(acceptance.dict())

    public_url = (
        os.environ.get("PUBLIC_WEBHOOK_URL", "")
        .replace("/api/webhooks/payment", "")
        .strip("/")
    )
    return {
        "acceptance_id": acceptance.id,
        "token": acceptance.token,
        "status": "PENDING",
        "link": f"{public_url}/aceite/{acceptance.token}",
    }


@api_router.post("/budgets/{budget_id}/acceptance/admin-confirm")
async def admin_confirm_acceptance(
    budget_id: str,
    body: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user),
):
    """Admin confirma aceite manualmente, sem necessidade de assinatura do cliente."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Apenas administradores podem confirmar aceite manualmente")

    doc = await db.service_acceptances.find_one({"budget_id": budget_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Aceite não encontrado para este orçamento")

    if doc.get("status") == "ACCEPTED":
        return {"success": True, "already_accepted": True}

    name = (body.get("name") or f"Admin — {current_user.name}").strip()
    now = datetime.utcnow()

    await db.service_acceptances.update_one(
        {"budget_id": budget_id},
        {"$set": {
            "status": "ACCEPTED",
            "accepted_at": now,
            "accepted_name": name,
            "accepted_ip": "admin-manual",
            "accepted_user_agent": "admin-override",
            "accepted_checkboxes": {"admin_override": True},
            "acceptance_status": "ACCEPTED",
            "acceptance_confirmed_at": now,
        }}
    )

    await log_audit(
        db=db,
        action="ADMIN_CONFIRMED",
        entity_type="service_acceptance",
        entity_id=doc["id"],
        user_id=current_user.id,
        user_name=current_user.name,
        details={"budget_id": budget_id, "admin_name": name, "override": True}
    )

    await db.budgets.update_one(
        {"id": budget_id},
        {"$set": {"acceptance_status": "ACCEPTED", "acceptance_confirmed_at": now, "accepted_name": name}}
    )

    return {"success": True, "accepted_at": now.isoformat(), "admin_override": True}


@api_router.get("/budgets/{budget_id}/acceptance/status")
async def get_acceptance_status(
    budget_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """Retorna o status do aceite de um orçamento."""
    doc = await db.service_acceptances.find_one({"budget_id": budget_id})
    if not doc:
        return {"has_acceptance": False}
    public_url = (
        os.environ.get("PUBLIC_WEBHOOK_URL", "")
        .replace("/api/webhooks/payment", "")
        .strip("/")
    )
    return {
        "has_acceptance": True,
        "status": doc.get("status", "PENDING"),
        "accepted_at": doc.get("accepted_at"),
        "accepted_name": doc.get("accepted_name"),
        "accepted_ip": doc.get("accepted_ip"),
        "link": f"{public_url}/aceite/{doc['token']}",
    }


@api_router.get("/acceptances")
async def list_acceptances(
    current_user: UserPublic = Depends(get_current_user),
):
    """Lista todos os aceites com info do orçamento — para painel de gestão."""
    public_url = (
        os.environ.get("PUBLIC_WEBHOOK_URL", "")
        .replace("/api/webhooks/payment", "")
        .strip("/")
    )
    docs = await db.service_acceptances.find({}).sort("created_at", -1).to_list(500)
    result = []
    for doc in docs:
        budget = await db.budgets.find_one({"id": doc.get("budget_id")}, {"client_name": 1, "total_value": 1, "budget_status": 1})
        gallery_token = doc.get("gallery_token")
        result.append({
            "id": doc.get("id"),
            "budget_id": doc.get("budget_id"),
            "client_name": budget.get("client_name", "—") if budget else "—",
            "total_value": budget.get("total_value", 0) if budget else 0,
            "status": doc.get("status", "PENDING"),
            "accepted_at": doc.get("accepted_at"),
            "accepted_name": doc.get("accepted_name"),
            "accepted_ip": doc.get("accepted_ip"),
            "created_at": doc.get("created_at"),
            "link": f"{public_url}/aceite/{doc['token']}",
            "gallery_link": f"{public_url}/galeria/{gallery_token}" if gallery_token else None,
        })
    return {"acceptances": result, "total": len(result)}


@api_router.get("/s/{short_id}")
async def short_link_redirect(short_id: str):
    """URL curta para o termo de aceite — serve OG tags para preview no WhatsApp."""
    from fastapi.responses import HTMLResponse
    doc = await db.service_acceptances.find_one({"short_id": short_id})
    if not doc:
        return HTMLResponse("<html><body>Link inválido.</body></html>", status_code=404)

    token = doc.get("token", "")
    budget_id = doc.get("budget_id", "")
    client_name = doc.get("client_name_on_budget", "Cliente")

    budget = await db.budgets.find_one({"id": budget_id}) if budget_id else None
    total = f"R$ {float(budget.get('total_value', 0)):.2f}" if budget else ""

    sys_cfg = await db.system_config.find_one({}) or {}
    company_name = sys_cfg.get("company_name", "SuperDry Lavanderia")

    public_url = (
        os.environ.get("PUBLIC_WEBHOOK_URL", "")
        .replace("/api/webhooks/payment", "")
        .strip("/")
    )

    logo_url = f"{public_url}/api/system-config/logo/file" if public_url else ""
    acceptance_url = f"/aceite/{token}"
    title = f"Orçamento {budget_id} — {company_name}"
    description = f"Olá {client_name}! Seu orçamento {total} está pronto. Clique para visualizar e assinar o termo de serviço."

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <meta property="og:type" content="website" />
  <meta property="og:title" content="{title}" />
  <meta property="og:description" content="{description}" />
  <meta property="og:image" content="{logo_url}" />
  <meta property="og:image:width" content="500" />
  <meta property="og:image:height" content="500" />
  <meta property="og:url" content="{public_url}/api/s/{short_id}" />
  <meta name="twitter:card" content="summary" />
  <meta http-equiv="refresh" content="0;url={acceptance_url}" />
</head>
<body>
  <script>window.location.replace('{acceptance_url}');</script>
  <p>Redirecionando... <a href="{acceptance_url}">Clique aqui</a></p>
</body>
</html>"""
    return HTMLResponse(html)


@api_router.get("/acceptance/{token}")
async def get_acceptance_public(token: str, request: HttpRequest):
    """Público — retorna dados do orçamento + textos de risco para a página de aceite."""
    doc = await db.service_acceptances.find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado")

    budget = await db.budgets.find_one({"id": doc["budget_id"]})
    if not budget:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    budget_cfg = await db.budget_config.find_one({}) or {}

    # Coleta categorias dos itens do orçamento — itens ficam embutidos no budget
    items = budget.get("items") or []
    # Fallback: tenta na coleção separada se embedded vier vazio
    if not items:
        items = await db.budget_items.find({"budget_id": doc["budget_id"]}).to_list(None)
    categories_present = set()
    for item in items:
        cat = item.get("service_category", "")
        if cat:
            categories_present.add(cat)

    # Mapeia categoria → chave no BudgetConfig → label legível
    CAT_MAP = {
        "ESTOFADOS":                  ("risks_estofados",            "Estofados"),
        "COLCHOES":                   ("risks_colchoes",             "Colchões"),
        "BOX":                        ("risks_box",                  "Box"),
        "TAPETES":                    ("risks_tapetes",              "Tapetes"),
        "CARPETES_E_TAPETES_NO_LOCAL":("risks_carpetes_tapetes_local","Carpetes e Tapetes (local)"),
        "CORTINAS":                   ("risks_cortinas",             "Cortinas"),
        "PERSIANAS":                  ("risks_persianas",            "Persianas"),
        "ITENS_INFANTIS":             ("risks_itens_infantis",       "Itens Infantis"),
        "VEICULOS":                   ("risks_veiculos",             "Veículos"),
        "IMPERMEABILIZACAO":          ("risks_impermeabilizacao",    "Impermeabilização"),
        "OUTROS_ITENS":               ("risks_outros_itens",         "Outros"),
    }

    risk_sections = []
    for cat in sorted(categories_present):
        if cat in CAT_MAP:
            key, label = CAT_MAP[cat]
            text = budget_cfg.get(key, "")
            if text:
                risk_sections.append({"category": cat, "label": label, "text": text})

    # Usa o snapshot do termo amarrado ao aceite (garante auditoria imutável).
    # Fallback: versão ativa atual → budget_config (para aceites antigos sem snapshot).
    if doc.get("term_text_snapshot"):
        general_conditions = doc["term_text_snapshot"]
    else:
        _current_tv = await _get_current_term_version()
        general_conditions = _current_tv["text"] if _current_tv else budget_cfg.get("general_conditions", "")

    footer_text = budget_cfg.get("footer_text", "")

    sys_cfg = await db.system_config.find_one({}) or {}
    company_name = sys_cfg.get("company_name", "SuperDry Lavanderia")
    company_phone = sys_cfg.get("phone", "")

    return {
        "acceptance_id": doc["id"],
        "status": doc.get("status", "PENDING"),
        "accepted_at": doc.get("accepted_at"),
        "accepted_name": doc.get("accepted_name"),
        "term_version_id": doc.get("term_version_id"),
        "budget": {
            "id": budget.get("id"),
            "client_name": budget.get("client_name"),
            "total_value": budget.get("total_value", 0),
            "item_count": len(items),
        },
        "risk_sections": risk_sections,
        "general_conditions": general_conditions,
        "footer_text": footer_text,
        "company_name": company_name,
        "company_phone": company_phone,
    }


@api_router.post("/acceptance/{token}/confirm")
async def confirm_acceptance(token: str, body: Dict[str, Any], request: HttpRequest):
    """Público — cliente confirma aceite dos termos."""
    doc = await db.service_acceptances.find_one({"token": token})
    if not doc:
        raise HTTPException(status_code=404, detail="Link inválido ou expirado")
    if doc.get("status") == "ACCEPTED":
        return {"success": True, "already_accepted": True}

    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "unknown")
    user_agent = request.headers.get("User-Agent", "unknown")
    accepted_name = (body.get("name") or "").strip()
    checkboxes = body.get("checkboxes", {})
    alternative_address = (body.get("alternative_address") or "").strip() or None
    address_note = (body.get("address_note") or "").strip() or None

    if not accepted_name:
        raise HTTPException(status_code=400, detail="Nome é obrigatório para confirmar o aceite")

    now = datetime.utcnow()
    update_fields = {
        "status": "ACCEPTED",
        "accepted_at": now,
        "accepted_ip": client_ip,
        "accepted_user_agent": user_agent,
        "accepted_name": accepted_name,
        "accepted_checkboxes": checkboxes,
        "updated_at": now,
    }
    # Retrocompatibilidade: aceites criados antes do versionamento não têm snapshot.
    # Salva o snapshot no momento da confirmação para garantir rastreabilidade.
    if not doc.get("term_text_snapshot"):
        _confirm_term = await _get_current_term_version()
        if _confirm_term:
            update_fields["term_text_snapshot"] = _confirm_term["text"]
            update_fields["term_version_id"] = _confirm_term["id"]
    if alternative_address:
        update_fields["alternative_address"] = alternative_address
    if address_note:
        update_fields["address_note"] = address_note

    await db.service_acceptances.update_one(
        {"token": token},
        {"$set": update_fields}
    )

    # Grava no budget também — e promove status para APROVADO automaticamente
    await db.budgets.update_one(
        {"id": doc["budget_id"]},
        {"$set": {
            "acceptance_status": "ACCEPTED",
            "acceptance_confirmed_at": now,
            "accepted_name": accepted_name,
            "budget_status": "APROVADO",
            "budget_status_updated_at": now,
            "budget_status_updated_by": f"aceite-cliente:{accepted_name}",
        }}
    )

    await db.audit_logs.insert_one(AuditLog(
        entity_type="service_acceptance",
        entity_id=doc["id"],
        action="ACCEPTED",
        user_id="CLIENT",
        user_name=accepted_name,
        details={"ip": client_ip, "user_agent": user_agent[:200], "budget_id": doc["budget_id"]},
    ).dict())

    return {"success": True, "accepted_at": now.isoformat()}


# ============================================================
# GALERIA DE FOTOS (notificação de conclusão)
# ============================================================

@api_router.post("/budgets/{budget_id}/notify-completion")
async def notify_completion(
    budget_id: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """Gera token de galeria e retorna texto WhatsApp de conclusão."""
    budget = await db.budgets.find_one({"id": budget_id})
    if not budget:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    # Cria ou reutiliza gallery_token na acceptance (ou no budget diretamente)
    gallery_token = None
    acceptance = await db.service_acceptances.find_one({"budget_id": budget_id})
    if acceptance and acceptance.get("gallery_token"):
        gallery_token = acceptance["gallery_token"]
    else:
        gallery_token = uuid.uuid4().hex + uuid.uuid4().hex
        if acceptance:
            await db.service_acceptances.update_one(
                {"budget_id": budget_id},
                {"$set": {"gallery_token": gallery_token, "updated_at": datetime.utcnow()}}
            )
        else:
            # Salva direto no budget
            await db.budgets.update_one(
                {"id": budget_id},
                {"$set": {"gallery_token": gallery_token}}
            )

    public_url = (
        os.environ.get("PUBLIC_WEBHOOK_URL", "")
        .replace("/api/webhooks/payment", "")
        .strip("/")
    )
    gallery_link = f"{public_url}/galeria/{gallery_token}"

    sys_cfg = await db.system_config.find_one({}) or {}
    company_name = sys_cfg.get("company_name", "SuperDry Lavanderia")

    client_name = budget.get("client_name", "")
    total = budget.get("total_value", 0)

    msg = (
        f"Olá *{client_name}*! 👋\n\n"
        f"Seu serviço foi *concluído* com sucesso pela *{company_name}*! ✅\n\n"
        f"Veja as fotos do antes e depois dos seus itens pelo link abaixo:\n"
        f"🔗 {gallery_link}\n\n"
        f"Valor total: *R$ {total:.2f}*\n\n"
        f"Obrigado pela confiança! 🙏"
    )

    phone = budget.get("client_phone", "")
    whatsapp_url = None
    if phone:
        digits = re.sub(r'\D', '', phone)
        if not digits.startswith('55'):
            digits = '55' + digits
        whatsapp_url = f"https://wa.me/{digits}?text={requests.utils.quote(msg)}"

    return {
        "gallery_token": gallery_token,
        "gallery_link": gallery_link,
        "message": msg,
        "whatsapp_url": whatsapp_url,
    }


@api_router.get("/gallery/{gallery_token}")
async def get_gallery_public(gallery_token: str):
    """Público — retorna fotos antes/depois de todos os itens do orçamento."""
    # Busca token na acceptance ou direto no budget
    acceptance = await db.service_acceptances.find_one({"gallery_token": gallery_token})
    if acceptance:
        budget_id = acceptance["budget_id"]
    else:
        budget = await db.budgets.find_one({"gallery_token": gallery_token})
        if not budget:
            raise HTTPException(status_code=404, detail="Link inválido ou expirado")
        budget_id = budget["id"]

    budget = await db.budgets.find_one({"id": budget_id})
    if not budget:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado")

    items = await db.budget_items.find({"budget_id": budget_id}).to_list(None)

    public_url = (
        os.environ.get("PUBLIC_WEBHOOK_URL", "")
        .replace("/api/webhooks/payment", "")
        .strip("/")
    )

    result_items = []
    for item in items:
        item_id = item.get("id")
        photos = await db.technician_photos.find({"item_id": item_id}).to_list(None)
        before = [p for p in photos if p.get("photo_type") == "BEFORE"]
        after  = [p for p in photos if p.get("photo_type") == "AFTER"]
        damage = [p for p in photos if p.get("photo_type") == "DAMAGE"]

        def photo_url(p):
            return f"{public_url}/api/technician/photos/file/{p['filename']}"

        result_items.append({
            "item_id": item_id,
            "service_name": item.get("service_name", ""),
            "status": item.get("status", ""),
            "before": [{"url": photo_url(p), "uploaded_at": p.get("uploaded_at")} for p in before],
            "after":  [{"url": photo_url(p), "uploaded_at": p.get("uploaded_at")} for p in after],
            "damage": [{"url": photo_url(p), "uploaded_at": p.get("uploaded_at")} for p in damage],
        })

    sys_cfg = await db.system_config.find_one({}) or {}

    return {
        "budget_id": budget_id,
        "client_name": budget.get("client_name", ""),
        "company_name": sys_cfg.get("company_name", "SuperDry Lavanderia"),
        "items": result_items,
    }


# ============================================================
# AUTH endpoints (Phase 1)
# ============================================================
@api_router.post("/auth/login", response_model=LoginResponse)
async def auth_login(payload: LoginRequest):
    """Login com email + senha. Retorna JWT."""
    email = (payload.email or "").strip().lower()
    user_doc = await db.users.find_one({"email": email})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")
    if not user_doc.get("is_active", True):
        raise HTTPException(status_code=403, detail="Usuário inativo")
    if not verify_password(payload.password, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Email ou senha incorretos")

    token = create_access_token(user_doc["id"], user_doc.get("role", "ATENDENTE"))
    pub = UserPublic(**{k: v for k, v in user_doc.items() if k != "password_hash"})
    try:
        await db.audit_logs.insert_one(AuditLog(
            entity_type="user", entity_id=user_doc["id"], action="LOGIN",
            user_id=user_doc["id"], user_name=user_doc.get("name"),
        ).dict())
    except Exception:
        pass
    return LoginResponse(access_token=token, user=pub)


@api_router.get("/auth/me", response_model=UserPublic)
async def auth_me(current_user: UserPublic = Depends(get_current_user)):
    return current_user


@api_router.post("/auth/change-password")
async def auth_change_password(
    body: Dict[str, str],
    current_user: UserPublic = Depends(get_current_user),
):
    old = body.get("old_password", "")
    new = body.get("new_password", "")
    if not new or len(new) < 4:
        raise HTTPException(status_code=400, detail="Nova senha muito curta (mínimo 4 caracteres)")
    user_doc = await db.users.find_one({"id": current_user.id})
    if not user_doc or not verify_password(old, user_doc.get("password_hash", "")):
        raise HTTPException(status_code=401, detail="Senha atual incorreta")
    await db.users.update_one(
        {"id": current_user.id},
        {"$set": {"password_hash": hash_password(new), "updated_at": datetime.utcnow()}},
    )
    await log_audit("user", current_user.id, "PASSWORD_CHANGE", current_user)
    return {"success": True}


# ============================================================
# USERS endpoints (admin)
# ============================================================
@api_router.get("/users/salespersons")
async def list_salespersons(current_user: UserPublic = Depends(get_current_user)):
    """Lista de vendedores ativos: retorna display_name (ou name) de todos os usuários ativos."""
    cursor = db.users.find({"is_active": {"$ne": False}}).sort("name", 1)
    docs = await cursor.to_list(length=1000)
    return [
        {
            "id": d.get("id"),
            "name": d.get("name"),
            "display_name": d.get("display_name") or d.get("name"),
        }
        for d in docs
    ]


@api_router.get("/users", response_model=List[UserPublic])
async def list_users(current_user: UserPublic = Depends(require_admin)):
    cursor = db.users.find({}).sort("name", 1)
    docs = await cursor.to_list(length=10000)
    return [UserPublic(**{k: v for k, v in d.items() if k != "password_hash"}) for d in docs]


@api_router.post("/users", response_model=UserPublic)
async def create_user(
    payload: UserCreate,
    current_user: UserPublic = Depends(require_admin),
):
    email = payload.email.strip().lower()
    if await db.users.find_one({"email": email}):
        raise HTTPException(status_code=400, detail="Email já cadastrado")
    user = User(
        name=payload.name.strip(),
        email=email,
        role=payload.role,
        is_active=payload.is_active,
        password_hash=hash_password(payload.password),
    )
    user_dict = user.dict()
    if payload.allowed_modules is not None:
        user_dict["allowed_modules"] = payload.allowed_modules
    if payload.display_name:
        user_dict["display_name"] = payload.display_name.strip()
    if payload.commission_pct is not None:
        user_dict["commission_pct"] = payload.commission_pct
    await db.users.insert_one(user_dict)
    await log_audit("user", user.id, "CREATE", current_user, {"after": {**user_dict, "password_hash": "***"}})
    return UserPublic(**{k: v for k, v in user_dict.items() if k != "password_hash"})


@api_router.put("/users/{user_id}", response_model=UserPublic)
async def update_user(
    user_id: str,
    payload: UserUpdate,
    current_user: UserPublic = Depends(require_admin),
):
    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    update_data: Dict[str, Any] = {}
    if payload.name is not None: update_data["name"] = payload.name.strip()
    if payload.display_name is not None: update_data["display_name"] = payload.display_name.strip()
    if payload.commission_pct is not None: update_data["commission_pct"] = payload.commission_pct
    if payload.email is not None: update_data["email"] = payload.email.strip().lower()
    if payload.role is not None: update_data["role"] = payload.role.value if hasattr(payload.role, "value") else payload.role
    if payload.is_active is not None: update_data["is_active"] = payload.is_active
    if payload.allowed_modules is not None: update_data["allowed_modules"] = payload.allowed_modules
    if payload.password:
        update_data["password_hash"] = hash_password(payload.password)
    update_data["updated_at"] = datetime.utcnow()

    await db.users.update_one({"id": user_id}, {"$set": update_data})
    await log_audit("user", user_id, "UPDATE", current_user, {"diff": {k: update_data.get(k) for k in update_data if k != "password_hash"}})
    new_doc = await db.users.find_one({"id": user_id})
    return UserPublic(**{k: v for k, v in new_doc.items() if k != "password_hash"})


@api_router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: UserPublic = Depends(require_admin),
):
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Você não pode excluir sua própria conta")
    existing = await db.users.find_one({"id": user_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    # Garante que ainda restará 1 admin
    if existing.get("role") == UserRole.ADMIN.value:
        admins = await db.users.count_documents({"role": UserRole.ADMIN.value})
        if admins <= 1:
            raise HTTPException(status_code=400, detail="É necessário pelo menos 1 administrador no sistema")
    await db.users.delete_one({"id": user_id})
    await log_audit("user", user_id, "DELETE", current_user, {"before": {**existing, "password_hash": "***"}})
    return {"success": True}


# ── Comissões ────────────────────────────────────────────────────────────────
#
# REGRA DE CÁLCULO (definitiva):
#   comissão_valor = item.paid_value × (item.commission_pct / 100)
#
# - item.paid_value = valor EFETIVAMENTE RECEBIDO para aquele item
#   (já considera pagamentos parciais e descontos)
# - commission_pct = % acordada no orçamento para aquele item
# - O cálculo é sempre sobre o recebido real, nunca sobre o valor orçado
#
@api_router.get("/commissions/summary")
async def commissions_summary(
    user_id: Optional[str] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Resumo de comissões por usuário.
    Filtra por user_id, ano e/ou mês (baseado em updated_at do item).
    Retorna: comissão devida (sobre pago) e comissão potencial (sobre total do orçamento).
    """
    pipeline = [
        {"$unwind": "$items"},
        {"$match": {
            "items.commission_enabled": True,
            "items.commission_user_id": {"$ne": None},
            "items.commission_pct": {"$gt": 0},
        }},
    ]

    if user_id:
        pipeline.append({"$match": {"items.commission_user_id": user_id}})

    # Filtro de período (usa updated_at do item)
    if year:
        date_filter: dict = {}
        start = f"{year}-01-01"
        end   = f"{year}-12-31"
        if month:
            import calendar
            last_day = calendar.monthrange(year, month)[1]
            start = f"{year}-{month:02d}-01"
            end   = f"{year}-{month:02d}-{last_day}"
        pipeline.append({"$match": {
            "items.updated_at": {"$gte": datetime.fromisoformat(start),
                                  "$lte": datetime.fromisoformat(end + "T23:59:59")}
        }})

    pipeline += [
        {"$project": {
            "_id": 0,
            "budget_id":            "$id",
            "client_name":          "$client_name",
            "item_id":              "$items.id",
            "service_name":         "$items.service_name",
            "commission_user_id":   "$items.commission_user_id",
            "commission_user_name": "$items.commission_user_name",
            "commission_pct":       "$items.commission_pct",
            "total_value":          "$items.total_value",
            "paid_value":           "$items.paid_value",
            "payment_status":       "$items.payment_status",
            # comissão devida = sobre o PAGO (regra definitiva)
            "commission_earned": {
                "$multiply": [
                    {"$ifNull": ["$items.paid_value", 0]},
                    {"$divide": [{"$ifNull": ["$items.commission_pct", 0]}, 100]}
                ]
            },
            # comissão potencial = sobre o ORÇADO (referência)
            "commission_potential": {
                "$multiply": [
                    {"$ifNull": ["$items.total_value", 0]},
                    {"$divide": [{"$ifNull": ["$items.commission_pct", 0]}, 100]}
                ]
            },
        }},
        {"$group": {
            "_id": {"user_id": "$commission_user_id", "user_name": "$commission_user_name"},
            "total_earned":    {"$sum": "$commission_earned"},
            "total_potential": {"$sum": "$commission_potential"},
            "items_count":     {"$sum": 1},
            "details":         {"$push": {
                "budget_id":      "$budget_id",
                "client_name":    "$client_name",
                "item_id":        "$item_id",
                "service_name":   "$service_name",
                "commission_pct": "$commission_pct",
                "total_value":    "$total_value",
                "paid_value":     "$paid_value",
                "payment_status": "$payment_status",
                "commission_earned":    "$commission_earned",
                "commission_potential": "$commission_potential",
            }}
        }},
        {"$sort": {"_id.user_name": 1}},
    ]

    results = []
    async for doc in db.budgets.aggregate(pipeline):
        results.append({
            "user_id":          doc["_id"]["user_id"],
            "user_name":        doc["_id"]["user_name"],
            "total_earned":     round(doc["total_earned"], 2),
            "total_potential":  round(doc["total_potential"], 2),
            "items_count":      doc["items_count"],
            "details":          doc["details"],
        })

    return {
        "summary": results,
        "grand_total_earned":    round(sum(r["total_earned"] for r in results), 2),
        "grand_total_potential": round(sum(r["total_potential"] for r in results), 2),
        "calculation_rule": "commission = item.paid_value × (commission_pct / 100)",
    }


@api_router.get("/audit-logs")
async def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    limit: int = 200,
    current_user: UserPublic = Depends(require_admin),
):
    from bson import ObjectId
    
    def clean_doc(doc):
        """Remove MongoDB ObjectId fields recursively"""
        if isinstance(doc, dict):
            return {k: clean_doc(v) for k, v in doc.items() if k != "_id" and not isinstance(v, ObjectId)}
        elif isinstance(doc, list):
            return [clean_doc(item) for item in doc]
        elif isinstance(doc, ObjectId):
            return str(doc)
        else:
            return doc
    
    q: Dict[str, Any] = {}
    if entity_type: q["entity_type"] = entity_type
    if entity_id: q["entity_id"] = entity_id
    cursor = db.audit_logs.find(q).sort("created_at", -1).limit(limit)
    docs = await cursor.to_list(length=limit)
    cleaned_docs = [clean_doc(d) for d in docs]
    return {"logs": cleaned_docs, "count": len(cleaned_docs)}



# ============================================================
# DASHBOARD detalhado (Phase 1)
# ============================================================
@api_router.get("/dashboard/summary")
async def get_dashboard_summary(current_user: UserPublic = Depends(get_current_user)):
    """Resumo expandido para Painel Inicial."""
    try:
        from datetime import date as _date
        today = _date.today().isoformat()

        # 1) Itens pendentes de rota: status route-eligible + sem rota corrente
        #    Só orçamentos APROVADOS (exclui RASCUNHO/ARQUIVADO/CANCELADO)
        route_statuses = [
            ServiceStatus.RETIRAR.value,
            ServiceStatus.EXECUTAR_NO_LOCAL.value,
            ServiceStatus.ENTREGAR.value,
        ]
        approved_filter = {"budget_status": "APROVADO"}
        items_pending_routes = 0
        async for b in db.budgets.find({**approved_filter, "items.status": {"$in": route_statuses}}):
            for it in (b.get("items") or []):
                if (it.get("status") in route_statuses
                        and not it.get("current_route_id")
                        and it.get("execution_mode") not in ("CLIENTE_TROUXE", "CLIENTE_LEVARA")):
                    items_pending_routes += 1

        # 2) Orçamentos ativos (APROVADOS com algum item pendente de rota)
        active_budgets = 0
        async for b in db.budgets.find({**approved_filter}):
            items = b.get("items") or []
            has_pending = any(
                (it.get("status") in route_statuses and not it.get("current_route_id"))
                for it in items
            )
            if has_pending:
                active_budgets += 1

        # 3) Execução de hoje — só conta event_ids que ainda existem como itens válidos
        execution_today = 0
        # Coleta todos os ITM-* válidos para cross-check
        valid_item_ids: set = set()
        async for b in db.budgets.find({}, {"items.id": 1}):
            for it in (b.get("items") or []):
                if it.get("id"):
                    valid_item_ids.add(it["id"])

        async for a in db.technician_assignments.find({"assigned_date": today, "status": {"$ne": "CANCELLED"}}):
            valid_events = [e for e in (a.get("event_ids") or []) if e in valid_item_ids]
            execution_today += len(valid_events)

        # 4) Em lavagem/execução
        wash_statuses = [
            ServiceStatus.EM_LAVAGEM.value,
            ServiceStatus.EM_LAVAGEM_PARCEIRO.value,
            ServiceStatus.COLETADO.value,
            ServiceStatus.AGUARDANDO_ENTREGA.value,
            ServiceStatus.AGUARDANDO_BUSCAR.value,
            ServiceStatus.EXECUCAO_PARCIAL.value,
        ]
        items_in_washing = 0
        async for b in db.budgets.find({"items.status": {"$in": wash_statuses}}):
            for it in (b.get("items") or []):
                if it.get("status") in wash_statuses:
                    items_in_washing += 1

        # 5) Pendências financeiras — itens já entregues/executados com pagamento em aberto.
        #    Usa os mesmos status que o módulo Financeiro exibe (ENTREGUE, EXECUTADO, BUSCOU).
        #    Só conta se payment_status está EXPLICITAMENTE em PENDENTE/PARCIAL/INADIMPLENTE
        #    (sem default "PENDENTE" para não inflar com itens que nunca foram entregues).
        delivered_statuses = {"ENTREGUE", "EXECUTADO", "BUSCOU"}
        pending_pay_set = {"PENDENTE", "PARCIAL", "INADIMPLENTE"}
        financial_pending = 0
        async for b in db.budgets.find({"items.status": {"$in": list(delivered_statuses)}}):
            for it in (b.get("items") or []):
                if (it.get("status") in delivered_statuses
                        and it.get("payment_status") in pending_pay_set):
                    financial_pending += 1

        # 6) Resumo do gerenciador financeiro (placeholder - implementado em fase futura)
        finance_summary = {
            "cash_balance": 0.0,
            "bank_balance": 0.0,
            "month_revenue": 0.0,
            "available": False,
        }

        # 7) Chamados e manutenção
        tickets_open = await db.tickets.count_documents({"status": {"$nin": ["FECHADO", "RESOLVIDO"]}}) if "tickets" in await db.list_collection_names() else 0

        # Compat: campos antigos
        total_clients = await db.clients.count_documents({})

        return {
            "items_pending_routes": items_pending_routes,
            "active_budgets": active_budgets,
            "execution_today": execution_today,
            "items_in_washing": items_in_washing,
            "financial_pending": financial_pending,
            "finance_summary": finance_summary,
            "tickets_open": tickets_open,
            "total_clients": total_clients,
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro no dashboard: {str(e)}")


@api_router.get("/service-status/options-legacy")
async def _legacy_service_status_options_marker():
    """Mantido como referência. Use /service-status/options."""
    return [{"value": s.value, "label": s.value} for s in ServiceStatus]


# ============================================================
# ITEM endpoints (pilar do sistema)
# ============================================================
async def _find_budget_and_item(item_id: str):
    """Encontra o orçamento que contém o item_id; retorna (budget, item)."""
    budget = await db.budgets.find_one({"items.id": item_id})
    if not budget:
        return None, None
    item = next((it for it in (budget.get("items") or []) if it.get("id") == item_id), None)
    return budget, item


async def _maybe_auto_archive_budget(budget_id: str, triggered_by: str = "auto"):
    """
    Arquiva automaticamente um orçamento quando todos os seus itens estão
    em status terminal (ENTREGUE/EXECUTADO/BUSCOU) E todos estão pagos
    (PAGO ou CORTESIA). Silencioso — não levanta exceção em caso de falha.
    """
    try:
        budget = await db.budgets.find_one({"id": budget_id})
        if not budget:
            return
        # Não rearquiva o que já está arquivado/cancelado
        if budget.get("budget_status") in ("ARQUIVADO", "CANCELADO"):
            return

        TERMINAL_STATUSES = {"ENTREGUE", "EXECUTADO", "BUSCOU", "CANCELADO_PELO_CLIENTE"}
        PAID_STATUSES     = {"PAGO", "CORTESIA"}

        items = [it for it in (budget.get("items") or []) if not it.get("client_desisted")]
        if not items:
            return  # orçamento vazio, não arquivar automaticamente

        all_terminal = all(it.get("status") in TERMINAL_STATUSES for it in items)
        all_paid     = all(it.get("payment_status") in PAID_STATUSES for it in items)

        if all_terminal and all_paid:
            await db.budgets.update_one(
                {"id": budget_id},
                {"$set": {
                    "budget_status": "ARQUIVADO",
                    "budget_status_updated_at": datetime.utcnow(),
                    "budget_status_updated_by": triggered_by,
                }}
            )
    except Exception:
        pass  # falha silenciosa — não bloqueia o fluxo de pagamento


async def _update_item_fields(item_id: str, fields: Dict[str, Any], user: UserPublic):
    """Atualiza campos de um item no array embedded, preserva auditoria."""
    fields["updated_at"] = datetime.utcnow()
    fields["updated_by"] = user.id
    set_ops = {f"items.$.{k}": v for k, v in fields.items()}
    res = await db.budgets.update_one(
        {"items.id": item_id},
        {"$set": set_ops},
    )
    return res.modified_count > 0


async def _append_to_item_array(item_id: str, array_field: str, value: Any):
    res = await db.budgets.update_one(
        {"items.id": item_id},
        {"$push": {f"items.$.{array_field}": value}},
    )
    return res.modified_count > 0


# ── Sincronia de cor Agenda↔status (mão única: sistema→Google) ─────────────────
#
# Regra confirmada com o dono: vermelho (tomate) = item finalizado sem pagamento
# completo; ao ficar PAGO, volta pra cor "base" do tipo de serviço (azul cobalto
# = 1 deslocamento; roxo uva = múltiplos deslocamentos — tapetes/cortinas/
# impermeabilização). Só mexe em eventos que o item JÁ tem vinculados
# (`agenda_event_ids`) — nunca cria evento, nunca mexe em evento solto/manual.
# A cor amarela (reservado/não confirmado) continua sendo escolha manual na
# criação do evento — não há sinal confiável no BudgetItem pra inferir isso.
#
FINISHED_ITEM_STATUSES = {
    ServiceStatus.ENTREGUE.value, ServiceStatus.EXECUTADO.value, ServiceStatus.BUSCOU.value,
}
MULTI_STOP_SERVICE_CATEGORIES = {"TAPETES", "CORTINAS", "IMPERMEABILIZACAO"}


def _base_color_id_for_item(item: Dict[str, Any]) -> str:
    """Azul cobalto por padrão (1 deslocamento); roxo uva se a categoria do
    serviço tipicamente envolve múltiplos deslocamentos."""
    category = (item.get("service_category") or "").upper()
    return "3" if category in MULTI_STOP_SERVICE_CATEGORIES else "9"


def _expected_color_id_for_item(item: Dict[str, Any]) -> str:
    """Cor que o(s) evento(s) vinculados a este item deveriam ter agora."""
    is_finished = item.get("status") in FINISHED_ITEM_STATUSES
    payment_status = item.get("payment_status", "PENDENTE")
    if is_finished and payment_status != PaymentStatusItem.PAGO.value:
        return "11"  # vermelho tomate — finalizado, ainda não pago
    return _base_color_id_for_item(item)


async def _sync_linked_events_color(item_id: str):
    """Atualiza a cor dos eventos do Google já vinculados a este item, conforme
    a regra acima. Silencioso em qualquer falha (Calendar não autenticado, item
    sem evento, erro de rede) — nunca deve quebrar o fluxo principal de
    status/pagamento por causa de um problema no Calendar."""
    try:
        _, item = await _find_budget_and_item(item_id)
        if not item:
            return
        event_ids = item.get("agenda_event_ids") or []
        if not event_ids:
            return

        creds_doc = await db.calendar_credentials.find_one({})
        if not creds_doc:
            return
        service = get_calendar_service(creds_doc["credentials"])
        new_color = _expected_color_id_for_item(item)

        for eid in event_ids:
            cal_doc = await db.calendar_events.find_one({"id": eid})
            if not cal_doc or not cal_doc.get("google_event_id"):
                continue
            if cal_doc.get("color_id") == new_color:
                continue  # já está na cor certa, evita chamada desnecessária ao Google
            try:
                service.events().patch(
                    calendarId='primary',
                    eventId=cal_doc["google_event_id"],
                    body={"colorId": new_color},
                ).execute()
                await db.calendar_events.update_one(
                    {"id": eid},
                    {"$set": {"color_id": new_color, "updated_at": datetime.utcnow()}},
                )
            except Exception as e:
                logger.error(f"Erro ao sincronizar cor do evento {eid} (item {item_id}): {e}")
    except Exception as e:
        logger.error(f"Erro geral em _sync_linked_events_color({item_id}): {e}")


@api_router.get("/items/{item_id}")
async def get_item(item_id: str, current_user: UserPublic = Depends(get_current_user)):
    """Buscar um item específico (rico)."""
    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    return {
        "item": {k: v for k, v in item.items() if not k.startswith("_")},
        "budget_id": budget.get("id"),
        "budget_payment_method": budget.get("payment_method"),
        "budget_salesperson": budget.get("salesperson"),
    }


@api_router.patch("/items/{item_id}")
async def patch_item(
    item_id: str,
    payload: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user),
):
    """Atualizar campos arbitrários de um item (com auditoria)."""
    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    # Campos proibidos (administrados via endpoints próprios)
    PROTECTED = {
        "id", "budget_id", "created_at", "created_by",
        "status_history", "execution_sessions", "payment_records",
        "route_history", "agenda_event_ids", "assignment_ids",
    }
    fields = {k: v for k, v in payload.items() if k not in PROTECTED}
    if not fields:
        raise HTTPException(status_code=400, detail="Nenhum campo válido para atualizar.")

    diff = {k: {"before": item.get(k), "after": v} for k, v in fields.items() if item.get(k) != v}

    await _update_item_fields(item_id, fields, current_user)

    # Se status mudou, append em history
    if "status" in fields and fields["status"] != item.get("status"):
        entry = {
            "status": fields["status"],
            "at": datetime.utcnow().isoformat(),
            "by_user_id": current_user.id,
            "by_user_name": current_user.name,
            "notes": payload.get("status_notes") or "Status atualizado",
        }
        await _append_to_item_array(item_id, "status_history", entry)

    await log_audit("item", item_id, "UPDATE", current_user, {"diff": diff})
    _, new_item = await _find_budget_and_item(item_id)
    return {"success": True, "item": new_item}


@api_router.post("/items/{item_id}/status")
async def change_item_status(
    item_id: str,
    payload: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user),
):
    """Mudar status do item (sempre grava em status_history)."""
    new_status = payload.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="Campo 'status' obrigatório.")
    valid = {s.value for s in ServiceStatus}
    if new_status not in valid:
        raise HTTPException(status_code=400, detail=f"Status inválido: {new_status}")

    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    if item.get("status") == new_status:
        return {"success": True, "unchanged": True}

    entry = {
        "status": new_status,
        "at": datetime.utcnow().isoformat(),
        "by_user_id": current_user.id,
        "by_user_name": current_user.name,
        "notes": payload.get("notes") or "",
    }

    # Statuses que indicam que o item saiu do ciclo da rota atual.
    # Ao atingir qualquer um deles, o vínculo com a rota anterior é limpo
    # automaticamente para que o item possa entrar em uma nova rota no futuro.
    CLEAR_ROUTE_ON = {
        ServiceStatus.COLETADO.value,           # retirado pelo técnico → vai para lavagem
        ServiceStatus.EM_LAVAGEM.value,         # entrou no processo interno
        ServiceStatus.EM_LAVAGEM_PARCEIRO.value,
        ServiceStatus.AGUARDANDO_ENTREGA.value, # pronto → disponível para rota de entrega
        ServiceStatus.AGUARDANDO_BUSCAR.value,
        ServiceStatus.ENTREGUE.value,           # ciclo encerrado
        ServiceStatus.EXECUTADO.value,
        ServiceStatus.BUSCOU.value,
        ServiceStatus.CANCELADO_PELO_CLIENTE.value,
    }
    update_fields: Dict[str, Any] = {"status": new_status}
    if new_status in CLEAR_ROUTE_ON and item.get("current_route_id"):
        update_fields["current_route_id"] = None
        update_fields["current_route_stop_id"] = None

    await _update_item_fields(item_id, update_fields, current_user)
    await _append_to_item_array(item_id, "status_history", entry)
    await log_audit("item", item_id, "STATUS_CHANGE", current_user, {
        "from": item.get("status"), "to": new_status, "notes": entry["notes"],
        "route_cleared": new_status in CLEAR_ROUTE_ON,
    })
    await _sync_linked_events_color(item_id)
    return {"success": True, "status": new_status}


@api_router.post("/items/{item_id}/schedule")
async def schedule_item(
    item_id: str,
    payload: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user),
):
    """Definir/atualizar datas planejadas de pickup/execution/delivery."""
    allowed = {
        "scheduled_pickup_date", "scheduled_pickup_time",
        "scheduled_execution_date", "scheduled_execution_time",
        "scheduled_delivery_date", "scheduled_delivery_time",
    }
    fields = {k: v for k, v in payload.items() if k in allowed}
    if not fields:
        raise HTTPException(status_code=400, detail="Nenhuma data válida enviada.")
    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    await _update_item_fields(item_id, fields, current_user)
    await log_audit("item", item_id, "SCHEDULE", current_user, {"fields": fields})
    return {"success": True, "scheduled": fields}


@api_router.post("/items/{item_id}/execution-session/start")
async def start_execution_session(
    item_id: str,
    payload: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user),
):
    """Inicia uma nova sessão de execução (técnico clicou em 'Iniciar')."""
    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    # Bloquear se já existe sessão aberta
    open_sess = [s for s in (item.get("execution_sessions") or []) if not s.get("finished_at")]
    if open_sess:
        raise HTTPException(status_code=400, detail="Já existe uma sessão de execução em andamento.")

    sess = {
        "id": f"SES-{uuid.uuid4().hex[:10]}",
        "started_at": datetime.utcnow().isoformat(),
        "finished_at": None,
        "technician_id": payload.get("technician_id") or item.get("technician_id"),
        "technician_name": payload.get("technician_name"),
        "location": payload.get("location"),
        "outcome": None,
        "reason": None,
        "notes": payload.get("notes") or "",
        "photos": [],
    }
    await _append_to_item_array(item_id, "execution_sessions", sess)

    # Atualiza datas/status do item
    fields = {"actual_started_at": datetime.utcnow()}
    if not item.get("technician_id") and sess["technician_id"]:
        fields["technician_id"] = sess["technician_id"]
    await _update_item_fields(item_id, fields, current_user)
    await log_audit("item", item_id, "EXEC_SESSION_START", current_user, {"session_id": sess["id"]})
    return {"success": True, "session": sess}


@api_router.post("/items/{item_id}/execution-session/{session_id}/finish")
async def finish_execution_session(
    item_id: str,
    session_id: str,
    payload: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user),
):
    """Encerra uma sessão de execução. outcome = COMPLETED | PARTIAL | ABORTED."""
    outcome = payload.get("outcome", "COMPLETED")
    if outcome not in ("COMPLETED", "PARTIAL", "ABORTED"):
        raise HTTPException(status_code=400, detail="outcome inválido.")

    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    sessions = list(item.get("execution_sessions") or [])
    target_idx = next((i for i, s in enumerate(sessions) if s.get("id") == session_id), None)
    if target_idx is None:
        raise HTTPException(status_code=404, detail="Sessão não encontrada.")
    if sessions[target_idx].get("finished_at"):
        raise HTTPException(status_code=400, detail="Sessão já encerrada.")

    now = datetime.utcnow().isoformat()
    sessions[target_idx]["finished_at"] = now
    sessions[target_idx]["outcome"] = outcome
    sessions[target_idx]["reason"] = payload.get("reason")
    sessions[target_idx]["notes"] = payload.get("notes", sessions[target_idx].get("notes") or "")
    if payload.get("photos"):
        sessions[target_idx]["photos"] = payload["photos"]

    update_fields = {"execution_sessions": sessions, "updated_at": datetime.utcnow(), "updated_by": current_user.id}

    # Atualizar status conforme outcome
    new_status = None
    if outcome == "COMPLETED":
        new_status = ServiceStatus.EXECUTADO.value
        update_fields["actual_finished_at"] = datetime.utcnow()
    elif outcome == "PARTIAL":
        new_status = ServiceStatus.EXECUCAO_PARCIAL.value
    elif outcome == "ABORTED":
        new_status = ServiceStatus.RETOQUE_NECESSARIO.value

    if new_status and new_status != item.get("status"):
        update_fields["status"] = new_status

    await db.budgets.update_one(
        {"items.id": item_id},
        {"$set": {f"items.$.{k}": v for k, v in update_fields.items()}},
    )

    if new_status and new_status != item.get("status"):
        entry = {
            "status": new_status,
            "at": now,
            "by_user_id": current_user.id,
            "by_user_name": current_user.name,
            "notes": f"Sessão {outcome}: {payload.get('reason') or payload.get('notes') or ''}".strip(),
        }
        await _append_to_item_array(item_id, "status_history", entry)

    await log_audit("item", item_id, "EXEC_SESSION_FINISH", current_user, {
        "session_id": session_id, "outcome": outcome, "reason": payload.get("reason"),
    })
    if new_status and new_status != item.get("status"):
        await _sync_linked_events_color(item_id)
    return {"success": True, "session": sessions[target_idx], "new_status": new_status}


@api_router.post("/items/{item_id}/payment")
async def register_item_payment(
    item_id: str,
    payload: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user),
):
    """Registrar um recebimento (parcial/total) para um item."""
    method = payload.get("method")
    value = float(payload.get("value") or 0)
    if not method:
        raise HTTPException(status_code=400, detail="Método de pagamento é obrigatório.")
    if value <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser > 0.")

    valid_methods = {m.value for m in PaymentMethod}
    # Accept both enum values and any custom method configured in system_config
    config = await db.system_config.find_one({})
    if config and config.get("payment_methods"):
        valid_methods |= {m["value"] for m in config["payment_methods"]}
    if method not in valid_methods:
        raise HTTPException(status_code=400, detail=f"Método inválido: {method}")

    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    # Data de recebimento: usa a informada pelo usuário (controle de quando o
    # dinheiro entrou de fato), com fallback para o instante do lançamento.
    paid_at_raw = payload.get("paid_at")
    now = datetime.utcnow()
    paid_at_dt = now
    if paid_at_raw:
        try:
            paid_at_dt = datetime.fromisoformat(paid_at_raw)
            if len(paid_at_raw) <= 10:  # só "YYYY-MM-DD", sem horário
                paid_at_dt = paid_at_dt.replace(hour=now.hour, minute=now.minute, second=now.second)
        except ValueError:
            paid_at_dt = now

    record = {
        "id": f"PAY-{uuid.uuid4().hex[:10]}",
        "method": method,
        "value": value,
        "paid_at": paid_at_dt.isoformat(),
        "recorded_by": current_user.id,
        "recorded_by_name": current_user.name,
        "notes": payload.get("notes") or "",
    }

    paid_total = float(item.get("paid_value") or 0) + value
    total_value = float(item.get("total_value") or 0)
    if total_value <= 0:
        payment_status = PaymentStatusItem.PAGO.value if value > 0 else PaymentStatusItem.PENDENTE.value
    elif paid_total + 0.001 >= total_value:
        payment_status = PaymentStatusItem.PAGO.value
    elif paid_total > 0:
        payment_status = PaymentStatusItem.PARCIAL.value
    else:
        payment_status = PaymentStatusItem.PENDENTE.value

    await _append_to_item_array(item_id, "payment_records", record)
    await _update_item_fields(item_id, {
        "paid_value": paid_total,
        "payment_status": payment_status,
    }, current_user)

    # Fix 2: propagar payment_received para o budget pai
    if budget:
        budget_id = budget.get("id")
        if budget_id:
            await db.budgets.update_one(
                {"id": budget_id},
                {"$set": {"payment_received": True, "payment_status": payment_status}},
            )

    await log_audit("item", item_id, "PAYMENT", current_user, {
        "method": method, "value": value, "paid_total": paid_total, "new_status": payment_status,
    })
    await _sync_linked_events_color(item_id)

    # Auto-arquivar orçamento se todos os itens estão finalizados e pagos
    if budget and budget.get("id"):
        await _maybe_auto_archive_budget(budget["id"], triggered_by=f"payment:{current_user.name or current_user.id}")

    return {"success": True, "record": record, "paid_value": paid_total, "payment_status": payment_status}


# ── Cobrança Consolidada ──────────────────────────────────────────────────────
#
# Permite quitar vários itens (mesmo de clientes diferentes) num único pagamento,
# com um RESPONSÁVEL FINANCEIRO (ex: mãe paga o serviço da filha).
#
# Design integration-ready: os campos provider / external_charge_id / payment_link /
# txid / status permitem plugar InfinitePay, PIX dinâmico ou agregador Open Finance
# (Pluggy/Belvo) depois, sem refatorar. Por ora provider=MANUAL (já marca como PAGO).
#
@api_router.post("/payments/consolidated")
async def create_consolidated_payment(
    payload: Dict[str, Any],
    current_user: UserPublic = Depends(get_current_user),
):
    item_ids     = payload.get("item_ids", [])
    method       = payload.get("method")
    payer_name   = (payload.get("payer_name") or "").strip()
    payer_phone  = (payload.get("payer_phone") or "").strip()
    notes        = (payload.get("notes") or "").strip()
    payment_link = (payload.get("payment_link") or "").strip()
    received_in  = payload.get("value")  # opcional; default = soma do que falta
    force_manual = bool(payload.get("force_manual"))  # baixa direta, ignora o gateway ativo

    # Data de recebimento: usa a informada pelo usuário (baixa manual de pagamento
    # já recebido por fora do sistema), com fallback para o instante do lançamento.
    paid_at_raw = payload.get("paid_at")
    _now = datetime.utcnow()
    paid_at_dt = _now
    if paid_at_raw:
        try:
            paid_at_dt = datetime.fromisoformat(paid_at_raw)
            if len(paid_at_raw) <= 10:  # só "YYYY-MM-DD", sem horário
                paid_at_dt = paid_at_dt.replace(hour=_now.hour, minute=_now.minute, second=_now.second)
        except ValueError:
            paid_at_dt = _now

    if not item_ids:
        raise HTTPException(status_code=400, detail="Selecione ao menos um item.")
    if not method:
        raise HTTPException(status_code=400, detail="Método de pagamento obrigatório.")

    # Carrega itens e calcula o que falta em cada um
    targets = []
    total_remaining = 0.0
    for iid in item_ids:
        budget, item = await _find_budget_and_item(iid)
        if not item:
            continue
        remaining = float(item.get("total_value") or 0) - float(item.get("paid_value") or 0)
        if remaining <= 0:
            continue
        targets.append({"item": item, "budget": budget, "remaining": round(remaining, 2)})
        total_remaining += remaining
    total_remaining = round(total_remaining, 2)

    if not targets:
        raise HTTPException(status_code=400, detail="Nenhum item com saldo a receber.")

    total_received = round(float(received_in), 2) if received_in else total_remaining

    cpid = await _next_id(db.consolidated_payments, "CPG-", 5)
    paid_at = paid_at_dt.isoformat()

    # Provedor de pagamento ativo (MANUAL aplica na hora; gateway cria cobrança PENDENTE).
    # force_manual permite dar baixa direta (pagamento já recebido por fora do sistema)
    # mesmo com um gateway (ex.: InfinitePay) configurado como provedor ativo.
    provider = payment_providers.get_provider()
    gateway_mode = (provider.name != "MANUAL") and not force_manual

    # Plano de distribuição do valor recebido, proporcional ao que falta em cada item.
    # Em MANUAL aplicamos já; em gateway guardamos o plano e só aplicamos no webhook.
    distributed = 0.0
    applied = []
    for idx, t in enumerate(targets):
        item = t["item"]
        if idx == len(targets) - 1:
            portion = round(total_received - distributed, 2)  # último absorve resíduo
        else:
            ratio = t["remaining"] / total_remaining if total_remaining else 1 / len(targets)
            portion = round(total_received * ratio, 2)
            distributed += portion
        if portion <= 0:
            continue

        if not gateway_mode:
            record = {
                "id": f"PAY-{uuid.uuid4().hex[:10]}",
                "method": method, "value": portion, "paid_at": paid_at,
                "recorded_by": current_user.id, "recorded_by_name": current_user.name,
                "notes": notes, "consolidated_payment_id": cpid,
                "payer_name": payer_name or None,
            }
            paid_total = round(float(item.get("paid_value") or 0) + portion, 2)
            total_value = float(item.get("total_value") or 0)
            if total_value <= 0:
                pstatus = "PAGO" if portion > 0 else "PENDENTE"
            elif paid_total + 0.001 >= total_value:
                pstatus = "PAGO"
            elif paid_total > 0:
                pstatus = "PARCIAL"
            else:
                pstatus = "PENDENTE"

            await _append_to_item_array(item["id"], "payment_records", record)
            await _update_item_fields(item["id"], {"paid_value": paid_total, "payment_status": pstatus}, current_user)
        else:
            pstatus = "PENDENTE"  # aguardando confirmação do webhook

        applied.append({"item_id": item["id"], "client_name": item.get("client_name"),
                        "service_name": item.get("service_name"), "value": portion, "new_status": pstatus})

    # Link do PDF do orçamento para a mensagem de cobrança (template aprovado em
    # 25/06/2026 — ver memory/INTEGRACOES_PAGAMENTO.md §8). Quando os itens vêm de
    # mais de um orçamento, usa o primeiro (mensagem cita "o último serviço prestado"
    # de forma genérica, então um único link de referência é suficiente).
    budget_ids = [t["budget"]["id"] for t in targets if t.get("budget") and t["budget"].get("id")]
    budget_id_ref = budget_ids[0] if budget_ids else None
    public_url = (
        os.environ.get("PUBLIC_WEBHOOK_URL", "")
        .replace("/api/webhooks/payment", "")
        .strip("/")
    )
    pdf_link = f"{public_url}/api/budgets/{budget_id_ref}/pdf" if (public_url and budget_id_ref) else None

    # Detalhamento por serviço — um item por ITM, com o nome do serviço (e do
    # cliente, quando a cobrança junta itens de clientes diferentes) para que
    # o pagador veja exatamente o que está pagando dentro do checkout.
    distinct_clients = {a.get("client_name") for a in applied if a.get("client_name")}
    line_items_payload = []
    for a in applied:
        svc = a.get("service_name") or "Serviço"
        if len(distinct_clients) > 1 and a.get("client_name"):
            desc = f"{svc} — {a['client_name']}"
        else:
            desc = svc
        line_items_payload.append({
            "description": f"{desc} ({a['item_id']})",
            "quantity": 1,
            "value": a["value"],
        })

    # Modo gateway: cria a cobrança externa (link/PIX) e deixa tudo PENDENTE até o webhook.
    external_charge_id = None
    pix_qr = None
    cp_status = "PAGO"
    if gateway_mode:
        try:
            charge = await provider.create_charge(
                amount=total_received,
                description=f"{cpid} — {payer_name or 'Cobrança SuperDry'}",
                txid=cpid,
                payer={"name": payer_name, "phone": payer_phone},
                items=line_items_payload,
            )
        except NotImplementedError:
            raise HTTPException(status_code=501,
                detail=f"Provedor {provider.name} ainda não implementado (create_charge).")
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Falha ao criar cobrança no provedor: {e}")
        external_charge_id = charge.charge_id
        pix_qr = charge.pix_qr
        payment_link = charge.payment_link or payment_link
        cp_status = "PENDENTE"

    # Estimativa de taxa e valor líquido a receber pela forma de pagamento.
    fees = await get_payment_fees()
    net = compute_net(total_received, fees.get(method, 0))

    doc = {
        "id": cpid,
        "payer_name": payer_name or None,
        "payer_phone": payer_phone or None,
        "item_ids": [t["item"]["id"] for t in targets],
        "budget_id": budget_id_ref,
        "pdf_link": pdf_link,
        "method": method,
        "total_value": total_received,
        # taxa/líquido estimados (confirmados pela integração no futuro)
        "fee_pct": net["fee_pct"],
        "fee_amount": net["fee_amount"],
        "net_value": net["net_value"],
        "notes": notes or None,
        # integração de pagamento
        "provider": "MANUAL" if force_manual else provider.name,
        "external_charge_id": external_charge_id,
        "payment_link": payment_link or None,
        "pix_qr": pix_qr,
        "txid": cpid if gateway_mode else None,
        "status": cp_status,         # MANUAL=PAGO; gateway=PENDENTE até webhook confirmar
        "applied": applied,
        "recorded_by": current_user.id,
        "recorded_by_name": current_user.name,
        "created_at": datetime.utcnow(),
    }
    await db.consolidated_payments.insert_one({k: v for k, v in doc.items()})
    await log_audit("consolidated_payment", cpid, "CREATE", current_user,
                    {"total": total_received, "items": len(applied),
                     "payer": payer_name, "provider": "MANUAL" if force_manual else provider.name,
                     "status": cp_status, "force_manual": force_manual})

    # Auto-arquivar orçamentos afetados se todos os itens estão finalizados e pagos
    if not gateway_mode:
        unique_budget_ids = list({t["budget"]["id"] for t in targets if t.get("budget") and t["budget"].get("id")})
        for bid in unique_budget_ids:
            await _maybe_auto_archive_budget(bid, triggered_by=f"consolidated:{cpid}")

    doc.pop("_id", None)
    return {"success": True, "consolidated_payment": doc}


@api_router.get("/payments/consolidated/pending")
async def list_pending_gateway_payments(current_user: UserPublic = Depends(get_current_user)):
    """
    Cobranças com link de pagamento (InfinitePay, etc.) ainda aguardando
    confirmação. Dá visibilidade dentro do sistema enquanto a confirmação
    automática (webhook) não está validada — permite acompanhar e, se
    necessário, confirmar manualmente após checar no painel do provedor.
    """
    cursor = db.consolidated_payments.find(
        {"status": "PENDENTE", "payment_link": {"$ne": None}}
    ).sort("created_at", -1)
    out = []
    async for d in cursor:
        out.append({
            "id": d.get("id"),
            "payer_name": d.get("payer_name"),
            "payer_phone": d.get("payer_phone"),
            "total_value": d.get("total_value"),
            "method": d.get("method"),
            "provider": d.get("provider"),
            "payment_link": d.get("payment_link"),
            "budget_id": d.get("budget_id"),
            "pdf_link": d.get("pdf_link"),
            "item_count": len(d.get("applied", [])),
            "created_at": d.get("created_at"),
        })
    return {"pending": out}


@api_router.post("/payments/consolidated/{cpid}/confirm-manual")
async def confirm_consolidated_payment_manual(
    cpid: str,
    current_user: UserPublic = Depends(get_current_user),
):
    """
    Confirma manualmente uma cobrança em modo gateway (ex.: InfinitePay) como
    PAGA, sem depender do webhook. Uso: operador conferiu o recebimento direto
    no painel do provedor (ou recebeu por outro meio) e dá baixa no sistema.
    Idempotente — chama o mesmo helper usado pelo webhook/redirect.
    """
    if current_user.role not in ("ADMIN", "FINANCEIRO"):
        raise HTTPException(status_code=403, detail="Sem permissão para confirmar pagamentos.")
    cp = await db.consolidated_payments.find_one({"id": cpid})
    if not cp:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada.")
    if cp.get("status") == "PAGO":
        return {"success": True, "note": "Já estava paga."}
    await _apply_cp_paid(cp, source=f"manual:{current_user.name}")
    await log_audit("consolidated_payment", cpid, "CONFIRM_MANUAL", current_user, {})
    return {"success": True}


@api_router.get("/payments/consolidated/{cpid}/whatsapp")
async def consolidated_payment_whatsapp(cpid: str, current_user: UserPublic = Depends(get_current_user)):
    """Texto de recibo consolidado para enviar via WhatsApp."""
    doc = await db.consolidated_payments.find_one({"id": cpid})
    if not doc:
        raise HTTPException(status_code=404, detail="Cobrança não encontrada.")
    sys_cfg = await db.system_config.find_one({}) or {}
    company = sys_cfg.get("company_name") or "SuperDry Lavanderia"
    lines = [f"*{company}* — Recibo de Pagamento", ""]
    if doc.get("payer_name"):
        lines.append(f"Recebido de: *{doc['payer_name']}*")
    lines.append(f"Comprovante: {doc['id']}")
    lines.append("")
    lines.append("Serviços pagos:")
    for a in doc.get("applied", []):
        lines.append(f"• {a['client_name']} — {a['service_name']}: R$ {a['value']:.2f}")
    lines.append("")
    lines.append(f"*Total: R$ {doc['total_value']:.2f}*")
    lines.append(f"Forma: {doc['method'].replace('PIX_CNPJ_', 'PIX ').replace('_', ' ')}")
    lines.append("")
    lines.append("Obrigado pela preferência! 🧼")
    text = "\n".join(lines)
    from urllib.parse import quote
    phone = re.sub(r"\D", "", doc.get("payer_phone") or "")
    url = f"https://wa.me/{('55'+phone) if phone else ''}?text={quote(text)}"
    return {"whatsapp_url": url, "text": text}


async def _apply_cp_paid(cp, source="webhook"):
    """Marca a cobrança consolidada como PAGA e aplica nos itens. Idempotente.
    Usado tanto pelo webhook quanto pelo redirect de retorno."""
    if cp.get("status") == "PAGO":
        return
    await db.consolidated_payments.update_one({"id": cp["id"]}, {"$set": {
        "status": "PAGO", "paid_at": datetime.utcnow().isoformat(), "provider_event": source,
    }})
    # objeto leve só com .id/.name (UserPublic exigiria campos que não temos aqui)
    system_user = type("SysUser", (), {"id": "SYSTEM", "name": source})()
    budget_ids_updated: set = set()
    for a in cp.get("applied", []):
        iid = a.get("item_id")
        budget, item = await _find_budget_and_item(iid)
        if not item:
            continue
        paid_total = round(float(item.get("paid_value") or 0) + float(a.get("value") or 0), 2)
        tv = float(item.get("total_value") or 0)
        pstatus = "PAGO" if (tv <= 0 or paid_total + 0.001 >= tv) else ("PARCIAL" if paid_total > 0 else "PENDENTE")
        await _append_to_item_array(iid, "payment_records", {
            "id": f"PAY-{uuid.uuid4().hex[:10]}", "method": cp.get("method"),
            "value": float(a.get("value") or 0), "paid_at": datetime.utcnow().isoformat(),
            "recorded_by": "SYSTEM", "recorded_by_name": source,
            "notes": f"Confirmado via {source}", "consolidated_payment_id": cp["id"],
        })
        await _update_item_fields(iid, {"paid_value": paid_total, "payment_status": pstatus}, system_user)
        # Fix 2: propagar payment_received para o budget pai (uma vez por budget)
        if budget and budget.get("id") and budget["id"] not in budget_ids_updated:
            await db.budgets.update_one(
                {"id": budget["id"]},
                {"$set": {"payment_received": True, "payment_status": pstatus}},
            )
            budget_ids_updated.add(budget["id"])


@api_router.get("/payments/infinitepay/return")
async def infinitepay_return(order_nsu: str = "", transaction_nsu: str = "",
                             slug: str = "", receipt_url: str = "", capture_method: str = ""):
    """
    Redirect de retorno do Checkout InfinitePay — 2º canal de captura (no ato do
    pagamento, lado do navegador do cliente). Confirma via payment_check e dá baixa.
    """
    try:
        with open(str(ROOT_DIR / "webhook_recebidos.log"), "a", encoding="utf-8") as wf:
            wf.write(f"\n[{datetime.utcnow().isoformat()}] REDIRECT order_nsu={order_nsu} "
                     f"tx={transaction_nsu} slug={slug} method={capture_method}\n")
    except Exception:
        pass

    provider = payment_providers.get_provider()
    cp = None
    if order_nsu:
        cp = await db.consolidated_payments.find_one({"$or": [{"id": order_nsu}, {"txid": order_nsu}]})
    if cp and cp.get("status") != "PAGO":
        confirm = getattr(provider, "confirm_payment", None)
        ok = True
        if confirm:
            ok = await confirm(order_nsu=order_nsu, transaction_nsu=transaction_nsu, slug=slug)
        if ok:
            await _apply_cp_paid(cp, "redirect")

    # Página simples de agradecimento (redireciona ao site em 4s)
    return HTMLResponse(
        "<!doctype html><html lang='pt-br'><head><meta charset='utf-8'>"
        "<meta http-equiv='refresh' content='4;url=https://lavesuperdry.com.br'>"
        "<title>Pagamento recebido</title></head>"
        "<body style='font-family:sans-serif;text-align:center;padding:48px;color:#1F4E8C'>"
        "<h1>✅ Pagamento recebido!</h1>"
        "<p>Obrigado pela preferência. Você será redirecionado em instantes…</p>"
        "<p style='color:#8CC63F;font-weight:bold'>SuperDry Lavanderia</p></body></html>")


@api_router.post("/webhooks/payment")
async def payment_webhook(request: HttpRequest):
    """
    Webhook de confirmação de pagamento do provedor (InfinitePay, etc.).
    INERTE por padrão (PAYMENT_PROVIDER=MANUAL) → retorna 503.
    Ao ativar um provedor real, este endpoint:
      1. valida a assinatura
      2. identifica a cobrança (txid = nosso CPG-XXXX)
      3. marca o consolidated_payment como PAGO e atualiza os itens
    URL pública sugerida: https://sistema.lavesuperdry.com.br/api/webhooks/payment
    """
    provider = payment_providers.get_provider()
    if provider.name == "MANUAL":
        raise HTTPException(status_code=503, detail="Nenhum provedor de pagamento configurado (PAYMENT_PROVIDER=MANUAL).")

    raw = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}

    # Registra TODA chamada recebida (diagnóstico do webhook InfinitePay)
    try:
        with open(str(ROOT_DIR / "webhook_recebidos.log"), "a", encoding="utf-8") as _wf:
            _wf.write(f"\n[{datetime.utcnow().isoformat()}] WEBHOOK RECEBIDO\n")
            _wf.write(f"  headers: {dict(headers)}\n")
            _wf.write(f"  body: {raw.decode('utf-8', 'ignore')}\n")
    except Exception:
        pass

    if not provider.verify_webhook(headers, raw):
        raise HTTPException(status_code=401, detail="Assinatura de webhook inválida.")

    import json as _json
    payload = _json.loads(raw or b"{}")
    event = provider.parse_webhook(payload)

    # Localiza a cobrança consolidada por txid (preferencial) ou charge_id
    cp = None
    if event.txid:
        cp = await db.consolidated_payments.find_one({"$or": [{"id": event.txid}, {"txid": event.txid}]})
    if not cp and event.charge_id:
        cp = await db.consolidated_payments.find_one({"external_charge_id": event.charge_id})
    if not cp:
        return {"ok": True, "note": "cobrança não encontrada — ignorado"}

    # Confirmação server-to-server (payment_check) — fonte da verdade quando o
    # provedor a oferece (InfinitePay Checkout não assina o webhook com HMAC).
    confirm = getattr(provider, "confirm_payment", None)
    if confirm and event.status == "PAGO":
        ok = await confirm(
            order_nsu=event.txid,
            transaction_nsu=payload.get("transaction_nsu"),
            slug=payload.get("invoice_slug") or payload.get("slug"),
        )
        if not ok:
            # Não confirmado pela API → não aplica. Retorna 200 para evitar retries infinitos.
            return {"ok": True, "note": "pagamento não confirmado pelo payment_check — ignorado"}

    if event.status == "PAGO":
        await _apply_cp_paid(cp, "webhook")

    return {"ok": True}


@api_router.get("/items/{item_id}/receipt")
async def generate_item_receipt(item_id: str):
    """Gerar recibo de pagamento em PDF para um item quitado ou com pagamentos."""
    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    payment_records = item.get("payment_records", [])
    if not payment_records:
        raise HTTPException(status_code=400, detail="Este item não possui pagamentos registrados.")

    client = await db.clients.find_one({"id": budget.get("client_id")})
    system_config = await db.system_config.find_one({}) or {}

    buffer = BytesIO()
    # Recibo em formato A5 (metade do A4) para compactar
    from reportlab.lib.pagesizes import A5
    doc = SimpleDocTemplate(
        buffer, pagesize=A5,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1*cm, bottomMargin=1.5*cm,
    )
    styles = getSampleStyleSheet()
    story = []

    # ── Estilos ────────────────────────────────────────────────────────────────
    title_style = ParagraphStyle('RTitle', parent=styles['Heading1'],
        fontSize=14, spaceAfter=4, alignment=1, textColor=colors.HexColor('#1e3a5f'))
    sub_style = ParagraphStyle('RSub', parent=styles['Normal'],
        fontSize=9, spaceAfter=2, alignment=1, textColor=colors.HexColor('#555555'))
    label_style = ParagraphStyle('RLabel', parent=styles['Normal'],
        fontSize=9, textColor=colors.HexColor('#444444'))
    value_style = ParagraphStyle('RValue', parent=styles['Normal'],
        fontSize=9, fontName='Helvetica-Bold')
    small_style = ParagraphStyle('RSmall', parent=styles['Normal'],
        fontSize=8, textColor=colors.HexColor('#777777'))
    center_style = ParagraphStyle('RCenter', parent=styles['Normal'],
        fontSize=9, alignment=1)

    # ── Logo + cabeçalho ───────────────────────────────────────────────────────
    logo_paths = ["/app/backend/uploads/logo.png", "/app/backend/logo-superdry.png"]
    logo_element = None
    for lp in logo_paths:
        if os.path.exists(lp):
            try:
                logo_element = Image(lp, width=0.75*inch, height=0.6*inch)
                break
            except Exception:
                pass

    company_name     = system_config.get('company_name', 'SuperDry Lavanderia')
    company_cnpj     = system_config.get('cnpj', '')
    company_phone    = system_config.get('phone', '')
    company_whatsapp = system_config.get('whatsapp', '')
    company_instagram= system_config.get('instagram', '')
    company_email    = system_config.get('email', '')
    company_address  = system_config.get('address_full', '')
    company_city     = system_config.get('city', '')
    company_state    = system_config.get('state', '')

    company_lines = [f"<b><font size='11'>{company_name}</font></b>"]
    if company_address:
        city_state = f", {company_city}/{company_state}" if company_city else ""
        company_lines.append(f"<font size='7.5' color='#555555'>{company_address}{city_state}</font>")
    contact_parts = []
    if company_phone:     contact_parts.append(f"Tel: {company_phone}")
    if company_whatsapp:  contact_parts.append(f"WhatsApp: {company_whatsapp}")
    if company_email:     contact_parts.append(company_email)
    if company_instagram: contact_parts.append(f"@{company_instagram}")
    if company_cnpj:      contact_parts.append(f"CNPJ: {company_cnpj}")
    if contact_parts:
        company_lines.append(f"<font size='7.5' color='#555555'>{' | '.join(contact_parts[:3])}</font>")
        if len(contact_parts) > 3:
            company_lines.append(f"<font size='7.5' color='#555555'>{' | '.join(contact_parts[3:])}</font>")

    company_para = Paragraph("<br/>".join(company_lines),
        ParagraphStyle('CompanyHeader', parent=styles['Normal'], fontSize=10, leading=13))

    if logo_element:
        from reportlab.lib.pagesizes import A5 as A5_size
        page_w = A5_size[0] - 3*cm
        logo_col = 0.85*inch
        header_table = Table([[logo_element, company_para]],
            colWidths=[logo_col, page_w - logo_col])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('ALIGN',  (1,0), (1,0),  'LEFT'),
            ('LEFTPADDING',  (0,0), (0,0), 0),
            ('RIGHTPADDING', (0,0), (0,0), 8),
        ]))
        story.append(header_table)
    else:
        story.append(company_para)

    story.append(Spacer(1, 8))

    # ── Título do recibo ───────────────────────────────────────────────────────
    recibo_num = f"REC-{item_id}"
    story.append(Paragraph("RECIBO DE PAGAMENTO", title_style))
    story.append(Paragraph(f"Nº {recibo_num}", small_style))
    story.append(Spacer(1, 6))

    # ── Linha divisória ────────────────────────────────────────────────────────
    story.append(Table([['']], colWidths=['100%'],
        style=TableStyle([('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor('#1e3a5f'))])))
    story.append(Spacer(1, 6))

    # ── Dados do cliente e serviço ─────────────────────────────────────────────
    client_name = item.get("client_name") or budget.get("client_name", "N/A")
    client_phone = client.get("phone_primary", "N/A") if client else "N/A"
    service_name = item.get("service_name", "N/A")
    budget_id = budget.get("id", "N/A")

    info_data = [
        [Paragraph("<b>Cliente:</b>", label_style), Paragraph(client_name, value_style)],
        [Paragraph("<b>Telefone:</b>", label_style), Paragraph(client_phone, value_style)],
        [Paragraph("<b>Serviço:</b>", label_style), Paragraph(service_name, value_style)],
        [Paragraph("<b>Orçamento:</b>", label_style), Paragraph(budget_id, value_style)],
    ]
    from reportlab.lib.pagesizes import A5 as A5_sz
    col_w = (A5_sz[0] - 3*cm) / 2
    info_table = Table(info_data, colWidths=[col_w*0.35, col_w*1.65])
    info_table.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))

    # ── Tabela de pagamentos ───────────────────────────────────────────────────
    story.append(Paragraph("<b>Pagamentos Registrados</b>", label_style))
    story.append(Spacer(1, 4))

    centered = ParagraphStyle('RC', parent=styles['Normal'], fontSize=8, alignment=1)

    pay_header = [
        Paragraph("<b><font color='white'>Data</font></b>", centered),
        Paragraph("<b><font color='white'>Forma</font></b>", centered),
        Paragraph("<b><font color='white'>Valor</font></b>", centered),
    ]
    pay_rows = [pay_header]
    for rec in payment_records:
        paid_at_raw = rec.get("paid_at", "")
        try:
            paid_dt = datetime.fromisoformat(paid_at_raw.replace('Z','+00:00'))
            paid_date_str = paid_dt.strftime("%d/%m/%Y")
        except Exception:
            paid_date_str = paid_at_raw[:10] if paid_at_raw else "—"

        method_raw = rec.get("method", "—")
        method_label = (method_raw
            .replace("PIX_CNPJ_", "PIX ")
            .replace("CREDITO_", "Créd. ")
            .replace("LINK_PAGAMENTO", "Link Pag.")
            .replace("_", " "))

        pay_rows.append([
            Paragraph(paid_date_str, centered),
            Paragraph(method_label, centered),
            Paragraph(f"R$ {float(rec.get('value',0)):.2f}", centered),
        ])

    col_w3 = (A5_sz[0] - 3*cm)
    pay_table = Table(pay_rows, colWidths=[col_w3*0.28, col_w3*0.44, col_w3*0.28])
    pay_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a5f')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    story.append(pay_table)
    story.append(Spacer(1, 8))

    # ── Totais ─────────────────────────────────────────────────────────────────
    total_value = float(item.get("total_value", 0))
    paid_total  = float(item.get("paid_value", 0))
    remaining   = total_value - paid_total
    pay_status  = item.get("payment_status", "PENDENTE")

    totals_data = [
        [Paragraph("Valor do Serviço:", label_style), Paragraph(f"R$ {total_value:.2f}", value_style)],
        [Paragraph("Total Pago:", label_style),       Paragraph(f"R$ {paid_total:.2f}", value_style)],
    ]
    if remaining > 0.01:
        totals_data.append([
            Paragraph("Saldo em Aberto:", label_style),
            Paragraph(f"R$ {remaining:.2f}", ParagraphStyle('Rem', parent=styles['Normal'],
                fontSize=9, fontName='Helvetica-Bold', textColor=colors.HexColor('#cc0000')))
        ])

    totals_table = Table(totals_data, colWidths=[col_w3*0.55, col_w3*0.45])
    totals_table.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 6))

    # ── Status final ───────────────────────────────────────────────────────────
    status_color = '#16a34a' if pay_status == 'PAGO' else '#ca8a04' if pay_status == 'PARCIAL' else '#dc2626'
    status_label = {'PAGO':'✓ QUITADO','PARCIAL':'⚡ PARCIALMENTE PAGO','PENDENTE':'⚠ EM ABERTO'}.get(pay_status, pay_status)
    story.append(Paragraph(
        f"<font color='{status_color}'><b>{status_label}</b></font>",
        ParagraphStyle('Status', parent=styles['Normal'], fontSize=11, alignment=1)
    ))
    story.append(Spacer(1, 8))

    # ── Linha divisória + rodapé ───────────────────────────────────────────────
    story.append(Table([['']], colWidths=['100%'],
        style=TableStyle([('LINEABOVE', (0,0), (-1,-1), 0.5, colors.HexColor('#aaaaaa'))])))
    story.append(Spacer(1, 4))

    receipt_date = datetime.utcnow().strftime("%d/%m/%Y às %H:%M")
    story.append(Paragraph(f"Recibo emitido em {receipt_date} — {company_name}", small_style))

    if pay_status == 'PAGO':
        story.append(Spacer(1, 12))
        story.append(Paragraph("_" * 45, center_style))
        story.append(Paragraph("Assinatura / Carimbo", center_style))

    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(
        BytesIO(buffer.read()),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=recibo_{item_id}.pdf"}
    )


@api_router.post("/items/multi-receipt")
async def generate_multi_receipt(payload: Dict[str, Any]):
    """Gera um único PDF de recibo consolidado para múltiplos itens selecionados."""
    item_ids = payload.get("item_ids", [])
    if not item_ids:
        raise HTTPException(status_code=400, detail="Nenhum item informado.")

    from reportlab.lib.pagesizes import A5 as A5_sz

    system_config = await db.system_config.find_one({}) or {}
    company_name     = system_config.get('company_name', 'SuperDry Lavanderia')
    company_cnpj     = system_config.get('cnpj', '')
    company_phone    = system_config.get('phone', '')
    company_whatsapp = system_config.get('whatsapp', '')
    company_email    = system_config.get('email', '')
    company_instagram= system_config.get('instagram', '')
    company_address  = system_config.get('address_full', '')
    company_city     = system_config.get('city', '')
    company_state    = system_config.get('state', '')

    # Busca todos os itens
    items_data = []
    for iid in item_ids:
        budget, item = await _find_budget_and_item(iid)
        if item:
            items_data.append((budget, item))
    if not items_data:
        raise HTTPException(status_code=404, detail="Nenhum item encontrado.")

    # Infere nome do cliente (único ou múltiplos)
    client_names = list(dict.fromkeys(
        it.get("client_name") or bud.get("client_name", "N/A")
        for bud, it in items_data
    ))
    client_label = client_names[0] if len(client_names) == 1 else ", ".join(client_names[:3])
    if len(client_names) > 3:
        client_label += f" +{len(client_names)-3}"

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A5_sz,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1*cm, bottomMargin=1.5*cm,
    )
    styles = getSampleStyleSheet()

    title_style  = ParagraphStyle('MRT', parent=styles['Heading1'], fontSize=14,
                                  spaceAfter=4, alignment=1, textColor=colors.HexColor('#1e3a5f'))
    label_style  = ParagraphStyle('MRL', parent=styles['Normal'], fontSize=9,
                                  textColor=colors.HexColor('#444444'))
    value_style  = ParagraphStyle('MRV', parent=styles['Normal'], fontSize=9,
                                  fontName='Helvetica-Bold')
    small_style  = ParagraphStyle('MRS', parent=styles['Normal'], fontSize=8,
                                  textColor=colors.HexColor('#777777'))
    center_style = ParagraphStyle('MRC', parent=styles['Normal'], fontSize=8, alignment=1)

    story = []

    # ── Logo + cabeçalho empresa ───────────────────────────────────────────────
    logo_element = None
    for lp in ["/app/backend/uploads/logo.png", "/app/backend/logo-superdry.png"]:
        if os.path.exists(lp):
            try: logo_element = Image(lp, width=0.75*inch, height=0.6*inch); break
            except: pass

    company_lines = [f"<b><font size='11'>{company_name}</font></b>"]
    if company_address:
        city_state = f", {company_city}/{company_state}" if company_city else ""
        company_lines.append(f"<font size='7.5' color='#555555'>{company_address}{city_state}</font>")
    contact_parts = []
    if company_phone:     contact_parts.append(f"Tel: {company_phone}")
    if company_whatsapp:  contact_parts.append(f"WhatsApp: {company_whatsapp}")
    if company_email:     contact_parts.append(company_email)
    if company_instagram: contact_parts.append(f"@{company_instagram}")
    if company_cnpj:      contact_parts.append(f"CNPJ: {company_cnpj}")
    if contact_parts:
        company_lines.append(f"<font size='7.5' color='#555555'>{' | '.join(contact_parts[:3])}</font>")
        if len(contact_parts) > 3:
            company_lines.append(f"<font size='7.5' color='#555555'>{' | '.join(contact_parts[3:])}</font>")

    company_para = Paragraph("<br/>".join(company_lines),
        ParagraphStyle('CHdr', parent=styles['Normal'], fontSize=10, leading=13))

    page_w = A5_sz[0] - 3*cm
    if logo_element:
        logo_col = 0.85*inch
        hdr_tbl = Table([[logo_element, company_para]], colWidths=[logo_col, page_w - logo_col])
        hdr_tbl.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ('LEFTPADDING', (0,0), (0,0), 0),
            ('RIGHTPADDING', (0,0), (0,0), 8),
        ]))
        story.append(hdr_tbl)
    else:
        story.append(company_para)

    story.append(Spacer(1, 8))

    # ── Título ─────────────────────────────────────────────────────────────────
    rec_id = f"REC-{item_ids[0][:10]}" if len(item_ids) == 1 else f"REC-MULTI-{len(item_ids)}itens"
    story.append(Paragraph("RECIBO DE PAGAMENTO", title_style))
    story.append(Paragraph(f"Nº {rec_id}", small_style))
    story.append(Spacer(1, 6))
    story.append(Table([['']], colWidths=['100%'],
        style=TableStyle([('LINEABOVE', (0,0), (-1,-1), 1, colors.HexColor('#1e3a5f'))])))
    story.append(Spacer(1, 6))

    # ── Dados do cliente ───────────────────────────────────────────────────────
    info_data = [
        [Paragraph("<b>Cliente:</b>", label_style), Paragraph(client_label, value_style)],
    ]
    if len(client_names) == 1:
        client_doc = await db.clients.find_one({"name": client_names[0]})
        phone = client_doc.get("phone_primary", "") if client_doc else ""
        if phone:
            info_data.append([Paragraph("<b>Telefone:</b>", label_style), Paragraph(phone, value_style)])
    info_table = Table(info_data, colWidths=[page_w*0.3, page_w*0.7])
    info_table.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 8))

    # ── Tabela de itens ────────────────────────────────────────────────────────
    story.append(Paragraph("<b>Serviços</b>", label_style))
    story.append(Spacer(1, 4))

    hdr_para = lambda t: Paragraph(f"<b><font color='white'>{t}</font></b>", center_style)
    tbl_header = [hdr_para("Serviço"), hdr_para("Valor"), hdr_para("Pago"), hdr_para("Status")]
    tbl_rows = [tbl_header]

    total_valor = 0.0
    total_pago  = 0.0

    for bud, it in items_data:
        svc_name   = it.get("service_name", "—")
        val        = float(it.get("total_value", 0))
        paid       = float(it.get("paid_value", 0))
        pstatus    = it.get("payment_status", "PENDENTE")
        status_lbl = {"PAGO": "✓ Pago", "PARCIAL": "Parcial", "CORTESIA": "Cortesia"}.get(pstatus, "Pendente")
        cname      = it.get("client_name") or bud.get("client_name", "")
        row_name   = f"{svc_name}" if len(client_names) == 1 else f"{svc_name}\n{cname}"
        total_valor += val
        total_pago  += paid
        tbl_rows.append([
            Paragraph(row_name, ParagraphStyle('SN', parent=styles['Normal'], fontSize=7.5)),
            Paragraph(f"R$ {val:.2f}",  center_style),
            Paragraph(f"R$ {paid:.2f}", center_style),
            Paragraph(status_lbl,        center_style),
        ])

    items_table = Table(tbl_rows, colWidths=[page_w*0.42, page_w*0.20, page_w*0.20, page_w*0.18])
    items_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e3a5f')),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f8fafc'), colors.white]),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#cccccc')),
        ('FONTSIZE', (0,0), (-1,-1), 7.5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 8))

    # ── Totais ─────────────────────────────────────────────────────────────────
    remaining = total_valor - total_pago
    totals_data = [
        [Paragraph("Total dos Serviços:", label_style), Paragraph(f"R$ {total_valor:.2f}", value_style)],
        [Paragraph("Total Pago:",         label_style), Paragraph(f"R$ {total_pago:.2f}",  value_style)],
    ]
    if remaining > 0.01:
        totals_data.append([
            Paragraph("Saldo em Aberto:", label_style),
            Paragraph(f"R$ {remaining:.2f}",
                ParagraphStyle('Rem2', parent=styles['Normal'], fontSize=9,
                    fontName='Helvetica-Bold', textColor=colors.HexColor('#cc0000')))
        ])
    totals_table = Table(totals_data, colWidths=[page_w*0.55, page_w*0.45])
    totals_table.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('ALIGN', (1,0), (1,-1), 'RIGHT'),
    ]))
    story.append(totals_table)
    story.append(Spacer(1, 6))

    # ── Status geral ───────────────────────────────────────────────────────────
    if total_pago >= total_valor - 0.01:
        overall_status, overall_color = "✓ QUITADO", '#16a34a'
    elif total_pago > 0:
        overall_status, overall_color = "⚡ PARCIALMENTE PAGO", '#ca8a04'
    else:
        overall_status, overall_color = "⚠ EM ABERTO", '#dc2626'

    story.append(Paragraph(
        f"<font color='{overall_color}'><b>{overall_status}</b></font>",
        ParagraphStyle('OSt', parent=styles['Normal'], fontSize=11, alignment=1)
    ))
    story.append(Spacer(1, 8))
    story.append(Table([['']], colWidths=['100%'],
        style=TableStyle([('LINEABOVE', (0,0), (-1,-1), 0.5, colors.HexColor('#aaaaaa'))])))
    story.append(Spacer(1, 4))
    receipt_date = datetime.utcnow().strftime("%d/%m/%Y às %H:%M")
    story.append(Paragraph(f"Recibo emitido em {receipt_date} — {company_name}", small_style))

    if total_pago >= total_valor - 0.01:
        story.append(Spacer(1, 14))
        story.append(Paragraph("_" * 45, ParagraphStyle('Sig', parent=styles['Normal'], fontSize=9, alignment=1)))
        story.append(Paragraph("Assinatura / Carimbo", center_style))

    doc.build(story)
    buffer.seek(0)
    fname = f"recibo_{item_ids[0]}.pdf" if len(item_ids) == 1 else f"recibo_consolidado_{len(item_ids)}itens.pdf"
    return StreamingResponse(
        BytesIO(buffer.read()),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={fname}"}
    )


@api_router.get("/items/{item_id}/pickup-receipt")
async def generate_pickup_receipt(item_id: str):
    """Comprovante de retirada — gerado quando o técnico coleta o item."""
    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    client = await db.clients.find_one({"id": budget.get("client_id")})
    system_config = await db.system_config.find_one({}) or {}

    buffer = BytesIO()
    from reportlab.lib.pagesizes import A5
    doc = SimpleDocTemplate(buffer, pagesize=A5,
        leftMargin=1.5*cm, rightMargin=1.5*cm, topMargin=1*cm, bottomMargin=1.5*cm)
    styles = getSampleStyleSheet()
    story = []

    label_style = ParagraphStyle('PLabel', parent=styles['Normal'], fontSize=9, textColor=colors.HexColor('#444444'))
    value_style = ParagraphStyle('PValue', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')
    small_style = ParagraphStyle('PSmall', parent=styles['Normal'], fontSize=8, textColor=colors.HexColor('#777777'))
    center_style = ParagraphStyle('PCenter', parent=styles['Normal'], fontSize=9, alignment=1)
    title_style  = ParagraphStyle('PTitle', parent=styles['Heading1'], fontSize=14, spaceAfter=4, alignment=1,
                                   textColor=colors.HexColor('#1e3a5f'))

    # Cabeçalho com logo + dados empresa
    logo_paths = ["/app/backend/uploads/logo.png", "/app/backend/logo-superdry.png"]
    logo_element = None
    for lp in logo_paths:
        if os.path.exists(lp):
            try: logo_element = Image(lp, width=0.75*inch, height=0.6*inch); break
            except Exception: pass

    company_name     = system_config.get('company_name', 'SuperDry Lavanderia')
    company_phone    = system_config.get('phone', '')
    company_whatsapp = system_config.get('whatsapp', '')
    company_address  = system_config.get('address_full', '')
    company_city     = system_config.get('city', '')
    company_state    = system_config.get('state', '')
    company_cnpj     = system_config.get('cnpj', '')

    lines = [f"<b><font size='11'>{company_name}</font></b>"]
    if company_address:
        cs = f", {company_city}/{company_state}" if company_city else ""
        lines.append(f"<font size='7.5' color='#555555'>{company_address}{cs}</font>")
    contacts = []
    if company_phone:    contacts.append(f"Tel: {company_phone}")
    if company_whatsapp: contacts.append(f"WhatsApp: {company_whatsapp}")
    if company_cnpj:     contacts.append(f"CNPJ: {company_cnpj}")
    if contacts:
        lines.append(f"<font size='7.5' color='#555555'>{' | '.join(contacts)}</font>")

    company_para = Paragraph("<br/>".join(lines),
        ParagraphStyle('CH', parent=styles['Normal'], fontSize=10, leading=13))

    if logo_element:
        from reportlab.lib.pagesizes import A5 as A5s
        page_w = A5s[0] - 3*cm
        ht = Table([[logo_element, company_para]], colWidths=[0.85*inch, page_w - 0.85*inch])
        ht.setStyle(TableStyle([('VALIGN',(0,0),(-1,-1),'MIDDLE'),
                                 ('LEFTPADDING',(0,0),(0,0),0),('RIGHTPADDING',(0,0),(0,0),8)]))
        story.append(ht)
    else:
        story.append(company_para)

    story.append(Spacer(1, 8))
    story.append(Table([['']], colWidths=['100%'],
        style=TableStyle([('LINEABOVE',(0,0),(-1,-1),1,colors.HexColor('#1e3a5f'))])))
    story.append(Spacer(1, 6))

    story.append(Paragraph("COMPROVANTE DE RETIRADA", title_style))
    story.append(Paragraph(f"Nº RET-{item_id}", small_style))
    story.append(Spacer(1, 8))

    # Data/hora da coleta
    coletado_at = None
    for h in reversed(item.get("status_history", [])):
        if h.get("status") == "COLETADO":
            coletado_at = h.get("at"); break
    if not coletado_at:
        coletado_at = datetime.utcnow().isoformat()
    try:
        dt = datetime.fromisoformat(coletado_at.replace('Z','+00:00'))
        coleta_str = dt.strftime("%d/%m/%Y às %H:%M")
    except Exception:
        coleta_str = coletado_at[:16] if coletado_at else "—"

    client_name  = item.get("client_name") or budget.get("client_name", "N/A")
    client_phone = client.get("phone_primary", "N/A") if client else "N/A"
    client_addr  = ""
    if client and client.get("address"):
        a = client["address"]
        client_addr = a.get("full_address") or f"{a.get('neighborhood','')}, {a.get('city','')}".strip(", ")

    from reportlab.lib.pagesizes import A5 as A5s2
    col_w = (A5s2[0] - 3*cm)
    cw   = [col_w*0.38, col_w*0.62]

    info = [
        [Paragraph("<b>Cliente:</b>",         label_style), Paragraph(client_name,  value_style)],
        [Paragraph("<b>Telefone:</b>",         label_style), Paragraph(client_phone, value_style)],
        [Paragraph("<b>Serviço:</b>",          label_style), Paragraph(item.get("service_name","—"), value_style)],
        [Paragraph("<b>Orçamento:</b>",        label_style), Paragraph(budget.get("id","—"), value_style)],
        [Paragraph("<b>Data da Coleta:</b>",   label_style), Paragraph(coleta_str, value_style)],
    ]
    if client_addr:
        info.append([Paragraph("<b>Endereço:</b>", label_style),
                     Paragraph(client_addr, ParagraphStyle('Addr', parent=styles['Normal'], fontSize=8))])

    it = Table(info, colWidths=cw)
    it.setStyle(TableStyle([('LEFTPADDING',(0,0),(-1,-1),0),('RIGHTPADDING',(0,0),(-1,-1),4),
                             ('BOTTOMPADDING',(0,0),(-1,-1),4),('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.append(it)
    story.append(Spacer(1, 12))

    # Declaração
    decl = (f"Declaro que recebi os itens acima identificados para realização dos serviços contratados, "
            f"comprometendo-me a devolvê-los após a conclusão. "
            f"Orçamento nº {budget.get('id','—')}, salvo conforme acordado.")
    story.append(Paragraph(decl,
        ParagraphStyle('Decl', parent=styles['Normal'], fontSize=8,
                       textColor=colors.HexColor('#444444'), leading=12)))
    story.append(Spacer(1, 20))

    # Assinaturas
    from reportlab.lib.pagesizes import A5 as A5s3
    col_w3 = (A5s3[0] - 3*cm)
    sig = Table([
        [Paragraph("_"*28, center_style), Paragraph("_"*28, center_style)],
        [Paragraph("Assinatura do Cliente", center_style), Paragraph("Assinatura do Técnico", center_style)],
    ], colWidths=[col_w3/2, col_w3/2])
    sig.setStyle(TableStyle([('ALIGN',(0,0),(-1,-1),'CENTER'), ('BOTTOMPADDING',(0,0),(-1,-1),4)]))
    story.append(sig)

    story.append(Spacer(1, 8))
    story.append(Table([['']], colWidths=['100%'],
        style=TableStyle([('LINEABOVE',(0,0),(-1,-1),0.5,colors.HexColor('#aaaaaa'))])))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Comprovante emitido em {datetime.utcnow().strftime('%d/%m/%Y às %H:%M')} — {company_name}",
        small_style))

    doc.build(story)
    buffer.seek(0)
    return StreamingResponse(BytesIO(buffer.read()), media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=comprovante_retirada_{item_id}.pdf"})


@api_router.get("/items/{item_id}/whatsapp-receipt")
async def whatsapp_receipt_link(item_id: str, doc_type: str = "receipt"):
    """Gera link wa.me com URL do PDF para compartilhar com o cliente."""
    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")
    client = await db.clients.find_one({"id": budget.get("client_id")})
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    phone_raw = (client.get("phone_primary") or "").replace(" ","").replace("-","").replace("(","").replace(")","").replace("+","")
    if not phone_raw.startswith("55"):
        phone_raw = "55" + phone_raw

    system_config = await db.system_config.find_one({}) or {}
    company_name = system_config.get('company_name', 'SuperDry Lavanderia')

    # URL pública do PDF (endpoint sem auth)
    # O REACT_APP_BACKEND_URL não está disponível no backend, usamos variável de ambiente
    backend_url = os.environ.get("REACT_APP_BACKEND_URL", "")
    if not backend_url:
        raise HTTPException(status_code=500, detail="REACT_APP_BACKEND_URL não configurado no backend.")

    client_name = item.get("client_name") or budget.get("client_name", "")
    service_name = item.get("service_name", "")

    if doc_type == "pickup":
        pdf_url = f"{backend_url}/api/items/{item_id}/pickup-receipt"
        msg = (
            f"Olá {client_name}! 👋\n\n"
            f"Segue o comprovante de retirada do seu {service_name}.\n\n"
            f"📄 Acesse o comprovante pelo link:\n{pdf_url}\n\n"
            f"Qualquer dúvida, estamos à disposição!\n"
            f"— {company_name}"
        )
    else:
        pdf_url = f"{backend_url}/api/items/{item_id}/receipt"
        total = float(item.get("total_value", 0))
        paid  = float(item.get("paid_value", 0))
        pay_status = item.get("payment_status", "PENDENTE")
        status_txt = "✅ QUITADO" if pay_status == "PAGO" else f"⚡ Pago: R$ {paid:.2f} de R$ {total:.2f}"
        msg = (
            f"Olá {client_name}! 👋\n\n"
            f"Segue o recibo do serviço: {service_name}\n"
            f"Situação: {status_txt}\n\n"
            f"📄 Acesse o recibo pelo link:\n{pdf_url}\n\n"
            f"Agradecemos a confiança!\n"
            f"— {company_name}"
        )

    import urllib.parse
    whatsapp_url = f"https://wa.me/{phone_raw}?text={urllib.parse.quote(msg)}"
    return {"whatsapp_url": whatsapp_url, "pdf_url": pdf_url, "phone": phone_raw}


@api_router.get("/items/{item_id}/timeline")
async def item_timeline(item_id: str, current_user: UserPublic = Depends(get_current_user)):
    """Linha do tempo completa do item (histórico unificado)."""
    budget, item = await _find_budget_and_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item não encontrado")

    events = []
    for h in (item.get("status_history") or []):
        events.append({
            "type": "STATUS",
            "at": h.get("at"),
            "label": f"Status → {h.get('status')}",
            "by": h.get("by_user_name"),
            "notes": h.get("notes"),
        })
    for s in (item.get("execution_sessions") or []):
        events.append({
            "type": "EXEC_START",
            "at": s.get("started_at"),
            "label": f"Iniciou execução ({s.get('technician_name') or s.get('technician_id') or '—'})",
            "by": s.get("technician_name"),
            "notes": s.get("notes"),
        })
        if s.get("finished_at"):
            events.append({
                "type": "EXEC_END",
                "at": s.get("finished_at"),
                "label": f"Encerrou execução: {s.get('outcome')}",
                "by": s.get("technician_name"),
                "notes": s.get("reason") or s.get("notes"),
            })
    for p in (item.get("payment_records") or []):
        events.append({
            "type": "PAYMENT",
            "at": p.get("paid_at"),
            "label": f"Pagamento {p.get('method')} — R$ {p.get('value'):.2f}",
            "by": p.get("recorded_by_name"),
            "notes": p.get("notes"),
        })

    # Eventos de rota
    for rid in (item.get("route_history") or []):
        events.append({"type": "ROUTE", "at": None, "label": f"Adicionado à rota {rid}", "by": None})

    # Ordenar por data (None último)
    def keyfn(e):
        return e.get("at") or "9999-12-31T00:00:00"
    events.sort(key=keyfn)
    return {"item_id": item_id, "events": events}


@api_router.get("/items")
async def list_items(
    status: Optional[str] = None,
    client_id: Optional[str] = None,
    technician_id: Optional[str] = None,
    route_id: Optional[str] = None,
    payment_status: Optional[str] = None,
    no_route: Optional[bool] = None,
    limit: int = 500,
    current_user: UserPublic = Depends(get_current_user),
):
    """Listagem direta de itens (filtros para Dashboard, Rotas, Financeiro, Técnico)."""
    match: Dict[str, Any] = {}
    if status:
        match["items.status"] = status
    if client_id:
        match["items.client_id"] = client_id
    if technician_id:
        match["items.technician_id"] = technician_id
    if route_id:
        match["items.current_route_id"] = route_id
    if payment_status:
        match["items.payment_status"] = payment_status
    if no_route:
        match["items.current_route_id"] = None

    pipeline = [
        {"$unwind": "$items"},
    ]
    # Filtros pós-unwind (aplicados ao item)
    item_match = {}
    if status: item_match["items.status"] = status
    if client_id: item_match["items.client_id"] = client_id
    if technician_id: item_match["items.technician_id"] = technician_id
    if route_id: item_match["items.current_route_id"] = route_id
    if payment_status: item_match["items.payment_status"] = payment_status
    if no_route: item_match["items.current_route_id"] = None
    if item_match:
        pipeline.append({"$match": item_match})
    pipeline.append({"$project": {"_id": 0, "item": "$items", "budget_id": "$id", "budget_payment_method": "$payment_method"}})
    pipeline.append({"$limit": limit})

    cursor = db.budgets.aggregate(pipeline)
    out = []
    async for doc in cursor:
        out.append(doc)
    return {"count": len(out), "items": out}


# Include the router in the main app
app.include_router(api_router)

# Gestor Financeiro (Fase 0) — router separado, import tardio proposital
# (ver docstring de finance_routes.py: depende de db/get_current_user/_next_id
# já definidos neste módulo no momento em que é importado).
import finance_routes  # noqa: E402
app.include_router(finance_routes.finance_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


async def _warmup_ollama():
    """Pré-carrega llama3.2:3b na RAM do Ollama após o boot do serviço.
    Evita cold-start de 90s na primeira chamada de Automação com IA."""
    import httpx as _httpx2
    await asyncio.sleep(8)  # aguarda o servidor concluir o boot
    try:
        async with _httpx2.AsyncClient(timeout=10.0) as hc:
            hcheck = await hc.get("http://localhost:11434/api/tags")
        if hcheck.status_code != 200:
            print("[warmup-ollama] Ollama não está disponível — skip.")
            return
        print("[warmup-ollama] Carregando llama3.2:3b na RAM...")
        async with _httpx2.AsyncClient(timeout=150.0) as hc:
            r = await hc.post("http://localhost:11434/api/generate", json={
                "model": "llama3.2:3b",
                "prompt": "olá",
                "stream": False,
                "keep_alive": -1,
                "options": {"temperature": 0.1, "num_predict": 5},
            })
        if r.status_code == 200:
            print("[warmup-ollama] llama3.2:3b carregado na RAM com sucesso.")
        else:
            print(f"[warmup-ollama] Ollama respondeu com status {r.status_code}.")
    except Exception as _we:
        print(f"[warmup-ollama] Erro no warmup (não crítico): {_we}")


@app.on_event("startup")
async def startup_bootstrap():
    """Cria índices e usuário admin padrão se necessário."""
    try:
        await db.users.create_index("email", unique=True)
        await db.clients.create_index("name_normalized")
        await db.clients.create_index("id", unique=True)
        await db.audit_logs.create_index([("entity_type", 1), ("entity_id", 1)])
    except Exception as e:
        print(f"[startup] erro criando índices: {e}")
    await ensure_default_admin(db)

    # Gestor Financeiro (Fase 0) — seed de categorias padrão PF/PJ, idempotente
    try:
        if await db.financial_categories.count_documents({}) == 0:
            for c in DEFAULT_CATEGORIES:
                cat_id = await _next_id(db.financial_categories, "CAT-", 4)
                await db.financial_categories.insert_one({
                    "id": cat_id, "name": c["name"], "kind": c["kind"], "parent_id": None,
                    "scope": c["scope"], "color": None, "icon": None, "archived": False,
                })
    except Exception as e:
        print(f"[startup] erro seed categorias financeiras: {e}")

    # Serviço placeholder "Tapete a Identificar" — usado quando a forma (quadrado/
    # redondo) ainda não é conhecida na hora de cadastrar o orçamento (antes disso
    # era obrigatório chutar uma forma). Idempotente. Ajuste 02/10/2026.
    try:
        if not await db.services.find_one({"id": "SRV-0046"}):
            await db.services.insert_one({
                "id": "SRV-0046",
                "name": "Tapete a Identificar (forma pendente)",
                "category": "TAPETES",
                "service_type": "LAVAGEM",
                "measure_type": "TAPETE_A_IDENTIFICAR",
                "execution_location": "CLIENTE_TROUXE",
                "cost_price": 0.0,
                "sale_price": 0.0,
                "is_active": True,
                "default_service_status": "CLIENTE_TROUXE",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            })
            print("[startup] serviço placeholder SRV-0046 (Tapete a Identificar) criado.")
    except Exception as e:
        print(f"[startup] erro seed serviço placeholder de tapete: {e}")

    # Pré-aquecimento do Ollama (carrega llama3.2:3b na RAM logo após o boot)
    asyncio.create_task(_warmup_ollama())

    # Poller de extrato bancário por e-mail (alternativa gratuita ao Open Finance
    # pago — ver memory/GESTOR_FINANCEIRO.md §18). Só inicia se configurado no .env.
    try:
        import email_statement_poller
        if email_statement_poller.is_configured():
            asyncio.create_task(email_statement_poller.poller_loop())
            print("[startup] poller de extrato por e-mail ativado.")
        else:
            print("[startup] poller de extrato por e-mail desativado (STATEMENT_EMAIL_USER não definido).")
    except Exception as e:
        print(f"[startup] erro iniciando poller de extrato: {e}")


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()


# ── Servir frontend React (build estático) ───────────────────────────────────
# O build é gerado em frontend/build/ via `npm run build`.
# Esta seção deve ficar APÓS todos os endpoints de API para não interceptá-los.
_FRONTEND_BUILD = Path(__file__).parent.parent / "frontend" / "build"

if _FRONTEND_BUILD.exists():
    # Arquivos estáticos do React (JS, CSS, media)
    app.mount("/static", StaticFiles(directory=str(_FRONTEND_BUILD / "static")), name="react-static")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_react_spa(full_path: str):
        """Catch-all: serve o index.html do React para qualquer rota não-API."""
        candidate = _FRONTEND_BUILD / full_path
        if candidate.exists() and candidate.is_file():
            return FileResponse(str(candidate))
        return FileResponse(str(_FRONTEND_BUILD / "index.html"))
