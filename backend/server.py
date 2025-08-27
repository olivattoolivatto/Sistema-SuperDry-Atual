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
from datetime import datetime, date
from enum import Enum
import googlemaps
import json
import asyncio
from io import BytesIO
import aiofiles
import re
import requests
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
    order_sequence: int = 0
    created_at: datetime = Field(default_factory=datetime.utcnow)

class Route(BaseModel):
    id: str = Field(default_factory=lambda: f"RTE-{str(uuid.uuid4().int)[:7].zfill(7)}")
    vehicle_type: VehicleType
    planned_date: str  # Format: "YYYY-MM-DD"
    planned_start_time: str  # Format: "HH:MM"
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
                # Get the optimized waypoint order
                waypoints = osrm_result['waypoints']
                optimized_order = []
                
                # Skip first and last (company positions)
                for i, waypoint in enumerate(waypoints[1:-1]):
                    waypoint_index = waypoint.get('waypoint_index', i)
                    if waypoint_index < len(automatica_stops):
                        optimized_order.append(automatica_stops[waypoint_index])
                
                if optimized_order:
                    optimized_automatica = optimized_order
                    print(f"OSRM optimization successful: {len(optimized_order)} stops reordered")
                else:
                    print("OSRM returned empty order, using original")
            else:
                print("OSRM response missing trips data, using original order")
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
    for i, stop in enumerate(final_order):
        stop.order_sequence = i + 1
    
    print(f"Final order: {len(final_order)} stops")
    
    return final_order

class RouteCreate(BaseModel):
    vehicle_type: VehicleType
    planned_date: str  # Format: "YYYY-MM-DD"
    planned_start_time: str
    stops: List[dict] = []  # Will contain budget_item_ids and priorities

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
        item_dict["status"] = ServiceStatus.RETIRAR if service_obj.execution_location == ExecutionLocation.RETIRADA else ServiceStatus.EXECUTAR_NO_LOCAL
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
                service_status=ServiceStatus(budget_item["status"])
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

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()