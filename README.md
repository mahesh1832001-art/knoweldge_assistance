## Setup and Installation

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd knowledge_assistant
```

Replace the placeholder with your GitHub repository URL.

### 2. Configure MySQL

1. Install and start MySQL in your local or hosted environment.
2. Create a database named `knowledge_assistant`.
3. Configure the database connection details in your backend `.env` file.

### 3. Configure the Backend

Navigate to the backend directory:

```bash
cd backend
python -m venv venv
```

Activate the virtual environment and install dependencies:

```bash
python -m pip install -r requirements.txt
```

Create a `.env` file using `.env.example` as a reference.

Configure the following environment variables with values appropriate for your environment:

```dotenv
DB_HOST=your_database_host
DB_PORT=3306
DB_USER=your_database_username
DB_PASSWORD=your_database_password
DB_NAME=knowledge_assistant

CHROMA_PATH=./chroma_data

OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key

ALLOWED_TOKEN_COUNT=20
REFILL_RATE=0.333333
```

Never commit `.env` or expose API keys in source code.

Start the backend:

```bash
python -m uvicorn app.main:app --reload
```

Use the backend URL and API documentation URL displayed or configured for your environment.

### 4. Configure the Frontend

Open a separate terminal and navigate to the frontend directory:

```bash
cd frontend
npm install
npm run dev
```

Open the frontend using the URL displayed by the development server.

Ensure the backend is running and its CORS configuration allows the frontend origin.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Check backend health |
| POST | `/documents` | Create a document using JSON input |
| GET | `/documents` | List uploaded documents |
| POST | `/documents/upload` | Upload a PDF or TXT document |
| POST | `/ask` | Ask a question about available documents |

## API Documentation

FastAPI automatically generates interactive API documentation. Open the Swagger UI URL for your running backend, typically available at the `/docs` path.

## Manual API Validation

Use the Swagger UI URL for your running backend to validate the following scenarios:

- Upload a valid PDF document.
- Upload a valid TXT document.
- Attempt to upload an empty document.
- Attempt to upload an unsupported file type.
- Attempt to upload a corrupted PDF.
- Attempt to upload a file larger than 10 MB.
- Retrieve the list of uploaded documents.
- Ask a question that can be answered from an uploaded document.
- Ask a question whose answer is not present in the uploaded documents.
- Verify that excessive requests to `/ask` return HTTP 429.
- Verify that answers include relevant source references.
