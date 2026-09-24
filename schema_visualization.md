# Database Schema Diagram: Accounts, Organizations & RBAC

This visual Entity-Relationship (ER) diagram represents the complete database structure defined in [`accounts_orgs_schema.sql`](file:///c:/Users/Pablo/Documents/projects/learning-backend/accounts_orgs_schema.sql).

---

## High-Level Architectural Map

```mermaid
graph TD
    subgraph Identity & Authentication
        U[users]
        ID[identities]
        S[sessions]
        T[api_tokens]
    end

    subgraph Organizations & Domain Governance
        O[organizations]
        TD[trusted_domains]
    end

    subgraph RBAC Infrastructure
        R[roles]
        P[permissions]
        RP[role_permissions]
    end

    subgraph Access & Onboarding
        M[memberships]
        INV[invitations]
    end

    subgraph Resources & Compliance
        PRJ[projects]
        AL[audit_logs]
    end

    U -->|1:N| ID
    U -->|1:N| S
    U -->|1:N| T
    U -->|Created by 1:N| O
    O -->|1:N| TD
    O -->|1:N Custom Roles| R
    R -->|N:M| RP
    P -->|N:M| RP
    TD -->|Default Role| R
    U -->|1:N Memberships| M
    O -->|1:N Memberships| M
    R -->|Assigned in| M
    O -->|1:N Invites| INV
    R -->|Assigned in| INV
    U -->|Invited by| INV
    U -->|Polymorphic Owner| PRJ
    O -->|Polymorphic Owner| PRJ
    O -->|Scoped Audit| AL
    U -->|Actor| AL
```

---

## Detailed Entity-Relationship (ER) Diagram

```mermaid
erDiagram
    users ||--o{ identities : "has external SSO links"
    users ||--o{ sessions : "owns active sessions"
    users ||--o{ api_tokens : "owns API tokens"
    users ||--o{ organizations : "created (optional)"
    users ||--o{ memberships : "participates in"
    users ||--o{ invitations : "sent (as inviter)"
    users ||--o{ projects : "owns (personal project)"
    users ||--o{ audit_logs : "performed action as actor"

    organizations ||--o{ memberships : "contains members"
    organizations ||--o{ invitations : "has pending invites"
    organizations ||--o{ trusted_domains : "defines domain auto-join"
    organizations ||--o{ roles : "owns custom roles"
    organizations ||--o{ projects : "owns (org project)"
    organizations ||--o{ audit_logs : "logs activity for"

    roles ||--o{ role_permissions : "grants permissions via"
    permissions ||--o{ role_permissions : "assigned to roles via"
    roles ||--o{ memberships : "defines role in"
    roles ||--o{ invitations : "defines target role in"
    roles ||--o{ trusted_domains : "defines default role for"

    users {
        uuid id PK
        citext email UK
        text password_hash
        text name
        text avatar_url
        timestamptz email_verified_at
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    identities {
        uuid id PK
        uuid user_id FK
        text provider
        text provider_user_id
        citext provider_email
        timestamptz created_at
    }

    sessions {
        uuid id PK
        uuid user_id FK
        text token_hash UK
        inet ip_address
        text user_agent
        timestamptz created_at
        timestamptz expires_at
        timestamptz revoked_at
    }

    api_tokens {
        uuid id PK
        uuid user_id FK
        text name
        text token_hash UK
        text_array scopes
        timestamptz last_used_at
        timestamptz created_at
        timestamptz expires_at
        timestamptz revoked_at
    }

    organizations {
        uuid id PK
        text name
        citext slug UK
        text billing_plan
        uuid created_by FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    trusted_domains {
        uuid id PK
        uuid organization_id FK
        text domain
        uuid default_role_id FK
        timestamptz created_at
    }

    roles {
        uuid id PK
        uuid organization_id FK
        text name
        boolean is_system
        timestamptz created_at
    }

    permissions {
        uuid id PK
        text key UK
        text description
    }

    role_permissions {
        uuid role_id PK_FK
        uuid permission_id PK_FK
    }

    memberships {
        uuid id PK
        uuid user_id FK
        uuid organization_id FK
        uuid role_id FK
        text status
        uuid invited_by FK
        timestamptz created_at
        timestamptz updated_at
    }

    invitations {
        uuid id PK
        uuid organization_id FK
        citext email
        uuid role_id FK
        text token UK
        uuid invited_by FK
        text status
        timestamptz expires_at
        timestamptz accepted_at
        timestamptz created_at
    }

    projects {
        uuid id PK
        text name
        uuid owner_user_id FK
        uuid owner_organization_id FK
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at
    }

    audit_logs {
        uuid id PK
        uuid organization_id FK
        uuid actor_user_id FK
        text action
        text target_type
        uuid target_id
        jsonb metadata
        timestamptz created_at
    }
```

---

## Relationship Summary & Key Constraints

| Parent Table | Child Table | Relationship Type | Foreign Key Field | On Delete Behavior | Design Purpose / Constraint |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `users` | `identities` | 1-to-Many | `user_id` | CASCADE | Allows multiple SSO auth providers (Google, GitHub) for one identity. |
| `users` | `sessions` | 1-to-Many | `user_id` | CASCADE | Active web sessions per user with explicit hash lookup and revocation. |
| `users` | `api_tokens` | 1-to-Many | `user_id` | CASCADE | Scoped API token access keys. |
| `users` | `organizations` | 1-to-Many | `created_by` | SET NULL | Tracks who originally created the organization without blocking org retention. |
| `organizations` | `trusted_domains` | 1-to-Many | `organization_id` | CASCADE | Domain auto-onboarding rules (`domain` + `organization_id` unique). |
| `roles` | `trusted_domains` | 1-to-Many | `default_role_id` | RESTRICT | Default role assigned to users auto-joined via matching email domain. |
| `organizations` | `roles` | 1-to-Many | `organization_id` | CASCADE | Null `organization_id` = global system role; non-null = custom org role. |
| `roles` | `role_permissions` | 1-to-Many | `role_id` | CASCADE | Join table connecting roles to permissions. |
| `permissions` | `role_permissions` | 1-to-Many | `permission_id` | CASCADE | Join table connecting permissions to roles. |
| `users` | `memberships` | 1-to-Many | `user_id` | CASCADE | Connects user identity to organization membership. |
| `organizations` | `memberships` | 1-to-Many | `organization_id` | CASCADE | Connects organization to user membership. |
| `roles` | `memberships` | 1-to-Many | `role_id` | RESTRICT | Defines user's active permissions inside that organization. |
| `organizations` | `invitations` | 1-to-Many | `organization_id` | CASCADE | Tracks invitations targeting an organization before membership creation. |
| `roles` | `invitations` | 1-to-Many | `role_id` | RESTRICT | Defines the pending role promised upon invitation acceptance. |
| `users` | `invitations` | 1-to-Many | `invited_by` | SET NULL | Tracks the inviting member. |
| `users` | `projects` | 1-to-Many (Polymorphic) | `owner_user_id` | CASCADE | Personal ownership of a project resource. |
| `organizations` | `projects` | 1-to-Many (Polymorphic) | `owner_organization_id` | CASCADE | Organizational ownership of a project resource. |
| `organizations` | `audit_logs` | 1-to-Many | `organization_id` | SET NULL | Scopes security audit log entries to an organization. |
| `users` | `audit_logs` | 1-to-Many | `actor_user_id` | SET NULL | Identifies the user executing the audited action. |

> [!NOTE]
> **Polymorphic Constraint in `projects`**: Enforced via PostgreSQL check constraint `chk_projects_single_owner`: `num_nonnulls(owner_user_id, owner_organization_id) = 1`. A project is owned strictly by a user OR an organization, never both and never neither.
