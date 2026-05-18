import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Brain, Shield, Zap, GitBranch, ChevronRight,
  RefreshCw, BarChart3, Network
} from 'lucide-react'

const features = [
  {
    icon: Brain,
    title: 'Intelligent Query Routing',
    desc: 'Auto-classifies every query into 5 types and routes to the optimal retrieval strategy.',
  },
  {
    icon: RefreshCw,
    title: 'Corrective RAG',
    desc: 'Evaluates retrieved chunks, refines weak searches, and tries again before answering.',
  },
  {
    icon: Shield,
    title: 'Hallucination Detection',
    desc: 'Extracts claims and verifies them against context before finalizing the response.',
  },
  {
    icon: BarChart3,
    title: 'Confidence Scoring',
    desc: 'A 4-factor score helps you understand when an answer is well grounded.',
  },
  {
    icon: GitBranch,
    title: 'Graceful Fallback Chain',
    desc: 'When documents fail, the system escalates transparently instead of pretending.',
  },
  {
    icon: Network,
    title: 'Full Decision Trace',
    desc: 'See every agent step, decision, retry, and quality check after a query runs.',
  },
]

const pipeline = [
  'Classify',
  'Route',
  'Retrieve',
  'Evaluate',
  'Generate',
  'Verify',
  'Score',
  'Respond',
]

const staggerContainer = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
}

const fadeUp = {
  hidden: { opacity: 0, y: 24 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: 'easeOut' } },
}

const radii = [
  'rounded-tl-[4rem] rounded-tr-[2rem] rounded-br-[3rem] rounded-bl-[2rem]',
  'rounded-tl-[2rem] rounded-tr-[4rem] rounded-br-[2rem] rounded-bl-[3.5rem]',
  'rounded-tl-[3rem] rounded-tr-[2rem] rounded-br-[4rem] rounded-bl-[2rem]',
]

