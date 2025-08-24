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
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

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
    """Get detailed information about a place"""
    try:
        details = gmaps.place(place_id, language='pt-BR')
        return {"details": details}
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
            spaceAfter=30,
            alignment=1  # Center
        )
        
        # Header
        story.append(Paragraph(f"ORÇAMENTO {budget_id}", title_style))
        story.append(Paragraph("SuperDry Lavanderia de Tapetes & Estofados", styles['Normal']))
        story.append(Spacer(1, 20))
        
        # Client information
        updated_date = budget.get("updated_at", datetime.utcnow())
        if isinstance(updated_date, str):
            updated_date = datetime.fromisoformat(updated_date.replace('Z', '+00:00'))
        formatted_date = updated_date.strftime("%d/%m/%Y")
        
        client_info = f"""
Cliente: {budget.get('client_name', 'N/A')}
Telefone: {client.get('phone_primary', 'N/A')}
Vendedor: {budget.get('salesperson', 'N/A')}
Forma de Pagamento: {budget.get('payment_method', 'N/A')}
Data: {formatted_date}
"""
        story.append(Paragraph(client_info, styles['Normal']))
        
        # Budget observations
        if budget.get('budget_observations'):
            story.append(Paragraph(f"Observações do Orçamento: {budget.get('budget_observations')}", styles['Normal']))
        
        story.append(Spacer(1, 20))
        
        # Services table
        story.append(Paragraph("SERVIÇOS", styles['Heading2']))
        
        table_data = [["Descrição", "Medidas", "Área M²", "Metragem Linear", "Unidade", "Valor"]]
        
        total_value = 0
        for item in budget.get('items', []):
            measures = ""
            if item.get('width') and item.get('height'):
                measures = f"{item.get('width')} x {item.get('height')}"
            elif item.get('diameter'):
                measures = f"Ø {item.get('diameter')}m"
            
            area_m2 = f"{item.get('area_m2', 0):.1f}" if item.get('area_m2', 0) > 0 else "-"
            linear_meters = f"{item.get('linear_meters', 0):.1f}" if item.get('linear_meters', 0) > 0 else "-"
            quantity = f"{item.get('quantity', 1):.0f}"
            value = f"R$ {item.get('total_value', 0):.2f}"
            
            total_value += item.get('total_value', 0)
            
            table_data.append([
                item.get('service_name', 'N/A'),
                measures,
                area_m2,
                linear_meters, 
                quantity,
                value
            ])
        
        # Total row
        table_data.append(["", "", "", "", "TOTAL", f"R$ {total_value:.2f}"])
        
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -2), colors.beige),
            ('BACKGROUND', (0, -1), (-1, -1), colors.lightgrey),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        story.append(table)
        story.append(Spacer(1, 30))
        
        # Signature section
        story.append(Paragraph("_" * 50, styles['Normal']))
        story.append(Paragraph("Assinatura do cliente", styles['Normal']))
        
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

@api_router.post("/budgets/{budget_id}/items")
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