# FLOWSTATE — Frontend Client (Next.js 16)

[![Next.js 16](https://img.shields.io/badge/Next.js-16%20App%20Router-black?style=flat&logo=next.js)](https://nextjs.org/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?style=flat&logo=react)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?style=flat&logo=typescript)](https://www.typescriptlang.org/)
[![TailwindCSS](https://img.shields.io/badge/TailwindCSS-v4-38B2AC?style=flat&logo=tailwind-css)](https://tailwindcss.com/)

This is the dedicated **`frontend`** branch of **FLOWSTATE**, isolating the standalone Next.js 16 client application.

---

## 🌟 Features Included in this Branch

- **Executive Engineering Dashboard:** Real-time 7-day velocity throughput, sprint health indicators, and upcoming milestones.
- **Kanban Board:** Dynamic drag-and-drop task status transitions across customizable pipeline stages (`backlog`, `todo`, `in_progress`, `in_review`, `done`).
- **Task Detail & Binary Attachments:** Drag-and-drop file upload zone (Supabase Storage integration), subtask checklists, and discussion threads.
- **Multi-Tab Sync:** Real-time tab-to-tab revalidation using browser `BroadcastChannel` and page focus events.
- **Engineering Analytics:** Recharts visualizations for task completion, cycle times, priority distributions, and individual member metrics.
- **Milestone Calendar:** Interactive monthly and weekly release schedule views.
- **1-Click CSV Exports:** Data export for initiatives and sprint tickets.

---

## 🚀 How to Run the Frontend

### 1. Prerequisites
- **Node.js** >= 18.18.0
- **npm** >= 9.0.0

### 2. Install Dependencies
```bash
npm install
```

### 3. Configure Environment Variables
Create a `.env.local` file in the root directory:
```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1
NEXT_PUBLIC_SUPABASE_URL=https://<YOUR_SUPABASE_PROJECT>.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<YOUR_SUPABASE_ANON_KEY>
```

### 4. Start the Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 🏗️ Directory Structure

```
flowstate (frontend branch)/
├── src/
│   ├── app/                      # Next.js 16 App Router
│   │   ├── (auth)/               # Login, Register, Forgot Password
│   │   └── (workspace)/          # Dashboard, Kanban, Projects, Analytics, Calendar, Teams
│   ├── components/               # Modular UI components & modals
│   ├── context/                  # React Contexts (WorkspaceContext, AuthContext, ToastContext)
│   ├── lib/                      # Supabase client, storage utilities, and formatting helpers
│   ├── services/                 # API client service layer connecting to FastAPI backend
│   └── types/                    # TypeScript interfaces
├── public/                       # Static assets & icons
├── package.json
└── tsconfig.json
```

---

## 🧪 Verification & Build

```bash
# Strict TypeScript compilation check
npx tsc --noEmit

# Production build
npm run build
```

---

## 🌿 Related Branches
- [`main`](https://github.com/Ani170320/flowstate/tree/main): Full monorepo containing both frontend and backend.
- [`backend`](https://github.com/Ani170320/flowstate/tree/backend): Dedicated FastAPI backend service.
