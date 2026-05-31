# Database Schema Guide

This document describes the SQLite database schema (`agentforge.db`) used by the agent framework.

## Tables

### 1. `users`
Tracks system users and external developers.
- `id` (INTEGER, Primary Key): Autoincremented identifier.
- `name` (TEXT, Not Null): Full name of the user.
- `email` (TEXT, Unique, Not Null): Email address.
- `created_at` (TEXT): ISO 8601 timestamp when user was added.

### 2. `pull_requests`
Tracks pull requests synced from GitHub or simulated locally.
- `id` (INTEGER, Primary Key): Autoincremented identifier.
- `title` (TEXT, Not Null): Summary of changes.
- `repo` (TEXT, Not Null): Repository path (`owner/repo`).
- `status` (TEXT, Not Null): PR state (`open`, `closed`, `merged`).
- `author` (TEXT, Not Null): GitHub handle of the author.
- `created_at` (TEXT): ISO 8601 timestamp.
