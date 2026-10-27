-- QUERY 04: At-the-Elbow Resolution Rate by Category
-- Question: "How much does floor (ATE) support keep off the command center's plate?"
-- Skills:   conditional aggregation, comparing two populations

SELECT category,
       COUNT(*)                                                             AS tickets,
       SUM(resolved_at_elbow)                                               AS fixed_at_elbow,
       ROUND(100.0 * SUM(resolved_at_elbow) / COUNT(*), 1)                  AS at_elbow_pct,
       ROUND(AVG(CASE WHEN resolved_at_elbow = 1
                      THEN (julianday(resolved_dt) - julianday(created_dt)) * 1440 END)) AS elbow_avg_minutes,
       ROUND(AVG(CASE WHEN resolved_at_elbow = 0
                      THEN (julianday(resolved_dt) - julianday(created_dt)) * 1440 END)) AS escalated_avg_minutes
FROM tickets
WHERE go_live_day >= 1
  AND status = 'Resolved'
GROUP BY category
ORDER BY at_elbow_pct DESC;
