# customChatbot

Chatbot multimodal NVIDIA Nemotron con interfaz inspirada en el diseño Apple.

## Capabilidades

- **Chat de texto** con los modelos Nemotron (Super 120B, Ultra 550B, Lightning 30B).
- **Análisis de imágenes**: descripciones, OCR y respuestas en español.
- **Análisis de video**: hasta 2 minutos con transcripción y línea de tiempo.
- **Búsqueda RAG**: índice local SQLite + Chroma con embeddings NVIDIA.
- **Entrada/salida de voz**: grabación de micrófono, transcripción y síntesis TTS.
- **Moderación de seguridad**: Llama Guard 4 12B.
- **Historial persistente**: SQLite con limpieza TTL de 24h.

## Arquitectura

- **Backend**: FastAPI + Python, corriendo en `http://127.0.0.1:8000` (o el host que elijas).
- **Frontend**: React + Vite + Tailwind, build estático que se publica en GitHub Pages.
- **RAG**: `nvidia/nemotron-3-embed-1b` + ChromaDB + SQLite.
- **Servicios NVIDIA**: cliente `AsyncOpenAI` con endpoints `/audio/transcriptions` y `/audio/speech`.

## Requisitos previos

1. **Python 3.12** instalado.
2. **Node.js** v22+ y npm.
3. **FFmpeg** disponible en `PATH`.
4. Una clave API NVIDIA en `backend/.env` (variable `NVIDIA_API_KEY` con prefijo `nvapi-`).

### Instalación rápida (backend)

```powershell
# 1. Entorno virtual
python -m venv .venv
& .venv\Scripts\Activate.ps1

# 2. Dependencias
pip install --upgrade pip
pip install -r requirements.txt

# 3. Configurar .env (copia el ejemplo y pon tu clave)
cp .env.example .env
# Edita backend/.env y pon NVIDIA_API_KEY=nvapi-...

# 4. Arrancar
& .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

### Instalación rápida (frontend)

```powershell
cd frontend
npm install
npm run build   # produce dist/ listo para GitHub Pages
```

## Despliegue en GitHub Pages

El frontend está configurado para servir en `https://dzzsee.github.io/customChatbot/`.

1. Crea un branch `gh-pages` o configura la acción `docs` en `.github/workflows/deploy.yml`.
2. El backend **no** se despliega en GitHub Pages (solo contenido estático). El archivo `render.yaml` permite desplegarlo en Render con:
   - CORS permitido para `https://dzzsee.github.io`.
   - `NVIDIA_API_KEY` configurada como variable de entorno.
   - Escucha en `0.0.0.0:$PORT`.
3. Tras crear el servicio, configura la variable de repositorio de GitHub Actions `VITE_API_BASE_URL` con la URL pública de Render. El workflow la inyecta durante el build (en desarrollo el proxy sigue usando `http://127.0.0.1:8000`).

### Flujo recomendado

```powershell
# 1. Construir frontend
cd frontend
npm run build

# 2. Commit y push (la acción de GitHub hará el deploy)
cd ..
git add .
git commit -m "feat: build frontend"
git push origin main

# 3. Configura Settings > Secrets and variables > Actions > Variables:
#    VITE_API_BASE_URL=https://customchatbot-api.onrender.com
```

## Licencia

MIT