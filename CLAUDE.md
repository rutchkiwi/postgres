We're implementing the ON CONFLCIT .. DO SELECT feature.

We've done the partitioning stuff.

Here is the mailing list thread for context:
INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Lists: 	pgsql-hackers
From: 	Andreas Karlsson <andreas(at)proxel(dot)se>
To: 	pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, Marko Tiikkaja <marko(at)joh(dot)to>
Subject: 	INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2024-12-01 17:47:20
Message-ID: 	2b5db2e6-8ece-44d0-9890-f256fdca9f7e@proxel.se
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

Hi!


This, ON CONFLICT DO SELECT, is a feature I have wished for ever since 
ON CONFLICT was added to PostgreSQL and I have worked with several code 
bases where it would have been useful. So now I finally got round to 
revive and rebase Marko's old patch.


Marko originally posted the patch back in 2017[1], but discussion sadly 
died and the patch bitrotted heavily (especially due to pluggable table 
AMs).


The patch is very similar to Marko's original but with some fixes like 
support for EXPLAIN, clean up, a bug-fix and heavy changes to move it 
from PG 11 to master.


This patch adds support both for SELECT with locking of the tuples (at a 
lock level the user can specify) and SELECT without any locking. I 
personally find both useful. There is no need to take any locks if you 
are just fetching the tuples and sending them back to the client and 
directly committing the transaction.


Without lock:


INSERT INTO testtab (key, fruit)
VALUES (1, 'Apple')
ON CONFLICT (key) DO SELECT FOR UPDATE
RETURNING *;


With lock:


INSERT INTO testtab (key, fruit)
VALUES (1, 'Apple')
ON CONFLICT (key) DO SELECT
RETURNING *;


What do you think? Is the current propose syntax good? Any other 
thoughts? If there is interest I will keep working on this patch.


Remaining work:


- Make sure it works with row level security correctly
- Verify that partitions are supported correctly
- Clean up code
- Clean up tests
- Write more comments
- Improve documentation (e.g. we may need to update documentation for 
CREATE POLICY)


References


1. 
https://www.postgresql.org/message-id/CAL9smLCdV-v3KgOJX3mU19FYK82N7yzqJj2HAwWX70E%3DP98kgQ%40mail.gmail.com


Andreas
Attachment 	Content-Type 	Size
v2-0001-Add-support-for-ON-CONFLICT-DO-SELECT-FOR.patch 	text/x-patch 	32.1 KB
From: 	Andreas Karlsson <andreas(at)proxel(dot)se>
To: 	pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, Marko Tiikkaja <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2024-12-03 08:52:43
Message-ID: 	e82b9888-602b-4a68-965b-4a3ed272d6e4@proxel.se
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

Hi,


Here is an updated version of the patch which fixes a few small bugs, 
including making sure it checks the update permission plus a bug found 
by Joel Jacobsson when it was called by SPI.


Andreas
Attachment 	Content-Type 	Size
v3-0001-Add-support-for-ON-CONFLICT-DO-SELECT-FOR.patch 	text/x-patch 	33.5 KB
From: 	"Joel Jacobson" <joel(at)compiler(dot)org>
To: 	"Andreas Karlsson" <andreas(at)proxel(dot)se>, pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, "Marko Tiikkaja" <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2024-12-03 10:24:26
Message-ID: 	5e8b911c-c274-4dbb-a143-cd8a7e6a03b9@app.fastmail.com
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

On Tue, Dec 3, 2024, at 09:52, Andreas Karlsson wrote:
> Hi,
>
> Here is an updated version of the patch which fixes a few small bugs, 
> including making sure it checks the update permission plus a bug found 
> by Joel Jacobsson when it was called by SPI.


+1 for this feature.


This seems especially useful when designing idempotent APIs.
Neat to only need a single statement, for what we
currently need two separate statements for.


Here is an attempt of a realistic example:


CREATE OR REPLACE FUNCTION get_or_create_license_key(_user_id bigint, _product_id bigint)
RETURNS UUID BEGIN ATOMIC
    INSERT INTO licenses (user_id, product_id)
    VALUES (_user_id, _product_id)
    ON CONFLICT (user_id, product_id) DO NOTHING;
    SELECT license_key
    FROM licenses
    WHERE user_id = _user_id
    AND product_id = _product_id;
END;


This can be simplified into:


CREATE OR REPLACE FUNCTION get_or_create_license_key(_user_id bigint, _product_id bigint)
RETURNS UUID BEGIN ATOMIC
    INSERT INTO licenses (user_id, product_id)
    VALUES (_user_id, _product_id)
    ON CONFLICT (user_id, product_id) DO SELECT RETURNING license_key;
END;


I've tested the patch successfully and also looked at the code briefly
and at first glance think it looks nice and clean.


/Joel


From: 	Andreas Karlsson <andreas(at)proxel(dot)se>
To: 	Joel Jacobson <joel(at)compiler(dot)org>, pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, Marko Tiikkaja <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2024-12-17 10:45:52
Message-ID: 	1ba45f71-f0de-479e-878d-8d71fb572484@proxel.se
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

On 12/3/24 11:24 AM, Joel Jacobson wrote:
> I've tested the patch successfully and also looked at the code briefly
> and at first glance think it looks nice and clean.


Thanks for the interest!


Here is an updated version which adds support for RLS. I am not 100% 
sure that my choices for RLS are correct since I decided to, similar to 
ON CONFLICT DO UPDATE, throw an error if the RLS checks fail rather than 
filter the RETURNING tuples using the RLS USING clause. I can see a case 
for either and am not familiar enough with RLS to have a good intuition 
for which.


Andreas
Attachment 	Content-Type 	Size
v4-0001-Add-support-for-ON-CONFLICT-DO-SELECT-FOR.patch 	text/x-patch 	37.5 KB
From: 	Andreas Karlsson <andreas(at)proxel(dot)se>
To: 	Joel Jacobson <joel(at)compiler(dot)org>, pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, Marko Tiikkaja <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2025-03-04 09:24:07
Message-ID: 	c01d7ee4-d50b-4faf-95f5-7fb76fceb93d@proxel.se
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

Hi,


Rebased the patch to add support for OLD.* and NEW.*.


Andreas
Attachment 	Content-Type 	Size
v5-0001-Add-support-for-ON-CONFLICT-DO-SELECT-FOR.patch 	text/x-patch 	51.4 KB
From: 	Andreas Karlsson <andreas(at)proxel(dot)se>
To: 	Joel Jacobson <joel(at)compiler(dot)org>, pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, Marko Tiikkaja <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2025-03-05 02:32:57
Message-ID: 	16551b07-a78d-43f1-9a73-2048dc90b9e8@proxel.se
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

On 3/4/25 10:24 AM, Andreas Karlsson wrote:
> Rebased the patch to add support for OLD.* and NEW.*.


Apparently the CI did not like that version.


Andreas
Attachment 	Content-Type 	Size
v6-0001-Add-support-for-ON-CONFLICT-DO-SELECT-FOR.patch 	text/x-patch 	51.4 KB
From: 	"Joel Jacobson" <joel(at)compiler(dot)org>
To: 	"Andreas Karlsson" <andreas(at)proxel(dot)se>, pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, "Marko Tiikkaja" <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2025-03-07 18:51:53
Message-ID: 	86f7d50e-0b2b-4339-bea6-23deb423aa19@app.fastmail.com
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

On Wed, Mar 5, 2025, at 03:32, Andreas Karlsson wrote:
> On 3/4/25 10:24 AM, Andreas Karlsson wrote:
>> Rebased the patch to add support for OLD.* and NEW.*.
>
> Apparently the CI did not like that version.
>
> Andreas
>
> Attachments:
> * v6-0001-Add-support-for-ON-CONFLICT-DO-SELECT-FOR.patch


+1 This patch adds a very useful feature.


I looked over the patch and noted that it touches some areas and concepts that
I don't feel sufficiently familiar with. For that reason, I'm removing myself
as a reviewer, hoping that someone with the appropriate expertise will step in.


That said, I read through the entire patch, and everything—code, comments, tests,
and documentation—appears tidy and well-structured. I didn't spot any obvious
errors or issues.


I did notice a couple of minor nits in the comments:


- The word "strength" is misspelled as "strength" in a few places.
- There's an extra "if" in the comment "Returns true if if we're done."


Overall, the patch looks solid to me.


/Joel


From: 	Kirill Reshke <reshkekirill(at)gmail(dot)com>
To: 	Andreas Karlsson <andreas(at)proxel(dot)se>
Cc: 	Joel Jacobson <joel(at)compiler(dot)org>, pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, Marko Tiikkaja <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2025-03-10 13:05:22
Message-ID: 	CALdSSPiVBc66zqmMCA8oT9wa1rTEDVGCZ4tPQisruLF+iGzLVw@mail.gmail.com
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

