import {
  lazy,
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  Activity,
  ArrowRight,
  BarChart3,
  BrainCircuit,
  ChevronDown,
  ClipboardList,
  FileBarChart2,
  FileSearch,
  GitBranch,
  LayoutDashboard,
  Menu,
  Moon,
  Network,
  RefreshCw,
  Search,
  Shield,
  Sparkles,
  Sun,
  X,
  Zap,
} from "lucide-react";

import { motion, AnimatePresence } from "framer-motion";

import { getDashboardData } from "./services/dashboardApi";
import { getActiveInvestigationId } from "./services/activeInvestigation";

import "./pages/investigations-page.css";
import "./pages/reports-page.css";
import "./pages/landing-page.css";
import GlobalSearch from "./components/GlobalSearch";
import "./components/global-search.css";


/* =========================================================
   LAZY LOADED MODULES
   ========================================================= */

const Evidence = lazy(() => import("./pages/Evidence"));
const Graph = lazy(() => import("./pages/Graph"));
const Analytics = lazy(() => import("./pages/Analytics"));
const Assistant = lazy(() => import("./pages/Assistant"));
const Cases = lazy(() => import("./pages/Cases"));
const Investigations = lazy(() => import("./pages/Investigations"));
const Reports = lazy(() => import("./pages/Reports"));
const InvestigationWorkspace = lazy(
  () => import("./pages/InvestigationWorkspace")
);


/* =========================================================
   CONFIGURATION
   ========================================================= */

const REFRESH_INTERVAL_MS = 10000;


/* =========================================================
   NAVIGATION
   ========================================================= */

const NAVIGATION = [
  {
    key: "dashboard",
    label: "Command Center",
    icon: LayoutDashboard,
    description: "Live intelligence overview",
  },
  {
    key: "evidence",
    label: "Evidence",
    icon: FileSearch,
    description: "Evidence intelligence",
  },
  {
    key: "graph",
    label: "Investigation Graph",
    icon: Network,
    description: "Connected intelligence",
  },
  {
    key: "analytics",
    label: "Analytics",
    icon: BarChart3,
    description: "Risk and patterns",
  },
  {
    key: "assistant",
    label: "AI Assistant",
    icon: BrainCircuit,
    description: "Investigative intelligence",
  },
  {
    key: "cases",
    label: "Cases",
    icon: GitBranch,
    description: "Case management",
  },
  {
    key: "investigations",
    label: "Investigations",
    icon: ClipboardList,
    description: "Investigation registry",
  },
  {
    key: "investigation-workspace",
    label: "Workspace",
    icon: Activity,
    description: "Unified investigation view",
  },
  {
    key: "reports",
    label: "Reports",
    icon: FileBarChart2,
    description: "Intelligence reporting",
  },
];


/* =========================================================
   URL ROUTING
   ========================================================= */

function getPageFromPath() {
  const path = window.location.pathname
    .replace(/^\/+|\/+$/g, "")
    .toLowerCase();

  switch (path) {
    case "dashboard":
      return "dashboard";

    case "evidence":
      return "evidence";

    case "graph":
      return "graph";

    case "analytics":
      return "analytics";

    case "assistant":
      return "assistant";

    case "cases":
      return "cases";

    case "investigations":
      return "investigations";

    case "investigation-workspace":
      return "investigation-workspace";

    case "reports":
      return "reports";

    case "":
      return "home";

    default:
      return "home";
  }
}


/* =========================================================
   HELPERS
   ========================================================= */

function formatNumber(value) {
  const numeric = Number(value);

  if (!Number.isFinite(numeric)) {
    return "—";
  }

  return numeric.toLocaleString();
}


function getRiskScore(summary) {
  const candidates = [
    summary?.risk?.score,
    summary?.risk?.risk_score,
    summary?.risk?.results?.score,
    summary?.risk?.results?.risk_score,
    summary?.risk?.results?.overall_score,
    summary?.risk?.assessment?.score,
    summary?.risk?.assessment?.risk_score,
  ];

  const value = candidates.find(
    (item) =>
      item !== undefined &&
      item !== null
  );

  if (value === undefined) {
    return null;
  }

  const numeric = Number(value);

  if (!Number.isFinite(numeric)) {
    return null;
  }

  return numeric <= 1
    ? Math.round(numeric * 100)
    : Math.round(numeric);
}


