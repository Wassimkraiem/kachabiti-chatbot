"use client";

import { startTransition, useCallback, useDeferredValue, useEffect, useState } from "react";

import { formatTimestamp, getErrorMessage, readJson, sortQuestions } from "@/lib/console";

type QuestionItem = {
  id: string;
  question: string;
  answer: string;
  updated_at?: string | null;
  score?: number | null;
};

type QuestionsResponse = {
  questions?: QuestionItem[];
};

type EditorState = {
  id: string | null;
  question: string;
  answer: string;
};

const EMPTY_EDITOR: EditorState = {
  id: null,
  question: "",
  answer: ""
};

export function QuestionsWorkspace() {
  const [questions, setQuestions] = useState<QuestionItem[]>([]);
  const [questionsPending, setQuestionsPending] = useState(true);
  const [questionError, setQuestionError] = useState("");
  const [search, setSearch] = useState("");
  const deferredSearch = useDeferredValue(search);
  const [editor, setEditor] = useState<EditorState>(EMPTY_EDITOR);
  const [savePending, setSavePending] = useState(false);
  const [deletePending, setDeletePending] = useState(false);

  const loadQuestions = useCallback(
    async ({ query = "", selectedId = null }: {
      query?: string;
      selectedId?: string | null;
    } = {}) => {
      const normalizedQuery = query.trim();
      setQuestionsPending(true);
      setQuestionError("");

      try {
        const params = new URLSearchParams();
        if (normalizedQuery) {
          params.set("query", normalizedQuery);
        }
        const endpoint = params.size ? `/api/questions?${params.toString()}` : "/api/questions";
        const data = await readJson<QuestionsResponse>(await fetch(endpoint, { cache: "no-store" }));
        const ordered = normalizedQuery ? (data.questions || []) : sortQuestions(data.questions || []);
        startTransition(() => {
          setQuestions(ordered);
          if (selectedId) {
            const selected = ordered.find((item) => item.id === selectedId);
            if (selected) {
              setEditor({
                id: selected.id,
                question: selected.question,
                answer: selected.answer
              });
            }
          }
        });
      } catch (error) {
        setQuestionError(getErrorMessage(error, "Could not load questions from Qdrant."));
      } finally {
        setQuestionsPending(false);
      }
    },
    []
  );

  useEffect(() => {
    void loadQuestions({ query: deferredSearch });
  }, [deferredSearch, loadQuestions]);

  async function handleSaveQuestion(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (savePending) {
      return;
    }

    const payload = {
      question: editor.question.trim(),
      answer: editor.answer.trim()
    };
    if (!payload.question || !payload.answer) {
      setQuestionError("Both question and answer are required.");
      return;
    }

    setSavePending(true);
    setQuestionError("");

    try {
      const url = editor.id ? `/api/questions/${editor.id}` : "/api/questions";
      const method = editor.id ? "PUT" : "POST";
      const data = await readJson<QuestionItem>(
        await fetch(url, {
          method,
          headers: { "content-type": "application/json" },
          body: JSON.stringify(payload)
        })
      );

      startTransition(() => {
        setEditor({
          id: data.id,
          question: data.question,
          answer: data.answer
        });
      });
      await loadQuestions({ query: deferredSearch, selectedId: data.id });
    } catch (error) {
      setQuestionError(getErrorMessage(error, "Could not save the question."));
    } finally {
      setSavePending(false);
    }
  }

  async function handleDeleteQuestion() {
    if (!editor.id || deletePending) {
      return;
    }

    setDeletePending(true);
    setQuestionError("");

    try {
      const response = await fetch(`/api/questions/${editor.id}`, { method: "DELETE" });
      if (!response.ok) {
        throw new Error(
          getErrorMessage(await response.json().catch(() => ({})), "Could not delete the question.")
        );
      }

      startTransition(() => {
        setEditor(EMPTY_EDITOR);
      });
      await loadQuestions({ query: deferredSearch });
    } catch (error) {
      setQuestionError(getErrorMessage(error, "Could not delete the question."));
    } finally {
      setDeletePending(false);
    }
  }

  function handleStartNewQuestion() {
    setQuestionError("");
    startTransition(() => {
      setEditor(EMPTY_EDITOR);
    });
  }

  const searchActive = deferredSearch.trim().length > 0;

  return (
    <section className="page-shell">
      <header className="page-hero">
        <div>
          <p className="eyebrow">Questions</p>
          <h2>Maintain the Qdrant FAQ without leaving the editor.</h2>
          <p className="hero-copy">
            Browse, search, update, add, or delete question-answer pairs from a dedicated workspace
            that gives the list and the current editor enough room to breathe.
          </p>
        </div>
        <div className="hero-stats">
          <article>
            <span>{searchActive ? "Search results" : "Total questions"}</span>
            <strong>{questions.length}</strong>
          </article>
          <article>
            <span>Selection</span>
            <strong>{editor.id ? "Editing" : "New item"}</strong>
          </article>
        </div>
      </header>

      <section className="panel manager-layout">
        <div className="question-list-shell">
          <div className="panel-head">
            <div>
              <p className="panel-kicker">Qdrant list</p>
              <h3>Stored questions</h3>
            </div>
            <button
              className="ghost-button"
              onClick={() => void loadQuestions({ query: deferredSearch, selectedId: editor.id })}
              type="button"
            >
              Refresh
            </button>
          </div>

          <label className="field-shell compact">
            <span>Search</span>
            <input
              onChange={(event) => setSearch(event.target.value)}
              placeholder="Semantic search in Qdrant..."
              value={search}
            />
          </label>

          <div className="question-list spacious">
            {questionsPending ? (
              <p className="muted-copy">
                {searchActive ? "Searching questions in Qdrant..." : "Loading questions..."}
              </p>
            ) : null}
            {!questionsPending && questions.length === 0 ? (
              <p className="muted-copy">
                {searchActive ? "No semantic matches found in Qdrant." : "No questions in Qdrant."}
              </p>
            ) : null}

            {questions.map((item) => (
              <button
                className={`question-row ${editor.id === item.id ? "active" : ""}`}
                key={item.id}
                onClick={() =>
                  setEditor({
                    id: item.id,
                    question: item.question,
                    answer: item.answer
                  })
                }
                type="button"
              >
                <strong>{item.question}</strong>
                <span>{item.answer}</span>
                <em>{formatTimestamp(item.updated_at)}</em>
              </button>
            ))}
          </div>
        </div>

        <form className="editor-card editor-pane" onSubmit={handleSaveQuestion}>
          <div className="editor-head">
            <div>
              <p className="panel-kicker">Editor</p>
              <h3>{editor.id ? "Update selected question" : "Create a new question"}</h3>
            </div>
            <div className="chat-head-actions">
              {editor.id ? (
                <button className="ghost-button" onClick={handleStartNewQuestion} type="button">
                  Add FAQ
                </button>
              ) : null}
              <span className="mini-badge">{editor.id ? `ID ${editor.id}` : "New item"}</span>
            </div>
          </div>

          <label className="field-shell">
            <span>Question</span>
            <textarea
              onChange={(event) =>
                setEditor((current) => ({ ...current, question: event.target.value }))
              }
              placeholder="What should the user ask?"
              rows={4}
              value={editor.question}
            />
          </label>

          <label className="field-shell">
            <span>Answer</span>
            <textarea
              onChange={(event) =>
                setEditor((current) => ({ ...current, answer: event.target.value }))
              }
              placeholder="Write the answer that should be stored in Qdrant."
              rows={10}
              value={editor.answer}
            />
          </label>

          <p className="keyboard-hint">Save with the button below after editing the selected record.</p>
          {questionError ? <p className="error-text">{questionError}</p> : null}

          <div className="actions split">
            <button className="primary-button" disabled={savePending} type="submit">
              {savePending ? "Saving..." : editor.id ? "Update question" : "Add question"}
            </button>
            <button className="ghost-button" onClick={handleStartNewQuestion} type="button">
              {editor.id ? "Add FAQ" : "Clear"}
            </button>
            <button
              className="danger-button"
              disabled={!editor.id || deletePending}
              onClick={handleDeleteQuestion}
              type="button"
            >
              {deletePending ? "Deleting..." : "Delete"}
            </button>
          </div>
        </form>
      </section>
    </section>
  );
}
