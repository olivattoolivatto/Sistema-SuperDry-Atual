"""
Script para corrigir a duplicata SRV-0002 na VM.

O que aconteceu:
- SRV-0002 original = "Lavagem de Tapete M²" (TAPETES)
- O novo serviço "limpeza de sofá tipo ilha" recebeu ID SRV-0002 por bug
  na geração de IDs (usava o created_at mais recente, não o maior número)
- O insert_one do MongoDB não sobrescreve — ambos existem como documentos distintos

Este script:
1. Mostra os dois documentos com id = SRV-0002
2. Renomeia o novo serviço (sofá ilha) para o próximo ID disponível
3. Confirma o resultado

Execute na VM:
    cd /home/opc/superdry/backend
    python3 fix_srv0002_duplicate.py
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

load_dotenv()

MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "superdry")


async def main():
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    print("=" * 60)
    print("SuperDry — Correção SRV-0002 duplicado")
    print("=" * 60)

    # 1. Busca todos os documentos com id = SRV-0002
    duplicates = await db.services.find({"id": "SRV-0002"}).to_list(length=None)
    print(f"\nDocumentos com id='SRV-0002' encontrados: {len(duplicates)}")
    for i, s in enumerate(duplicates):
        print(f"\n  [{i+1}] _id: {s['_id']}")
        print(f"       name: {s.get('name')}")
        print(f"       category: {s.get('category')}")
        print(f"       service_type: {s.get('service_type')}")
        print(f"       created_at: {s.get('created_at')}")
        print(f"       is_active: {s.get('is_active')}")

    if len(duplicates) < 2:
        print("\n✅ Não há duplicata. Nada a corrigir.")
        client.close()
        return

    # 2. Identifica qual é o original (TAPETES) e qual é o novo (ESTOFADOS/sofá ilha)
    original = next((s for s in duplicates if s.get("category") == "TAPETES"), None)
    novo = next((s for s in duplicates if s.get("category") != "TAPETES"), None)

    if not original or not novo:
        print("\n⚠️  Não foi possível identificar automaticamente qual é o original.")
        print("    Verifique manualmente e ajuste o script.")
        client.close()
        return

    print(f"\n✅ Original identificado: '{original['name']}' (_id: {original['_id']})")
    print(f"⚠️  Duplicata a renomear: '{novo['name']}' (_id: {novo['_id']})")

    # 3. Encontra o próximo ID disponível
    all_services = await db.services.find(
        {"id": {"$regex": r"^SRV-\d+$"}}, {"id": 1}
    ).to_list(length=None)
    used_nums = set()
    for s in all_services:
        try:
            used_nums.add(int(s["id"].split("-")[1]))
        except Exception:
            pass

    next_num = 1
    while next_num in used_nums:
        next_num += 1
    new_id = f"SRV-{str(next_num).zfill(4)}"

    print(f"\n🔢 Próximo ID disponível: {new_id}")
    confirm = input(f"\nRenomear '{novo['name']}' de SRV-0002 para {new_id}? [s/N] ").strip().lower()

    if confirm != 's':
        print("Operação cancelada.")
        client.close()
        return

    # 4. Atualiza o documento novo com o ID correto
    from datetime import datetime
    result = await db.services.update_one(
        {"_id": novo["_id"]},
        {"$set": {"id": new_id, "updated_at": datetime.utcnow()}}
    )

    if result.modified_count == 1:
        print(f"\n✅ Sucesso! '{novo['name']}' agora tem ID {new_id}")
        print(f"   SRV-0002 continua sendo: '{original['name']}' (TAPETES)")
    else:
        print("\n❌ Falha ao atualizar. Verifique manualmente.")

    # 5. Verifica resultado final
    remaining = await db.services.find({"id": "SRV-0002"}).to_list(length=None)
    print(f"\nDocumentos com id='SRV-0002' após correção: {len(remaining)}")
    for s in remaining:
        print(f"  - {s['name']} ({s['category']})")

    client.close()
    print("\nConcluído.")


if __name__ == "__main__":
    asyncio.run(main())