function getRiskLabel(score) {
  if (score === null) {
    return "Unavailable";
  }

  if (score >= 70) {
    return "High";
  }

  if (score >= 40) {
    return "Moderate";
  }

  return "Minimal";
}


/* =========================================================
   APP
   ========================================================= */

function App() {
  const [activePage, setActivePage] = useState(
    getPageFromPath
  );

  const [globalSearchOpen, setGlobalSearchOpen] =
  useState(false);

  const [theme, setTheme] = useState(() => {
    try {
      return (
        localStorage.getItem("trinetra-theme") ||
        "dark"
      );
    } catch {
      return "dark";
    }
  });

  const [mobileMenuOpen, setMobileMenuOpen] =
    useState(false);

  const [searchOpen, setSearchOpen] =
    useState(false);

  const [searchQuery, setSearchQuery] =
    useState("");

  const [systemData, setSystemData] =
    useState(null);

  const [systemLoading, setSystemLoading] =
    useState(true);

  const [systemRefreshing, setSystemRefreshing] =
    useState(false);

  const [systemError, setSystemError] =
    useState(null);

 


  /* =======================================================
     THEME
     ======================================================= */

  useEffect(() => {
    document.documentElement.dataset.theme =
      theme;

    try {
      localStorage.setItem(
        "trinetra-theme",
        theme
      );
    } catch {
      // localStorage is optional.
    }
  }, [theme]);

  useEffect(() => {
  const handleGlobalSearchShortcut = (event) => {
    if (
      (event.ctrlKey || event.metaKey) &&
      event.key.toLowerCase() === "k"
    ) {
      event.preventDefault();
      setGlobalSearchOpen(true);
    }
  };

  window.addEventListener(
    "keydown",
    handleGlobalSearchShortcut
  );

  return () => {
    window.removeEventListener(
      "keydown",
      handleGlobalSearchShortcut
    );
  };
}, []);


  /* =======================================================
     API-DRIVEN SYSTEM OVERVIEW
     ======================================================= */

  const loadSystemData = useCallback(
    async (manual = false) => {
      if (manual) {
        setSystemRefreshing(true);
      } else {
        setSystemLoading(true);
      }

      try {
        /*
         * This is ONLY the landing/command-center
         * system overview.
         *
         * It does NOT make investigation 1 the
         * global application context.
         */
        const data = await getDashboardData(getActiveInvestigationId());

        setSystemData(data);
        setSystemError(null);
      } catch (error) {
        setSystemError(
          error?.message ||
            "Unable to connect to TRINETRA backend."
        );
      } finally {
        setSystemLoading(false);
        setSystemRefreshing(false);
      }
    },
    []
  );


  useEffect(() => {
    loadSystemData();

    const timer =
      window.setInterval(
        () => loadSystemData(),
        REFRESH_INTERVAL_MS
      );

    return () =>
      window.clearInterval(timer);
  }, [loadSystemData]);


  /* =======================================================
     BROWSER BACK / FORWARD
     ======================================================= */

  useEffect(() => {
    const handlePopState = () => {
      setActivePage(
        getPageFromPath()
      );

      setMobileMenuOpen(false);
    };

    window.addEventListener(
      "popstate",
      handlePopState
    );

    return () => {
      window.removeEventListener(
        "popstate",
        handlePopState
      );
    };
  }, []);


  /* =======================================================
     NAVIGATION
     ======================================================= */

  const navigate = useCallback(
    (page) => {
      setActivePage(page);
      setMobileMenuOpen(false);
      setSearchOpen(false);
      setSearchQuery("");

      const path =
        page === "home"
          ? "/"
          : `/${page}`;

      if (
        window.location.pathname !== path
      ) {
        window.history.pushState(
          {},
          "",
          path
        );
      }

      window.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    },
    []
  );


  /* =======================================================
     SEARCH
     ======================================================= */

  const searchResults = useMemo(() => {
    const query =
      searchQuery.trim().toLowerCase();

    if (!query) {
      return NAVIGATION.slice(0, 6);
    }

    return NAVIGATION.filter(
      (item) =>
        item.label
          .toLowerCase()
          .includes(query) ||
        item.description
          .toLowerCase()
          .includes(query)
    );
  }, [searchQuery]);


  /* =======================================================
     SYSTEM METRICS
     ======================================================= */

  const stats = useMemo(() => {
    const graphNodes =
      systemData?.stats?.nodes ?? null;

    const graphRelationships =
      systemData?.stats?.relationships ?? null;

    const evidence = Array.isArray(
      systemData?.evidence
    )
      ? systemData.evidence.length
      : null;

    const risk =
      getRiskScore(
        systemData?.summary
      );

    return {
      nodes: graphNodes,
      relationships:
        graphRelationships,
      evidence,
      risk,
    };
  }, [systemData]);


  /* =======================================================
     PAGE RENDERER
     ======================================================= */

  const renderPage = () => {
    switch (activePage) {
      case "dashboard":
        return (
          <CommandCenter
            systemData={systemData}
            stats={stats}
            loading={systemLoading}
            error={systemError}
            onNavigate={navigate}
          />
        );

      case "evidence":
        return (
          <Suspense fallback={<PageLoading />}>
            <Evidence />
          </Suspense>
        );

      case "graph":
        return (
          <Suspense fallback={<PageLoading />}>
            <Graph />
          </Suspense>
        );

      case "analytics":
        return (
          <Suspense fallback={<PageLoading />}>
            <Analytics />
          </Suspense>
        );

      case "assistant":
        return (
          <Suspense fallback={<PageLoading />}>
            <Assistant />
          </Suspense>
        );

      case "cases":
        return (
          <Suspense fallback={<PageLoading />}>
            <Cases />
          </Suspense>
        );

      case "investigations":
        return (
          <Suspense fallback={<PageLoading />}>
            <Investigations />
          </Suspense>
        );

      case "investigation-workspace":
        return (
          <Suspense fallback={<PageLoading />}>
            <InvestigationWorkspace />
          </Suspense>
        );

      case "reports":
        return (
          <Suspense fallback={<PageLoading />}>
            <Reports />
          </Suspense>
        );

      case "home":
      default:
        return (
          <LandingPage
            stats={stats}
            loading={systemLoading}
            systemError={systemError}
            onNavigate={navigate}
          />
        );
    }
  };


  return (
    <div className="tn-app">

      {/* =================================================
          ANIMATED BACKGROUND
          ================================================= */}

      <AnimatedBackground />


      {/* =================================================
          NAVBAR
          ================================================= */}

      <Navbar
        activePage={activePage}
        onNavigate={navigate}
        theme={theme}
        onToggleTheme={() =>
          setTheme(
            (current) =>
              current === "dark"
                ? "light"
                : "dark"
          )
        }
        mobileMenuOpen={
          mobileMenuOpen
        }
        onToggleMobileMenu={() =>
          setMobileMenuOpen(
            (current) => !current
          )
        }
        onSearch={() =>
          setSearchOpen(true)
        }
      />


      {/* =================================================
          SEARCH OVERLAY
          ================================================= */}

      <AnimatePresence>
        {searchOpen && (
          <SearchOverlay
            query={searchQuery}
            setQuery={setSearchQuery}
            results={searchResults}
            onNavigate={navigate}
            onClose={() =>
              setSearchOpen(false)
            }
          />
        )}
      </AnimatePresence>


      {/* =================================================
          MOBILE NAV
          ================================================= */}

      <AnimatePresence>
        {mobileMenuOpen && (
          <MobileNavigation
            activePage={activePage}
            navigation={NAVIGATION}
            onNavigate={navigate}
          />
        )}
      </AnimatePresence>


      {/* =================================================
          MAIN CONTENT
          ================================================= */}

      <main className="tn-app-main">
        {renderPage()}
      </main>


      {/* =================================================
          FLOATING AI ASSISTANT
          ================================================= */}

      <FloatingAssistant
        onOpen={() =>
          navigate("assistant")
        }
      />


      {/* =================================================
          FOOTER
          ================================================= */}

      {activePage === "home" && (
        <LandingFooter
          onNavigate={navigate}
        />
      )}

    </div>
  );
}


