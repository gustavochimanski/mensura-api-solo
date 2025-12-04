'use client'

export type RememberedCredentials = {
  username: string
  password: string
}

type StoredCredentialsPayload = {
  username: string
  iv: string
  data: string
  lastUsed?: number
}

export type RememberedUserMetadata = {
  username: string
  lastUsed?: number
}

const DB_NAME = 'unitec-supervisor-remember'
const KEY_STORE = 'keys'
const CREDENTIAL_STORE = 'credentials'
const KEY_ID = 'remember-key'
const LEGACY_CREDENTIAL_ID = 'credential'
const encoder = new TextEncoder()
const decoder = new TextDecoder()

let dbPromise: Promise<IDBDatabase> | null = null
let cachedKey: CryptoKey | null = null

function isSupportedEnvironment() {
  return (
    typeof window !== 'undefined' &&
    typeof window.indexedDB !== 'undefined' &&
    typeof window.crypto !== 'undefined' &&
    typeof window.crypto.subtle !== 'undefined'
  )
}

export function isRememberMeAvailable() {
  return isSupportedEnvironment()
}

async function openDatabase() {
  if (!isSupportedEnvironment()) {
    throw new Error('Remember-me storage não suportado neste ambiente.')
  }

  if (!dbPromise) {
    dbPromise = new Promise<IDBDatabase>((resolve, reject) => {
      const request = window.indexedDB.open(DB_NAME, 1)

      request.onupgradeneeded = () => {
        const db = request.result

        if (!db.objectStoreNames.contains(KEY_STORE)) {
          db.createObjectStore(KEY_STORE)
        }

        if (!db.objectStoreNames.contains(CREDENTIAL_STORE)) {
          db.createObjectStore(CREDENTIAL_STORE)
        }
      }

      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error ?? new Error('Falha ao abrir banco IndexedDB do remember-me.'))
    })
  }

  return dbPromise
}

function promisifyRequest<T>(request: IDBRequest<T>) {
  return new Promise<T>((resolve, reject) => {
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error ?? new Error('Falha na operação IndexedDB.'))
  })
}

function awaitTransactionCompletion(transaction: IDBTransaction) {
  return new Promise<void>((resolve, reject) => {
    transaction.oncomplete = () => resolve()
    transaction.onabort = () => reject(transaction.error ?? new Error('Transação IndexedDB abortada.'))
    transaction.onerror = () => reject(transaction.error ?? new Error('Erro na transação IndexedDB.'))
  })
}

function bufferToBase64(buffer: ArrayBuffer) {
  const bytes = new Uint8Array(buffer)
  let binary = ''

  for (let i = 0; i < bytes.length; i += 1) {
    binary += String.fromCharCode(bytes[i])
  }

  return window.btoa(binary)
}

function base64ToArrayBuffer(base64: string) {
  const binary = window.atob(base64)
  const length = binary.length
  const bytes = new Uint8Array(length)

  for (let i = 0; i < length; i += 1) {
    bytes[i] = binary.charCodeAt(i)
  }

  return bytes.buffer
}

async function getOrCreateKey() {
  if (!isSupportedEnvironment()) {
    return null
  }

  if (cachedKey) {
    return cachedKey
  }

  const db = await openDatabase()

  try {
    const tx = db.transaction(KEY_STORE, 'readonly')
    const store = tx.objectStore(KEY_STORE)
    const storedKey = await promisifyRequest(store.get(KEY_ID))
    await awaitTransactionCompletion(tx)

    if (storedKey instanceof CryptoKey) {
      cachedKey = storedKey
      return cachedKey
    }

    if (storedKey) {
      const importedKey = await window.crypto.subtle.importKey(
        'raw',
        storedKey as ArrayBuffer,
        'AES-GCM',
        true,
        ['encrypt', 'decrypt']
      )
      cachedKey = importedKey
      return cachedKey
    }
  } catch (error) {
    console.error('Falha ao recuperar chave do remember-me:', error)
  }

  const newKey = await window.crypto.subtle.generateKey(
    {
      name: 'AES-GCM',
      length: 256,
    },
    true,
    ['encrypt', 'decrypt']
  )

  try {
    const exportedKey = await window.crypto.subtle.exportKey('raw', newKey)
    const tx = db.transaction(KEY_STORE, 'readwrite')
    const store = tx.objectStore(KEY_STORE)
    store.put(exportedKey, KEY_ID)
    await awaitTransactionCompletion(tx)
  } catch (error) {
    console.error('Falha ao persistir chave do remember-me:', error)
  }

  cachedKey = newKey
  return cachedKey
}

async function getAllStoredPayloads(db: IDBDatabase) {
  const tx = db.transaction(CREDENTIAL_STORE, 'readonly')
  const store = tx.objectStore(CREDENTIAL_STORE)
  const request = store.getAll()
  const result = (await promisifyRequest(request)) as StoredCredentialsPayload[] | undefined
  await awaitTransactionCompletion(tx)
  return (result ?? []).filter(Boolean)
}

