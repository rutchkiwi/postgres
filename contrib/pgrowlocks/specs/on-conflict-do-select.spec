# Tests for ON CONFLICT DO SELECT with row-level locking

setup
{
  CREATE TABLE conflict_test (key int PRIMARY KEY, val text);
  INSERT INTO conflict_test VALUES (1, 'original');
}

teardown
{
  DROP TABLE conflict_test;
}

session s1
step s1_begin { BEGIN; }
step s1_doselect_nolock { INSERT INTO conflict_test VALUES (1, 'new') ON CONFLICT (key) DO SELECT RETURNING *; }
step s1_doselect_keyshare { INSERT INTO conflict_test VALUES (1, 'new') ON CONFLICT (key) DO SELECT FOR KEY SHARE RETURNING *; }
step s1_doselect_share { INSERT INTO conflict_test VALUES (1, 'new') ON CONFLICT (key) DO SELECT FOR SHARE RETURNING *; }
step s1_doselect_nokeyupd { INSERT INTO conflict_test VALUES (1, 'new') ON CONFLICT (key) DO SELECT FOR NO KEY UPDATE RETURNING *; }
step s1_doselect_update { INSERT INTO conflict_test VALUES (1, 'new') ON CONFLICT (key) DO SELECT FOR UPDATE RETURNING *; }
step s1_rollback { ROLLBACK; }

session s2
step s2_rowlocks { SELECT locked_row, multi, modes FROM pgrowlocks('conflict_test'); }

# Test 1: No locking - should not show in pgrowlocks
permutation s1_begin s1_doselect_nolock s2_rowlocks s1_rollback

# Test 2: FOR KEY SHARE - should show lock
permutation s1_begin s1_doselect_keyshare s2_rowlocks s1_rollback

# Test 3: FOR SHARE - should show lock
permutation s1_begin s1_doselect_share s2_rowlocks s1_rollback

# Test 4: FOR NO KEY UPDATE - should show lock
permutation s1_begin s1_doselect_nokeyupd s2_rowlocks s1_rollback

# Test 5: FOR UPDATE - should show lock
permutation s1_begin s1_doselect_update s2_rowlocks s1_rollback