/* =========================================================
   ANIMATED BACKGROUND
   ========================================================= */

function AnimatedBackground() {
  return (
    <div
      className="tn-animated-background"
      aria-hidden="true"
    >
      <div className="tn-bg-orb tn-bg-orb-one" />
      <div className="tn-bg-orb tn-bg-orb-two" />
      <div className="tn-bg-orb tn-bg-orb-three" />

      <div className="tn-bg-grid" />

      <div className="tn-bg-noise" />
    </div>
  );
}


/* =========================================================
   NAVBAR
   ========================================================= */

function Navbar({
  activePage,
  onNavigate,
  theme,
  onToggleTheme,
  mobileMenuOpen,
  onToggleMobileMenu,
  onSearch,
}) {
  return (
    <header className="tn-navbar">

      <div className="tn-navbar-inner">

        {/* BRAND */}

        <button
          type="button"
          className="tn-navbar-brand"
          onClick={() =>
            onNavigate("home")
          }
        >
          <div className="tn-navbar-logo">
            <span />
            <span />
            <span />
          </div>

          <div>
            <div className="tn-navbar-brand-name">
              TRINETRA
            </div>

            <div className="tn-navbar-brand-caption">
              INTELLIGENCE PLATFORM
            </div>
          </div>
        </button>


        {/* DESKTOP NAV */}

        <nav className="tn-navbar-nav">
          {NAVIGATION.slice(0, 7).map(
            (item) => {
              const Icon = item.icon;

              return (
                <button
                  key={item.key}
                  type="button"
                  className={`tn-navbar-link ${
                    activePage === item.key
                      ? "active"
                      : ""
                  }`}
                  onClick={() =>
                    onNavigate(
                      item.key
                    )
                  }
                >
                  <Icon size={15} />

                  <span>
                    {item.label}
                  </span>
                </button>
              );
            }
          )}

          <button
            type="button"
            className={`tn-navbar-link ${
              activePage ===
              "investigation-workspace"
                ? "active"
                : ""
            }`}
            onClick={() =>
              onNavigate(
                "investigation-workspace"
              )
            }
          >
            <Activity size={15} />
            <span>Workspace</span>
          </button>

          <button
            type="button"
            className={`tn-navbar-link ${
              activePage === "reports"
                ? "active"
                : ""
            }`}
            onClick={() =>
              onNavigate("reports")
            }
          >
            <FileBarChart2 size={15} />
            <span>Reports</span>
          </button>
        </nav>


        {/* ACTIONS */}

        <div className="tn-navbar-actions">

          <button
            type="button"
            className="tn-navbar-search"
            onClick={onSearch}
          >
            <Search size={15} />
            <span>Search</span>
            <kbd>⌘K</kbd>
          </button>


          <button
            type="button"
            className="tn-theme-button"
            onClick={onToggleTheme}
            aria-label="Toggle theme"
          >
            {theme === "dark" ? (
              <Sun size={16} />
            ) : (
              <Moon size={16} />
            )}
          </button>


          <button
            type="button"
            className="tn-mobile-menu-button"
            onClick={onToggleMobileMenu}
            aria-label="Open navigation"
          >
            {mobileMenuOpen ? (
              <X size={19} />
            ) : (
              <Menu size={19} />
            )}
          </button>

        </div>

      </div>
    </header>
  );
}


