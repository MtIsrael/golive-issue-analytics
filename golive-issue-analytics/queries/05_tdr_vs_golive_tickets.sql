-- QUERY 05: Did TDR Predict Go-Live Problems?
-- Question: "Devices that failed Technical Device Readiness testing: did they
--            cause more go-live tickets than devices that passed?"
-- Skills:   LEFT JOIN with aggregation, per-unit rate, comparing cohorts

WITH device_tickets AS (
    SELECT w.workstation_id,
           r.final_status,
           COUNT(t.ticket_id) AS tickets
    FROM workstations w
    JOIN tdr_results r   ON r.workstation_id = w.workstation_id
    LEFT JOIN tickets t  ON t.workstation_id = w.workstation_id
                        AND t.go_live_day >= 1
    GROUP BY w.workstation_id, r.final_status
)
SELECT final_status                                   AS tdr_status,
       COUNT(*)                                       AS devices,
       SUM(tickets)                                   AS golive_tickets,
       ROUND(1.0 * SUM(tickets) / COUNT(*), 2)        AS tickets_per_device,
       SUM(CASE WHEN tickets >= 3 THEN 1 ELSE 0 END)  AS devices_with_3plus_tickets
FROM device_tickets
GROUP BY final_status
ORDER BY tickets_per_device DESC;
