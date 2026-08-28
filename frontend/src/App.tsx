import { NavLink, Route, Routes } from "react-router-dom";
import CapabilitiesPage from "./pages/CapabilitiesPage";
import EventsPage from "./pages/EventsPage";
import FilterRulesPage from "./pages/FilterRulesPage";
import KnowledgePage from "./pages/KnowledgePage";
import OrganizationsPage from "./pages/OrganizationsPage";
import OwnersPage from "./pages/OwnersPage";
import SourcesPage from "./pages/SourcesPage";

const NAV_ITEMS = [
  { to: "/events", label: "事件 / 运行" },
  { to: "/sources", label: "信息源" },
  { to: "/filter-rules", label: "过滤规则" },
  { to: "/organizations", label: "重点单位" },
  { to: "/knowledge", label: "行业知识" },
  { to: "/capabilities", label: "公司能力" },
  { to: "/owners", label: "客户经理" },
];

export default function App() {
  return (
    <>
      <aside className="app-sidebar">
        <h1>Opportunity Platform</h1>
        <nav>
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => (isActive ? "active" : undefined)}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="app-content">
        <Routes>
          <Route path="/" element={<EventsPage />} />
          <Route path="/events" element={<EventsPage />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/filter-rules" element={<FilterRulesPage />} />
          <Route path="/organizations" element={<OrganizationsPage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/capabilities" element={<CapabilitiesPage />} />
          <Route path="/owners" element={<OwnersPage />} />
        </Routes>
      </main>
    </>
  );
}