/* =========================================================
   SEARCH OVERLAY
   ========================================================= */

function SearchOverlay({
  query,
  setQuery,
  results,
  onNavigate,
  onClose,
}) {
  return (
    <motion.div
      className="tn-search-overlay"
      initial={{
        opacity: 0,
      }}
      animate={{
        opacity: 1,
      }}
      exit={{
        opacity: 0,
      }}
    >
      <motion.div
        className="tn-search-modal"
        initial={{
          y: -20,
          scale: 0.98,
        }}
        animate={{
          y: 0,
          scale: 1,
        }}
        exit={{
          y: -20,
          scale: 0.98,
        }}
      >

        <div className="tn-search-header">

          <div className="tn-search-input-wrap">
            <Search size={18} />

            <input
              autoFocus
              value={query}
              onChange={(event) =>
                setQuery(
                  event.target.value
                )
              }
              placeholder="Search TRINETRA modules..."
            />
          </div>

          <button
            type="button"
            onClick={onClose}
            className="tn-search-close"
          >
            <X size={18} />
          </button>

        </div>


        <div className="tn-search-results">

          {results.length === 0 ? (
            <div className="tn-search-empty">
              <Search size={24} />

              <strong>
                No module found
              </strong>

              <span>
                Try Evidence, Graph,
                Analytics, Cases or Reports.
              </span>
            </div>
          ) : (
            results.map((item) => {
              const Icon = item.icon;

              return (
                <button
                  type="button"
                  key={item.key}
                  className="tn-search-result"
                  onClick={() =>
                    onNavigate(
                      item.key
                    )
                  }
                >
                  <div className="tn-search-result-icon">
                    <Icon size={18} />
                  </div>

                  <div>
                    <strong>
                      {item.label}
                    </strong>

                    <span>
                      {item.description}
                    </span>
                  </div>

                  <ArrowRight
                    size={16}
                  />
                </button>
              );
            })
          )}

        </div>

      </motion.div>
    </motion.div>
  );
}


