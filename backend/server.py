from fastapi import FastAPI, APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import FileResponse, StreamingResponse
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
from typing import Tuple
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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
    service_id: str
    service_name: str
    service_code: str
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
    execution_location: ExecutionLocation

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
    salesperson: Salesperson
    internal_observations: Optional[str] = None
    budget_observations: Optional[str] = None
    items: List[BudgetItem] = []
    total_value: float = 0.0
    total_area_m2: float = 0.0
    total_linear_meters: float = 0.0
    total_units: int = 0
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
    budget_item_id: str
    client_id: str
    client_name: str
    service_name: str
    service_value: float
    address: dict  # Contains full_address, latitude, longitude, neighborhood
    priority: Priority = Priority.AUTOMATICA
    estimated_duration: int = 30  # minutes (30 for Retirar/Entregar, 120 for Executar)
    service_status: ServiceStatus
    order_sequence: int = 0  # Optimized route order from OSRM
    delivery_order: int = 0  # Actual delivery sequence (may differ from route order)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Route(BaseModel):
    id: str = Field(default_factory=lambda: f"RTE-{str(uuid.uuid4().int)[:7].zfill(7)}")
    vehicle_type: VehicleType
    planned_date: str  # Format: "YYYY-MM-DD"
    planned_start_time: str  # Format: "HH:MM"
    alias: Optional[str] = None  # Custom route name
    status: RouteStatus = RouteStatus.PLANNED
    stops: List[RouteStop] = []
    total_duration: int = 0  # minutes
    total_distance: float = 0.0  # km
    company_address: dict  # Start/end point
    route_geometry: Optional[dict] = None  # OSRM route data
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_edited_by: Optional[str] = "Sistema"  # Future: user who made last edit

# OSRM Integration Functions
OSRM_BASE_URL = "http://router.project-osrm.org"

# ── Geoapify Integration ──────────────────────────────────────────────────────
GEOAPIFY_API_KEY = os.environ.get("GEOAPIFY_API_KEY", "01c4cd29f11547d49cbcd136694c775c")
GEOAPIFY_ROUTE_PLANNER_URL = "https://api.geoapify.com/v1/routeplanner"


async def calculate_route_geoapify(stops: list, company_coords: tuple, vehicle_type: str = "CARRO") -> dict:
    """Calculate optimized route using Geoapify Route Planner API."""
    try:
        mode = "drive"  # Geoapify uses drive for both car and motorcycle
        company_lon, company_lat = company_coords
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
                "start_location": [company_lon, company_lat],
                "end_location":   [company_lon, company_lat],
                "time_windows":   [[0, 86400]]
            }],
            "jobs": jobs
        }
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


