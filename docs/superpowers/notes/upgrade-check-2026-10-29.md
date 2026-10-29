# Upgrade check, 2026-10-29

Command: `scripts/upgrade-check/build_reference_db.sh /tmp/taiga-ref` (original upstream `main`, `sample_data`:
7 projects, 114 user stories, 108 tasks, 90 issues, 903 attachments, 15 users), then
`scripts/upgrade-check/run_upgrade_check.sh /tmp/taiga-ref` on branch `django6-work` (Django 6.1.2, PostgreSQL 15).

Result: **UPGRADE CHECK PASSED** (full output below).

What the check proves
- Upgrade over the reference database: every table keeps its row count (except `django_migrations`),
  no index OID disappears (the six `index_together` indexes were renamed, not rebuilt), and the schema
  differs only by those six index renames.
- Fresh install (`migrate` from zero): the same, plus three known differences that `--fresh` accepts
  (IDENTITY instead of serial primary keys; no `references_project<N>` sequences without projects;
  `history_historyentry` columns NOT NULL as the models say). 12 triggers exist after a fresh install
  (migration `projects 0046`).

Known divergence worth a CHANGELOG line: databases created by the original code keep nullable columns in
`history_historyentry` and serial primary keys; fresh databases of the fork get the NOT NULL columns and
IDENTITY keys. Both work with the fork.

## Output

```
== upgrade over the reference database
-- row counts
-- index OIDs (a rename must keep the OID; nothing may be rebuilt)
-- schema
renamed index: attachments_attachment_content_type_id_object_id_3f2e447c_idx -> attachments_content_44d952_idx
renamed index: custom_attributes_epiccu_epic_id_d413e57a_idx -> custom_attr_epic_id_361630_idx
renamed index: custom_attributes_issuec_issue_id_868161f8_idx -> custom_attr_issue_i_61760e_idx
renamed index: custom_attributes_taskcu_task_id_3d1ccf5e_idx -> custom_attr_task_id_6b8175_idx
renamed index: custom_attributes_userst_user_story_id_99b10c43_idx -> custom_attr_user_st_ac90c4_idx
renamed index: projects_project_name_id_44f44a5f_idx -> projects_pr_name_06522d_idx
== fresh install
renamed index: attachments_attachment_content_type_id_object_id_3f2e447c_idx -> attachments_content_44d952_idx
renamed index: custom_attributes_epiccu_epic_id_d413e57a_idx -> custom_attr_epic_id_361630_idx
renamed index: custom_attributes_issuec_issue_id_868161f8_idx -> custom_attr_issue_i_61760e_idx
renamed index: custom_attributes_taskcu_task_id_3d1ccf5e_idx -> custom_attr_task_id_6b8175_idx
renamed index: custom_attributes_userst_user_story_id_99b10c43_idx -> custom_attr_user_st_ac90c4_idx
renamed index: projects_project_name_id_44f44a5f_idx -> projects_pr_name_06522d_idx
triggers on fresh install: 12
UPGRADE CHECK PASSED
```