/* =========================================================
   MOBILE NAVIGATION
   ========================================================= */

function MobileNavigation({
  activePage,
  navigation,
  onNavigate,
}) {
  return (
    <motion.div
      className="tn-mobile-navigation"
      initial={{
        opacity: 0,
        y: -10,
      }}
      animate={{
        opacity: 1,
        y: 0,
      }}
      exit={{
        opacity: 0,
        y: -10,
      }}
    >
      {navigation.map((item) => {
        const Icon = item.icon;

        return (
          <button
            type="button"
            key={item.key}
            className={`tn-mobile-nav-item ${
              activePage === item.key
                ? "active"
                : ""
            }`}
            onClick={() =>
              onNavigate(
                item.key
              )
            }
          >
            <Icon size={17} />

            <div>
              <strong>
                {item.label}
              </strong>

              <span>
                {item.description}
              </span>
            </div>

            <ArrowRight size={15} />
          </button>
        );
      })}
    </motion.div>
  );
}


/* =========================================================
   LANDING PAGE
   ========================================================= */

function LandingPage({
  stats,
  loading,
  systemError,
  onNavigate,
}) {
  return (
    <div className="tn-landing">

      {/* HERO */}

      <section className="tn-landing-hero">

        <motion.div
          className="tn-landing-copy"
          initial={{
            opacity: 0,
            y: 24,
          }}
          animate={{
            opacity: 1,
            y: 0,
          }}
          transition={{
            duration: 0.7,
          }}
        >

          <div className="tn-landing-eyebrow">
            <span className="tn-live-dot" />
            INTELLIGENCE OPERATIONS PLATFORM
          </div>


          <h1>
            Turn complex intelligence
            into{" "}
            <span>
              connected insight.
            </span>
          </h1>


          <p>
            TRINETRA brings evidence,
            entities, relationships,
            investigations, analytics,
            graph intelligence and AI
            assistance into one operational
            platform.
          </p>


          <div className="tn-landing-actions">

            <button
              type="button"
              className="tn-primary-action"
              onClick={() =>
                onNavigate("dashboard")
              }
            >
              Open Command Center
              <ArrowRight size={17} />
            </button>


            <button
              type="button"
              className="tn-secondary-action"
              onClick={() =>
                onNavigate("graph")
              }
            >
              Explore Intelligence Graph
              <Network size={16} />
            </button>

          </div>


          <div className="tn-landing-trust">

            <Shield size={15} />

            <span>
              API-driven · PostgreSQL · Neo4j ·
              Analytics · AI
            </span>

          </div>

        </motion.div>


        {/* HERO VISUAL */}

        <HeroIntelligenceVisual
          stats={stats}
          loading={loading}
        />

      </section>


      {/* LIVE STATUS */}

      <section className="tn-landing-status">

        <div className="tn-status-card">

          <div>
            <span className="tn-status-label">
              SYSTEM STATUS
            </span>

            <strong>
              {systemError
                ? "DEGRADED"
                : "OPERATIONAL"}
            </strong>
          </div>

          <div className="tn-status-pulse">
            <span />
            LIVE API
          </div>

        </div>


        <LiveMetric
          label="Graph Nodes"
          value={stats.nodes}
          loading={loading}
        />

        <LiveMetric
          label="Relationships"
          value={stats.relationships}
          loading={loading}
        />

        <LiveMetric
          label="Evidence"
          value={stats.evidence}
          loading={loading}
        />

        <LiveMetric
          label="Risk Signal"
          value={
            stats.risk === null
              ? "—"
              : `${stats.risk}/100`
          }
          loading={loading}
        />

      </section>


      {/* PLATFORM FEATURES */}

      <section className="tn-features-section">

        <div className="tn-section-heading">

          <div>
            <span className="tn-section-kicker">
              PLATFORM CAPABILITIES
            </span>

            <h2>
              One intelligence
              operating layer.
            </h2>
          </div>

          <p>
            Explore every part of TRINETRA
            without being locked to a single
            investigation or case.
          </p>

        </div>


        <div className="tn-feature-grid">

          <FeatureCard
            icon={FileSearch}
            number="01"
            title="Evidence Intelligence"
            description="Upload, extract, search and connect documentary evidence to the intelligence model."
            onClick={() =>
              onNavigate("evidence")
            }
          />

          <FeatureCard
            icon={Network}
            number="02"
            title="Connected Graph"
            description="Explore entities and relationships through the Neo4j intelligence graph."
            onClick={() =>
              onNavigate("graph")
            }
          />

          <FeatureCard
            icon={BarChart3}
            number="03"
            title="Analytics"
            description="Identify patterns, centrality, connectivity and analytical risk signals."
            onClick={() =>
              onNavigate("analytics")
            }
          />

          <FeatureCard
            icon={ClipboardList}
            number="04"
            title="Investigations"
            description="Manage multiple investigations independently using live backend data."
            onClick={() =>
              onNavigate("investigations")
            }
          />

          <FeatureCard
            icon={GitBranch}
            number="05"
            title="Case Management"
            description="Create and manage cases while keeping investigation scope separate."
            onClick={() =>
              onNavigate("cases")
            }
          />

          <FeatureCard
            icon={BrainCircuit}
            number="06"
            title="AI Investigation Assistant"
            description="Ask grounded questions using investigation context, graph intelligence and evidence."
            onClick={() =>
              onNavigate("assistant")
            }
          />

          <FeatureCard
            icon={Activity}
            number="07"
            title="Investigation Workspace"
            description="Bring evidence, entities, relationships and analytics together around the selected investigation."
            onClick={() =>
              onNavigate(
                "investigation-workspace"
              )
            }
          />

          <FeatureCard
            icon={FileBarChart2}
            number="08"
            title="Intelligence Reports"
            description="Generate structured intelligence reports and investigative documentary outputs."
            onClick={() =>
              onNavigate("reports")
            }
          />

        </div>

      </section>


      {/* HOW IT WORKS */}

      <section className="tn-platform-flow">

        <div className="tn-section-heading">

          <div>
            <span className="tn-section-kicker">
              OPERATIONAL MODEL
            </span>

            <h2>
              From raw evidence
              to intelligence.
            </h2>
          </div>

        </div>


        <div className="tn-flow">

          <FlowStep
            number="01"
            title="Ingest"
            description="Evidence enters TRINETRA through the API."
            icon={UploadIcon}
          />

          <FlowStep
            number="02"
            title="Extract"
            description="Documents and OCR become structured intelligence."
            icon={Zap}
          />

          <FlowStep
            number="03"
            title="Connect"
            description="Entities and relationships form the graph."
            icon={Network}
          />

          <FlowStep
            number="04"
            title="Analyze"
            description="Patterns and risk signals surface."
            icon={BarChart3}
          />

          <FlowStep
            number="05"
            title="Investigate"
            description="Analysts explore, ask and report."
            icon={BrainCircuit}
          />

        </div>

      </section>


      {/* FINAL CTA */}

      <section className="tn-landing-cta">

        <div>

          <span>
            READY FOR INTELLIGENCE OPERATIONS?
          </span>

          <h2>
            Explore TRINETRA.
          </h2>

          <p>
            Start from the platform,
            then choose the intelligence
            workflow you need.
          </p>

        </div>

        <button
          type="button"
          className="tn-primary-action"
          onClick={() =>
            onNavigate("dashboard")
          }
        >
          Enter Platform
          <ArrowRight size={17} />
        </button>

      </section>

    </div>
  );
}


