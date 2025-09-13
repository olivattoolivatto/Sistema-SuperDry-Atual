from fastapi import FastAPI, APIRouter, HTTPException, Query, UploadFile, File
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

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

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
REDIRECT_URI = os.getenv('REDIRECT_URI', 'https://laundry-agenda-1.preview.emergentagent.com/agenda')

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
    service_id: str
    service_name: str
    service_code: str
    quantity: float = 1.0
    unit_price: float
    area_m2: Optional[float] = None
    linear_meters: Optional[float] = None
    total_value: float
    observations: Optional[str] = None
    status: ServiceStatus = ServiceStatus.RETIRAR
    is_retoque: bool = False
    execution_location: ExecutionLocation
    # Medidas específicas para diferentes tipos
    width: Optional[float] = None
    height: Optional[float] = None
    diameter: Optional[float] = None
    fabric_folds: Optional[int] = None
    fabric_per_fold: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

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
    
    updated_at: datetime = Field(default_factory=datetime.utcnow)

class BudgetCreate(BaseModel):
    client_id: str
    payment_method: PaymentMethod
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
async def create_client(client_data: ClientCreate):
    """Criar um novo cliente"""
    try:
        # Generate sequential ID
        last_client = await db.clients.find_one(sort=[("created_at", -1)])
        if last_client:
            last_id_num = int(last_client["id"].split("-")[1])
            new_id_num = last_id_num + 1
        else:
            new_id_num = 1
        
        client_dict = client_data.dict()
        client_dict["id"] = f"CLI-{str(new_id_num).zfill(4)}"
        client_dict["created_at"] = datetime.utcnow()
        client_dict["updated_at"] = datetime.utcnow()
        
        client = Client(**client_dict)
        
        await db.clients.insert_one(client.dict())
        return client
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating client: {str(e)}")

@api_router.get("/clients", response_model=List[Client])
async def get_clients(skip: int = 0, limit: int = 100, search: str = None):
    """Listar clientes"""
    try:
        query = {}
        if search:
            query = {
                "$or": [
                    {"name": {"$regex": search, "$options": "i"}},
                    {"id": {"$regex": search, "$options": "i"}},
                    {"phone_primary": {"$regex": search, "$options": "i"}}
                ]
            }
        
        cursor = db.clients.find(query).skip(skip).limit(limit)
        clients = await cursor.to_list(length=limit)
        return [Client(**client) for client in clients]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting clients: {str(e)}")

@api_router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: str):
    """Obter cliente específico"""
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return Client(**client)

@api_router.put("/clients/{client_id}", response_model=Client)
async def update_client(client_id: str, client_data: ClientCreate):
    """Atualizar cliente"""
    client = await db.clients.find_one({"id": client_id})
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    update_data = client_data.dict()
    update_data["updated_at"] = datetime.utcnow()
    
    await db.clients.update_one({"id": client_id}, {"$set": update_data})
    
    updated_client = await db.clients.find_one({"id": client_id})
    return Client(**updated_client)

