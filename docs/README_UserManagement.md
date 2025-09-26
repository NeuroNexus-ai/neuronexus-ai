# User Management in NeuroNexus-AI

The project supports **multiple user management models** in a flexible way.  
Each model can be enabled or disabled as needed.  
The idea is to implement them **gradually** and **under control**.

---

## 🎯 Types of User Management

- **Bootstrap**  
  The very first user is created as a **superuser**.  
  This happens only when the database is empty.

- **Admin-Provisioned**  
  Administrators can manually create users and assign roles/permissions.

- **Self-Sign-Up**  
  Anyone can register themselves (usually with email verification).

- **Invites**  
  Admins send invite links or codes to allow new user registrations.

- **SSO / OAuth2**  
  External authentication via Google / GitHub / Keycloak / … etc.

---

## 🔑 How They Work Together

- Shared database tables: `users`, `roles`, `sessions`, `tokens`.  
- Separate endpoints for each flow:
  - `/auth/bootstrap` → first user only.  
  - `/auth/register` → open registration.  
  - `/auth/invite` → invite code entry.  
  - `/auth/oauth/google` → OAuth login example.  

- Activation rules:
  - **Bootstrap** works only if user count = 0.  
  - **Admin-Provisioned** requires `admin` role.  
  - **Self-Sign-Up** works only if enabled in config.  
  - **Invites** work only if the invite system is enabled.  
  - **SSO** works only if identity provider settings are configured.

---

## ⚙️ Configuration & Control

Each type can be toggled via environment variables:

```env
ENABLE_SELF_SIGNUP=true
ENABLE_INVITES=true
ENABLE_SSO=true
```

Authorization is enforced through **Role-Based Access Control (RBAC)** to define which users can access which features.

---

## 🛠️ Streamlit UI

The **Auth** tab in the UI shows the following (based on configuration):

- 🔑 **Login**  
- 🆕 **Register (Self-Sign-Up)** → visible only if enabled  
- 📩 **Enter Invite Code** → visible only if enabled  
- 🌐 **Login with Google/GitHub** → visible only if enabled  
- ⚙️ **Admin Panel** → user management (admins only)  

---

## ✅ Summary

- All user management models can coexist in the same project.  
- The key is **config flags + RBAC permissions**.  
- Suggested roadmap:
  1. Start simple with **Bootstrap + Admin-Provisioned**.  
  2. Add **Self-Sign-Up + Invites** when needed.  
  3. Enable **SSO** as the user base grows or clients request it.  