async def optimize_route_with_priorities_geoapify(stops: list, company_coords: tuple, vehicle_type: str = "CARRO"):
    """Optimize route using Geoapify, respecting manual priorities.
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

    if auto_stops:
        try:
            result   = await calculate_route_geoapify(auto_stops, company_coords, vehicle_type)
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
        {"value": "DEBITO",                  "label": "Débito"},
        {"value": "BOLETO",                  "label": "Boleto"},
        {"value": "LINK_PAGAMENTO",          "label": "Link de Pagamento"},
        {"value": "TRANSFERENCIA",           "label": "Transferência"},
        {"value": "PERMUTA",                 "label": "Permuta"},
    ])
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BudgetCreate(BaseModel):
    client_id: str
    payment_method: str          # free string — validated against DB list at runtime
    salesperson: Salesperson
    internal_observations: Optional[str] = None
    budget_observations: Optional[str] = None
    items: Optional[List[dict]] = []

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
    """Hybrid search using Places API and Geocoding API"""
    try:
        results = []
        
        # Search using Places API (for locations, businesses, landmarks)
        try:
            places_response = gmaps.places_autocomplete(
                query, 
                language='pt-BR', 
                components=[{'country': 'BR'}]
            )
            
            # Add Places API results
            if isinstance(places_response, list):
                for place in places_response:
                    if isinstance(place, dict):
                        results.append({
                            **place,
                            'source': 'places'
                        })
        except Exception as places_error:
            print(f"Places API error: {places_error}")
        
        # Search using Geocoding API (for addresses)
        try:
            geocode_response = gmaps.geocode(
                query, 
                language='pt-BR'
            )
            
            # Add unique Geocoding API results
            existing_place_ids = {p.get('place_id') for p in results if p.get('place_id')}
            
            if isinstance(geocode_response, list):
                for geocode in geocode_response:
                    if isinstance(geocode, dict) and geocode.get('place_id') not in existing_place_ids:
                        formatted_address = geocode.get('formatted_address', '')
                        
                        # Parsing baseado no padrão: rua, número - bairro, cidade - estado, CEP, país
                        parts = [p.strip() for p in formatted_address.split(',')]
                        
                        # Bairro
                        neighborhood = None
                        if len(parts) >= 2:
                            first_part = parts[1]
                            if '-' in first_part:
                                neighborhood = first_part.split('-')[1].strip()
                            else:
                                neighborhood = first_part
                        
                        # Cidade e estado
                        city = None
                        state = None
                        if len(parts) >= 3 and '-' in parts[2]:
                            city = parts[2].split('-')[0].strip()
                            state = parts[2].split('-')[1].strip()
                        
                        # Rua (main_text) e complemento (secondary_text)
                        main_text = parts[0] if len(parts) >= 1 else formatted_address
                        secondary_text = ', '.join(parts[1:]) if len(parts) > 1 else ''
                        
                        # Get geometry/coordinates from geocode result
                        geometry = geocode.get('geometry', {})
                        location = geometry.get('location', {})
                        latitude = location.get('lat') if isinstance(location, dict) else None
                        longitude = location.get('lng') if isinstance(location, dict) else None
                        
                        formatted_result = {
                            'place_id': geocode.get('place_id'),
                            'description': formatted_address,
                            'structured_formatting': {
                                'main_text': main_text,
                                'secondary_text': secondary_text
                            },
                            'neighborhood': neighborhood,
                            'city': city,
                            'state': state,
                            'geometry': {
                                'location': {
                                    'lat': latitude,
                                    'lng': longitude
                                }
                            } if latitude and longitude else None,
                            'source': 'geocoding'
                        }
                        results.append(formatted_result)
        except Exception as geocode_error:
            print(f"Geocoding API error: {geocode_error}")
        
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
        # Generate sequential ID
        last_service = await db.services.find_one(sort=[("created_at", -1)])
        if last_service:
            last_id_num = int(last_service["id"].split("-")[1])
            new_id_num = last_id_num + 1
        else:
            new_id_num = 1
        
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
            event = {
                'summary': f'{stop["service_status"]} - {stop["client_name"]}',
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
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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
    date: str = Query(default=datetime.now().strftime('%Y-%m-%d'))
):
    """Get hybrid tasks for technician (agenda + status-based)"""
    try:
        tasks = {
            "agenda_events": [],
            "status_items": [],
            "assignments": []
        }
        
        # 1. Buscar assignments da agenda para o técnico
        assignments_cursor = await db.technician_assignments.find({
            "technician_id": technician_id,
            "assigned_date": date,
            "status": {"$in": ["ASSIGNED", "IN_PROGRESS"]}
        }).to_list(None)
        
        # Convert MongoDB documents to JSON-serializable format
        assignments = []
        for assignment in assignments_cursor:
            # Remove MongoDB ObjectId fields and convert to dict
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
        
        # 2. DESENCAPSULAR ASSIGNMENTS EM ITENS INDIVIDUAIS
        # A lógica do sistema por status funcionava melhor porque trabalhava com budget_items individuais
        # Agora aplicaremos a mesma lógica aos assignments, desencapsulando-os
        for assignment in assignments:
            # Para cada event_id no assignment, criar um item individual como status_items
            for event_id in assignment.get("event_ids", []):
                if event_id.startswith('ITM-'):  # Apenas budget_item_ids válidos
                    # Buscar dados do budget item específico
                    budget_found = None
                    item_found = None
                    
                    budgets = await db.budgets.find({}).to_list(None)
                    for budget in budgets:
                        if budget.get('items'):
                            for item in budget['items']:
                                if item.get('id') == event_id:
                                    budget_found = budget
                                    item_found = item
                                    break
                        if item_found:
                            break
                    
                    if budget_found and item_found:
                        # Buscar dados do cliente
                        client = await db.clients.find_one({"id": budget_found.get('client_id')})
                        
                        # Criar item desencapsulado no formato que funcionava
                        desencapsulated_item = {
                            "id": item_found.get('id'),
                            "budget_id": budget_found.get('id'),
                            "client_id": budget_found.get('client_id'),
                            "client_name": client.get('name') if client else 'Cliente não encontrado',
                            "client_address": client.get('address') if client else {},
                            "client_phone": client.get('phone_primary') if client else '',
                            "service_name": item_found.get('service_name'),
                            "service_value": item_found.get('total_value', 0),
                            "status": item_found.get('status'),
                            "observations": item_found.get('observations', ''),
                            "internal_observations": budget_found.get('internal_observations', ''),
                            "budget_observations": budget_found.get('budget_observations', ''),
                            # Campos extras do assignment para controle
                            "assignment_id": assignment.get("id"),
                            "assignment_type": assignment.get("assignment_type"),
                            "assignment_status": assignment.get("status"),
                            "assigned_date": assignment.get("assigned_date"),
                            "route_id": assignment.get("route_id")
                        }
                        
                        tasks["status_items"].append(desencapsulated_item)
        
        return tasks
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting technician tasks: {str(e)}")

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

@api_router.post("/calendar/events/direct")
async def create_direct_calendar_event(event_request: DirectEventCreate):
    """Create a direct calendar event (not from route)"""
    try:
        # Get credentials from database
        creds_doc = await db.calendar_credentials.find_one({})
        if not creds_doc:
            raise HTTPException(status_code=400, detail="Google Calendar not authenticated")
        
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
            'colorId': '5'  # Amarelo banana para eventos criados manualmente
        }
        
        # Create event in Google Calendar
        google_event = service.events().insert(calendarId='primary', body=event).execute()
        
        # Store event in database
        calendar_event = CalendarEvent(
            id=f"CAL-{str(uuid.uuid4().int)[:7].zfill(7)}",
            route_id=None,  # Não associado a uma rota
            stop_id=None,   # Não associado a um stop
            summary=event['summary'],
            description=event.get('description'),
            location=event.get('location'),
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            google_event_id=google_event['id']
        )
        
        await db.calendar_events.insert_one(calendar_event.dict())
        
        return {
            "message": "Direct calendar event created successfully",
            "event": calendar_event.dict(),
            "google_event_id": google_event['id']
        }
        
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
            
            formatted_events.append({
                'id': event.get('id'),
                'summary': event.get('summary', 'Sem título'),
                'description': event.get('description', ''),
                'location': event.get('location', ''),
                'start_datetime': start_dt.isoformat(),
                'end_datetime': end_dt.isoformat(),
                'color_id': event.get('colorId'),  # Cor do evento no Google Calendar
                'is_system_event': False,  # Evento externo (não criado pelo sistema)
                'google_event_id': event.get('id')
            })
        
        return {"events": formatted_events}
        
    except Exception as e:
        logger.error(f"Error fetching Google Calendar events: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
        
        return {
            "id": event.get('id'),
            "summary": event.get('summary', ''),
            "description": event.get('description', ''),
            "location": event.get('location', ''),
            "start_datetime": start_dt.isoformat(),
            "end_datetime": end_dt.isoformat(),
            "color_id": event.get('colorId'),  # Cor do evento no Google Calendar
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


def calc_budget_totals(items: List[dict]) -> dict:
    return {
        "total_value": sum(float(i.get("total_value", 0) or 0) for i in items),
        "total_area_m2": sum(float(i.get("area_m2", 0) or 0) for i in items),
        "total_linear_meters": sum(float(i.get("linear_meters", 0) or 0) for i in items),
        "total_units": len(items),
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
        budget_dict.update(calc_budget_totals(processed_items))

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
        update_data.update(calc_budget_totals(processed_items))

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
    """Forçar exclusão de orçamento (ADMIN). Limpa vínculos de rota/sessão antes de deletar."""
    if current_user.role != "ADMIN":
        raise HTTPException(status_code=403, detail="Apenas administradores podem forçar exclusão.")
    budget = await db.budgets.find_one({"id": budget_id})
    if not budget:
        raise HTTPException(status_code=404, detail="Orçamento não encontrado.")
    # Limpa current_route_id de qualquer rota que aponte para estes itens
    for it in (budget.get("items") or []):
        route_id = it.get("current_route_id")
        if route_id:
            await db.routes.update_one(
                {"id": route_id},
                {"$pull": {"stops": {"budget_item_id": it["id"]}}}
            )
    await db.budgets.delete_one({"id": budget_id})
    await log_audit("budget", budget_id, "FORCE_DELETE", current_user, {"reason": "admin force delete"})
    return {"message": "Orçamento excluído forçadamente."}

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
    """Gerar mensagem formatada para WhatsApp"""
    try:
        budget = await db.budgets.find_one({"id": budget_id})
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        # Get client info
        client = await db.clients.find_one({"id": budget.get("client_id")})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Format date
        updated_date = budget.get("updated_at", datetime.utcnow())
        if isinstance(updated_date, str):
            updated_date = datetime.fromisoformat(updated_date.replace('Z', '+00:00'))
        formatted_date = updated_date.strftime("%d/%m/%Y")
        
        # Build WhatsApp message
        message = f"""*#### ORÇAMENTO PERSONALIZADO ####*
