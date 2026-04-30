-- Q1_optimized: The original query suffers from inefficient filtering and grouping due to the use of the `DATE(last_login)` function in the `WHERE` clause and `GROUP BY` clause. This prevents the database from effectively using standard B-tree indexes on `last_login` alone. By creating a composite index on `(last_login DESC, country_code)`, we enable PostgreSQL to: 
1. Efficiently filter records for the last 30 days using the `last_login` part of the index. 
2. Directly support the grouping by `country_code` for the filtered set of rows.
3. Support the `ORDER BY login_date DESC` because the `last_login` values are already ordered in descending order, and `DATE(last_login)` will maintain this relative order. 

While the `DATE(last_login)` is still applied in the `SELECT` and `GROUP BY`, the index significantly reduces the number of rows that need to be processed and grouped. The `DESC` on `last_login` in the index aligns with the `ORDER BY login_date DESC` clause, further optimizing the sorting part.
-- Expected benefit: Significant performance improvement, especially on large `users` tables. The query execution time is expected to decrease from potentially minutes to seconds or milliseconds. This is due to avoiding a full table scan or a less efficient index scan, and enabling much faster filtering and grouping. The index also helps with the sorting phase.
-- Risks: The primary risk is the overhead associated with maintaining the new index. Every `INSERT`, `UPDATE`, and `DELETE` operation on the `users` table will now incur a slight performance penalty to update `idx_users_last_login_country_code`. However, for a read-heavy query like this, the benefits of the index will almost certainly outweigh the write costs. It's also important to monitor the index's usage to ensure it remains effective over time.
SELECT DATE(last_login) as login_date, country_code, COUNT(*) as dau
FROM users
WHERE last_login >= NOW() - INTERVAL '30 days'
GROUP BY DATE(last_login), country_code
ORDER BY login_date DESC, dau DESC;;

CREATE INDEX idx_users_last_login_country_code ON users (last_login DESC, country_code);;

-- Q2: The original query's performance is hindered by the lack of an index that can efficiently filter `positions` by `status` and simultaneously support the join with `accounts`. The new index `idx_positions_status_account_id` on `(status, account_id)` is a composite index. It allows PostgreSQL to quickly find all rows where `status = 'open'` and then efficiently use `account_id` for the join with the `accounts` table. The existing indexes on `accounts(user_id)` and `users(email)` are retained as they are beneficial for the respective joins. The `GROUP BY` and `ORDER BY` clauses will operate on a significantly smaller, pre-filtered dataset due to the improved indexing, leading to a more efficient execution plan. The `ORDER BY` clause will benefit from the fact that the `SUM(p.pnl)` is calculated on a filtered set, and the final sort will be on a potentially smaller set of aggregated results.
-- Expected benefit: Significant performance improvement, especially for large `positions` tables. The query execution time is expected to decrease from potentially minutes to seconds or milliseconds, as the database will avoid full table scans and inefficient join strategies. The filtering on `p.status = 'open'` will be very fast, and the subsequent joins will be more efficient.
-- Risks: The primary risk is the overhead associated with maintaining the new index. For very high write workloads on the `positions` table, the new index might slightly increase the time for INSERT, UPDATE, and DELETE operations. However, for read-heavy workloads and queries like this one, the performance gains from the index will far outweigh the write overhead. It's crucial to monitor index usage and performance after deployment.
SELECT u.email, a.currency, SUM(p.pnl) AS total_pnl, COUNT(p.id) AS position_count
FROM positions p
JOIN accounts a ON p.account_id = a.id
JOIN users u ON a.user_id = u.id
WHERE p.status = 'open'
GROUP BY u.email, a.currency
ORDER BY total_pnl DESC;;

CREATE INDEX idx_positions_status_account_id ON positions (status, account_id);;
CREATE INDEX idx_accounts_user_id ON accounts (user_id);;
CREATE INDEX idx_users_email ON users (email);;

-- Q3: The original query lacked an index on `transactions.account_id` which is crucial for the join with `accounts`. The optimized query adds a composite index `idx_transactions_account_id_type_status_created_at` on `transactions`. This index covers the join column (`account_id`), the filtering conditions (`transaction_type`, `status`), and the ordering column (`created_at`). By including `created_at DESC` in the index, PostgreSQL can potentially use the index for both filtering (last 90 days) and sorting, avoiding a separate sort operation. The `INNER JOIN` syntax is more explicit than the implicit `JOIN` used in the original query, though functionally equivalent. `idx_users_id` is added for completeness, though `users.id` is already indexed as the PRIMARY KEY.
-- Expected benefit: Significant performance improvement, especially on large `transactions` tables. The query should be much faster due to efficient index usage for joins, filtering, and sorting. The query planner will be able to find matching rows in `transactions` much quicker and avoid a full table scan. The sort operation, if performed by the index, will be extremely fast.
-- Risks: The primary risk is the overhead of maintaining the new index. For very high write volumes on the `transactions` table, the index maintenance might slightly increase write latency. However, for read-heavy workloads or moderate write volumes, the performance gains for this specific query will likely outweigh this overhead. Ensure that the `NOW() - INTERVAL '90 days'` filter is applied efficiently by the index. The `created_at DESC` in the index definition is important for the `ORDER BY` clause.
SELECT t.reference, t.amount, t.currency, t.created_at, t.processed_at, u.email, u.country_code, EXTRACT(EPOCH FROM (t.processed_at - t.created_at)) / 3600 AS processing_hours FROM transactions t INNER JOIN accounts a ON t.account_id = a.id INNER JOIN users u ON a.user_id = u.id WHERE t.transaction_type = 'withdrawal' AND t.status = 'completed' AND t.created_at >= NOW() - INTERVAL '90 days' ORDER BY t.created_at DESC;;

