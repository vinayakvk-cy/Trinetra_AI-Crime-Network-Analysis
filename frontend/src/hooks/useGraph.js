import { useCallback, useEffect, useState } from "react";

import {
  getGraphHealth,
  getGraphStats,
  getNeighborhood,
  getEntityRelationships,
  getShortestPath,
  normalizeRelationships,
} from "../services/graphApi";

export function useGraph() {
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);

  const [relationships, setRelationships] = useState([]);
  const [neighborhood, setNeighborhood] = useState(null);
  const [shortestPath, setShortestPath] = useState(null);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  /**
   * Load basic graph health and statistics.
   */
  const loadGraph = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [healthResult, statsResult] =
        await Promise.all([
          getGraphHealth(),
          getGraphStats(),
        ]);

      setHealth(healthResult);
      setStats(statsResult);

      return {
        health: healthResult,
        stats: statsResult,
      };
    } catch (err) {
      const message =
        err?.response?.data?.detail ||
        err?.message ||
        "Failed to load graph data.";

      setError(message);

      throw err;
    } finally {
      setLoading(false);
    }
  }, []);

  /**
   * Load an entity neighborhood from Neo4j.
   */
  const loadNeighborhood = useCallback(
    async ({
      entityType,
      entityValue,
      depth = 1,
      limit = 100,
    }) => {
      setLoading(true);
      setError(null);

      try {
        const result = await getNeighborhood({
          entityType,
          entityValue,
          depth,
          limit,
        });

        setNeighborhood(result);

        /*
         * Neighborhood responses contain relationship
         * arrays inside each returned path.
         *
         * Flatten them so graph components can consume
         * a simple relationship collection.
         */
        const flattened = [];

        if (Array.isArray(result?.results)) {
          result.results.forEach((item) => {
            if (!Array.isArray(item?.relationships)) {
              return;
            }

            item.relationships.forEach((relationship) => {
              flattened.push({
                ...relationship,

                source_id:
                  item.start_id || null,

                source_type:
                  item.start_type || null,

                source_value:
                  item.start_value || null,

                target_id:
                  item.neighbor_id || null,

                target_type:
                  item.neighbor_type || null,

                target_value:
                  item.neighbor_value || null,
              });
            });
          });
        }

        setRelationships(
          normalizeRelationships(flattened)
        );

        return result;
      } catch (err) {
        const message =
          err?.response?.data?.detail ||
          err?.message ||
          "Failed to load entity neighborhood.";

        setError(message);

        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Load direct relationships for an entity.
   */
  const loadRelationships = useCallback(
    async ({ entityType, entityValue }) => {
      setLoading(true);
      setError(null);

      try {
        const result = await getEntityRelationships({
          entityType,
          entityValue,
        });

        const normalized =
          normalizeRelationships(result);

        setRelationships(normalized);

        return result;
      } catch (err) {
        const message =
          err?.response?.data?.detail ||
          err?.message ||
          "Failed to load entity relationships.";

        setError(message);

        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Trace the shortest path between two entities.
   */
  const traceShortestPath = useCallback(
    async ({
      sourceType,
      sourceValue,
      targetType,
      targetValue,
      maxDepth = 6,
    }) => {
      setLoading(true);
      setError(null);

      try {
        const result = await getShortestPath({
          sourceType,
          sourceValue,
          targetType,
          targetValue,
          maxDepth,
        });

        setShortestPath(result);

        return result;
      } catch (err) {
        const message =
          err?.response?.data?.detail ||
          err?.message ||
          "Failed to trace shortest path.";

        setError(message);

        throw err;
      } finally {
        setLoading(false);
      }
    },
    []
  );

  /**
   * Clear the currently selected graph data.
   */
  const clearGraphSelection = useCallback(() => {
    setNeighborhood(null);
    setShortestPath(null);
    setRelationships([]);
    setError(null);
  }, []);

  /**
   * Automatically load graph health/stats when the
   * hook is first mounted.
   */
  useEffect(() => {
    loadGraph().catch(() => {
      // Error is already stored in state.
    });
  }, [loadGraph]);

  return {
    health,
    stats,

    relationships,
    neighborhood,
    shortestPath,

    loading,
    error,

    loadGraph,
    loadNeighborhood,
    loadRelationships,
    traceShortestPath,
    clearGraphSelection,
  };
}