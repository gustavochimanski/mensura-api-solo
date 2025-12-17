# Guia de Implementação: Google Maps no Frontend

## 🔒 Segurança

**IMPORTANTE**: O backend NÃO expõe a API key do Google Maps. Cada aplicação (frontend) deve ter sua própria API key do Google Maps configurada diretamente no frontend.

### Por que isso é mais seguro?

1. **Isolamento**: A API key do backend fica protegida e só é usada para operações server-side
2. **Controle de acesso**: Cada frontend tem sua própria key com restrições específicas
3. **Limitação de danos**: Se uma key for comprometida, apenas um frontend é afetado

---

## 📋 Pré-requisitos

1. **Criar API Key no Google Cloud Console**:
   - Acesse [Google Cloud Console](https://console.cloud.google.com/)
   - Crie um projeto ou selecione um existente
   - Vá em "APIs & Services" > "Credentials"
   - Crie uma nova API Key
   - **IMPORTANTE**: Configure restrições de HTTP referrer para aceitar apenas seu domínio:
     - Exemplo: `https://seusite.com/*`
     - Exemplo: `https://*.seusite.com/*` (para subdomínios)
   - Habilite as seguintes APIs:
     - Maps JavaScript API
     - Geocoding API (opcional, se quiser usar direto)
     - Places API (opcional, se quiser usar direto)

2. **Configurar no Frontend**:
   - Adicione a API key como variável de ambiente no frontend
   - Exemplo: `VITE_GOOGLE_MAPS_API_KEY` ou `NEXT_PUBLIC_GOOGLE_MAPS_API_KEY`

---

## 🚀 Endpoints do Backend Disponíveis

Todos os endpoints requerem autenticação via header `X-Super-Token` do cliente.

### 1. Buscar Endereços por Texto

**Endpoint**: `GET /api/localizacao/client/buscar-endereco`

**Query Parameters**:
- `text` (obrigatório): Texto para buscar endereços
- `max_results` (opcional, padrão: 10): Número máximo de resultados (1-10)

**Exemplo de Requisição**:
```typescript
const response = await fetch(
  `${API_BASE_URL}/api/localizacao/client/buscar-endereco?text=Rua das Flores, 123&max_results=5`,
  {
    headers: {
      'X-Super-Token': clienteSuperToken,
      'Content-Type': 'application/json'
    }
  }
);

const enderecos = await response.json();
```

**Resposta**:
```json
[
  {
    "estado": "São Paulo",
    "codigo_estado": "SP",
    "cidade": "São Paulo",
    "bairro": "Centro",
    "logradouro": "Rua das Flores",
    "numero": "123",
    "cep": "01310-100",
    "latitude": -23.5505,
    "longitude": -46.6333,
    "endereco_formatado": "Rua das Flores, 123 - Centro, São Paulo - SP, 01310-100"
  }
]
```

### 2. Geocodificação Reversa (Coordenadas → Endereço)

**Endpoint**: `POST /api/localizacao/client/geocodificar-reversa`

**Body**:
```json
{
  "latitude": -23.5505,
  "longitude": -46.6333
}
```

**Exemplo de Requisição**:
```typescript
const response = await fetch(
  `${API_BASE_URL}/api/localizacao/client/geocodificar-reversa`,
  {
    method: 'POST',
    headers: {
      'X-Super-Token': clienteSuperToken,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      latitude: -23.5505,
      longitude: -46.6333
    })
  }
);

const endereco = await response.json();
```

**Resposta**: Mesmo formato do endpoint de busca de endereços.

### 3. Listar Endereços do Cliente

**Endpoint**: `GET /api/cadastros/client/enderecos`

**Resposta**:
```json
[
  {
    "id": 1,
    "cliente_id": 123,
    "logradouro": "Rua das Flores",
    "numero": "123",
    "complemento": "Apto 45",
    "bairro": "Centro",
    "cidade": "São Paulo",
    "estado": "SP",
    "cep": "01310-100",
    "ponto_referencia": "Próximo ao mercado",
    "latitude": -23.5505,
    "longitude": -46.6333,
    "is_principal": true
  }
]
```

### 4. Criar/Atualizar Endereço

**Endpoint**: `PUT /api/cadastros/client/enderecos/{endereco_id}` ou `POST /api/cadastros/client/enderecos`

**Body para criar/atualizar**:
```json
{
  "logradouro": "Rua das Flores",
  "numero": "123",
  "complemento": "Apto 45",
  "bairro": "Centro",
  "cidade": "São Paulo",
  "estado": "SP",
  "cep": "01310-100",
  "ponto_referencia": "Próximo ao mercado",
  "latitude": -23.5505,
  "longitude": -46.6333,
  "is_principal": false
}
```

---

## 🗺️ Implementação do Mapa Interativo

### Passo 1: Instalar Dependências

**React**:
```bash
npm install @react-google-maps/api
# ou
yarn add @react-google-maps/api
```

**Vue**:
```bash
npm install @googlemaps/js-api-loader
# ou
yarn add @googlemaps/js-api-loader
```

**Vanilla JS**: Use a biblioteca diretamente via CDN.

### Passo 2: Carregar Google Maps API

**React com @react-google-maps/api**:
```tsx
import { GoogleMap, LoadScript, Marker, useJsApiLoader } from '@react-google-maps/api';

const libraries = ['places'];

function MapComponent({ onLocationChange, initialLocation }) {
  const { isLoaded } = useJsApiLoader({
    id: 'google-map-script',
    googleMapsApiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY, // ou process.env.REACT_APP_GOOGLE_MAPS_API_KEY
    libraries
  });

  const [map, setMap] = useState(null);
  const [markerPosition, setMarkerPosition] = useState(
    initialLocation || { lat: -15.7975, lng: -47.8919 }
  );

  const onMapLoad = (mapInstance) => {
    setMap(mapInstance);
  };

  const onMarkerDragEnd = async (e) => {
    const newPosition = {
      lat: e.latLng.lat(),
      lng: e.latLng.lng()
    };
    
    setMarkerPosition(newPosition);

    // Chama geocodificação reversa do backend
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/localizacao/client/geocodificar-reversa`,
        {
          method: 'POST',
          headers: {
            'X-Super-Token': clienteSuperToken,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            latitude: newPosition.lat,
            longitude: newPosition.lng
          })
        }
      );

      const endereco = await response.json();
      
      // Chama callback com novo endereço
      if (onLocationChange) {
        onLocationChange({
          ...endereco,
          latitude: newPosition.lat,
          longitude: newPosition.lng
        });
      }
    } catch (error) {
      console.error('Erro ao obter endereço:', error);
    }
  };

  if (!isLoaded) {
    return <div>Carregando mapa...</div>;
  }

  return (
    <GoogleMap
      mapContainerStyle={{ width: '100%', height: '400px' }}
      center={markerPosition}
      zoom={15}
      onLoad={onMapLoad}
      onClick={(e) => {
        // Permite clicar no mapa para mover o marcador
        const newPosition = {
          lat: e.latLng.lat(),
          lng: e.latLng.lng()
        };
        setMarkerPosition(newPosition);
        onMarkerDragEnd({ latLng: { lat: () => newPosition.lat, lng: () => newPosition.lng } });
      }}
    >
      <Marker
        position={markerPosition}
        draggable={true}
        onDragEnd={onMarkerDragEnd}
        title="Arraste para ajustar a localização"
      />
    </GoogleMap>
  );
}
```

**Vue 3**:
```vue
<template>
  <div ref="mapContainer" style="width: 100%; height: 400px;"></div>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { Loader } from '@googlemaps/js-api-loader';

