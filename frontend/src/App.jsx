
import { useEffect, useState } from "react";
import "./App.css";

const API_URL = "http://127.0.0.1:8000";
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB
const ALLOWED_EXTENSIONS = [".pdf", ".txt"];

function App() {
  const [documents, setDocuments] = useState([]);
  const [file, setFile] = useState(null);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [sources, setSources] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, []);

  async function loadDocuments() {
    try {
      const response = await fetch(`${API_URL}/documents`);

      if (!response.ok) {
        throw new Error("Failed to load documents");
      }

      const data = await response.json();

      setDocuments(
        Array.isArray(data) ? data : data.documents || []
      );
    } catch {
      setMessage(
        "Cannot connect to FastAPI. Make sure the backend is running."
      );
    }
  }

  function handleFileChange(event) {
    const selectedFile = event.target.files?.[0];

    setFile(null);
    setMessage("");

    if (!selectedFile) {
      return;
    }

    const extension = selectedFile.name
      .toLowerCase()
      .slice(selectedFile.name.lastIndexOf("."));

    if (!ALLOWED_EXTENSIONS.includes(extension)) {
      setMessage("Only PDF and TXT files are allowed.");
      event.target.value = "";
      return;
    }

    if (selectedFile.size === 0) {
      setMessage("The selected file is empty.");
      event.target.value = "";
      return;
    }

    if (selectedFile.size > MAX_FILE_SIZE) {
      setMessage("File size must not exceed 10 MB.");
      event.target.value = "";
      return;
    }

    setFile(selectedFile);
  }

  async function uploadDocument(event) {
    event.preventDefault();

    if (!file) {
      setMessage("Please select a PDF or TXT file.");
      return;
    }

    setUploading(true);
    setMessage("");

    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(`${API_URL}/documents/upload`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Document upload failed."
        );
      }

      setMessage(data.message || "Document uploaded successfully!");
      setFile(null);
      event.target.reset();

      await loadDocuments();
    } catch (error) {
      setMessage(error.message || "Unable to upload the document.");
    } finally {
      setUploading(false);
    }
  }

  async function askQuestion(event) {
    event.preventDefault();

    if (!question.trim()) {
      return;
    }

    setLoading(true);
    setAnswer("");
    setSources([]);
    setMessage("");

    try {
      const response = await fetch(`${API_URL}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: question.trim(),
        }),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          typeof data.detail === "string"
            ? data.detail
            : "Unable to answer the question."
        );
      }

      setAnswer(data.answer);
      setSources(data.sources || []);
    } catch (error) {
      setMessage(error.message || "Unable to connect to the backend.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <header className="header">
        <h1>Mini Knowledge Assistant</h1>
        <p>Upload documents and ask questions about their content.</p>
      </header>

      {message && (
        <div className="message" role="status">
          <span>{message}</span>
          <button
            type="button"
            onClick={() => setMessage("")}
            aria-label="Dismiss message"
          >
            ×
          </button>
        </div>
      )}

      <main className="layout">
        <section className="card">
          <h2>Upload Document</h2>

          <form onSubmit={uploadDocument}>
            <label htmlFor="documentFile">Select PDF or TXT file</label>

            <input
              id="documentFile"
              type="file"
              accept=".pdf,.txt,application/pdf,text/plain"
              onChange={handleFileChange}
              disabled={uploading}
              required
            />

            <p className="muted">Maximum file size: 10 MB</p>

            {file && (
              <p className="selected-file">
                Selected: <strong>{file.name}</strong>
              </p>
            )}

            <button type="submit" disabled={uploading || !file}>
              {uploading ? "Uploading..." : "Upload Document"}
            </button>
          </form>

          <h2 className="section-title">
            Uploaded Documents ({documents.length})
          </h2>

          {documents.length === 0 ? (
            <p className="muted">No documents found.</p>
          ) : (
            <ul className="document-list">
              {documents.map((doc) => (
                <li key={doc.id}>
                  <strong>{doc.title}</strong>
                  <small>Document ID: {doc.id}</small>
                </li>
              ))}
            </ul>
          )}
        </section>

        <section className="card">
          <h2>Ask a Question</h2>

          <form onSubmit={askQuestion}>
            <label htmlFor="question">Your question</label>

            <textarea
              id="question"
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="Example: How many days does a refund take?"
              rows={4}
              maxLength={2000}
              required
            />

            <button type="submit" disabled={loading}>
              {loading ? "Finding answer..." : "Ask Question"}
            </button>
          </form>

          {answer && (
            <div className="answer">
              <h2>Answer</h2>
              <p className="answer-text">{answer}</p>

              <h3>Sources</h3>

              {sources.length === 0 ? (
                <p className="muted">No source references returned.</p>
              ) : (
                sources.map((source, index) => (
                  <article
                    className="source"
                    key={source.chunk_id ?? index}
                  >
                    <strong>{source.title}</strong>
                    <p>{source.content}</p>

                    {source.document_id != null && (
                      <small>Document ID: {source.document_id}</small>
                    )}
                  </article>
                ))
              )}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
