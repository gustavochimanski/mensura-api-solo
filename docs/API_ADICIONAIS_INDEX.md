# 📚 Índice - Documentação de Adicionais e Complementos

## 📖 Documentações Disponíveis

### 1. **API_ADICIONAIS_ADMIN.md** 
Documentação completa para **administradores** com todos os endpoints CRUD:
- ✅ Criar, listar, buscar, atualizar e deletar adicionais
- ✅ Criar, listar, buscar, atualizar e deletar complementos
- ✅ Vincular/desvincular adicionais a complementos
- ✅ Vincular complementos a produtos
- ✅ Gerenciar ordem dos adicionais
- ✅ Autenticação via JWT (Bearer token)

**Use quando**: Precisa gerenciar (criar/editar/deletar) adicionais e complementos.

---

### 2. **API_ADICIONAIS_CLIENT.md**
Documentação para **clientes** com endpoints de leitura:
- ✅ Listar complementos de um produto
- ✅ Listar complementos de um combo
- ✅ Listar complementos de uma receita
- ✅ Autenticação via X-Super-Token

**Use quando**: Precisa apenas consultar complementos e adicionais (sem criar/editar).

---

## 🎯 Qual Documentação Usar?

| Cenário | Documentação |
|---------|--------------|
| Criar/editar/deletar adicionais | **API_ADICIONAIS_ADMIN.md** |
| Criar/editar/deletar complementos | **API_ADICIONAIS_ADMIN.md** |
| Vincular adicionais a complementos | **API_ADICIONAIS_ADMIN.md** |
| Consultar complementos de um produto | **API_ADICIONAIS_CLIENT.md** |
| Consultar complementos de um combo | **API_ADICIONAIS_CLIENT.md** |
| Exibir complementos no app do cliente | **API_ADICIONAIS_CLIENT.md** |

---

## 🔗 Links Rápidos

- [📘 Documentação Admin](./API_ADICIONAIS_ADMIN.md)
- [📗 Documentação Client](./API_ADICIONAIS_CLIENT.md)

---

## 🗄️ Estrutura do Banco

- **Tabela**: `catalogo.adicionais` - Armazena os adicionais (itens independentes)
- **Tabela**: `catalogo.complemento_produto` - Armazena os complementos (grupos)
- **Tabela**: `catalogo.complemento_item_link` - Vínculo N:N entre complementos e adicionais

---

## 🔑 Autenticação

- **Admin**: `Authorization: Bearer {jwt_token}`
- **Client**: `X-Super-Token: {cliente_token}`

---

**Última atualização**: 2024