export default function HomePage() {
  return (
    <div className="organic-page">
      <div className="pointer-events-none absolute -left-28 top-28 h-80 w-80 organic-blob bg-brand-500/15 blur-3xl" />
      <div className="pointer-events-none absolute right-0 top-52 h-96 w-96 organic-blob-alt bg-clay-500/15 blur-3xl" />

      <nav className="sticky top-4 z-50 mx-auto mt-4 flex h-16 max-w-6xl items-center justify-between rounded-full border border-timber/60 bg-white/70 px-4 shadow-soft backdrop-blur-md sm:px-6">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-full bg-brand-500 shadow-soft">
            <Brain className="h-5 w-5 text-brand-50" />
          </div>
          <span className="font-display text-xl font-bold text-surface-950">AgenticRAG</span>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/login" className="rounded-full px-4 py-2 text-sm font-bold text-brand-700 transition-all hover:bg-brand-500/10">
            Sign in
          </Link>
          <Link to="/signup" className="organic-button px-5 py-2.5 text-sm">
            Get started
          </Link>
        </div>
      </nav>

      <section className="relative mx-auto grid max-w-7xl items-center gap-12 px-6 py-24 lg:grid-cols-[1.1fr_0.9fr] lg:py-32">
        <motion.div initial="hidden" animate="show" variants={staggerContainer}>
          <motion.div variants={fadeUp} className="mb-8 inline-flex items-center gap-2 rounded-full border border-brand-500/20 bg-brand-500/10 px-4 py-2 text-sm font-bold text-brand-700">
            <Zap className="h-4 w-4" />
            Production-grade Agentic RAG
          </motion.div>
          <motion.h1 variants={fadeUp} className="font-display text-5xl font-bold leading-[0.98] text-surface-950 md:text-7xl">
            Trustworthy AI with roots in your documents.
          </motion.h1>
          <motion.p variants={fadeUp} className="mt-8 max-w-2xl text-lg leading-8 text-surface-800">
            A self-correcting RAG system that classifies queries, detects hallucinations,
            scores confidence, and knows when to say it does not know.
          </motion.p>
          <motion.div variants={fadeUp} className="mt-10 flex flex-wrap items-center gap-4">
            <Link to="/signup" className="organic-button inline-flex items-center gap-2">
              Start Building <ChevronRight className="h-4 w-4" />
            </Link>
            <Link to="/login" className="organic-button-secondary inline-flex items-center gap-2">
              Sign in
            </Link>
          </motion.div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, rotate: -4, y: 24 }}
          animate={{ opacity: 1, rotate: -2, y: 0 }}
          transition={{ duration: 0.7 }}
          className="organic-card relative p-6 lg:p-8"
        >
          <div className="absolute -right-6 -top-6 h-28 w-28 organic-blob bg-clay-500/20 blur-2xl" />
          <p className="mb-6 font-mono text-xs uppercase tracking-widest text-brand-700">Agentic Pipeline</p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {pipeline.map((step, i) => (
              <div key={step} className="rounded-[1.5rem] border border-timber/60 bg-white/60 p-4 text-center shadow-soft transition-all duration-300 hover:-translate-y-1">
                <div className="mx-auto mb-2 flex h-8 w-8 items-center justify-center rounded-full bg-brand-500/10 text-sm font-bold text-brand-700">
                  {i + 1}
                </div>
                <p className="text-xs font-bold text-surface-900">{step}</p>
              </div>
            ))}
          </div>
        </motion.div>
      </section>

      <section className="bg-surface-200/40 px-6 py-24">
        <div className="mx-auto max-w-6xl">
          <div className="mb-14 max-w-2xl">
            <p className="mb-3 font-mono text-xs uppercase tracking-widest text-brand-700">What makes it agentic</p>
            <h2 className="font-display text-4xl font-bold text-surface-950 md:text-5xl">The RAG system that checks its own footing.</h2>
          </div>
          <motion.div
            variants={staggerContainer}
            initial="hidden"
            whileInView="show"
            viewport={{ once: true }}
            className="grid gap-6 md:grid-cols-2 lg:grid-cols-3"
          >
            {features.map((feature, i) => {
              const Icon = feature.icon
              return (
                <motion.div
                  key={feature.title}
                  variants={fadeUp}
                  className={`group border border-timber/60 bg-surface-50/80 p-6 shadow-soft transition-all duration-300 hover:-translate-y-1 hover:shadow-deep ${radii[i % radii.length]}`}
                >
                  <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-2xl bg-brand-500/10 transition-colors group-hover:bg-brand-500">
                    <Icon className="h-7 w-7 text-brand-700 transition-colors group-hover:text-white" />
                  </div>
                  <h3 className="font-display text-xl font-bold text-surface-950">{feature.title}</h3>
                  <p className="mt-3 text-sm leading-6 text-surface-800">{feature.desc}</p>
                </motion.div>
              )
            })}
          </motion.div>
        </div>
      </section>

      <section className="px-6 py-24">
        <div className="organic-card mx-auto max-w-5xl p-8 text-center md:p-12">
          <h2 className="font-display text-4xl font-bold text-surface-950">Ready to build trustworthy AI?</h2>
          <p className="mx-auto mt-4 max-w-2xl text-surface-800">
            Upload your documents, ask questions, and watch the agent reason transparently.
          </p>
          <Link to="/signup" className="organic-button mt-8 inline-flex items-center gap-2">
            Get started for free <ChevronRight className="h-4 w-4" />
          </Link>
        </div>
      </section>

      <footer className="border-t border-timber/60 px-6 py-8">
        <div className="mx-auto flex max-w-6xl flex-col gap-2 text-sm text-surface-800 sm:flex-row sm:items-center sm:justify-between">
          <span>AgenticRAG - Built with FastAPI, LangGraph, ChromaDB, React</span>
          <span>Excellence Technologies</span>
        </div>
      </footer>
    </div>
  )
}