_SuperDry Lavanderia de Tapetes e Estofados_

Código do Orçamento: {budget_id}
Cliente: {budget.get('client_name', 'N/A')}
Atendente: {budget.get('salesperson', 'N/A')}
Data do Orçamento: {formatted_date}

Quantidade de Itens: {len(budget.get('items', []))} unid."""

        # Add items
        for item in budget.get('items', []):
            item_line = f"- {item.get('service_name', 'N/A')}"
            
            # Add measurements based on service type
            if item.get('area_m2', 0) > 0:
                if item.get('diameter'):
                    # Tapete redondo
                    item_line += f" - Ø{item.get('diameter'):.1f}m - {item.get('area_m2'):.1f} m²"
                elif item.get('width') and item.get('height'):
                    # Tapete retangular
                    item_line += f" - {item.get('width'):.1f} x {item.get('height'):.1f} - {item.get('area_m2'):.1f} m²"
                else:
                    # Apenas área sem medidas específicas
                    item_line += f" - {item.get('area_m2'):.1f} m²"
            elif item.get('linear_meters', 0) > 0:
                # Cortinas - mostrar metragem linear
                if item.get('fabric_folds') and item.get('fabric_per_fold'):
                    # Mostrar cálculo das dobras se disponível
                    item_line += f" - {item.get('fabric_folds'):.0f} dobras x {item.get('fabric_per_fold'):.0f}cm - {item.get('linear_meters'):.1f}m lineares"
                else:
                    # Apenas metragem linear
                    item_line += f" - {item.get('linear_meters'):.1f}m lineares"
            else:
                # Unitário
                quantity = item.get('quantity', 1)
                if quantity > 1:
                    item_line += f" - {quantity:.0f} unid."
                else:
                    item_line += f" - 1 unid."
            
            item_line += f" - R$ {item.get('total_value', 0):.2f}"
            message += f"\n_{item_line}_"
        
        # Add total
        message += f"\n\n*VALOR TOTAL: R$ {budget.get('total_value', 0):.2f}*"
        
        # Add footer - shorter version for WhatsApp
        message += f"""