On Wed, 5 Mar 2025 at 07:33, Andreas Karlsson <andreas(at)proxel(dot)se> wrote:
>
> On 3/4/25 10:24 AM, Andreas Karlsson wrote:
> > Rebased the patch to add support for OLD.* and NEW.*.
>
> Apparently the CI did not like that version.
>
> Andreas


Hi!
Applied v6.


1) Should we answer INSERT 0 10 here?


```
reshke=# table tt ;
 i
---
 1
 2
 3
 4
 5
(5 rows)
reshke=# insert into tt values(5) on conflict (i) do select returning *;
 i
---
 5
(1 row)


INSERT 0 1
```


2)  PostgreSQL fails with this query:


> reshke=*# insert into tt values(5) on conflict (i) do select for update returning *;
> server closed the connection unexpectedly
>    This probably means the server terminated abnormally
    before or while processing the request.
The connection to the server was lost. Attempting reset: Failed.
The connection to the server was lost. Attempting reset: Failed.
!?>


```
Program received signal SIGSEGV, Segmentation fault.
0x000055960508713e in assign_collations_walker ()
(gdb) bt
#0  0x000055960508713e in assign_collations_walker ()
#1  0x00005596052653c2 in expression_tree_walker_impl ()
#2  0x0000559605087619 in assign_collations_walker ()
#3  0x0000559605086f8b in assign_expr_collations ()
#4  0x0000559605086e99 in assign_query_collations_walker ()
#5  0x0000559605265a46 in query_tree_walker_impl ()
#6  0x0000559605086e2d in assign_query_collations ()
#7  0x0000559605042c22 in transformInsertStmt ()
#8  0x000055960504192f in transformStmt ()
#9  0x000055960504186b in transformOptionalSelectInto ()
#10 0x0000559605041798 in transformTopLevelStmt ()
#11 0x000055960504131e in parse_analyze_fixedparams ()
#12 0x000055960545b908 in pg_analyze_and_rewrite_fixedparams ()
#13 0x000055960545c124 in exec_simple_query ()
#14 0x0000559605461314 in PostgresMain ()
#15 0x00005596054585cb in BackendMain ()
#16 0x000055960537dee9 in postmaster_child_launch ()
#17 0x0000559605384286 in BackendStartup ()
#18 0x0000559605381c31 in ServerLoop ()
#19 0x0000559605381531 in PostmasterMain ()
#20 0x0000559605236d2c in main ()
(gdb) Quit
(gdb) quit
```


I tried to recompile with --enable-debug and issue stop reproducing...


-- 
Best regards,
Kirill Reshke


From: 	Kirill Reshke <reshkekirill(at)gmail(dot)com>
To: 	Andreas Karlsson <andreas(at)proxel(dot)se>
Cc: 	Joel Jacobson <joel(at)compiler(dot)org>, pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, Marko Tiikkaja <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2025-03-10 13:10:48
Message-ID: 	CALdSSPjmM1e96BNE04j_kaRVSRk+Hrd_jLKvsns5iyZZTQimkg@mail.gmail.com
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

On Mon, 10 Mar 2025 at 18:05, Kirill Reshke <reshkekirill(at)gmail(dot)com> wrote:
>
> On Wed, 5 Mar 2025 at 07:33, Andreas Karlsson <andreas(at)proxel(dot)se> wrote:
> >
> > On 3/4/25 10:24 AM, Andreas Karlsson wrote:
> > > Rebased the patch to add support for OLD.* and NEW.*.
> >
> > Apparently the CI did not like that version.
> >
> > Andreas
>
> Hi!
> Applied v6.
>
> 1) Should we answer INSERT 0 10 here?


Sorry, i mean: INSERT 0 0


-- 
Best regards,
Kirill Reshke


From: 	Dean Rasheed <dean(dot)a(dot)rasheed(at)gmail(dot)com>
To: 	Kirill Reshke <reshkekirill(at)gmail(dot)com>
Cc: 	Andreas Karlsson <andreas(at)proxel(dot)se>, Joel Jacobson <joel(at)compiler(dot)org>, pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, Marko Tiikkaja <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2025-03-12 11:02:14
Message-ID: 	CAEZATCXYQp4NvK2QME-KGXj58iCvN4UW3Vg=i7+tro65TJZzKg@mail.gmail.com
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

