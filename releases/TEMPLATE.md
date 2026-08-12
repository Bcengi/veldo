---
schema: veldo.release/v1
id: REL-0000
# One line, in the user's terms: the increment this release cuts.
title: The increment this release cuts
# release | mvp. OPTIONAL, and at most one release in the repository may claim mvp:
# the MVP is simply the first release, and the word lives here rather than on a plan.
kind: release
# draft -> ready -> in_progress -> released -> closed
status: draft
# Bump on any scope change after approval; stale revisions invalidate dependent context.
revision: 1
owner: who-answers-for-this
# approved_by / approved_at: required the moment status leaves draft. A release groups
# approved plans, so it leaves draft only by a recorded human approval, exactly as a plan
# does.
# What done is called for the whole group, not for any one member.
milestone: What done is called
# THE GROUP. Each member is a plan (the floor) or another release, and nothing else: a spec
# id is refused, because a spec binds to a plan and never to a release. There is no cap on
# the depth, so a release may group releases that group plans. A member has ONE parent: a
# target claimed by two releases is refused, and so is a member ring.
#
# A member's target file need not exist yet. An unelaborated member is counted and carries
# no digest, rather than being silently dropped or silently resolved.
members:
  - kind: plan
    target: PLAN-0000
  - kind: release
    target: REL-0001
---

# The release

## What it promises

What is true for a user once every member has landed, in one paragraph. This is the group's
promise, not a summary of its members: if it reads as a list of the plans below, the grouping
has not been decided yet.

## Why these members, and in this order

One line per member saying what it contributes to the promise above. A member that serves no
part of the promise does not belong in the release.

## What it does not include

The named exclusions, so a reader can tell a deferred decision from an oversight.