const props = defineProps({
  initialLocation: {
    type: Object,
    default: () => ({ lat: -15.7975, lng: -47.8919 })
  },
  onLocationChange: Function
});

const mapContainer = ref(null);
let map = null;
let marker = null;

onMounted(async () => {
  const loader = new Loader({
    apiKey: import.meta.env.VITE_GOOGLE_MAPS_API_KEY,
    version: 'weekly',
    libraries: ['places']
  });

  const { Map } = await loader.importLibrary('maps');
  const { Marker } = await loader.importLibrary('marker');

  map = new Map(mapContainer.value, {
    center: props.initialLocation,
    zoom: 15
  });

  marker = new Marker({
    position: props.initialLocation,
    map: map,
    draggable: true,
    title: 'Arraste para ajustar a localização'
  });

  marker.addListener('dragend', async (e) => {
    const position = marker.getPosition();
    const newLocation = {
      lat: position.lat(),
      lng: position.lng()
    };

    // Chama geocodificação reversa
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/localizacao/client/geocodificar-reversa`,
        {
          method: 'POST',
          headers: {
            'X-Super-Token': clienteSuperToken,
            'Content-Type': 'application/json'
          },
          body: JSON.stringify(newLocation)
        }
      );

      const endereco = await response.json();
      
      if (props.onLocationChange) {
        props.onLocationChange({
          ...endereco,
          latitude: newLocation.lat,
          longitude: newLocation.lng
        });
      }
    } catch (error) {
      console.error('Erro ao obter endereço:', error);
    }
  });

  // Permite clicar no mapa para mover o marcador
  map.addListener('click', (e) => {
    const newLocation = {
      lat: e.latLng.lat(),
      lng: e.latLng.lng()
    };
    marker.setPosition(newLocation);
    marker.getDragObject().trigger('dragend');
  });
});
</script>
```

### Passo 3: Integrar com Busca de Endereços

```tsx
function AddressSelector({ onAddressSelect }) {
  const [searchText, setSearchText] = useState('');
  const [results, setResults] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);

  const handleSearch = async () => {
    if (!searchText.trim()) return;

    try {
      const response = await fetch(
        `${API_BASE_URL}/api/localizacao/client/buscar-endereco?text=${encodeURIComponent(searchText)}&max_results=5`,
        {
          headers: {
            'X-Super-Token': clienteSuperToken,
            'Content-Type': 'application/json'
          }
        }
      );

      const enderecos = await response.json();
      setResults(enderecos);
    } catch (error) {
      console.error('Erro ao buscar endereços:', error);
    }
  };

  const handleSelectAddress = (endereco) => {
    setSelectedLocation({
      lat: endereco.latitude,
      lng: endereco.longitude
    });
    setResults([]);
    setSearchText(endereco.endereco_formatado);
    
    if (onAddressSelect) {
      onAddressSelect(endereco);
    }
  };

  return (
    <div>
      <input
        type="text"
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
        onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
        placeholder="Digite o endereço..."
      />
      <button onClick={handleSearch}>Buscar</button>

      {results.length > 0 && (
        <ul>
          {results.map((endereco, index) => (
            <li key={index} onClick={() => handleSelectAddress(endereco)}>
              {endereco.endereco_formatado}
            </li>
          ))}
        </ul>
      )}

      {selectedLocation && (
        <MapComponent
          initialLocation={selectedLocation}
          onLocationChange={onAddressSelect}
        />
      )}
    </div>
  );
}
```

### Passo 4: Salvar Endereço Ajustado

```tsx
async function saveAddress(enderecoData, enderecoId = null) {
  const url = enderecoId
    ? `${API_BASE_URL}/api/cadastros/client/enderecos/${enderecoId}`
    : `${API_BASE_URL}/api/cadastros/client/enderecos`;

  const method = enderecoId ? 'PUT' : 'POST';

  try {
    const response = await fetch(url, {
      method,
      headers: {
        'X-Super-Token': clienteSuperToken,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        logradouro: enderecoData.logradouro,
        numero: enderecoData.numero,
        complemento: enderecoData.complemento,
        bairro: enderecoData.bairro,
        cidade: enderecoData.cidade,
        estado: enderecoData.codigo_estado || enderecoData.estado,
        cep: enderecoData.cep,
        latitude: enderecoData.latitude,
        longitude: enderecoData.longitude,
        ponto_referencia: enderecoData.ponto_referencia
      })
    });

    if (!response.ok) {
      throw new Error('Erro ao salvar endereço');
    }

    const savedAddress = await response.json();
    return savedAddress;
  } catch (error) {
    console.error('Erro ao salvar endereço:', error);
    throw error;
  }
}
```

---

## 📝 Fluxo Completo de Uso

1. **Usuário busca endereço** → Chama `/client/buscar-endereco`
2. **Mostra opções** → Usuário seleciona um endereço
3. **Carrega mapa** → Mostra o mapa com marcador na localização selecionada
4. **Usuário arrasta marcador** → Chama `/client/geocodificar-reversa` para obter endereço atualizado
5. **Usuário confirma** → Chama `PUT /enderecos/{id}` para salvar coordenadas ajustadas

---

## 🔐 Configuração de Segurança no Google Cloud Console

1. Acesse [Google Cloud Console](https://console.cloud.google.com/)
2. Vá em "APIs & Services" > "Credentials"
3. Clique na sua API Key
4. Em "Application restrictions", selecione "HTTP referrers (web sites)"
5. Adicione seus domínios:
   - `https://seusite.com/*`
   - `https://*.seusite.com/*`
   - `http://localhost:*` (apenas para desenvolvimento)
6. Em "API restrictions", selecione "Restrict key" e escolha:
   - Maps JavaScript API
   - Geocoding API (opcional)
   - Places API (opcional)

---

## ⚠️ Tratamento de Erros

```typescript
async function handleApiError(response: Response) {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Erro desconhecido' }));
    
    if (response.status === 401) {
      // Token inválido - redirecionar para login
      window.location.href = '/login';
    } else if (response.status === 503) {
      // Serviço indisponível
      alert('Serviço de mapas temporariamente indisponível');
    } else {
      alert(error.detail || 'Erro ao processar requisição');
    }
    
    throw new Error(error.detail || 'Erro desconhecido');
  }
}
```

---

## 📚 Recursos Adicionais

- [Google Maps JavaScript API Documentation](https://developers.google.com/maps/documentation/javascript)
- [React Google Maps API](https://react-google-maps-api-docs.netlify.app/)
- [Google Maps API Pricing](https://developers.google.com/maps/billing-and-pricing/pricing)

---

## ✅ Checklist de Implementação

- [ ] Criar API Key no Google Cloud Console
- [ ] Configurar restrições de HTTP referrer
- [ ] Adicionar API key como variável de ambiente no frontend
- [ ] Instalar biblioteca do Google Maps
- [ ] Implementar componente de mapa
- [ ] Integrar busca de endereços
- [ ] Implementar geocodificação reversa ao arrastar marcador
- [ ] Implementar salvamento de endereço ajustado
- [ ] Testar em diferentes navegadores
- [ ] Testar em dispositivos móveis
- [ ] Configurar tratamento de erros