/* =========================================================
   HERO INTELLIGENCE VISUAL
   ========================================================= */

function HeroIntelligenceVisual({
  stats,
  loading,
}) {
  return (
    <motion.div
      className="tn-hero-visual"
      initial={{
        opacity: 0,
        scale: 0.96,
      }}
      animate={{
        opacity: 1,
        scale: 1,
      }}
      transition={{
        duration: 0.8,
        delay: 0.15,
      }}
    >

      <div className="tn-hero-visual-glow" />

      <div className="tn-hero-orbit orbit-one" />
      <div className="tn-hero-orbit orbit-two" />

      <div className="tn-hero-core">
        <div className="tn-core-icon">
          <Network size={30} />
        </div>

        <strong>
          TRINETRA
        </strong>

        <span>
          CONNECTED INTELLIGENCE
        </span>
      </div>


      <div className="tn-hero-node node-a">
        <span />
        <strong>
          EVIDENCE
        </strong>
      </div>

      <div className="tn-hero-node node-b">
        <span />
        <strong>
          ENTITIES
        </strong>
      </div>

      <div className="tn-hero-node node-c">
        <span />
        <strong>
          GRAPH
        </strong>
      </div>

      <div className="tn-hero-node node-d">
        <span />
        <strong>
          ANALYTICS
        </strong>
      </div>


      <div className="tn-hero-live-card">

        <div>
          <Activity size={14} />

          <span>
            LIVE SYSTEM
          </span>
        </div>

        <strong>
          {loading
            ? "SYNCING..."
            : `${formatNumber(
                stats.nodes
              )} NODES`}
        </strong>

      </div>

    </motion.div>
  );
}


