-- QUERY 06: Repeat-Offender Devices
-- Question: "Which specific devices keep generating tickets? Pull them for swap-out."
-- Skills:   GROUP BY + HAVING, GROUP_CONCAT, joining four tables

SELECT w.device_name,
       w.device_type,
       d.name                                    AS department,
       w.location,
       r.final_status                            AS tdr_status,
       COUNT(*)                                  AS golive_tickets,
       GROUP_CONCAT(DISTINCT t.subcategory)      AS issues_reported
FROM tickets t
JOIN workstations w ON w.workstation_id = t.workstation_id
JOIN departments  d ON d.department_id  = w.department_id
JOIN tdr_results  r ON r.workstation_id = w.workstation_id
WHERE t.go_live_day >= 1
GROUP BY w.workstation_id
HAVING COUNT(*) >= 4
ORDER BY golive_tickets DESC;
