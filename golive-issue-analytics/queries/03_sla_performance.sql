-- QUERY 03: Resolution Time vs SLA by Priority
-- Question: "Are we meeting resolution targets, and for which priorities are we falling behind?"
-- Skills:   join to a targets table, time math, SLA breach logic

SELECT t.priority,
       s.target_hours                                                         AS sla_hours,
       COUNT(*)                                                               AS resolved_tickets,
       ROUND(AVG((julianday(t.resolved_dt) - julianday(t.created_dt)) * 24), 1) AS avg_hours_to_resolve,
       SUM(CASE WHEN (julianday(t.resolved_dt) - julianday(t.created_dt)) * 24 > s.target_hours
                THEN 1 ELSE 0 END)                                            AS breached,
       ROUND(100.0 * SUM(CASE WHEN (julianday(t.resolved_dt) - julianday(t.created_dt)) * 24 <= s.target_hours
                              THEN 1 ELSE 0 END) / COUNT(*), 1)               AS met_sla_pct
FROM tickets t
JOIN sla_targets s ON s.priority = t.priority
WHERE t.status = 'Resolved'
  AND t.go_live_day >= 1
GROUP BY t.priority, s.target_hours
ORDER BY t.priority;