/* =========================================================
   LIVE METRIC
   ========================================================= */

function LiveMetric({
  label,
  value,
  loading,
}) {
  return (
    <div className="tn-live-metric">

      <span>
        {label}
      </span>

      <strong>
        {loading
          ? "..."
          : typeof value === "number"
          ? formatNumber(value)
          : value}
      </strong>

    </div>
  );
}


/* =========================================================
   FEATURE CARD
   ========================================================= */

function FeatureCard({
  icon: Icon,
  number,
  title,
  description,
  onClick,
}) {
  return (
    <motion.button
      type="button"
      className="tn-feature-card"
      onClick={onClick}
      whileHover={{
        y: -7,
      }}
      transition={{
        duration: 0.2,
      }}
    >

      <div className="tn-feature-top">

        <span>
          {number}
        </span>

        <Icon size={20} />

      </div>


      <div className="tn-feature-content">

        <h3>
          {title}
        </h3>

        <p>
          {description}
        </p>

      </div>


      <div className="tn-feature-arrow">
        <ArrowRight size={16} />
      </div>

    </motion.button>
  );
}


/* =========================================================
   FLOW STEP
   ========================================================= */

function FlowStep({
  number,
  title,
  description,
  icon: Icon,
}) {
  return (
    <div className="tn-flow-step">

      <div className="tn-flow-number">
        {number}
      </div>

      <div className="tn-flow-icon">
        <Icon size={20} />
      </div>

      <h3>
        {title}
      </h3>

      <p>
        {description}
      </p>

    </div>
  );
}


/* =========================================================
   COMMAND CENTER
   ========================================================= */

