from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import HTMLResponse

from app.api.dependencies import get_collection_inspection_service
from app.api.schemas.viewer import (
    QdrantDocumentResponse,
    QdrantDocumentsResponse,
    ViewerChunkResponse,
    ViewerDocumentResponse,
    ViewerOverviewResponse,
)
from app.application.services.inspection import CollectionInspectionService

router = APIRouter(tags=["viewer"])


@router.get("/viewer", response_class=HTMLResponse, include_in_schema=False)
async def viewer_page() -> HTMLResponse:
    return HTMLResponse(_VIEWER_HTML)


@router.get(
    "/api/v1/viewer/overview",
    response_model=ViewerOverviewResponse,
    summary="Inspect ingested documents and Qdrant chunks",
)
async def get_viewer_overview(
    limit: int = Query(default=120, ge=1, le=500),
    offset: str | None = Query(default=None),
    inspection_service: CollectionInspectionService = Depends(get_collection_inspection_service),
) -> ViewerOverviewResponse:
    overview = await inspection_service.get_overview(limit=limit, offset=offset)
    return ViewerOverviewResponse(
        collection_name=overview.collection_name,
        documents=[
            ViewerDocumentResponse(
                id=document.id,
                filename=document.filename,
                content_type=document.content_type,
                extension=document.extension,
                size_bytes=document.size_bytes,
                status=document.status,
                created_at=document.created_at,
                updated_at=document.updated_at,
                error=document.error,
            )
            for document in overview.documents
        ],
        chunks=[
            ViewerChunkResponse(
                id=chunk.id,
                document_id=chunk.document_id,
                filename=chunk.filename,
                content=chunk.content,
                chunk_index=chunk.chunk_index,
                metadata=chunk.metadata,
            )
            for chunk in overview.chunks
        ],
        total_documents=overview.total_documents,
        total_chunks=overview.total_chunks,
        page_size=overview.page_size,
        next_offset=overview.next_offset,
        collection_exists=overview.collection_exists,
        qdrant_available=overview.qdrant_available,
        qdrant_error=overview.qdrant_error,
    )


@router.get(
    "/api/v1/qdrant/documents",
    response_model=QdrantDocumentsResponse,
    summary="List unique documents currently stored in Qdrant",
)
async def get_qdrant_documents(
    batch_size: int = Query(default=256, ge=1, le=1000),
    inspection_service: CollectionInspectionService = Depends(get_collection_inspection_service),
) -> QdrantDocumentsResponse:
    overview = await inspection_service.get_qdrant_documents(batch_size=batch_size)
    return QdrantDocumentsResponse(
        collection_name=overview.collection_name,
        documents=[
            QdrantDocumentResponse(
                document_id=document.document_id,
                filename=document.filename,
                chunk_count=document.chunk_count,
                status=document.status,
                content_type=document.content_type,
                extension=document.extension,
                size_bytes=document.size_bytes,
                created_at=document.created_at,
                updated_at=document.updated_at,
                error=document.error,
            )
            for document in overview.documents
        ],
        total_documents=overview.total_documents,
        total_chunks=overview.total_chunks,
        collection_exists=overview.collection_exists,
        qdrant_available=overview.qdrant_available,
        qdrant_error=overview.qdrant_error,
    )


