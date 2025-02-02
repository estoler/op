WITH
reference_version AS (
  SELECT '13.2.1' AS minimum_version),
version_split AS (
  SELECT version AS current_version,
-- Split minimum_version strings
    CAST(SPLIT(minimum_version, ".", 0)AS int) AS min_ver_major,
    CAST(SPLIT(minimum_version, ".", 1)AS int) AS min_ver_minor,
    CAST(SPLIT(minimum_version, ".", 2)AS int) AS min_ver_patch,
-- Split installed_version strings
    COALESCE(major, 0) AS current_ver_major,
    COALESCE(minor, 0) AS current_ver_minor,
    COALESCE(patch, 0) AS current_ver_patch
   FROM os_version
   LEFT JOIN reference_version
),
failure_logic AS (
  SELECT *,
    CASE
-- Scope to only 13.x devices
      WHEN  current_ver_major = 13
       AND (
-- Check major versions
           (min_ver_major >  current_ver_major)
-- Check minor versions
        OR (
            min_ver_major >= current_ver_major
        AND min_ver_minor >  current_ver_minor)
-- Check patch versions
        OR (
            min_ver_major >= current_ver_major
        AND min_ver_minor >= current_ver_minor
        AND min_ver_patch >  current_ver_patch)
    )
      THEN 'FAIL'
-- Passing Condition: Pass all 12.x versions or < 13.2.1 versions
      WHEN current_ver_major < 13
        OR (
           min_ver_major <= current_ver_major
       AND min_ver_minor <= current_ver_minor
       AND min_ver_patch <=  current_ver_patch
    )
      THEN 'PASS'
      ELSE 'UNKNOWN'
    END AS KOLIDE_CHECK_STATUS
  FROM version_split
)
SELECT * FROM failure_logic;

WITH _minimum_version(check_version) AS (VALUES
  ('8.10.38')
)
SELECT display_name AS name, bundle_version AS version, path,
  CASE
    WHEN bundle_version IS NULL THEN 'INAPPLICABLE'
    WHEN bundle_version >= check_version COLLATE VERSION THEN 'PASS'
    WHEN bundle_version BETWEEN SUBSTR(check_version, 1, 1) AND check_version COLLATE VERSION THEN 'FAIL'
    ELSE 'UNKNOWN'
  END AS KOLIDE_CHECK_STATUS
FROM _minimum_version
LEFT JOIN apps ON bundle_identifier = 'com.1password.1password' COLLATE NOCASE;