async function getStoredPayloadByKey(db: IDBDatabase, key: IDBValidKey) {
  const tx = db.transaction(CREDENTIAL_STORE, 'readonly')
  const store = tx.objectStore(CREDENTIAL_STORE)
  const payload = (await promisifyRequest(store.get(key))) as StoredCredentialsPayload | undefined
  await awaitTransactionCompletion(tx)
  return payload ?? null
}

async function persistPayload(payload: StoredCredentialsPayload) {
  try {
    const db = await openDatabase()
    const tx = db.transaction(CREDENTIAL_STORE, 'readwrite')
    const store = tx.objectStore(CREDENTIAL_STORE)
    const key = payload.username || LEGACY_CREDENTIAL_ID
    store.put(payload, key)

    if (key !== LEGACY_CREDENTIAL_ID) {
      store.delete(LEGACY_CREDENTIAL_ID)
    }

    await awaitTransactionCompletion(tx)
  } catch (error) {
    console.error('Falha ao atualizar credencial lembrada:', error)
  }
}

export async function storeRememberedCredentials(credentials: RememberedCredentials) {
  try {
    const key = await getOrCreateKey()

    if (!key) {
      return
    }

    const db = await openDatabase()
    const iv = window.crypto.getRandomValues(new Uint8Array(12))
    const encryptedBuffer = await window.crypto.subtle.encrypt(
      {
        name: 'AES-GCM',
        iv,
      },
      key,
      encoder.encode(credentials.password)
    )

    const payload: StoredCredentialsPayload = {
      username: credentials.username,
      iv: bufferToBase64(iv.buffer),
      data: bufferToBase64(encryptedBuffer),
      lastUsed: Date.now(),
    }

    const tx = db.transaction(CREDENTIAL_STORE, 'readwrite')
    const store = tx.objectStore(CREDENTIAL_STORE)
    store.put(payload, payload.username)
    store.delete(LEGACY_CREDENTIAL_ID)
    await awaitTransactionCompletion(tx)
  } catch (error) {
    console.error('Falha ao armazenar credenciais lembradas:', error)
  }
}

export async function listRememberedUsers(): Promise<RememberedUserMetadata[]> {
  try {
    const db = await openDatabase()
    const payloads = await getAllStoredPayloads(db)

    if (!payloads.length) {
      const legacyPayload = await getStoredPayloadByKey(db, LEGACY_CREDENTIAL_ID)
      if (legacyPayload) {
        payloads.push(legacyPayload)
      }
    }

    const mapped = payloads
      .filter((payload) => Boolean(payload?.username))
      .map((payload) => ({
        username: payload.username,
        lastUsed: payload.lastUsed,
      }))

    return mapped.sort((a, b) => (b.lastUsed ?? 0) - (a.lastUsed ?? 0))
  } catch (error) {
    console.error('Falha ao listar credenciais lembradas:', error)
    return []
  }
}

async function getPayloadForUsername(username?: string) {
  const db = await openDatabase()

  if (username) {
    const payload = await getStoredPayloadByKey(db, username)

    if (payload) {
      return payload
    }
  }

  const payloads = await getAllStoredPayloads(db)

  if (!payloads.length) {
    const legacyPayload = await getStoredPayloadByKey(db, LEGACY_CREDENTIAL_ID)
    return legacyPayload
  }

  const sorted = payloads.sort((a, b) => (b.lastUsed ?? 0) - (a.lastUsed ?? 0))
  return sorted[0]
}

export async function getRememberedCredentials(username?: string) {
  try {
    const key = await getOrCreateKey()

    if (!key) {
      return null
    }

    const payload = await getPayloadForUsername(username)
    if (!payload || !payload.data || !payload.iv) {
      return null
    }

    const decrypted = await window.crypto.subtle.decrypt(
      {
        name: 'AES-GCM',
        iv: base64ToArrayBuffer(payload.iv),
      },
      key,
      base64ToArrayBuffer(payload.data)
    )

    void persistPayload({
      ...payload,
      lastUsed: Date.now(),
    })

    return {
      username: payload.username,
      password: decoder.decode(decrypted),
    }
  } catch (error) {
    console.error('Falha ao recuperar credenciais lembradas:', error)
    return null
  }
}

export async function clearRememberedCredentials(username?: string) {
  if (!isSupportedEnvironment()) {
    return
  }

  try {
    const db = await openDatabase()
    const tx = db.transaction(CREDENTIAL_STORE, 'readwrite')
    const store = tx.objectStore(CREDENTIAL_STORE)

    if (username) {
      store.delete(username)

      if (username !== LEGACY_CREDENTIAL_ID) {
        store.delete(LEGACY_CREDENTIAL_ID)
      }
    } else {
      store.clear()
    }

    await awaitTransactionCompletion(tx)
  } catch (error) {
    console.error('Falha ao limpar credenciais lembradas:', error)
  }
}

export async function removeRememberedCredential(username: string) {
  await clearRememberedCredentials(username)
}

