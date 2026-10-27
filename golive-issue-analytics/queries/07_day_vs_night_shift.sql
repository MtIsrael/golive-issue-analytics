-- QUERY 07: Day vs Night Shift Support
-- Question: "Is overnight support coverage adequate?"
-- Skills:   grouping on two dimensions, response vs resolution metrics

SELECT shift,
       priority,
       COUNT(*)                                                                AS tickets,
       ROUND(AVG(first_response_min), 1)                                       AS avg_first_response_min,
       ROUND(AVG((julianday(resolved_dt) - julianday(created_dt)) * 24), 1)    AS avg_hours_to_resolve,
       ROUND(100.0 * SUM(resolved_at_elbow) / COUNT(*), 1)                     AS at_elbow_pct
FROM tickets
WHERE go_live_day >= 1
  AND status = 'Resolved'
GROUP BY shift, priority
ORDER BY priority, shift;
