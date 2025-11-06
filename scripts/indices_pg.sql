-- Enable trigram for fast ILIKE '%...%' searches
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- =======================
-- Employees
-- =======================
-- exact lookups
CREATE INDEX IF NOT EXISTS idx_emp_email         ON employees (email);
CREATE INDEX IF NOT EXISTS idx_emp_joined        ON employees (date_joined);
CREATE INDEX IF NOT EXISTS idx_emp_dept_id       ON employees (department_id);
CREATE INDEX IF NOT EXISTS idx_emp_proj_id       ON employees (project_id);

-- fuzzy searches (ILIKE '%term%')
CREATE INDEX IF NOT EXISTS idx_emp_first_name_trgm ON employees USING gin (first_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_emp_last_name_trgm  ON employees USING gin (last_name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_emp_title_trgm      ON employees USING gin (title gin_trgm_ops);

-- =======================
-- Departments / Projects
-- =======================
CREATE INDEX IF NOT EXISTS idx_dept_name_trgm   ON departments USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_proj_name_trgm   ON projects    USING gin (name gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_proj_client_trgm ON projects    USING gin (client gin_trgm_ops);

-- =======================
-- Attendance
-- =======================
CREATE INDEX IF NOT EXISTS idx_att_date         ON attendance (date);
CREATE INDEX IF NOT EXISTS idx_att_status       ON attendance (status);
CREATE INDEX IF NOT EXISTS idx_att_emp_id       ON attendance (employee_id);
-- common combined filter: date + status
CREATE INDEX IF NOT EXISTS idx_att_date_status  ON attendance (date, status);
