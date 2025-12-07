# Impact Radar - Marketing Site

A modern, performant marketing website built with Next.js 14, showcasing the Impact Radar event-driven signal engine for equity and biotech traders.

## Tech Stack

- **Next.js 14**: App Router, Server Components, React Server Components
- **TypeScript**: Full type safety throughout
- **Tailwind CSS**: Utility-first styling with custom design tokens
- **Framer Motion**: Smooth animations and transitions
- **Lucide React**: Consistent iconography

## Design System

### Color Palette
- Background: `#0B0F14` (Dark blue-black)
- Panel: `#11161D` (Elevated surface)
- Text: `#EAF0F7` (Primary text)
- Muted: `#9FB2C7` (Secondary text)
- Primary: `#7C9EFF` (Brand blue)
- Accent: `#00E0A4` (Accent green)

### Typography
- Headings: Space Grotesk (variable font)
- Body: Inter (variable font)

## Development

```bash
cd marketing-site
npm run dev
```

The development server runs on `http://localhost:3000` by default.

For production deployment on Replit, the site runs on port 5000:

```bash
npm run build
npm start -- -p 5000
```

## Project Structure

```
marketing-site/
├── app/                    # Next.js App Router pages
│   ├── page.tsx           # Homepage
│   ├── pricing/           # Pricing page
│   ├── product/           # Product features
│   ├── security/          # Security & privacy
│   ├── docs/              # Documentation
│   ├── contact/           # Contact form
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/            # Reusable React components
│   ├── ui/                # shadcn/ui components
│   ├── Header.tsx
│   ├── Footer.tsx
│   ├── Hero.tsx
│   ├── EventCard.tsx
│   ├── ScoreChip.tsx
│   ├── Section.tsx
│   └── ScannerStatus.tsx
├── lib/                   # Utilities
│   └── utils.ts           # cn() helper
└── public/                # Static assets
```

## Features

- **Responsive Design**: Mobile-first, fully responsive across all devices
- **Performance**: Optimized with Next.js Server Components and static generation
- **Accessibility**: WCAG 2.1 AA compliant with semantic HTML
- **SEO**: Comprehensive meta tags, Open Graph, Twitter Cards
- **Analytics**: Plausible Analytics integration (privacy-friendly)

## Pages

### Main Pages
- `/` - Homepage with hero, features, and demo sections
- `/product` - Detailed product features breakdown
- `/pricing` - Three pricing tiers (Free, Pro, Team) with FAQ
- `/security` - Security practices and compliance information
- `/contact` - Contact form with support options
- `/app` - Application access and waitlist

### Documentation
- `/docs` - Documentation hub with quickstart and API links
- `/docs/quickstart` - Step-by-step getting started guide
- `/docs/api` - REST API reference with examples
- `/docs/events` - Event types and impact scoring explanation

### Company & Legal
- `/about` - Company mission, team, and values
- `/changelog` - Release history and feature updates
- `/legal/privacy` - Privacy policy
- `/legal/terms` - Terms of service

### Error Pages
- Custom 404 page with branded experience

## Deployment

The site is configured to run on Replit with the following workflow:

```bash
cd marketing-site && npm run build && npm start -- -p 5000
```

This builds the production bundle and serves it on port 5000, which is exposed as the public-facing webview.

## Key Features

### Dashboard Components
- **Events Feed**: Real-time event monitoring with impact scores and AI summaries
- **Playbook Library**: Trading strategy templates with event-to-playbook matching
- **Modeling Workspace**: Topology-based market analysis tools (Shape Explorer, Topology Analyzer, Strategy Lab)
- **Portfolio Risk**: VaR-95, CVaR, and hedge recommendations
- **Community Forum**: Discord-style chat with @Quant AI mentions

### AI Integration
- **RadarQuant AI**: GPT-5.1-powered assistant for event analysis and market insights
- **AI Event Summaries**: Fetches and analyzes actual SEC/FDA filing content
- **Historical Pattern Matching**: Similar past events with price outcomes

### Authentication & Monetization
- **JWT-based Auth**: Secure session management
- **Plan Tiers**: Free, Pro, Team with feature gating
- **Stripe Integration**: Subscription management

## License

Proprietary - Impact Radar
