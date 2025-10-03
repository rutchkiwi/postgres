-- create table insertconflicttest(key int4, fruit text);

-- create unique index op_index on insertconflicttest(key);

-- insert into insertconflicttest values (1, 'Apple') on conflict (key) do select returning OLD.*, NEW.*;;

BEGIN;
create table on_conflict_select_partitoned (a int primary key, b text) partition by list (a);
create table on_conflict_select_partitoned_p1 partition of on_conflict_select_partitoned for values in (1);
create table on_conflict_select_partitoned_p2 partition of on_conflict_select_partitoned for values in (2);

insert into on_conflict_select_partitoned values (1, 'xxx')
  on conflict (a) do select for update returning *;
insert into on_conflict_select_partitoned values (1, 'xxx')
  on conflict (a) do select for update returning *;
