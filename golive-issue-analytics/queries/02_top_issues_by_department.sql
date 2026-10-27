-- QUERY 02: Top 3 Issues per Department (Go-Live Days 1-3)
-- Question: "Where should we stage extra ATE and technical staff for the first 72 hours?"
-- Skills:   window function RANK() for top-N-per-group

WITH counts AS (
    SELECT d.name AS department,
           t.subcategory,
           t.category,
           COUNT(*) AS tickets,
           RANK() OVER (PARTITION BY d.name ORDER BY COUNT(*) DESC) AS rnk
    FROM tickets t
    JOIN departments d ON d.department_id = t.department_id
    WHERE t.go_live_day BETWEEN 1 AND 3
    GROUP BY d.name, t.subcategory, t.category
)
SELECT department, rnk AS rank, subcategory, category, tickets
FROM counts
WHERE rnk <= 3
ORDER BY department, rnk, tickets DESC;