@api_router.delete("/clients/{client_id}")
async def delete_client(client_id: str):
    """Excluir cliente"""
    result = await db.clients.delete_one({"id": client_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Client not found")
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
async def get_google_auth_url():
    """Get Google OAuth authorization URL"""
    try:
        flow = get_google_auth_flow()
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'
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
        
        # 2. Buscar itens por status (modo híbrido)
        # Itens com status de rua que não foram atribuídos via agenda
        assigned_event_ids = []
        for assignment in assignments:
            assigned_event_ids.extend(assignment.get("event_ids", []))
        
        # Buscar budget items com status RETIRAR, EXECUTAR_NO_LOCAL, ENTREGAR
        # que não estão em assignments
        budgets = await db.budgets.find({}).to_list(None)
        
        for budget in budgets:
            if not budget.get('items'):
                continue
                
            for item in budget['items']:
                if (item.get('status') in ['RETIRAR', 'EXECUTAR_NO_LOCAL', 'ENTREGAR'] and
                    item.get('id') not in assigned_event_ids):
                    
                    # Buscar dados do cliente
                    client = await db.clients.find_one({"id": budget.get('client_id')})
                    
                    status_item = {
                        "id": item.get('id'),
                        "budget_id": budget.get('id'),
                        "client_id": budget.get('client_id'),
                        "client_name": client.get('name') if client else 'Cliente não encontrado',
                        "client_address": client.get('address', {}).get('full_address') if client else '',
                        "client_phone": client.get('phone_primary') if client else '',
                        "service_name": item.get('service_name'),
                        "service_value": item.get('total_value', 0),
                        "status": item.get('status'),
                        "observations": item.get('observations', ''),
                        "internal_observations": budget.get('internal_observations', '')
                    }
                    
                    tasks["status_items"].append(status_item)
        
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
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating assignment: {str(e)}")

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
@api_router.post("/budgets", response_model=Budget)
async def create_budget(budget_data: BudgetCreate):
    """Criar um novo orçamento"""
    try:
        # Verify client exists
        client = await db.clients.find_one({"id": budget_data.client_id})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        # Generate sequential ID
        last_budget = await db.budgets.find_one(sort=[("created_at", -1)])
        if last_budget:
            last_id_num = int(last_budget["id"].split("-")[1])
            new_id_num = last_id_num + 1
        else:
            new_id_num = 1
        
        budget_dict = budget_data.dict()
        budget_dict["id"] = f"ORC-{str(new_id_num).zfill(7)}"
        budget_dict["client_name"] = client["name"]
        budget_dict["created_at"] = datetime.utcnow()
        budget_dict["updated_at"] = datetime.utcnow()
        
        # Process items if provided
        processed_items = []
        if budget_data.items:
            for item_data in budget_data.items:
                # Generate item ID if not provided
                if 'id' not in item_data or not item_data['id']:
                    item_data['id'] = f"ITM-{str(datetime.utcnow().timestamp()).replace('.', '')[:7]}"
                
                # Ensure required fields
                if 'created_at' not in item_data:
                    item_data['created_at'] = datetime.utcnow().isoformat()
                if 'status' not in item_data:
                    item_data['status'] = 'RETIRAR'
                    
                processed_items.append(item_data)
        
        budget_dict['items'] = processed_items
        
        # Calculate totals
        total_value = sum(float(item.get('total_value', 0)) for item in processed_items)
        total_area_m2 = sum(float(item.get('area_m2', 0)) for item in processed_items)
        total_linear_meters = sum(float(item.get('linear_meters', 0)) for item in processed_items)
        total_units = len(processed_items)
        
        budget_dict.update({
            'total_value': total_value,
            'total_area_m2': total_area_m2,
            'total_linear_meters': total_linear_meters,
            'total_units': total_units
        })
        
        budget = Budget(**budget_dict)
        
        await db.budgets.insert_one(budget.dict())
        return budget
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error creating budget: {str(e)}")

@api_router.get("/budgets", response_model=List[Budget])
async def get_budgets(skip: int = 0, limit: int = 100, search: str = None):
    """Listar orçamentos"""
    try:
        query = {}
        if search:
            query = {
                "$or": [
                    {"id": {"$regex": search, "$options": "i"}},
                    {"client_name": {"$regex": search, "$options": "i"}}
                ]
            }
        
        cursor = db.budgets.find(query).skip(skip).limit(limit)
        budgets = await cursor.to_list(length=limit)
        return [Budget(**budget) for budget in budgets]
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error getting budgets: {str(e)}")

@api_router.get("/budgets/{budget_id}", response_model=Budget)
async def get_budget(budget_id: str):
    """Obter orçamento específico"""
    budget = await db.budgets.find_one({"id": budget_id})
    if not budget:
        raise HTTPException(status_code=404, detail="Budget not found")
    return Budget(**budget)

@api_router.put("/budgets/{budget_id}", response_model=Budget)
async def update_budget(budget_id: str, budget_data: BudgetCreate):
    """Atualizar orçamento"""
    try:
        budget = await db.budgets.find_one({"id": budget_id})
        if not budget:
            raise HTTPException(status_code=404, detail="Budget not found")
        
        # Verify client exists
        client = await db.clients.find_one({"id": budget_data.client_id})
        if not client:
            raise HTTPException(status_code=404, detail="Client not found")
        
        update_data = budget_data.dict()
        update_data["client_name"] = client["name"]
        update_data["updated_at"] = datetime.utcnow()
        
        # Process items if provided
        processed_items = []
        if budget_data.items:
            for item_data in budget_data.items:
                # Generate item ID if not provided
                if 'id' not in item_data or not item_data['id']:
                    item_data['id'] = f"ITM-{str(datetime.utcnow().timestamp()).replace('.', '')[:7]}"
                
                # Ensure required fields
                if 'created_at' not in item_data:
                    item_data['created_at'] = datetime.utcnow().isoformat()
                if 'status' not in item_data:
                    item_data['status'] = 'RETIRAR'
                
                processed_items.append(item_data)
        
        update_data['items'] = processed_items
        
        # Calculate totals
        total_value = sum(float(item.get('total_value', 0)) for item in processed_items)
        total_area_m2 = sum(float(item.get('area_m2', 0)) for item in processed_items)
        total_linear_meters = sum(float(item.get('linear_meters', 0)) for item in processed_items)
        total_units = len(processed_items)
        
        update_data.update({
            'total_value': total_value,
            'total_area_m2': total_area_m2,
            'total_linear_meters': total_linear_meters,
            'total_units': total_units
        })
        
        await db.budgets.update_one({"id": budget_id}, {"$set": update_data})
        
        updated_budget = await db.budgets.find_one({"id": budget_id})
        return Budget(**updated_budget)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error updating budget: {str(e)}")

@api_router.delete("/budgets/{budget_id}")
async def delete_budget(budget_id: str):
    """Excluir orçamento"""
    result = await db.budgets.delete_one({"id": budget_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Budget not found")
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
async def get_available_budget_items_for_routes():
    """Get budget items available for routes (status: RETIRAR, EXECUTAR_NO_LOCAL, ENTREGAR)"""
    try:
        # Find budgets with items in route-eligible status
        route_statuses = [ServiceStatus.RETIRAR, ServiceStatus.EXECUTAR_NO_LOCAL, ServiceStatus.ENTREGAR]
        
        pipeline = [
            {"$unwind": "$items"},
            {"$match": {"items.status": {"$in": route_statuses}}},
            {"$lookup": {
                "from": "clients",
                "localField": "client_id", 
                "foreignField": "id",
                "as": "client_info"
            }},
            {"$unwind": "$client_info"},
            {"$project": {
                "budget_id": "$id",
                "client_id": "$client_id",
                "client_name": "$client_name",
                "item": "$items",
                "client_address": "$client_info.address"
            }}
        ]
        
        cursor = db.budgets.aggregate(pipeline)
        results = []
        
        async for doc in cursor:
            item_data = {
                "budget_item_id": doc["item"]["id"],
                "budget_id": doc["budget_id"],
                "client_id": doc["client_id"],
                "client_name": doc["client_name"],
                "service_name": doc["item"]["service_name"],
                "service_code": doc["item"]["service_code"],
                "service_value": doc["item"]["total_value"],
                "status": doc["item"]["status"],
                "neighborhood": doc["client_address"].get("neighborhood", ""),
                "address": doc["client_address"]
            }
            results.append(item_data)
        
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
            
            # Generate stop ID
            last_stop = await db.routes.find_one({"stops.id": {"$exists": True}}, sort=[("created_at", -1)])
            stop_counter = 1
            if last_stop and last_stop.get("stops"):
                for stop in last_stop["stops"]:
                    if stop.get("id", "").startswith("STP-"):
                        try:
                            stop_num = int(stop["id"].split("-")[1])
                            stop_counter = max(stop_counter, stop_num + 1)
                        except:
                            pass
            
            stop_id = f"STP-{str(stop_counter).zfill(7)}"
            
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

@api_router.delete("/routes/{route_id}")
async def delete_route(route_id: str):
    """Delete a route"""
    try:
        result = await db.routes.delete_one({"id": route_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Route not found")
        return {"message": "Route deleted successfully"}
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
async def update_budget_item_status(item_id: str, status: str = Query(...)):
    """Update the status of a specific budget item"""
    try:
        # Validate status
        if status not in [s.value for s in ServiceStatus]:
            raise HTTPException(status_code=400, detail=f"Invalid status. Valid options: {[s.value for s in ServiceStatus]}")
        
        # Find the budget containing this item
        budget = await db.budgets.find_one({"items.id": item_id})
        if not budget:
            raise HTTPException(status_code=404, detail="Budget item not found")
        
        # Update the specific item's status
        result = await db.budgets.update_one(
            {"items.id": item_id},
            {"$set": {"items.$.status": status, "items.$.updated_at": datetime.utcnow().isoformat()}}
        )
        
        if result.modified_count == 0:
            raise HTTPException(status_code=404, detail="Failed to update budget item status")
        
        return {"success": True, "item_id": item_id, "new_status": status}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error updating budget item status: {str(e)}")

@api_router.get("/service-status/options")
async def get_service_status_options():
    """Get all available service status options"""
    return {"status_options": [{"value": status.value, "label": status.value} for status in ServiceStatus]}

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()