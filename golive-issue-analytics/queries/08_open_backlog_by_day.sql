-- QUERY 08: Open Ticket Backlog at End of Each Go-Live Day
-- Question: "Is the command center keeping up, or is the backlog growing?"
-- Skills:   recursive CTE, point-in-time "open as of" logic

WITH RECURSIVE days(n, day_end) AS (
    SELECT 1, datetime('2026-10-01 23:59')
    UNION ALL
    SELECT n + 1, datetime(day_end, '+1 day') FROM days WHERE n < 14
)
SELECT d.n                                                       AS go_live_day,
       date(d.day_end)                                           AS date,
       COUNT(t.ticket_id)                                        AS open_at_end_of_day,
       SUM(CASE WHEN t.priority IN ('P1', 'P2') THEN 1 ELSE 0 END) AS open_p1_p2,
       SUM(CASE WHEN t.category = 'Application / Build' THEN 1 ELSE 0 END) AS open_build_requests
FROM days d
LEFT JOIN tickets t
       ON t.created_dt <= d.day_end
      AND (t.resolved_dt IS NULL OR t.resolved_dt > d.day_end)
GROUP BY d.n, d.day_end
ORDER BY d.n;
