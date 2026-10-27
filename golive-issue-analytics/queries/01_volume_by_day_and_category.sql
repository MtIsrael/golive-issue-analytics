-- QUERY 01: Ticket Volume by Go-Live Day and Category
-- Question: "When did volume peak, and what kinds of issues drove each day?"
-- Skills:   conditional aggregation (pivot), percent-of-total

SELECT go_live_day,
       COUNT(*)                                                        AS total_tickets,
       SUM(CASE WHEN category = 'Printing'            THEN 1 ELSE 0 END) AS printing,
       SUM(CASE WHEN category = 'Login / Access'      THEN 1 ELSE 0 END) AS login_access,
       SUM(CASE WHEN category = 'Hardware / Device'   THEN 1 ELSE 0 END) AS hardware,
       SUM(CASE WHEN category = 'Workflow / Training' THEN 1 ELSE 0 END) AS workflow,
       SUM(CASE WHEN category = 'Application / Build' THEN 1 ELSE 0 END) AS app_build,
       SUM(CASE WHEN category = 'Interface'           THEN 1 ELSE 0 END) AS interface,
       ROUND(100.0 * SUM(CASE WHEN category IN ('Printing', 'Login / Access', 'Hardware / Device')
                              THEN 1 ELSE 0 END) / COUNT(*), 1)         AS technical_pct
FROM tickets
GROUP BY go_live_day
ORDER BY go_live_day;