_VIEWER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Kachabiti Collection Viewer</title>
  <style>
    :root {
      --paper: #f3efe4;
      --paper-strong: #e5decc;
      --ink: #171717;
      --muted: #60584a;
      --accent: #b14f2b;
      --accent-soft: rgba(177, 79, 43, 0.12);
      --panel: rgba(255, 252, 247, 0.72);
      --border: rgba(23, 23, 23, 0.14);
      --ok: #285f45;
      --warn: #915f10;
      --shadow: 0 18px 50px rgba(38, 31, 23, 0.12);
    }

    * {
      box-sizing: border-box;
    }

    body {
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(177, 79, 43, 0.18), transparent 30%),
        radial-gradient(circle at right, rgba(40, 95, 69, 0.14), transparent 25%),
        linear-gradient(180deg, #f6f2e9 0%, #ece4d4 100%);
      font-family: "Iowan Old Style", "Palatino Linotype", "Book Antiqua", Georgia, serif;
    }

    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      background-image:
        linear-gradient(rgba(23, 23, 23, 0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(23, 23, 23, 0.03) 1px, transparent 1px);
      background-size: 32px 32px;
      mask-image: radial-gradient(circle at center, black 40%, transparent 100%);
    }

    .shell {
      width: min(1380px, calc(100vw - 32px));
      margin: 24px auto;
      display: grid;
      gap: 18px;
    }

    .hero,
    .panel {
      border: 1px solid var(--border);
      border-radius: 24px;
      background: var(--panel);
      backdrop-filter: blur(18px);
      box-shadow: var(--shadow);
    }

    .hero {
      overflow: hidden;
      position: relative;
      padding: 28px;
    }

    .hero::after {
      content: "";
      position: absolute;
      inset: auto -10% -40% 45%;
      height: 180px;
      background: linear-gradient(90deg, transparent, rgba(177, 79, 43, 0.16), transparent);
      transform: rotate(-6deg);
    }

    .eyebrow {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(23, 23, 23, 0.06);
      font: 600 12px/1.2 "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    h1 {
      margin: 18px 0 10px;
      font-size: clamp(2.4rem, 5vw, 4.8rem);
      line-height: 0.92;
      letter-spacing: -0.06em;
      max-width: 10ch;
    }

    .hero p {
      margin: 0;
      max-width: 62ch;
      color: var(--muted);
      font-size: 1.02rem;
    }

    .stats {
      margin-top: 24px;
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 12px;
      position: relative;
      z-index: 1;
    }

    .stat {
      padding: 14px 16px;
      border-radius: 18px;
      background: rgba(255, 255, 255, 0.48);
      border: 1px solid rgba(23, 23, 23, 0.08);
    }

    .stat-label {
      color: var(--muted);
      font: 600 11px/1.2 "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .stat-value {
      margin-top: 10px;
      font-size: 1.75rem;
      letter-spacing: -0.04em;
    }

    .workspace {
      display: grid;
      grid-template-columns: 360px minmax(0, 1fr);
      gap: 18px;
      align-items: start;
    }

    .panel {
      padding: 18px;
    }

    .panel-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 16px;
    }

    .panel-title {
      margin: 0;
      font-size: 1.15rem;
      letter-spacing: -0.03em;
    }

    .meta {
      color: var(--muted);
      font: 500 12px/1.2 "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
    }

    .toolbar {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
      margin-bottom: 14px;
    }

    .pill,
    button,
    input {
      border-radius: 999px;
      font: 600 12px/1.2 "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
    }

    button {
      border: 1px solid rgba(23, 23, 23, 0.12);
      background: white;
      color: var(--ink);
      padding: 11px 14px;
      cursor: pointer;
      transition: transform 140ms ease, border-color 140ms ease, background 140ms ease;
    }

    button:hover {
      transform: translateY(-1px);
      border-color: rgba(23, 23, 23, 0.28);
      background: #fff8f2;
    }

    button:disabled {
      cursor: wait;
      opacity: 0.6;
      transform: none;
    }

    input {
      border: 1px solid rgba(23, 23, 23, 0.1);
      background: rgba(255, 255, 255, 0.8);
      color: var(--ink);
      padding: 11px 14px;
      min-width: 220px;
      outline: none;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 9px 12px;
      border: 1px solid rgba(23, 23, 23, 0.1);
      background: rgba(255, 255, 255, 0.55);
    }

    .pill.ok {
      color: var(--ok);
      border-color: rgba(40, 95, 69, 0.2);
      background: rgba(40, 95, 69, 0.08);
    }

    .pill.warn {
      color: var(--warn);
      border-color: rgba(145, 95, 16, 0.2);
      background: rgba(145, 95, 16, 0.1);
    }

    .scroll {
      display: grid;
      gap: 12px;
      max-height: 72vh;
      overflow: auto;
      padding-right: 4px;
    }

    .card {
      border-radius: 18px;
      border: 1px solid rgba(23, 23, 23, 0.08);
      background: rgba(255, 255, 255, 0.6);
      padding: 15px;
      transition: transform 140ms ease, border-color 140ms ease, background 140ms ease;
    }

    .card:hover {
      transform: translateY(-2px);
      border-color: rgba(23, 23, 23, 0.18);
      background: rgba(255, 255, 255, 0.85);
    }

    .doc-card.active {
      border-color: rgba(177, 79, 43, 0.35);
      background: linear-gradient(180deg, rgba(177, 79, 43, 0.1), rgba(255, 255, 255, 0.88));
    }

    .filename {
      margin: 0 0 8px;
      font-size: 1.05rem;
      line-height: 1.1;
    }

    .mono,
    .chunk-meta,
    .status-row {
      font-family: "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
    }

    .status-row,
    .chunk-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px 12px;
      color: var(--muted);
      font-size: 12px;
    }

    .doc-status {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--accent);
    }

    .dot {
      width: 10px;
      height: 10px;
      border-radius: 50%;
      background: currentColor;
      box-shadow: 0 0 0 4px currentColor;
      opacity: 0.18;
    }

    .chunk-copy {
      margin-top: 12px;
      color: #2f2a23;
      line-height: 1.55;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .metadata {
      margin-top: 14px;
      padding-top: 12px;
      border-top: 1px dashed rgba(23, 23, 23, 0.12);
      color: var(--muted);
      font: 500 12px/1.5 "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .empty {
      padding: 22px;
      border-radius: 18px;
      border: 1px dashed rgba(23, 23, 23, 0.18);
      color: var(--muted);
      background: rgba(255, 255, 255, 0.4);
      text-align: center;
    }

    .notice {
      margin-bottom: 14px;
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid rgba(145, 95, 16, 0.2);
      background: rgba(145, 95, 16, 0.08);
      color: #6a4709;
      font: 500 13px/1.5 "IBM Plex Mono", "SFMono-Regular", Consolas, monospace;
    }

    .load-more {
      width: 100%;
      margin-top: 12px;
      justify-self: stretch;
    }

    @media (max-width: 980px) {
      .stats,
      .workspace {
        grid-template-columns: 1fr;
      }

      .scroll {
        max-height: none;
      }

      input {
        min-width: 0;
        width: 100%;
      }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="eyebrow">Kachabiti / Collection Viewer</div>
      <h1>Inspect what reached Qdrant.</h1>
      <p>
        Browse ingested document metadata, inspect stored chunks, and confirm exactly what landed in the active
        collection without leaving the app.
      </p>
      <div class="stats">
        <div class="stat">
          <div class="stat-label">Collection</div>
          <div class="stat-value mono" id="stat-collection">...</div>
        </div>
        <div class="stat">
          <div class="stat-label">Documents</div>
          <div class="stat-value" id="stat-documents">0</div>
        </div>
        <div class="stat">
          <div class="stat-label">Chunks In Qdrant</div>
          <div class="stat-value" id="stat-chunks">0</div>
        </div>
        <div class="stat">
          <div class="stat-label">Visible Chunks</div>
          <div class="stat-value" id="stat-visible">0</div>
        </div>
      </div>
    </section>

    <section class="workspace">
      <aside class="panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">Documents</h2>
            <div class="meta">Local metadata and ingestion status</div>
          </div>
          <div class="pill" id="doc-filter-pill">All documents</div>
        </div>
        <div class="scroll" id="documents"></div>
      </aside>

      <section class="panel">
        <div class="panel-head">
          <div>
            <h2 class="panel-title">Collection Payload</h2>
            <div class="meta">Chunk text and payload saved in Qdrant</div>
          </div>
          <div class="pill" id="qdrant-pill">Checking Qdrant</div>
        </div>
        <div class="toolbar">
          <button id="refresh" type="button">Refresh</button>
          <button id="clear-filter" type="button">Show All</button>
          <input id="search" type="search" placeholder="Filter chunks by filename, document id, or text" />
        </div>
        <div id="notice"></div>
        <div class="scroll" id="chunks"></div>
        <button class="load-more" id="load-more" type="button" hidden>Load More Chunks</button>
      </section>
    </section>
  </main>

  <script>
    const state = {
      documents: [],
      chunks: [],
      selectedDocumentId: null,
      searchTerm: "",
      nextOffset: null,
      loading: false,
      collectionName: "",
      totalChunks: 0,
    };

    const elements = {
      documents: document.getElementById("documents"),
      chunks: document.getElementById("chunks"),
      notice: document.getElementById("notice"),
      refresh: document.getElementById("refresh"),
      clearFilter: document.getElementById("clear-filter"),
      loadMore: document.getElementById("load-more"),
      search: document.getElementById("search"),
      statCollection: document.getElementById("stat-collection"),
      statDocuments: document.getElementById("stat-documents"),
      statChunks: document.getElementById("stat-chunks"),
      statVisible: document.getElementById("stat-visible"),
      qdrantPill: document.getElementById("qdrant-pill"),
      docFilterPill: document.getElementById("doc-filter-pill"),
    };

    function escapeHtml(value) {
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
    }

    function formatBytes(bytes) {
      if (!Number.isFinite(bytes) || bytes < 0) return "n/a";
      const units = ["B", "KB", "MB", "GB"];
      let value = bytes;
      let unitIndex = 0;
      while (value >= 1024 && unitIndex < units.length - 1) {
        value /= 1024;
        unitIndex += 1;
      }
      return `${value.toFixed(value >= 10 || unitIndex === 0 ? 0 : 1)} ${units[unitIndex]}`;
    }

    function formatDate(value) {
      if (!value) return "unknown";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return date.toLocaleString();
    }

    function setLoading(isLoading) {
      state.loading = isLoading;
      elements.refresh.disabled = isLoading;
      elements.loadMore.disabled = isLoading;
      elements.refresh.textContent = isLoading ? "Refreshing..." : "Refresh";
    }

    async function fetchOverview({ append = false } = {}) {
      if (state.loading) return;
      setLoading(true);
      const params = new URLSearchParams({ limit: "120" });
      if (append && state.nextOffset) {
        params.set("offset", state.nextOffset);
      }

      try {
        const response = await fetch(`/api/v1/viewer/overview?${params.toString()}`);
        const payload = await response.json();
        if (!response.ok) {
          throw new Error(payload.detail || "Failed to load collection overview.");
        }

        state.collectionName = payload.collection_name;
        state.documents = payload.documents;
        state.totalChunks = payload.total_chunks;
        state.nextOffset = payload.next_offset;
        state.chunks = append ? [...state.chunks, ...payload.chunks] : payload.chunks;

        renderNotice(payload);
        renderStats();
        renderDocuments();
        renderChunks();
      } catch (error) {
        elements.notice.innerHTML = `<div class="notice">${escapeHtml(error.message)}</div>`;
      } finally {
        setLoading(false);
      }
    }

    function renderNotice(payload) {
      const messages = [];
      if (!payload.qdrant_available) {
        messages.push(`Qdrant is currently unreachable. ${payload.qdrant_error || ""}`.trim());
        elements.qdrantPill.className = "pill warn";
        elements.qdrantPill.textContent = "Qdrant unavailable";
      } else if (!payload.collection_exists) {
        messages.push("The collection does not exist yet. Ingest a document first and it will be created automatically.");
        elements.qdrantPill.className = "pill warn";
        elements.qdrantPill.textContent = "Collection empty";
      } else {
        elements.qdrantPill.className = "pill ok";
        elements.qdrantPill.textContent = "Qdrant reachable";
      }

      elements.notice.innerHTML = messages.length
        ? messages.map((message) => `<div class="notice">${escapeHtml(message)}</div>`).join("")
        : "";
    }

    function renderStats() {
      elements.statCollection.textContent = state.collectionName || "...";
      elements.statDocuments.textContent = String(state.documents.length);
      elements.statChunks.textContent = String(state.totalChunks);
      elements.statVisible.textContent = String(getVisibleChunks().length);
      const activeDocument = state.documents.find((item) => item.id === state.selectedDocumentId);
      elements.docFilterPill.textContent = activeDocument ? activeDocument.filename : "All documents";
    }

    function renderDocuments() {
      if (!state.documents.length) {
        elements.documents.innerHTML = '<div class="empty">No document metadata found yet.</div>';
        return;
      }

      elements.documents.innerHTML = state.documents.map((documentItem) => {
        const isActive = state.selectedDocumentId === documentItem.id;
        return `
          <button class="card doc-card ${isActive ? "active" : ""}" data-document-id="${escapeHtml(documentItem.id)}" type="button">
            <div class="doc-status"><span class="dot"></span>${escapeHtml(documentItem.status)}</div>
            <h3 class="filename">${escapeHtml(documentItem.filename)}</h3>
            <div class="status-row">
              <span>${escapeHtml(documentItem.id)}</span>
              <span>${escapeHtml(documentItem.extension)}</span>
              <span>${escapeHtml(formatBytes(documentItem.size_bytes))}</span>
            </div>
            <div class="status-row" style="margin-top:10px;">
              <span>Updated ${escapeHtml(formatDate(documentItem.updated_at))}</span>
            </div>
            ${documentItem.error ? `<div class="metadata">${escapeHtml(documentItem.error)}</div>` : ""}
          </button>
        `;
      }).join("");

      for (const button of elements.documents.querySelectorAll("[data-document-id]")) {
        button.addEventListener("click", () => {
          const documentId = button.getAttribute("data-document-id");
          state.selectedDocumentId = state.selectedDocumentId === documentId ? null : documentId;
          renderStats();
          renderDocuments();
          renderChunks();
        });
      }
    }

    function getVisibleChunks() {
      const term = state.searchTerm.trim().toLowerCase();
      return state.chunks.filter((chunk) => {
        if (state.selectedDocumentId && chunk.document_id !== state.selectedDocumentId) {
          return false;
        }

        if (!term) {
          return true;
        }

        const haystack = [
          chunk.filename,
          chunk.document_id,
          chunk.id,
          chunk.content,
          JSON.stringify(chunk.metadata || {}),
        ].join(" ").toLowerCase();
        return haystack.includes(term);
      });
    }

    function renderChunks() {
      const visibleChunks = getVisibleChunks();
      renderStats();

      if (!visibleChunks.length) {
        elements.chunks.innerHTML = '<div class="empty">No matching chunks in the loaded page.</div>';
      } else {
        elements.chunks.innerHTML = visibleChunks.map((chunk) => `
          <article class="card">
            <div class="chunk-meta">
              <span>${escapeHtml(chunk.filename)}</span>
              <span>doc ${escapeHtml(chunk.document_id)}</span>
              <span>chunk ${escapeHtml(chunk.chunk_index)}</span>
              <span>${escapeHtml(chunk.id)}</span>
            </div>
            <div class="chunk-copy">${escapeHtml(chunk.content)}</div>
            <div class="metadata">${escapeHtml(JSON.stringify(chunk.metadata || {}, null, 2))}</div>
          </article>
        `).join("");
      }

      elements.loadMore.hidden = !state.nextOffset;
    }

    elements.refresh.addEventListener("click", () => {
      state.nextOffset = null;
      fetchOverview({ append: false });
    });

    elements.clearFilter.addEventListener("click", () => {
      state.selectedDocumentId = null;
      state.searchTerm = "";
      elements.search.value = "";
      renderStats();
      renderDocuments();
      renderChunks();
    });

    elements.loadMore.addEventListener("click", () => {
      if (state.nextOffset) {
        fetchOverview({ append: true });
      }
    });

    elements.search.addEventListener("input", (event) => {
      state.searchTerm = event.target.value || "";
      renderChunks();
    });

    fetchOverview({ append: false });
  </script>
</body>
</html>
"""
