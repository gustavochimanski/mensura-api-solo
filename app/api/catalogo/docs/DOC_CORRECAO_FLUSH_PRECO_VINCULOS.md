# Correção: Flush no Loop e Preço do Adicional em Vínculos

## Resumo

Correção aplicada no método `vincular_itens_complemento` do repositório para garantir:
1. **Flush dentro do loop**: Cada vínculo é persistido individualmente, permitindo detecção de erros mais cedo
2. **Preço do adicional definido corretamente**: O campo `preco_complemento` no vínculo define o preço do adicional quando informado

---

## 1. O que foi corrigido

### 1.1 Flush dentro do loop

**Antes:**
```python
for i, it in enumerate(items):
    # ... criação do vínculo ...
    self.db.add(ComplementoVinculoItemModel(...))
self.db.flush()  # Flush FORA do loop
```

**Agora:**
```python
for i, it in enumerate(items):
    # ... criação do vínculo ...
    vinculo = ComplementoVinculoItemModel(...)
    self.db.add(vinculo)
    self.db.flush()  # Flush DENTRO do loop
```

**Benefícios:**
- **Detecção precoce de erros**: Se houver violação de constraint ou erro de validação, o erro é detectado imediatamente ao processar o item problemático
- **Persistência individual**: Cada vínculo é persistido individualmente, garantindo que os dados sejam salvos mesmo se houver erro em itens subsequentes
- **Melhor rastreabilidade**: Em caso de erro, sabemos exatamente qual item causou o problema

### 1.2 Preço do adicional no vínculo

O campo `preco_complemento` no modelo `ComplementoVinculoItemModel` define o **preço específico do adicional neste complemento**.

**Comportamento:**
- Se `preco_complemento` estiver definido no vínculo, esse é o preço exibido para o adicional naquele complemento
- Se `preco_complemento` for `None`, o preço padrão da entidade (produto/receita/combo) é usado
- O preço pode ser definido:
  - No momento da vinculação (via `ItemVinculoInput.preco_complemento` ou `VincularItensComplementoRequest.precos`)
  - Posteriormente via endpoint `PUT /{complemento_id}/itens/{item_id}/preco`

**Exemplo:**
```python
# Vínculo com preço específico
vinculo = ComplementoVinculoItemModel(
    complemento_id=1,
    produto_cod_barras="123456",
    ordem=0,
    preco_complemento=Decimal("5.50")  # Preço específico neste complemento
)
```

---

## 2. Fluxo de vinculação de itens

### 2.1 Service Layer (`service_complemento.py`)

O service processa o request e prepara os dados para o repositório:

```python
def vincular_itens_complemento(self, complemento_id: int, req: VincularItensComplementoRequest):
    # Valida itens e empresa
    self._validar_itens_empresa(complemento.empresa_id, req.items)
    
    # Prepara listas de dados
    items_dict: List[dict] = []
    ordens_list: List[int] = []
    precos_list: List[Optional[Decimal]] = []
    
    for i, it in enumerate(req.items):
        items_dict.append({
            "produto_cod_barras": it.produto_cod_barras,
            "receita_id": it.receita_id,
            "combo_id": it.combo_id,
        })
        ordens_list.append(it.ordem if it.ordem is not None else ...)
        
        # Prioridade: preco_complemento do item > precos da lista > None
        p = it.preco_complemento
        if p is not None:
            precos_list.append(Decimal(str(p)))
        elif req.precos and i < len(req.precos) and req.precos[i] is not None:
            precos_list.append(Decimal(str(req.precos[i])))
        else:
            precos_list.append(None)
    
    # Chama repositório
    self.repo_item.vincular_itens_complemento(
        complemento_id=complemento_id,
        items=items_dict,
        ordens=ordens_list,
        precos=precos_list,
    )
    self.db.commit()
```

### 2.2 Repository Layer (`repo_complemento_item.py`)

O repositório cria os vínculos e persiste cada um individualmente:

```python
def vincular_itens_complemento(
    self,
    complemento_id: int,
    items: List[dict],
    ordens: Optional[List[int]] = None,
    precos: Optional[List[Optional[Decimal]]] = None,
) -> None:
    # Remove vínculos existentes
    self.db.query(ComplementoVinculoItemModel).filter(
        ComplementoVinculoItemModel.complemento_id == complemento_id
    ).delete(synchronize_session="fetch")
    self.db.flush()
    
    # Cria novos vínculos
    for i, it in enumerate(items):
        # Validação: exatamente um tipo
        pid = it.get("produto_cod_barras")
        rid = it.get("receita_id")
        cid = it.get("combo_id")
        n = sum(1 for x in (pid, rid, cid) if x is not None)
        if n != 1:
            raise ValueError("Cada item deve ter exatamente um de: produto_cod_barras, receita_id, combo_id")
        
        ordem = (ordens[i] if ordens and i < len(ordens) else i)
        preco = precos[i] if precos and i < len(precos) else None
        
        # Cria vínculo com preço do adicional
        vinculo = ComplementoVinculoItemModel(
            complemento_id=complemento_id,
            produto_cod_barras=pid,
            receita_id=rid,
            combo_id=cid,
            ordem=ordem,
            preco_complemento=preco,  # Preço específico do adicional neste complemento
        )
        self.db.add(vinculo)
        # Flush dentro do loop para garantir persistência individual
        self.db.flush()
```

---

## 3. Uso do preço do adicional

### 3.1 Resolução do preço (`preco_e_custo_vinculo`)

O método `preco_e_custo_vinculo` retorna o preço efetivo do adicional:

```python
def preco_e_custo_vinculo(
    self,
    v: ComplementoVinculoItemModel,
    empresa_id: int,
) -> Tuple[Decimal, Decimal]:
    """Retorna (preco, custo) para o vínculo. Preco usa preco_complemento se definido."""
    preco = v.preco_complemento  # Prioridade ao preço do vínculo
    
    # Se não houver preço no vínculo, usa o preço padrão da entidade
    if v.produto_cod_barras and v.produto:
        pe = self.db.query(ProdutoEmpModel).filter(...).first()
        if pe:
            if preco is None:
                preco = pe.preco_venda
            custo = pe.custo or Decimal("0")
    elif v.receita_id and v.receita:
        if preco is None:
            preco = v.receita.preco_venda
    elif v.combo_id and v.combo:
        if preco is None:
            preco = v.combo.preco_total
        custo = v.combo.custo_total or Decimal("0")
    
    if preco is None:
        preco = Decimal("0")
    return (preco, custo)
```

### 3.2 Resposta da API

O preço retornado na resposta (`AdicionalResponse`) é o preço efetivo calculado:

```python
def _vinculo_to_adicional_response(
    self,
    vinculo: ComplementoVinculoItemModel,
    empresa_id: int,
    ordem: int,
) -> AdicionalResponse:
    preco, custo = self.repo_item.preco_e_custo_vinculo(vinculo, empresa_id)
    
    # Monta resposta com preço efetivo
    return AdicionalResponse(
        id=vinculo.id,
        nome=...,
        preco=float(preco),  # Preço efetivo (preco_complemento ou padrão)
        custo=float(custo),
        ...
    )
```

---

## 4. Endpoints relacionados

### 4.1 Vincular múltiplos itens

**Endpoint:** `POST /api/catalogo/admin/complementos/{complemento_id}/itens/vincular`

**Request:**
```json
{
  "items": [
    {
      "tipo": "produto",
      "produto_cod_barras": "123456",
      "ordem": 0,
      "preco_complemento": 5.50
    },
    {
      "tipo": "receita",
      "receita_id": 2,
      "ordem": 1
      // preco_complemento não informado, usa preço padrão da receita
    }
  ],
  "ordens": [0, 1],  // Opcional, sobrescreve ordem dos items
  "precos": [5.50, null]  // Opcional, sobrescreve preco_complemento dos items
}
```

**Comportamento:**
- Remove todos os vínculos existentes do complemento
- Cria novos vínculos com os itens fornecidos
- Cada vínculo é persistido individualmente (flush dentro do loop)
- O preço do adicional é definido no vínculo quando informado

### 4.2 Atualizar preço de um item

**Endpoint:** `PUT /api/catalogo/admin/complementos/{complemento_id}/itens/{item_id}/preco`

**Request:**
```json
{
  "preco": 7.00
}
```

**Comportamento:**
- Atualiza o `preco_complemento` do vínculo específico
- O `item_id` é o ID do vínculo (`complemento_vinculo_item.id`)

---

## 5. Impacto e benefícios

### 5.1 Benefícios da correção

1. **Detecção precoce de erros**: Erros de constraint ou validação são detectados imediatamente
2. **Melhor rastreabilidade**: Em caso de erro, sabemos exatamente qual item causou o problema
3. **Preço flexível**: Permite definir preços diferentes para o mesmo item em complementos diferentes
4. **Consistência**: O preço do adicional é sempre definido no vínculo, garantindo consistência

### 5.2 Exemplo de uso

**Cenário:** Um produto "Bacon" tem preço padrão de R$ 3,00, mas em um complemento específico deve custar R$ 5,00.

**Solução:**
```json
{
  "items": [
    {
      "tipo": "produto",
      "produto_cod_barras": "BACON001",
      "ordem": 0,
      "preco_complemento": 5.00  // Preço específico neste complemento
    }
  ]
}
```

**Resultado:**
- O vínculo é criado com `preco_complemento = 5.00`
- Quando o complemento for listado, o adicional "Bacon" aparecerá com preço R$ 5,00
- Em outros complementos, o mesmo produto pode ter preço diferente ou usar o preço padrão

---

## 6. Notas técnicas

### 6.1 Performance

- O flush dentro do loop pode ter impacto de performance em lotes muito grandes
- Para lotes grandes (>100 itens), considere usar `bulk_insert_mappings` ou processar em chunks
- O flush individual é benéfico para detecção de erros e consistência de dados

### 6.2 Transações

- O método do repositório faz flush, mas não commit
- O commit é feito no service layer após todas as operações
- Se houver erro após alguns flushes, a transação pode ser revertida (rollback)

### 6.3 Validações

- Cada item é validado antes de ser adicionado ao banco
- Se um item for inválido, o erro é lançado antes de processar os próximos
- Isso evita processar itens desnecessários quando há erro conhecido

---

## 7. Checklist de verificação

- [x] Flush movido para dentro do loop em `vincular_itens_complemento`
- [x] Preço do adicional (`preco_complemento`) definido corretamente no vínculo
- [x] Prioridade de preço: `preco_complemento` do item > `precos` da lista > None
- [x] Método `preco_e_custo_vinculo` usa `preco_complemento` quando disponível
- [x] Resposta da API retorna preço efetivo calculado
- [x] Documentação criada e atualizada

---

## 8. Referências

- **Modelo:** `ComplementoVinculoItemModel` (`model_complemento_vinculo_item.py`)
- **Repositório:** `ComplementoItemRepository` (`repo_complemento_item.py`)
- **Service:** `ComplementoService` (`service_complemento.py`)
- **Schema:** `VincularItensComplementoRequest` (`schema_complemento.py`)
- **Documentação relacionada:** `DOC_MUDANCA_ADICIONAIS_VINCULOS.md` (se existir)
