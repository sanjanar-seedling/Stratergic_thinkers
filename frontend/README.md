# 🌱 Frontend — Seedlings

> React TypeScript SPA providing the founder-facing UI.

## 📖 Overview

The Seedlings frontend is a single-page application built with React 19, TypeScript, and Vite. It delivers a journaling, decision-tracking, and AI sparring experience for founders, wrapped in a dark/light themed UI with sidebar navigation and protected routes. Client-side encryption is available for sensitive data before it leaves the browser.

## 📁 Directory Structure

```
frontend/src/
├── pages/                  # Route-level page components
│   ├── LoginPage.tsx       # Email/password + OAuth login
│   ├── SignupPage.tsx       # New account registration
│   ├── OAuthCallbackPage.tsx # OAuth provider redirect handler
│   ├── JournalPage.tsx     # Daily journaling (default route)
│   ├── DecisionsPage.tsx   # Decision log & tracker
│   ├── SparringPage.tsx    # AI sparring partner
│   ├── DashboardPage.tsx   # Metrics & overview dashboard
│   ├── InsightsPage.tsx    # Founder insights
│   ├── PrivacyPage.tsx     # Privacy controls & encryption settings
│   ├── SettingsPage.tsx    # User preferences
│   ├── FrameworkAssistant.tsx  # Decision framework helper
│   └── InterventionsPage.tsx   # Suggested interventions
├── components/             # Shared UI components
│   ├── Sidebar.tsx         # App-wide sidebar navigation
│   ├── ThemeProvider.tsx   # Dark/light theme context provider
│   ├── ThemeToggle.tsx     # Theme switch control
│   ├── VoiceMemo.tsx       # Voice recording & transcription widget
│   ├── ReflectionToggle.tsx # Reflection prompt toggle
│   └── ui/                 # Radix-based primitives (button, card, input, etc.)
├── contexts/
│   └── AuthContext.tsx     # Authentication state & protected-route logic
├── services/
│   ├── api.ts              # Axios HTTP client for backend API
│   └── encryption.ts       # Client-side encryption utilities
├── lib/
│   └── utils.ts            # Shared helpers (cn, etc.)
├── App.tsx                 # Router, providers, route definitions
├── main.tsx                # Vite entry point
└── index.css               # Tailwind CSS v4 imports & global styles
```

## 🔑 Key Components

| Module | Purpose |
|---|---|
| `JournalPage` | Default route — daily founder journaling interface |
| `DecisionsPage` | Log, track, and review strategic decisions |
| `SparringPage` | AI-powered sparring partner for pressure-testing ideas |
| `DashboardPage` | Visual dashboard with charts (Recharts) |
| `InsightsPage` | Aggregated founder insights and patterns |
| `FrameworkAssistant` | Guided decision-making frameworks |
| `InterventionsPage` | Suggested behavioral interventions |
| `PrivacyPage` | Client-side encryption controls and data privacy settings |
| `SettingsPage` | Account and app preferences |
| `Sidebar` | Fixed sidebar with navigation links and theme toggle |
| `ThemeProvider` | Provides dark/light mode context to the component tree |
| `VoiceMemo` | Record voice memos with browser MediaRecorder API |
| `AuthContext` | Manages auth state, login/signup, OAuth flow, and `ProtectedRoute` guard |
| `api.ts` | Axios instance configured with `VITE_API_URL`; attaches auth tokens |
| `encryption.ts` | Client-side encrypt/decrypt helpers for sensitive journal data |

## 📦 Dependencies

| Category | Packages |
|---|---|
| **UI Framework** | `react` 19, `react-dom` 19, Radix UI primitives (`dialog`, `dropdown-menu`, `tabs`, `tooltip`, `avatar`, etc.) |
| **Styling** | `tailwindcss` 4, `@tailwindcss/vite`, `tailwind-merge`, `class-variance-authority`, `clsx`, `lucide-react` icons |
| **Routing** | `react-router-dom` 7 |
| **HTTP** | `axios` |
| **Data Viz** | `recharts` 3 |
| **Dev Tools** | `vite` 7, `typescript` 5.9, `eslint` 9, `eslint-plugin-react-hooks`, `eslint-plugin-react-refresh` |

## 🚀 Getting Started

```bash
# Install dependencies
cd frontend
npm install

# Configure environment
cp .env.example .env
# Edit .env — set VITE_API_URL (default: http://localhost:8000/api)

# Start dev server (default: http://localhost:5173)
npm run dev

# Production build
npm run build        # outputs to dist/
npm run preview      # preview production build locally
```

## 📚 Related Documentation

- [Root README](../README.md) — project overview, architecture, and setup
- [Backend README](../backend/README.md) — API server, database, and auth details
