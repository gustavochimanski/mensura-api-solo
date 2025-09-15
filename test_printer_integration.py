"""
Script de teste para integração com Printer API
"""
import asyncio
import httpx
import json
from datetime import datetime


async def test_printer_api_health():
    """Testa se a Printer API está funcionando"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            print(f"✅ Printer API Health: {response.status_code}")
            print(f"   Resposta: {response.json()}")
            return response.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao conectar com Printer API: {e}")
        return False


async def test_printer_api_print():
    """Testa impressão de um pedido de exemplo"""
    try:
        pedido_teste = {
            "numero": 999,
            "cliente": "Cliente Teste",
            "itens": [
                {
                    "descricao": "Hambúrguer Teste",
                    "quantidade": 1,
                    "preco": 25.90
                },
                {
                    "descricao": "Batata Frita",
                    "quantidade": 2,
                    "preco": 8.50
                }
            ],
            "total": 42.90,
            "tipo_pagamento": "DINHEIRO",
            "troco": 7.10
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/print",
                json=pedido_teste
            )
            print(f"✅ Teste de Impressão: {response.status_code}")
            print(f"   Resposta: {response.json()}")
            return response.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao testar impressão: {e}")
        return False


async def test_mensura_api_endpoints():
    """Testa os endpoints da API Mensura"""
    base_url = "http://localhost:8001"  # Ajuste conforme sua configuração
    
    try:
        async with httpx.AsyncClient() as client:
            # Testa status da printer
            response = await client.get(f"{base_url}/api/delivery/pedidos/impressao/status-printer")
            print(f"✅ Status Printer: {response.status_code}")
            print(f"   Resposta: {response.json()}")
            
            # Testa listar pendentes (precisa de empresa_id válido)
            response = await client.get(f"{base_url}/api/delivery/pedidos/impressao/pendentes?empresa_id=1")
            print(f"✅ Listar Pendentes: {response.status_code}")
            print(f"   Resposta: {response.json()}")
            
    except Exception as e:
        print(f"❌ Erro ao testar API Mensura: {e}")


async def main():
    """Executa todos os testes"""
    print("🔍 Testando Integração Printer API + Mensura API")
    print("=" * 50)
    
    print("\n1. Testando Printer API...")
    printer_ok = await test_printer_api_health()
    
    if printer_ok:
        print("\n2. Testando impressão...")
        await test_printer_api_print()
    
    print("\n3. Testando API Mensura...")
    await test_mensura_api_endpoints()
    
    print("\n" + "=" * 50)
    print("✅ Testes concluídos!")


if __name__ == "__main__":
    asyncio.run(main())