function CommandCenter({
  systemData,
  stats,
  loading,
  error,
  onNavigate,
}) {
  const investigation =
    systemData?.summary
      ?.investigation || {};

  return (
    <section className="tn-command-center-page">

      <div className="tn-module-header">

        <div>

          <span className="tn-section-kicker">
            TRINETRA COMMAND CENTER
          </span>

          <h1>
            Intelligence Operations
          </h1>

          <p>
            Live system overview across
            PostgreSQL, Neo4j and analytics.
          </p>

        </div>

        <div className="tn-module-status">
          <span />
          API CONNECTED
        </div>

      </div>


      <div className="tn-command-stat-grid">

        <LiveMetric
          label="Graph Nodes"
          value={stats.nodes}
          loading={loading}
        />

        <LiveMetric
          label="Relationships"
          value={stats.relationships}
          loading={loading}
        />

        <LiveMetric
          label="Evidence"
          value={stats.evidence}
          loading={loading}
        />

        <LiveMetric
          label="Risk Signal"
          value={
            stats.risk === null
              ? "—"
              : `${stats.risk}/100`
          }
          loading={loading}
        />

      </div>


      <div className="tn-command-grid">

        <div className="tn-command-panel">

          <span className="tn-section-kicker">
            SYSTEM
          </span>

          <h2>
            Connected intelligence
          </h2>

          <p>
            TRINETRA is connected to the
            backend intelligence stack.
          </p>

          <div className="tn-command-sources">

            <span>
              <i />
              PostgreSQL
            </span>

            <span>
              <i />
              Neo4j
            </span>

            <span>
              <i />
              Analytics
            </span>

          </div>

        </div>


        <div className="tn-command-panel">

          <span className="tn-section-kicker">
            AVAILABLE MODULES
          </span>

          <div className="tn-command-links">

            <CommandLink
              title="Evidence"
              onClick={() =>
                onNavigate("evidence")
              }
            />

            <CommandLink
              title="Graph"
              onClick={() =>
                onNavigate("graph")
              }
            />

            <CommandLink
              title="Analytics"
              onClick={() =>
                onNavigate("analytics")
              }
            />

            <CommandLink
              title="AI Assistant"
              onClick={() =>
                onNavigate("assistant")
              }
            />

            <CommandLink
              title="Reports"
              onClick={() =>
                onNavigate("reports")
              }
            />

          </div>

        </div>

      </div>


      <div className="tn-command-investigation">

        <span className="tn-section-kicker">
          CURRENT API CONTEXT
        </span>

        <h2>
          {investigation.title ||
            "No active investigation context"}
        </h2>

        <p>
          {investigation.objective ||
            "Select an investigation inside the relevant module to work with investigation-specific data."}
        </p>

        <button
          type="button"
          className="tn-secondary-action"
          onClick={() =>
            onNavigate(
              "investigations"
            )
          }
        >
          Browse investigations
          <ArrowRight size={16} />
        </button>

      </div>


      {error && (
        <div className="tn-command-error">
          <Shield size={16} />

          <span>
            {error}
          </span>
        </div>
      )}

    </section>
  );
}


/* =========================================================
   COMMAND LINK
   ========================================================= */

function CommandLink({
  title,
  onClick,
}) {
  return (
    <button
      type="button"
      onClick={onClick}
    >
      <span>
        {title}
      </span>

      <ArrowRight size={15} />
    </button>
  );
}


/* =========================================================
   UPLOAD ICON
   ========================================================= */

function UploadIcon(props) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.8"
      {...props}
    >
      <path
        d="M12 3v12"
      />

      <path
        d="m7 8 5-5 5 5"
      />

      <path
        d="M5 21h14"
      />

      <path
        d="M5 16v5"
      />

      <path
        d="M19 16v5"
      />
    </svg>
  );
}


/* =========================================================
   FLOATING AI ASSISTANT
   ========================================================= */

function FloatingAssistant({
  onOpen,
}) {
  return (
    <motion.button
      type="button"
      className="tn-floating-assistant"
      onClick={onOpen}
      initial={{
        opacity: 0,
        scale: 0.8,
      }}
      animate={{
        opacity: 1,
        scale: 1,
      }}
      transition={{
        delay: 0.8,
        type: "spring",
      }}
      whileHover={{
        scale: 1.05,
      }}
      whileTap={{
        scale: 0.96,
      }}
    >

      <span className="tn-assistant-pulse" />

      <BrainCircuit size={21} />

      <div>
        <strong>
          AI Assistant
        </strong>

        <span>
          Ask TRINETRA
        </span>
      </div>

    </motion.button>
  );
}


/* =========================================================
   LANDING FOOTER
   ========================================================= */

function LandingFooter({
  onNavigate,
}) {
  return (
    <footer className="tn-landing-footer">

      <div>

        <strong>
          TRINETRA
        </strong>

        <span>
          Intelligence Platform
        </span>

      </div>


      <div className="tn-footer-links">

        <button
          type="button"
          onClick={() =>
            onNavigate("graph")
          }
        >
          Graph
        </button>

        <button
          type="button"
          onClick={() =>
            onNavigate("analytics")
          }
        >
          Analytics
        </button>

        <button
          type="button"
          onClick={() =>
            onNavigate("assistant")
          }
        >
          AI Assistant
        </button>

        <button
          type="button"
          onClick={() =>
            onNavigate("reports")
          }
        >
          Reports
        </button>

      </div>


      <span className="tn-footer-build">
        TRINETRA // PROTOTYPE
      </span>

    </footer>
  );
}


/* =========================================================
   PAGE LOADING
   ========================================================= */

function PageLoading() {
  return (
    <div className="tn-page-loading">

      <RefreshCw
        size={25}
        className="tn-spin"
      />

      <span>
        Loading TRINETRA module...
      </span>

    </div>
  );
}


export default App;