> On 3/4/25 10:24 AM, Andreas Karlsson wrote:
> Rebased the patch to add support for OLD.* and NEW.*.


create table t (key int primary key, val text);
insert into t values (1, 'old');


insert into t values (1, 'new') on conflict (key) do select for update
  returning old.*, new.*;


 key | val | key | val
-----+-----+-----+-----
   1 | old |     |
(1 row)


IMO this should cause new.* be the same as old.*. This is kind-of like
a "do update" that changes nothing, with the end result being that old
and new are the same, because nothing was changed. Currently, the only
command that can cause new to be NULL is a DELETE, because the new
state of the table is that the row no longer exists, which isn't the
case here.


On Mon, 10 Mar 2025 at 13:11, Kirill Reshke <reshkekirill(at)gmail(dot)com> wrote:
>
> On Mon, 10 Mar 2025 at 18:05, Kirill Reshke <reshkekirill(at)gmail(dot)com> wrote:
> >
> > 1) Should we answer INSERT 0 10 here?
>
> Sorry, i mean: INSERT 0 0


Hmm, I would say that the patch is correct -- the count should be the
number of rows inserted, updated or selected for return (and the
"Outputs" section of the doc page for INSERT should be updated to say
that). That way, the count always matches the number of rows returned
when there's a RETURNING clause, which I think is true of all other
DML commands.


Regards,
Dean


From: 	Dean Rasheed <dean(dot)a(dot)rasheed(at)gmail(dot)com>
To: 	Kirill Reshke <reshkekirill(at)gmail(dot)com>
Cc: 	Andreas Karlsson <andreas(at)proxel(dot)se>, Joel Jacobson <joel(at)compiler(dot)org>, pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, Marko Tiikkaja <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2025-03-31 15:33:13
Message-ID: 	CAEZATCV_Urr7FO_xQ+yHyhssbJYwns+pqg0j35eDajN2+zFBGw@mail.gmail.com
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

> > On 3/4/25 10:24 AM, Andreas Karlsson wrote:
> > Rebased the patch to add support for OLD.* and NEW.*.
>


I took a closer look at this, and I have a number of comments:


* The changes for RLS look correct. However, in
get_row_security_policies(), it's not necessary to add
WCO_RLS_UPDATE_CHECK checks from UPDATE policies when doing ON
CONFLICT DO SELECT because it's not going to do an UPDATE. Also, some
code duplication can be avoided, because basically the plain DO SELECT
case is the same as the other cases, but with some checks not
required. So it's much simpler to leave the code structure as it was,
and just disable the checks that aren't needed based on the
permissions required by the command being executed, which IMO makes
the code easier to follow.


* In ExecOnConflictSelect(), the comment block for RLS checking seems
to have been copied verbatim from ExecOnConflictUpdate(), but it needs
updating, because the two cases are different.


* As I mentioned before, I think that when returning OLD/NEW values,
ON CONFLICT DO SELECT should behave the same as ON CONFLICT DO UPDATE
would do if it didn't change anything.


* Looking at the WHERE clause, I think it's a mistake to not allow
excluded values in it. That makes the WHERE clause of ON CONFLICT DO
SELECT inconsistent with the WHERE clause of ON CONFLICT DO UPDATE.
And that inconsistency might make it tricky to add support for
excluded later, since it requires the use of qualified column names.
It seems to me that it might be very useful to be able to refer to
excluded values -- e.g., to return just the rows that where different
from what it tried to insert -- and supporting it only requires minor
tweaks to transformOnConflictClause(), set_plan_refs(), and
ExecOnConflictSelect().


* ruleutils.c needs support for deparsing ON CONFLICT DO SELECT.


* When inserting into a table with a rule, if the rule action is
INSERT ... ON CONFLICT DO SELECT ... RETURNING, then the triggering
query must also have a RETURNING clause. The parser check for a
RETURNING clause doesn't catch that, so there needs to also be a check
in the rewriter.


Attached is an update, with fixes for those issues, plus a bit of
miscellaneous tidying up (as a separate patch for ease of review).


There's at least one more code issue that I didn't have time to look at:


create table foo (a int primary key, b text) partition by list (a);
create table foo_p1 partition of foo for values in (1);
create table foo_p2 partition of foo for values in (2);


insert into foo values (1, 'xxx')
  on conflict (a) do select for update returning *;
insert into foo values (1, 'xxx')
  on conflict (a) do select for update returning *;


server closed the connection unexpectedly