CREATE INDEX idx_transactions_account_id_type_status_created_at ON transactions (account_id, transaction_type, status, created_at DESC);;
CREATE INDEX idx_accounts_user_id ON accounts(user_id);;
CREATE INDEX idx_users_id ON users(id);;

-- Q4: The original query suffered from a potential full table scan due to the `WHERE u.created_at >= '2024-01-01'` clause. The optimization involves adding indexes to support this filter and the subsequent grouping and aggregation. 

1. `idx_users_created_at`: This index directly supports the `WHERE u.created_at >= '2024-01-01'` clause, allowing PostgreSQL to quickly identify the relevant rows. 
2. `idx_users_country_code_created_at`: This composite index is beneficial for the `GROUP BY u.country_code` and the `WHERE u.created_at >= '2024-01-01'` clause. It can help satisfy both filtering and grouping more efficiently. 
3. `idx_users_kyc_status`: While `COUNT(*) FILTER` can be optimized by the query planner using other indexes, having an index on `kyc_status` can further assist in quickly counting rows based on these conditions, especially if the data distribution is skewed. 
4. `idx_users_created_at_last_login`: This index can help with the calculation of `avg_days_to_first_login` by providing quick access to `created_at` and `last_login` for the filtered rows. 

Additionally, casting '2024-01-01' to `timestamptz` ensures type consistency with the `created_at` column. Using `86400.0` instead of `86400` for division ensures floating-point division, which is generally expected for average calculations.
-- Expected benefit: Significant performance improvement, especially on large 'users' tables. The query execution time is expected to reduce from potentially minutes to seconds or milliseconds. The addition of indexes will make the filtering on `created_at` much faster, and the subsequent grouping and aggregations will operate on a much smaller, pre-filtered dataset.
-- Risks: The primary risk is the overhead associated with maintaining these new indexes. Inserts, updates, and deletes on the 'users' table will become slightly slower. However, for read-heavy workloads like this query, the performance gains typically outweigh the write overhead. It's crucial to monitor the write performance after index creation and consider their necessity if write operations become a bottleneck.
SELECT u.country_code,
       COUNT(*) FILTER (WHERE u.kyc_status = 'verified') as verified,
       COUNT(*) FILTER (WHERE u.kyc_status = 'pending') as pending,
       COUNT(*) FILTER (WHERE u.kyc_status = 'rejected') as rejected,
       AVG(EXTRACT(EPOCH FROM (u.last_login - u.created_at)) / 86400.0) as avg_days_to_first_login
FROM users u
WHERE u.created_at >= '2024-01-01'::timestamptz
GROUP BY u.country_code
ORDER BY verified DESC;;

CREATE INDEX idx_users_created_at ON users(created_at);;
CREATE INDEX idx_users_country_code_created_at ON users(country_code, created_at);;
CREATE INDEX idx_users_kyc_status ON users(kyc_status);;
CREATE INDEX idx_users_created_at_last_login ON users(created_at, last_login);;

-- Q5: The primary bottleneck in the original query was the inefficient filtering on the JSONB 'metadata' column. The '@>' operator, while powerful, requires a full scan of the 'audit_log' table if there isn't a suitable index. By adding a GIN index on the 'metadata' column, PostgreSQL can efficiently locate rows where the JSONB contains the specified key-value pair ('{"account_id": 12345}'). The explicit cast '::jsonb' ensures the literal is treated as JSONB, which is good practice though often inferred. The rest of the query structure (JOIN, date filtering, ORDER BY) is standard and efficient given the existing indexes.
-- Expected benefit: Significant performance improvement, especially for large 'audit_log' tables. The query will transition from a full table scan on 'audit_log' to an index scan, drastically reducing the number of rows that need to be examined. This will result in much faster query execution times, potentially reducing latency from seconds or minutes to milliseconds.
-- Risks: The main risk is the overhead associated with maintaining the GIN index. GIN indexes are generally larger and slower to update than B-tree indexes. If the 'audit_log' table experiences a very high rate of writes and updates, the index maintenance could become a performance bottleneck for write operations. However, for read-heavy workloads or moderately busy tables, the benefits of the GIN index for this specific query will likely outweigh the write overhead. The index also consumes disk space.
SELECT al.created_at, al.action, al.ip_address, al.metadata, u.email, u.country_code
FROM audit_log al
JOIN users u ON al.user_id = u.id
WHERE al.metadata @> '{"account_id": 12345}'::jsonb
  AND al.created_at >= NOW() - INTERVAL '7 days'
ORDER BY al.created_at DESC;;

CREATE INDEX idx_audit_log_metadata ON audit_log USING GIN (metadata);;

