---
name: Branch merge via common ancestor
description: When combining two Neon branches, clone from their common ancestor so both source branches remain leaves and can be deleted afterwards.
---

## Rule
When merging data from two sibling Neon snapshot branches into one combined snapshot, clone the new branch from their **common ancestor** (not from either source branch).

**Why:** Neon refuses to delete a branch that has children. If you clone the combined branch from source-branch-A, then source-branch-A becomes a parent of the combined branch and can never be deleted. Cloning from the common ancestor keeps both source branches as pure leaves, so they can be deleted immediately after the merge data has been verified.

**How to apply:**
- Identify the ancestor branch all source branches share (e.g. `snap_ph03_3a_AllProjects` for both PMT and NQPS 3b branches).
- Create the combined branch via `_create_branch(proj, name, ancestor_branch_id)`.
- INSERT only the project-specific delta rows from each source branch (CCIs, extra analysis passes). Shared data (sources, signals, zachman_cells) is already present in the ancestor clone.
- After verification, delete source branches (now leaves), then walk up their ancestor chains.