It looks to me like ExecInitPartitionInfo() needs updating to
initialise the WHERE clause for ON CONFLICT DO SELECT.


I think there is still a fair bit more to do to get this into a
committable state. The docs in particular need work. For example, on
the INSERT page:


* The INSERT synopsis fails to mention that DO SELECT supports WHERE.
* The paragraph about privileges needs updating for DO SELECT.
* The final paragraph under "output_expression" should mention DO SELECT.
* The "ON CONFLICT clause" section doesn't mention DO SELECT at all.
* The "Outputs" section should mention select.
* The "Examples" section should have at least one example of DO SELECT.


The penultimate paragraph of section 6.4, "Returning Data from
Modified Rows" also needs updating. There may be more places. I'd
suggest a bit of grepping in the docs (and probably also in the code)
for other places that need updating.


It also feels like this needs more regression tests, plus some new
isolation test cases.


Regards,
Dean
Attachment 	Content-Type 	Size
v7-0001-Add-support-for-ON-CONFLICT-DO-SELECT-FOR.patch 	text/x-patch 	51.4 KB
v7-0002-Review-comments-for-ON-CONFLICT-DO-SELECT.patch 	text/x-patch 	35.1 KB
From: 	Andreas Karlsson <andreas(at)proxel(dot)se>
To: 	Dean Rasheed <dean(dot)a(dot)rasheed(at)gmail(dot)com>, Kirill Reshke <reshkekirill(at)gmail(dot)com>
Cc: 	Joel Jacobson <joel(at)compiler(dot)org>, pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, Marko Tiikkaja <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2025-05-12 18:33:14
Message-ID: 	8c3a9e64-0b29-40ae-962a-626d7fe90ba8@proxel.se
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

On 3/31/25 5:33 PM, Dean Rasheed wrote:
>>> On 3/4/25 10:24 AM, Andreas Karlsson wrote:
>>> Rebased the patch to add support for OLD.* and NEW.*.
>>
> 
> I took a closer look at this, and I have a number of comments:


Thanks for taking a look and improving my patch! And thanks to Kirill too.


> * The changes for RLS look correct. However, in
> get_row_security_policies(), it's not necessary to add
> WCO_RLS_UPDATE_CHECK checks from UPDATE policies when doing ON
> CONFLICT DO SELECT because it's not going to do an UPDATE. Also, some
> code duplication can be avoided, because basically the plain DO SELECT
> case is the same as the other cases, but with some checks not
> required. So it's much simpler to leave the code structure as it was,
> and just disable the checks that aren't needed based on the
> permissions required by the command being executed, which IMO makes
> the code easier to follow.


Correct, though I have not yet made up my mind if removing the 
duplicated code makes things easier or harder to follow but that will 
likely be obvious in the next version of the patch. In this place it 
makes things nicer but in other places I am less certain.


> * In ExecOnConflictSelect(), the comment block for RLS checking seems
> to have been copied verbatim from ExecOnConflictUpdate(), but it needs
> updating, because the two cases are different.


Thanks for spotting and fixing!


> * As I mentioned before, I think that when returning OLD/NEW values,
> ON CONFLICT DO SELECT should behave the same as ON CONFLICT DO UPDATE
> would do if it didn't change anything.


Yeah, you are right. I made a thinko when designing this.


> * Looking at the WHERE clause, I think it's a mistake to not allow
> excluded values in it. That makes the WHERE clause of ON CONFLICT DO
> SELECT inconsistent with the WHERE clause of ON CONFLICT DO UPDATE.
> And that inconsistency might make it tricky to add support for
> excluded later, since it requires the use of qualified column names.
> It seems to me that it might be very useful to be able to refer to
> excluded values -- e.g., to return just the rows that where different
> from what it tried to insert -- and supporting it only requires minor
> tweaks to transformOnConflictClause(), set_plan_refs(), and
> ExecOnConflictSelect().


Yes, for sure! That would be really useful. Thanks!
  > * ruleutils.c needs support for deparsing ON CONFLICT DO SELECT.
> 
> * When inserting into a table with a rule, if the rule action is
> INSERT ... ON CONFLICT DO SELECT ... RETURNING, then the triggering
> query must also have a RETURNING clause. The parser check for a
> RETURNING clause doesn't catch that, so there needs to also be a check
> in the rewriter.


Correct.


