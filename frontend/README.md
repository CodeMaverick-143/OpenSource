# Contributor Dashboard Frontend

Production-ready Astro frontend for the ContriVerse open-source contribution platform.

## 🚀 Features

- **Server-Side Rendering (SSR)**: Fast first paint with Astro's SSR capabilities
- **Type-Safe API Integration**: All 7 backend dashboard APIs fully integrated
- **Minimal Client-Side JS**: Astro Islands for interactive components only
- **Responsive Design**: Mobile-first Tailwind CSS styling
- **Production-Ready**: Error handling, empty states, and edge case coverage

## 📋 Dashboard Pages

1. **Overview** (`/dashboard`) - Summary statistics and quick navigation
2. **My PRs** (`/dashboard/prs`) - PR list with filtering, sorting, and pagination
3. **Points History** (`/dashboard/points`) - Transaction ledger with pagination
4. **Rank & Progress** (`/dashboard/rank`) - Leaderboard rank and progress tracking
5. **Profile & Badges** (`/dashboard/profile`) - Badges, skills, and contribution graph

## 🛠️ Tech Stack

- **Framework**: Astro (SSR mode)
- **Styling**: Tailwind CSS v4
- **Interactivity**: React (Astro Islands)
- **Type Safety**: TypeScript (strict mode)
- **Backend**: FastAPI (Python)

## 📦 Installation

```bash
# Install dependencies
npm install

# Copy environment variables
cp .env.example .env

# Update .env with your backend URL
# PUBLIC_API_BASE_URL=http://localhost:8000/api/v1
```

## 🏃 Development

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview
```

The dev server will start on `http://localhost:4321` by default.

## 🔧 Configuration

### Environment Variables

- `PUBLIC_API_BASE_URL`: Backend API base URL (default: `http://localhost:8000/api/v1`)

### Backend Requirements

The frontend expects the backend to be running with the following endpoints:

- `GET /dashboard/prs` - PR list with filtering
- `GET /dashboard/points` - Points transaction history
- `GET /dashboard/badges` - User badges (earned + available)
- `GET /dashboard/rank` - User rank information
- `GET /dashboard/contributions` - Contribution graph data
- `GET /dashboard/skills` - User skill tags
- `GET /dashboard/stats` - Dashboard summary statistics

### Authentication

The frontend uses cookie-based authentication (JWT tokens in HttpOnly cookies). Ensure the backend is configured with:

- CORS enabled for the frontend origin
- `credentials: true` in CORS settings
- Cookies sent with `SameSite=Lax` or `SameSite=None; Secure`

## 📁 Project Structure

```
frontend/
├── src/
│   ├── components/
│   │   ├── layout/          # Base layouts
│   │   ├── dashboard/       # Dashboard components
│   │   ├── islands/         # Interactive components (React)
│   │   └── ui/              # Reusable UI components
│   ├── lib/
│   │   ├── api.ts           # API client
│   │   ├── types.ts         # TypeScript types
│   │   └── utils.ts         # Utility functions
│   ├── pages/
│   │   ├── index.astro      # Home page
│   │   └── dashboard/       # Dashboard routes
│   └── styles/
│       └── global.css       # Global styles
├── public/                  # Static assets
├── astro.config.mjs         # Astro configuration
├── tailwind.config.mjs      # Tailwind configuration
└── tsconfig.json            # TypeScript configuration
```

## 🎨 Components

### Server-Rendered Components (Astro)

- `StatsOverview` - Dashboard statistics grid
- `PRCard` / `PRList` - PR display components
- `PointTransaction` / `PointsHistory` - Points ledger
- `RankDisplay` - Rank and progress visualization
- `BadgeGrid` - Badge display
- `SkillTags` - Skill tag cloud
- `ContributionGraph` - Heatmap-style contribution graph

### Interactive Islands (React)

- `FilterControls` - PR filtering and sorting
- `PaginationControls` - Pagination UI
- `TimeRangeToggle` - Contribution graph time range selector

## 🔒 Error Handling

The dashboard gracefully handles:

- **Zero PRs**: Empty state with helpful message
- **No points history**: Empty state placeholder
- **Rank not assigned**: Placeholder with explanation
- **Archived projects**: Visual indicator on PR cards
- **API errors**: User-friendly error messages
- **Network failures**: Graceful degradation

## 🚀 Deployment

### Build

```bash
npm run build
```

This creates a `dist/` directory with the production build.

### Run Production Server

```bash
node dist/server/entry.mjs
```

The server will start on port `4321` by default. Set `PORT` environment variable to change.

### Environment Variables for Production

```bash
PUBLIC_API_BASE_URL=https://api.contriverse.com/api/v1
PORT=3000
```

## 📝 API Client Usage

```typescript
import { getPRs, getDashboardStats } from '../lib/api';

// Fetch PRs with filters
const prs = await getPRs({
  status: 'MERGED',
  sort_by: 'recent',
  page: 1,
  limit: 20
});

// Fetch dashboard stats
const stats = await getDashboardStats();
```

## 🎯 Performance

- **Fast First Paint**: Server-side rendering ensures quick initial load
- **Minimal JS**: Only ~8KB of client-side JavaScript for islands
- **Code Splitting**: Automatic code splitting per route
- **Optimized Assets**: Tailwind CSS purging removes unused styles

## 🧪 Testing

```bash
# Type checking
npx tsc --noEmit

# Build verification
npm run build
```

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

This is part of the ContriVerse open-source contribution platform. See the main repository README for contribution guidelines.
