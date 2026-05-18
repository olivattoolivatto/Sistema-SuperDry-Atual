import asyncio
import json
import sys
from datetime import datetime

# Garante que o Python encontre as pastas do app novo
sys.path.append('/app')
sys.path.append('/app/backend')

try:
    from backend.server import db
except ImportError:
    from server import db

async def importar():
    try:
        print("Lendo o arquivo meus_servicos.json...")
        with open('/app/meus_servicos.json', 'r', encoding='utf-8') as f:
            servicos = json.load(f)
        
        if not servicos:
            print("Nenhum serviço encontrado no arquivo.")
            return
            
        print(f"Encontrados {len(servicos)} serviços para importar.")
        
        # Vamos verificar se o serviço já existe para não duplicar
        for s in servicos:
            # Converte as datas de texto para o formato correto do banco
            if "created_at" in s and isinstance(s["created_at"], str):
                s["created_at"] = datetime.fromisoformat(s["created_at"])
            if "updated_at" in s and isinstance(s["updated_at"], str):
                s["updated_at"] = datetime.fromisoformat(s["updated_at"])
                
            # Procura se já tem um serviço com o mesmo ID (Ex: SRV-0001)
            existente = await db.services.find_one({"id": s["id"]})
            
            if existente:
                print(f"Serviço {s['id']} ({s['name']}) já existe no banco novo. Pulando...")
            else:
                await db.services.insert_one(s)
                print(f"Sucesso: {s['id']} ({s['name']}) importado!")
                
        print('\n=== MIGRAÇÃO CONCLUÍDA COM SUCESSO! ===\n')
    except Exception as e:
        print('\n=== ERRO na importação:', str(e), '===\n')

if __name__ == "__main__":
    asyncio.run(importar())