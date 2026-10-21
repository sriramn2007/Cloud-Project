# Real Dataset and Role-Based Access

## Dataset choice

The project now uses the **Diabetes 130-US Hospitals for Years 1999–2008** dataset from the UCI Machine Learning Repository (dataset 296). It contains 101,766 de-identified hospital encounter records from 130 US hospitals and is licensed under CC BY 4.0.

Source: https://archive.ics.uci.edu/dataset/296/diabetes+130+us+hospitals+for+years+1999+2008

The dataset is historical and public. It is included for classroom demonstration only. It must not be described as live confidential patient data or used for clinical decisions. The role boundary demonstrates authorization and least privilege; it does not turn a public dataset into private clinical data.

## Roles

The application has two demo roles:

| Role | Username | Password | Access |
|---|---|---|---|
| Doctor | `doctor` | `doctor-demo` | Common operational fields plus selected demographic and clinical fields |
| Nurse | `nurse` | `nurse-demo` | Common operational/admission fields only |

The doctor-only endpoint is:

```text
GET /api/data/clinical
```

The common endpoint is:

```text
GET /api/data/common
```

Both require a bearer token from:

```text
POST /api/auth/login
```

## Frontend behavior

The dashboard opens with a login screen. The selected role is stored only in browser local storage for this local demonstration. A doctor sees the clinical view in Admissions data; a nurse sees only the common view. The backend enforces the same restriction, so changing the frontend alone cannot grant nurse access to clinical fields.

## Production warning

The passwords are intentionally demo credentials and are not suitable for production. A production deployment must use a real identity provider, password hashing, secret management, audited access, HTTPS, database row-level security, and a formal healthcare privacy/compliance review.
