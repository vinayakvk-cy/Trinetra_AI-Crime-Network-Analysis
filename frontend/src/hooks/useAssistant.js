import { useCallback, useState } from "react";

import {
  askAssistant,
  askInvestigationAssistant,
  getAssistantContext,
  getAssistantHealth,
  extractAssistantAnswer,
  extractAssistantSources,
  extractAssistantContext,
} from "../services/assistantApi";

export function useAssistant(
  investigationId = null
) {
  const [messages, setMessages] = useState([]);

  const [context, setContext] = useState([]);
  const [sources, setSources] = useState([]);

  const [health, setHealth] = useState(null);

  const [loading, setLoading] = useState(false);
  const [contextLoading, setContextLoading] =
    useState(false);

  const [error, setError] = useState(null);

  /**
   * Add a message to the conversation.
   */
  const addMessage = useCallback(
    (message) => {
      setMessages((current) => [
        ...current,
        message,
      ]);
    },
    []
  );

  /**
   * Clear the conversation.
   */
  const clearMessages = useCallback(() => {
    setMessages([]);
    setSources([]);
    setError(null);
  }, []);

  /**
   * Ask the general assistant.
   */
  const ask = useCallback(
    async ({
      question,
      entityId = null,
    } = {}) => {
      if (!question || !question.trim()) {
        throw new Error(
          "Assistant question is required."
        );
      }

      setLoading(true);
      setError(null);

      const userMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: question.trim(),
        timestamp: new Date().toISOString(),
      };

      setMessages((current) => [
        ...current,
        userMessage,
      ]);

      try {
        const result = await askAssistant({
          question: question.trim(),
          investigationId,
          entityId,
        });

        const answer =
          extractAssistantAnswer(result);

        const resultSources =
          extractAssistantSources(result);

        setSources(resultSources);

        const assistantMessage = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content:
            answer ||
            "The assistant returned no answer.",
          sources: resultSources,
          timestamp: new Date().toISOString(),
        };

        setMessages((current) => [
          ...current,
          assistantMessage,
        ]);

        return result;
      } catch (err) {
        const message =
          (typeof err?.response?.data?.detail === "string" ? err.response.data.detail : err?.response?.data?.detail?.message || err?.response?.data?.detail?.msg) ||
          err?.message ||
          "Assistant request failed.";

        setError(message);

        const errorMessage = {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          content: `Unable to answer the question: ${message}`,
          error: true,
          timestamp: new Date().toISOString(),
        };

        setMessages((current) => [
          ...current,
          errorMessage,
        ]);

        throw err;
      } finally {
        setLoading(false);
      }
    },
    [investigationId]
  );

  /**
   * Ask specifically about the active investigation.
   */
  const askInvestigation = useCallback(
    async (question) => {
      if (!investigationId) {
        throw new Error(
          "Investigation ID is required."
        );
      }

      if (!question || !question.trim()) {
        throw new Error(
          "Assistant question is required."
        );
      }

      setLoading(true);
      setError(null);

      const userMessage = {
        id: `user-${Date.now()}`,
        role: "user",
        content: question.trim(),
        timestamp: new Date().toISOString(),
      };

      setMessages((current) => [
        ...current,
        userMessage,
      ]);

      try {
        const result =
          await askInvestigationAssistant(
            investigationId,
            question.trim()
          );

        const answer =
          extractAssistantAnswer(result);

        const resultSources =
          extractAssistantSources(result);

        setSources(resultSources);

        const assistantMessage = {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content:
            answer ||
            "The investigation assistant returned no answer.",
          sources: resultSources,
          timestamp: new Date().toISOString(),
        };

        setMessages((current) => [
          ...current,
          assistantMessage,
        ]);

        return result;
      } catch (err) {
        const message =
          (typeof err?.response?.data?.detail === "string" ? err.response.data.detail : err?.response?.data?.detail?.message || err?.response?.data?.detail?.msg) ||
          err?.message ||
          "Investigation assistant request failed.";

        setError(message);

        const errorMessage = {
          id: `assistant-error-${Date.now()}`,
          role: "assistant",
          content: `Unable to answer the investigation question: ${message}`,
          error: true,
          timestamp: new Date().toISOString(),
        };

        setMessages((current) => [
          ...current,
          errorMessage,
        ]);

        throw err;
      } finally {
        setLoading(false);
      }
    },
    [investigationId]
  );

  /**
   * Retrieve the context currently available to
   * the assistant.
   */
  const loadContext = useCallback(
    async ({
      entityId = null,
      memoryLimit = 10,
    } = {}) => {
      setContextLoading(true);
      setError(null);

      try {
        const result =
          await getAssistantContext({
            investigationId,
            entityId,
            memoryLimit,
          });

        const records =
          extractAssistantContext(result);

        setContext(records);

        return records;
      } catch (err) {
        const message =
          (typeof err?.response?.data?.detail === "string" ? err.response.data.detail : err?.response?.data?.detail?.message || err?.response?.data?.detail?.msg) ||
          err?.message ||
          "Failed to load assistant context.";

        setError(message);

        throw err;
      } finally {
        setContextLoading(false);
      }
    },
    [investigationId]
  );

  /**
   * Check the assistant service.
   */
  const checkHealth = useCallback(async () => {
    try {
      const result =
        await getAssistantHealth();

      setHealth(result);

      return result;
    } catch (err) {
      setHealth({
        success: false,
        error:
          (typeof err?.response?.data?.detail === "string" ? err.response.data.detail : err?.response?.data?.detail?.message || err?.response?.data?.detail?.msg) ||
          err?.message ||
          "Assistant health check failed.",
      });

      throw err;
    }
  }, []);

  /**
   * Send a suggested question.
   */
  const askSuggestedQuestion =
    useCallback(
      async (question, entityId = null) => {
        return ask({
          question,
          entityId,
        });
      },
      [ask]
    );

  return {
    messages,

    context,
    sources,

    health,

    loading,
    contextLoading,

    error,

    ask,
    askInvestigation,
    askSuggestedQuestion,

    loadContext,
    checkHealth,

    addMessage,
    clearMessages,
  };
}