*PDF com maiores detalhes em anexo!*

_Caso tenha dúvidas, estou à disposição! Agradecemos a confiança._

-> Orçamento válido por até 30 dias.

SuperDry Lavanderia
Instagram: @superdrylavanderia"""

        # Clean phone number for WhatsApp URL
        phone_raw = client.get('phone_primary', '').replace(' ', '').replace('-', '').replace('(', '').replace(')', '').replace('+', '')
        
        # Ensure phone starts with country code
        if not phone_raw.startswith('55'):
            phone_clean = f"55{phone_raw}"
        else:
            phone_clean = phone_raw
        
        # Create WhatsApp URL with proper encoding
        import urllib.parse
        message_encoded = urllib.parse.quote(message, safe='')
        
        # Create two versions - one with text parameter and one without for manual paste
        whatsapp_url = f"https://wa.me/{phone_clean}"
        whatsapp_url_with_text = f"https://wa.me/{phone_clean}?text={message_encoded}"
        
        # Check if URL is too long (WhatsApp limit ~2000 chars)
        if len(whatsapp_url_with_text) > 2000:
            # Provide URL without text parameter for manual copy/paste
            return {
                "message": message,
                "phone": client.get("phone_primary", ""),
                "whatsapp_url": whatsapp_url,
                "whatsapp_url_with_text": None,
                "note": "Mensagem muito longa para URL automática. Use o campo 'message' para copiar e colar manualmente."
            }
        else:
            return {
                "message": message,
                "phone": client.get("phone_primary", ""),
                "whatsapp_url": whatsapp_url_with_text,
                "whatsapp_url_simple": whatsapp_url,
                "note": "Mensagem incluída na URL automaticamente."
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
        
        # Get budget configuration for risk texts
        config = await db.budget_config.find_one({})
        if not config:
            # Create default config if doesn't exist
            config = BudgetConfig().dict()
            await db.budget_config.insert_one(config)
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)
        styles = getSampleStyleSheet()
        story = []
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=10,
            alignment=1  # Center
        )
        
        section_style = ParagraphStyle(
            'SectionHeader',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=12,
            spaceBefore=20,
            textColor=colors.black
        )

        big_style = ParagraphStyle(
            'BigNormal',
            parent=styles['Normal'],
            fontSize=int(styles['Normal'].fontSize * 1.5),   # 50% maior
            leading=int(styles['Normal'].leading * 0.6),     # 40% menor
            alignment=1  # Center
        )
        
        # Header
        story.append(Paragraph(f"ORÇAMENTO {budget_id}", title_style))
        story.append(Paragraph("SuperDry Lavanderia de Tapetes & Estofados", big_style))
        story.append(Spacer(1, 30))
        
        # Client information with logo - using table layout
        updated_date = budget.get("updated_at", datetime.utcnow())
        if isinstance(updated_date, str):
            updated_date = datetime.fromisoformat(updated_date.replace('Z', '+00:00'))
        formatted_date = updated_date.strftime("%d/%m/%Y")
        
        # Create client info as HTML for proper formatting
        client_info_html = f"""
        <b>Cliente:</b> {budget.get('client_name', 'N/A')}<br/>
        <b>Telefone:</b> {client.get('phone_primary', 'N/A')}<br/>
        <b>Vendedor:</b> {budget.get('salesperson', 'N/A')}<br/>
        <b>Forma de Pagamento:</b> {budget.get('payment_method', 'N/A')}<br/>
        <b>Data:</b> {formatted_date}
        """
        
        client_info_paragraph = Paragraph(client_info_html, styles['Normal'])
        
        # Add logo if exists
        logo_path = "/app/backend/logo-superdry.png"
        if os.path.exists(logo_path):
            try:
                # Create logo image with fixed sizing
                logo = Image(logo_path, width=1.1*inch, height=0.88*inch)
                
                # Create table with client info and logo
                info_table_data = [[client_info_paragraph, logo]]
                info_table = Table(info_table_data, colWidths=[4*inch, 2*inch])
                info_table.setStyle(TableStyle([
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
                ]))
                story.append(info_table)
            except Exception as e:
                # Fallback if logo fails to load
                print(f"Warning: Could not load logo: {e}")
                story.append(client_info_paragraph)
        else:
            # No logo file, just add client info
            story.append(client_info_paragraph)
        
        # Budget observations
        if budget.get('budget_observations'):
            story.append(Paragraph(f"<b>Observações do Orçamento:</b> {budget.get('budget_observations')}", styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Section 1: Services table
        story.append(Paragraph("1. SERVIÇOS", section_style))

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

                # Determine service category for risk texts
                service_name = (item.get('service_name') or '').upper()
                if any(word in service_name for word in ['SOFÁ', 'CADEIRA', 'POLTRONA', 'ALMOFADA', 'ESTOFADO']):
                        service_categories.add('risks_estofados')
                elif any(word in service_name for word in ['COLCHÃO', 'COLCHAO']):
                        service_categories.add('risks_colchoes')
                elif 'BOX' in service_name:
                        service_categories.add('risks_box')
                elif any(word in service_name for word in ['TAPETE', 'CARPETE']) and 'LOCAL' in service_name:
                        service_categories.add('risks_carpetes_tapetes_local')
                elif any(word in service_name for word in ['TAPETE', 'CARPETE']):
                        service_categories.add('risks_tapetes')
                elif 'CORTINA' in service_name:
                        service_categories.add('risks_cortinas')
                elif 'PERSIANA' in service_name:
                        service_categories.add('risks_persianas')
                elif any(word in service_name for word in ['CARRINHO', 'CADEIRINHA', 'BEBÊ', 'BEBE', 'INFANTIL']):
                        service_categories.add('risks_itens_infantis')
                elif any(word in service_name for word in ['VEÍCULO', 'VEICULO', 'BANCO', 'CARRO']):
                        service_categories.add('risks_veiculos')
                elif 'IMPERMEABILIZAÇÃO' in service_name or 'IMPERMEABILIZACAO' in service_name:
                        service_categories.add('risks_impermeabilizacao')
                else:
                        service_categories.add('risks_outros_itens')

                table_data.append([
                        Paragraph(item.get('service_name') or 'N/A', centered_style),
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
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
                ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
                ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(table)
        story.append(Spacer(1, 30))
        
        # Section 2: Risk texts based on service categories
        if service_categories:
            story.append(Paragraph("2. RISCOS E ADVERTÊNCIAS", section_style))
            
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
                    story.append(Paragraph(f"<b>{category_name}:</b>", styles['Normal']))
                    story.append(Paragraph(formatted_text, styles['Normal']))
                    story.append(Spacer(1, 10))
        
        # Section 3: General conditions
        general_conditions = config.get('general_conditions', '')
        if general_conditions:
            story.append(Paragraph("3. CONDIÇÕES GERAIS", section_style))
            formatted_conditions = format_html_text(general_conditions)
            story.append(Paragraph(formatted_conditions, styles['Normal']))
            story.append(Spacer(1, 20))
        
        # Signature section
        story.append(Spacer(1, 30))
        story.append(Paragraph("_" * 60, styles['Normal']))
        story.append(Paragraph("Assinatura do cliente", styles['Normal']))
        
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

@api_router.get("/payment-methods")
async def get_payment_methods():
    """Retorna lista de formas de pagamento configuradas no sistema."""
    config = await db.system_config.find_one({})
    if config and config.get("payment_methods"):
        return {"payment_methods": config["payment_methods"]}
    # fallback padrão
    default = SystemConfig()
    return {"payment_methods": default.payment_methods}

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
@api_router.get("/budget-items/available-for-routes")
async def get_available_budget_items_for_routes(current_user: UserPublic = Depends(get_current_user)):
    """Itens disponíveis para rota: status route-eligible + sem rota corrente."""
    try:
        route_statuses = [
            ServiceStatus.RETIRAR.value,
            ServiceStatus.EXECUTAR_NO_LOCAL.value,
            ServiceStatus.ENTREGAR.value,
        ]
        pipeline = [
            {"$unwind": "$items"},
            {"$match": {
                "items.status": {"$in": route_statuses},
                "$or": [
                    {"items.current_route_id": None},
                    {"items.current_route_id": {"$exists": False}},
                ],
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
            status = item.get("status")
            # Endereço específico por etapa, com fallback no cliente
            if status == ServiceStatus.RETIRAR.value:
                addr = item.get("pickup_address") or doc.get("client_address") or {}
            elif status == ServiceStatus.ENTREGAR.value:
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
                    else item.get("scheduled_delivery_date") if status == ServiceStatus.ENTREGAR.value
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
        
        # Merge stops at same address (same lat/lng)
        merged_stops = []
        address_groups = {}
        
        for stop in optimized_stops:
            address_key = f"{stop.address['latitude']},{stop.address['longitude']}"
            if address_key in address_groups:
                # Merge with existing stop - add 60 minutes for additional service
                existing_stop = address_groups[address_key]
                existing_stop.estimated_duration += 60
                existing_stop.service_name += f" + {stop.service_name}"
                existing_stop.service_value += stop.service_value
            else:
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
async def optimize_route_geoapify_endpoint(route_id: str):
    """Optimize route using Geoapify Route Planner API"""
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
            await optimize_route_with_priorities_geoapify(stops, company_coords, vehicle_type)

        # Merge stops at same address
        merged_stops    = []
        address_groups  = {}
        for stop in optimized_stops:
            key = f"{stop.address['latitude']},{stop.address['longitude']}"
            if key in address_groups:
                address_groups[key].estimated_duration += 60
                address_groups[key].service_name       += f" + {stop.service_name}"
                address_groups[key].service_value      += stop.service_value
            else:
                address_groups[key] = stop
                merged_stops.append(stop)

        # Geoapify 'time' already includes service time at stops + travel time
        # Use it directly; fallback to service time sum if Geoapify had no data
        if travel_min > 0:
            total_min = int(travel_min)
        else:
            total_min = sum(s.estimated_duration for s in merged_stops)

        await db.routes.update_one(
            {"id": route_id},
            {"$set": {
                "stops":          [s.dict() for s in merged_stops],
                "total_duration": total_min,
                "total_distance": round(dist_km, 2),
                "route_geometry": route_geometry,
                "updated_at":     datetime.utcnow(),
                "last_edited_by": "Geoapify"
            }}
        )
        return {
            "message":                "Route optimized successfully with Geoapify",
            "total_stops":            len(merged_stops),
            "total_duration_minutes": total_min,
            "total_distance_km":      round(dist_km, 2),
            "geoapify_status":        "success" if dist_km > 0 else "fallback"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error optimizing route with Geoapify: {str(e)}")


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
    await db.users.insert_one(user.dict())
    await log_audit("user", user.id, "CREATE", current_user, {"after": {**user.dict(), "password_hash": "***"}})
    return UserPublic(**{k: v for k, v in user.dict().items() if k != "password_hash"})


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
    if payload.email is not None: update_data["email"] = payload.email.strip().lower()
    if payload.role is not None: update_data["role"] = payload.role.value if hasattr(payload.role, "value") else payload.role
    if payload.is_active is not None: update_data["is_active"] = payload.is_active
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
        route_statuses = [
            ServiceStatus.RETIRAR.value,
            ServiceStatus.EXECUTAR_NO_LOCAL.value,
            ServiceStatus.ENTREGAR.value,
        ]
        items_pending_routes = 0
        async for b in db.budgets.find({"items.status": {"$in": route_statuses}}):
            for it in (b.get("items") or []):
                if it.get("status") in route_statuses and not it.get("current_route_id"):
                    items_pending_routes += 1

        # 2) Orçamentos ativos (com algum item pendente de rota)
        active_budgets = 0
        async for b in db.budgets.find({}):
            items = b.get("items") or []
            has_pending = any(
                (it.get("status") in route_statuses and not it.get("current_route_id"))
                for it in items
            )
            if has_pending:
                active_budgets += 1

        # 3) Execução de hoje (assignments do técnico)
        execution_today = 0
        async for a in db.technician_assignments.find({"assigned_date": today, "status": {"$ne": "CANCELLED"}}):
            execution_today += len(a.get("event_ids") or [])

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

        # 5) Pendências financeiras (itens com payment_status != PAGO e != CORTESIA)
        pending_payment_statuses = ["PENDENTE", "PARCIAL", "INADIMPLENTE"]
        financial_pending = 0
        async for b in db.budgets.find({"items.payment_status": {"$in": pending_payment_statuses}}):
            for it in (b.get("items") or []):
                if it.get("payment_status", "PENDENTE") in pending_payment_statuses:
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
    await _update_item_fields(item_id, {"status": new_status}, current_user)
    await _append_to_item_array(item_id, "status_history", entry)
    await log_audit("item", item_id, "STATUS_CHANGE", current_user, {
        "from": item.get("status"), "to": new_status, "notes": entry["notes"],
    })
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

    record = {
        "id": f"PAY-{uuid.uuid4().hex[:10]}",
        "method": method,
        "value": value,
        "paid_at": datetime.utcnow().isoformat(),
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

    await log_audit("item", item_id, "PAYMENT", current_user, {
        "method": method, "value": value, "paid_total": paid_total, "new_status": payment_status,
    })
    return {"success": True, "record": record, "paid_value": paid_total, "payment_status": payment_status}


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

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()