> Attached is an update, with fixes for those issues, plus a bit of
> miscellaneous tidying up (as a separate patch for ease of review).
> 
> There's at least one more code issue that I didn't have time to look at:
> 
> create table foo (a int primary key, b text) partition by list (a);
> create table foo_p1 partition of foo for values in (1);
> create table foo_p2 partition of foo for values in (2);
> 
> insert into foo values (1, 'xxx')
>    on conflict (a) do select for update returning *;
> insert into foo values (1, 'xxx')
>    on conflict (a) do select for update returning *;
> 
> server closed the connection unexpectedly
> 
> It looks to me like ExecInitPartitionInfo() needs updating to
> initialise the WHERE clause for ON CONFLICT DO SELECT.


I have fixed that one and some other issues locally and will submit a 
new version in a while after I have added more tests because you are 
very correct in that a big issue with my last version of the patch was 
the big lack of tests and lack of making sure all features which 
interact with UPSERT actually worked with my changes. Plus some islation 
tests would be nice to have.


 > I think there is still a fair bit more to do to get this into a
 > committable state. The docs in particular need work. For example, on
 > the INSERT page:


Yeah, the docs really need to be fixed.


Andreas


From: 	Dean Rasheed <dean(dot)a(dot)rasheed(at)gmail(dot)com>
To: 	Andreas Karlsson <andreas(at)proxel(dot)se>
Cc: 	Kirill Reshke <reshkekirill(at)gmail(dot)com>, Joel Jacobson <joel(at)compiler(dot)org>, pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>, Marko Tiikkaja <marko(at)joh(dot)to>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2025-06-25 11:39:08
Message-ID: 	CAEZATCV0Xpo4QHkpa66GtA_frfGpaJcK3ua6mSKhb3SQd=xAuQ@mail.gmail.com
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

On Mon, 12 May 2025 at 19:33, Andreas Karlsson <andreas(at)proxel(dot)se> wrote:
>
> I have fixed that one and some other issues locally and will submit a
> new version in a while after I have added more tests because you are
> very correct in that a big issue with my last version of the patch was
> the big lack of tests and lack of making sure all features which
> interact with UPSERT actually worked with my changes. Plus some islation
> tests would be nice to have.
>


+1. Don't forget to move the CF entry to the next open CF.


FYI, over on [1] I proposed more tests and doc updates for RLS. I
think those updates might make it easier to test and document the RLS
aspects of this patch.


[1] https://www.postgresql.org/message-id/flat/CAEZATCWqnfeChjK=n1V_dYZT4rt4mnq+ybf9c0qXDYTVMsy8pg(at)mail(dot)gmail(dot)com


Regards,
Dean


From: 	"v(at)viktorh(dot)net" <v(at)viktorh(dot)net>
To: 	pgsql-hackers <pgsql-hackers(at)postgresql(dot)org>
Cc: 	Andreas Karlsson <andreas(at)proxel(dot)se>
Subject: 	Re: INSERT ... ON CONFLICT DO SELECT [FOR ...] take 2
Date: 	2025-09-02 18:56:31
Message-ID: 	91BEF220-A4D2-423E-96CF-384813432C3C@viktorh.net
Views: 	Whole Thread | Raw Message | Download mbox | Resend email
Lists: 	pgsql-hackers

Hello, I was working on my own patch for the same thing, until I found this was already there. 
I think this would be very useful for a lot of people.
Do you need any help moving this forward Anderas? I have both tests and docs written, although not for the FOR UPDATE part.


> On 25 Jun 2025, at 13:39, Dean Rasheed <dean(dot)a(dot)rasheed(at)gmail(dot)com> wrote:
> 
> On Mon, 12 May 2025 at 19:33, Andreas Karlsson <andreas(at)proxel(dot)se> wrote:
>> 
>> I have fixed that one and some other issues locally and will submit a
>> new version in a while after I have added more tests because you are
>> very correct in that a big issue with my last version of the patch was
>> the big lack of tests and lack of making sure all features which
>> interact with UPSERT actually worked with my changes. Plus some islation
>> tests would be nice to have.
>> 
> 
> +1. Don't forget to move the CF entry to the next open CF.
> 
> FYI, over on [1] I proposed more tests and doc updates for RLS. I
> think those updates might make it easier to test and document the RLS
> aspects of this patch.
> 
> [1] https://www.postgresql.org/message-id/flat/CAEZATCWqnfeChjK=n1V_dYZT4rt4mnq+ybf9c0qXDYTVMsy8pg(at)mail(dot)gmail(dot)com
> 
> Regards,
> Dean
> 
> 
> 
