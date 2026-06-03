import {
  BookOpenCheck,
  ChevronRight,
  PackageCheck,
  Ruler,
  Search,
  Sprout
} from "./icons";
import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { SeoHead } from "./SeoHead";
import type { GuidePost } from "../lib/api";
import { guidePath } from "../lib/seo";
import { useLanguage } from "../contexts/LanguageContext";
import { withLanguagePrefix } from "../lib/localizedRoutes";
import { guideHeadingId } from "../lib/guideMarkdown";

type Props = {
  guides: GuidePost[];
};

type GuideView = GuidePost & {
  family: string;
  plant: string;
  section: "Cẩm nang" | "Chăm sóc";
};

type GuideBlock = {
  heading: string;
  headingId?: string;
  body: string[];
  bullets: string[];
  tables: string[][][];
  images: { url: string; index: number }[];
};

const FAMILY_ORDER = ["Cây ăn quả", "Cây công nghiệp", "Cây lương thực", "Cây trồng khác"];

const CROP_META: Record<string, { plant: string; family: string }> = {
  sau_rieng: { plant: "Sầu riêng", family: "Cây công nghiệp" },
  mit: { plant: "Mít", family: "Cây ăn quả" },
  thanh_long: { plant: "Thanh long", family: "Cây ăn quả" },
  cam: { plant: "Cam", family: "Cây ăn quả" },
  xoai: { plant: "Xoài", family: "Cây ăn quả" },
  chom_chom: { plant: "Chôm chôm", family: "Cây ăn quả" },
  ca_phe: { plant: "Cà phê", family: "Cây công nghiệp" },
  ho_tieu: { plant: "Tiêu", family: "Cây công nghiệp" },
  lua: { plant: "Lúa", family: "Cây lương thực" },
  ot: { plant: "Ớt", family: "Cây trồng khác" }
};

export function GuideLibrary({ guides }: Props) {
  const { language } = useLanguage();
  const copy = language === "en"
    ? {
        seoTitle: "Crop production guides for durian, coffee, pepper and rice",
        seoDescription: "A practical farming guide library covering crop care, pest prevention, disease control and field-ready production workflows.",
        kicker: "Farming guides",
        title: "Crop production techniques",
        description: "Choose a crop group, select a crop, then read either field guides or care workflows by topic.",
        mobileFilters: "Mobile guide filters",
        shortcut: "Your shortcuts",
        plants: "crops",
        search: "Search technical guides",
        minutes: "min read",
        openGuide: "Open full guide"
      }
    : {
        seoTitle: "Quy trình kỹ thuật trồng sầu riêng, cà phê, hồ tiêu và lúa",
        seoDescription: "Thư viện hướng dẫn kỹ thuật nông nghiệp: cẩm nang, chăm sóc cây trồng, phòng trừ sâu bệnh và quy trình canh tác dễ tra cứu.",
        kicker: "Hướng dẫn nông nghiệp",
        title: "Quy trình kỹ thuật trồng trọt",
        description: "Chọn nhóm cây, chọn cây trồng rồi đọc cẩm nang hoặc quy trình chăm sóc theo từng chủ đề.",
        mobileFilters: "Bộ lọc hướng dẫn trên di động",
        shortcut: "Lối tắt của bạn",
        plants: "cây",
        search: "Tìm bài kỹ thuật",
        minutes: "phút đọc",
        openGuide: "Mở bài hướng dẫn đầy đủ"
      };
  const normalizedGuides = useMemo(() => guides.map(toGuideView).sort(sortGuides), [guides]);
  const [activeFamily, setActiveFamily] = useState("Cây công nghiệp");
  const [activePlant, setActivePlant] = useState("");
  const [activeSection, setActiveSection] = useState<"Cẩm nang" | "Chăm sóc">("Cẩm nang");
  const [query, setQuery] = useState("");
  const [selectedSlug, setSelectedSlug] = useState("");

  const familyStats = useMemo(() => {
    return FAMILY_ORDER.map((family) => ({
      family,
      count: normalizedGuides.filter((guide) => guide.family === family).length,
      plants: new Set(normalizedGuides.filter((guide) => guide.family === family).map((guide) => guide.plant)).size
    })).filter((item) => item.count > 0);
  }, [normalizedGuides]);

  const currentFamily = familyStats.some((item) => item.family === activeFamily)
    ? activeFamily
    : familyStats[0]?.family ?? "Cây công nghiệp";

  const plants = useMemo(() => {
    const plantMap = new Map<string, number>();
    normalizedGuides
      .filter((guide) => guide.family === currentFamily)
      .forEach((guide) => plantMap.set(guide.plant, (plantMap.get(guide.plant) ?? 0) + 1));
    return Array.from(plantMap.entries())
      .map(([plant, count]) => ({ plant, count }))
      .sort((a, b) => a.plant.localeCompare(b.plant, "vi"));
  }, [currentFamily, normalizedGuides]);

  const currentPlant = plants.some((item) => item.plant === activePlant) ? activePlant : plants[0]?.plant ?? "";
  const plantGuides = normalizedGuides.filter((guide) => guide.family === currentFamily && guide.plant === currentPlant);
  const sections = (["Cẩm nang", "Chăm sóc"] as const).map((section) => ({
    section,
    count: plantGuides.filter((guide) => guide.section === section).length
  }));
  const currentSection = sections.some((item) => item.section === activeSection && item.count > 0)
    ? activeSection
    : sections.find((item) => item.count > 0)?.section ?? activeSection;

  const visibleGuides = plantGuides.filter((guide) => {
    const matchesSection = guide.section === currentSection;
    const searchable = `${guide.title} ${guide.summary} ${guide.content}`.toLowerCase();
    return matchesSection && searchable.includes(query.trim().toLowerCase());
  });
  const selectedGuide = visibleGuides.find((guide) => guide.slug === selectedSlug) ?? visibleGuides[0] ?? plantGuides[0];

  return (
    <section className="content-page guide-workspace paper">
      <SeoHead
        title={copy.seoTitle}
        description={copy.seoDescription}
        canonical="/huong-dan"
      />
      <div className="p-wrap">
      <div className="tool-titlebar">
        <div>
          <span className="p-kicker">
            <span className="bar" />
            {copy.kicker}
          </span>
          <h1>{copy.title}</h1>
        </div>
        <p className="lead">{copy.description}</p>
      </div>

          <div className="g-families" aria-label={copy.mobileFilters}>
            {familyStats.map((item) => (
              <button
                type="button"
                className={`g-fam ${item.family === currentFamily ? "active" : ""}`}
                key={item.family}
                onClick={() => {
                  setActiveFamily(item.family);
                  setActivePlant("");
                  setSelectedSlug("");
                }}
              >
                <span className="nm">{displayFamily(item.family, language)}</span>
                <span className="ct">{language === "en" ? `${item.count} guides · ${item.plants} crops` : `${item.count} bài · ${item.plants} cây`}</span>
              </button>
            ))}
          </div>

          <div className="g-plants">
            {plants.map((item) => (
              <button
                type="button"
                className={item.plant === currentPlant ? "active" : ""}
                key={item.plant}
                onClick={() => {
                  setActivePlant(item.plant);
                setSelectedSlug("");
              }}
            >
              {displayPlant(item.plant, language)}
              <small>{item.count}</small>
            </button>
          ))}
          </div>

          <div className="g-browser">
            <aside className="g-list-panel">
              <div className="g-sections">
                {sections.map((item) => (
                  <button
                    type="button"
                    className={item.section === currentSection ? "active" : ""}
                    key={item.section}
                    disabled={item.count === 0}
                    onClick={() => {
                      setActiveSection(item.section);
                      setSelectedSlug("");
                    }}
                  >
                    {item.section === "Cẩm nang" ? <BookOpenCheck size={15} /> : <Sprout size={15} />}
                    {displaySection(item.section, language)}
                    <small>{item.count}</small>
                  </button>
                ))}
              </div>

              <label className="g-search">
                <Search size={16} />
                <input
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setSelectedSlug("");
                  }}
                  placeholder={copy.search}
                />
              </label>

              <div className="g-list">
                {visibleGuides.map((guide) => (
                  <button
                    type="button"
                    className={`g-item ${guide.slug === selectedGuide?.slug ? "active" : ""}`}
                    key={guide.slug}
                    onClick={() => setSelectedSlug(guide.slug)}
                  >
                    <span className="ti">{guide.title}</span>
                    <ChevronRight className="arr" size={15} />
                    <span className="mt">
                      {displaySection(guide.section, language)} · {displayPlant(guide.plant, language)} · {estimateReadingMinutes(guide.content)} {copy.minutes}
                    </span>
                  </button>
                ))}
                {visibleGuides.length === 0 ? (
                  <div className="guide-empty">{language === "en" ? "No matching guides." : "Không có bài phù hợp."}</div>
                ) : null}
              </div>
            </aside>

            <article className="g-detail">
              {selectedGuide ? (
                <>
                  <header>
                    <div className="g-tagrow">
                      <span className="brand">{selectedGuide.category}</span>
                      <span>{displayFamily(selectedGuide.family, language)}</span>
                      <span>{displayPlant(selectedGuide.plant, language)}</span>
                    </div>
                    <h2>{selectedGuide.title}</h2>
                    <p className="summary">{selectedGuide.summary}</p>
                    <div className="g-metagrid">
                      <div className="m">
                        <span className="k">{language === "en" ? "Reading time" : "Thời gian đọc"}</span>
                        <span className="v">{estimateReadingMinutes(selectedGuide.content)} {copy.minutes}</span>
                      </div>
                      <div className="m">
                        <span className="k">{language === "en" ? "Difficulty" : "Độ khó"}</span>
                        <span className="v">{technicalDifficulty(selectedGuide.content, language).replace(/^Độ khó:\s*|^Difficulty:\s*/i, "")}</span>
                      </div>
                      <div className="m">
                        <span className="k">{language === "en" ? "Updated" : "Cập nhật"}</span>
                        <span className="v">{formatGuideDate(selectedGuide.published_at, language)}</span>
                      </div>
                    </div>
                    <Link className="guide-canonical-link" to={withLanguagePrefix(guidePath(selectedGuide.slug), language)}>
                      {copy.openGuide}
                    </Link>
                  </header>
                  <div className="g-article">
                    <GuideContent content={selectedGuide.content} postId={selectedGuide.post_id} />
                    <GuideReferencePanel guide={selectedGuide} />
                  </div>
                </>
              ) : (
                <div className="guide-empty">
                  {language === "en" ? "Choose a crop to view its guides." : "Chọn một cây trồng để xem hướng dẫn."}
                </div>
              )}
            </article>
          </div>
      </div>
    </section>
  );
}

function GuideContent({ content, postId }: { content: string; postId: number }) {
  const { language } = useLanguage();
  const lines = content
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line && !line.toLowerCase().startsWith("nguồn"));
  const blocks: GuideBlock[] = [];
  let current: GuideBlock | null = null;
  let activeTable: string[][] | null = null;
  let imageIndex = 0;

  for (const line of lines) {
    const heading = normalizeGuideHeading(line);
    if (heading) {
      current = { heading: heading.text, headingId: heading.id, body: [], bullets: [], tables: [], images: [] };
      blocks.push(current);
      activeTable = null;
      continue;
    }
    if (!current) {
      current = { heading: language === "en" ? "Field notes" : "Ghi chú kỹ thuật", body: [], bullets: [], tables: [], images: [] };
      blocks.push(current);
    }
    if (line.startsWith("|")) {
      const cells = parseTableRow(line);
      if (cells.length && !cells.every((cell) => /^:?-{3,}:?$/.test(cell))) {
        if (!activeTable) {
          activeTable = [];
          current.tables.push(activeTable);
        }
        activeTable.push(cells);
      }
      continue;
    }
    activeTable = null;
    if (line.startsWith("IMAGE::")) {
      current.images.push({ url: line.slice("IMAGE::".length), index: imageIndex++ });
      continue;
    }
    if (line.startsWith("- ")) {
      current.bullets.push(line.slice(2));
    } else {
      current.body.push(line);
    }
  }

  return (
    <div className="g-prose">
      {blocks.map((block) => (
        <section key={block.heading}>
          <h3 id={block.headingId}>{block.heading || (language === "en" ? "Field notes" : "Ghi chú kỹ thuật")}</h3>
          {block.body.map((line) => (
            <p key={line}>{renderInlineMarkdown(line, language)}</p>
          ))}
          {block.tables.map((table, index) => renderMarkdownTable(table, index, language))}
          {block.images.length ? (
            <div className="guide-image-grid">
              {block.images.map((image) => (
                <img
                  src={guideImageUrl(postId, image.index)}
                  alt={block.heading}
                  loading="lazy"
                  decoding="async"
                  width="420"
                  height="260"
                  key={image.index}
                  onError={(event) => {
                    event.currentTarget.style.display = "none";
                  }}
                />
              ))}
            </div>
          ) : null}
          {block.bullets.length ? (
            <ul>
              {block.bullets.map((line) => (
                <li key={line}>{renderInlineMarkdown(line, language)}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ))}
    </div>
  );
}

function GuideReferencePanel({ guide }: { guide: GuideView }) {
  const { language } = useLanguage();
  const specs = standardSpecs(guide, language);
  const supplies = relatedSupplies(guide, language);

  return (
    <aside className="g-ref" aria-label={language === "en" ? "Quick reference" : "Thông tin tra cứu nhanh"}>
      <h4><Ruler size={14} /> {language === "en" ? "Standard checks" : "Thông số tiêu chuẩn"}</h4>
      {specs.map((item) => (
        <div className="row" key={item.label}>
          <span>{item.label}</span>
          <b>{item.value}</b>
        </div>
      ))}
      <h4><PackageCheck size={14} /> {language === "en" ? "Related supplies" : "Vật tư liên quan"}</h4>
      {supplies.map((item) => (
        <div className="row" key={item}>
          <span>{item}</span>
          <b>OK</b>
        </div>
      ))}
    </aside>
  );
}

function estimateReadingMinutes(content: string) {
  const words = content.replace(/IMAGE::\S+/g, "").trim().split(/\s+/).filter(Boolean).length;
  return Math.max(2, Math.ceil(words / 230));
}

function technicalDifficulty(content: string, language: "vi" | "en" = "vi") {
  const normalized = content.toLowerCase();
  const complexSignals = ["phun", "bệnh", "sâu", "liều", "ppm", "nấm", "cắt tỉa", "xử lý"];
  const score = complexSignals.filter((signal) => normalized.includes(signal)).length;
  if (language === "en") {
    if (score >= 4) return "Difficulty: advanced";
    if (score >= 2) return "Difficulty: intermediate";
    return "Difficulty: basic";
  }
  if (score >= 4) return "Độ khó: nâng cao";
  if (score >= 2) return "Độ khó: trung bình";
  return "Độ khó: cơ bản";
}

function standardSpecs(guide: GuideView, language: "vi" | "en" = "vi") {
  const plant = guide.plant.toLowerCase();
  const groupLabel = language === "en" ? "Crop group" : "Nhóm cây";
  const intervalLabel = language === "en" ? "Check interval" : "Chu kỳ kiểm tra";
  const focusLabel = language === "en" ? "Watch first" : "Ưu tiên theo dõi";
  if (plant.includes("cà phê") || plant.includes("tiêu")) {
    return [
      { label: groupLabel, value: displayFamily(guide.family, language) },
      { label: intervalLabel, value: language === "en" ? "Every 7-10 days" : "7-10 ngày/lần" },
      { label: focusLabel, value: language === "en" ? "Soil moisture, canopy, pests and diseases" : "Ẩm độ đất, tán lá, sâu bệnh" }
    ];
  }
  if (plant.includes("lúa")) {
    return [
      { label: groupLabel, value: displayFamily(guide.family, language) },
      { label: intervalLabel, value: language === "en" ? "Every 3-5 days" : "3-5 ngày/lần" },
      { label: focusLabel, value: language === "en" ? "Water level, planthoppers and leaf diseases" : "Mực nước, rầy, bệnh lá" }
    ];
  }
  return [
    { label: groupLabel, value: displayFamily(guide.family, language) },
    { label: intervalLabel, value: language === "en" ? "Every 5-7 days" : "5-7 ngày/lần" },
    { label: focusLabel, value: language === "en" ? "Canopy, fruit, roots and drainage" : "Tán cây, trái, rễ và thoát nước" }
  ];
}

function relatedSupplies(guide: GuideView, language: "vi" | "en" = "vi") {
  const text = `${guide.title} ${guide.summary} ${guide.content}`.toLowerCase();
  const supplies = new Set<string>();
  if (text.includes("bệnh") || text.includes("disease") || text.includes("nấm") || text.includes("fung") || text.includes("loét")) {
    supplies.add(language === "en" ? "Pest and disease scouting log" : "Bộ test/ghi nhận sâu bệnh");
  }
  if (text.includes("cắt") || text.includes("prun") || text.includes("tỉa") || text.includes("tạo tán")) {
    supplies.add(language === "en" ? "Pruning shears and cut-sanitizing tools" : "Kéo cắt tỉa, dụng cụ vệ sinh vết cắt");
  }
  if (text.includes("tưới") || text.includes("irrig") || text.includes("nước") || text.includes("ẩm")) {
    supplies.add(language === "en" ? "Soil moisture sensor or irrigation log" : "Cảm biến ẩm đất hoặc sổ theo dõi tưới");
  }
  if (text.includes("phun") || text.includes("spray")) {
    supplies.add(language === "en" ? "Sprayer, protective gear and dose label" : "Bình phun, đồ bảo hộ, nhãn ghi liều dùng");
  }
  if (!supplies.size) {
    supplies.add(language === "en" ? "Orchard record book" : "Sổ ghi chép vườn");
    supplies.add(language === "en" ? "Field inspection kit" : "Dụng cụ kiểm tra hiện trường");
  }
  return Array.from(supplies).slice(0, 4);
}

function formatGuideDate(value: string, language: "vi" | "en" = "vi") {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return language === "en" ? "updating" : "đang cập nhật";
  return date.toLocaleDateString(language === "en" ? "en-US" : "vi-VN");
}

function displayFamily(value: string, language: "vi" | "en") {
  if (language !== "en") return value;
  const labels: Record<string, string> = {
    "Cây ăn quả": "Fruit crops",
    "Cây công nghiệp": "Industrial crops",
    "Cây lương thực": "Food crops",
    "Cây trồng khác": "Other crops"
  };
  return labels[value] ?? value;
}

function displayPlant(value: string, language: "vi" | "en") {
  if (language !== "en") return value;
  const labels: Record<string, string> = {
    "Sầu riêng": "Durian",
    "Mít": "Jackfruit",
    "Thanh long": "Dragon fruit",
    "Cam": "Citrus",
    "Xoài": "Mango",
    "Chôm chôm": "Rambutan",
    "Cà phê": "Coffee",
    "Tiêu": "Black pepper",
    "Lúa": "Rice",
    "Ớt": "Chili"
  };
  return labels[value] ?? value;
}

function displaySection(value: string, language: "vi" | "en") {
  if (language !== "en") return value;
  return value === "Chăm sóc" ? "Care" : "Field guide";
}

function guideImageUrl(postId: number, imageIndex: number) {
  return `/api/v1/content/guide-images/${postId}/${imageIndex}`;
}

function normalizeGuideHeading(line: string) {
  if (isGuideHeading(line)) return { text: line, id: guideHeadingId(line) };
  if (!line.startsWith("#")) return null;
  const rawHeading = line
    .replace(/^#{1,6}\s+/, "")
    .trim();
  const heading = rawHeading
    .replace(/^\d+(?:\.\d+)?\.\s*/, "")
    .trim();
  return heading ? { text: heading, id: guideHeadingId(rawHeading) } : null;
}

function isGuideHeading(line: string) {
  return [
    "Mục tiêu",
    "Khi nào áp dụng",
    "Cách làm tại vườn",
    "Theo dõi sau khi làm",
    "Lỗi cần tránh",
    "Ghi chép nên có"
  ].includes(line);
}

function parseTableRow(line: string) {
  return line
    .split("|")
    .map((cell) => cell.trim())
    .filter(Boolean);
}

function renderMarkdownTable(table: string[][], index: number, language: "vi" | "en" = "vi") {
  if (!table.length) return null;
  const [head, ...rows] = table;
  return (
    <div className="guide-markdown-table" key={`table-${index}`}>
      <table>
        <thead>
          <tr>{head.map((cell) => <th key={cell}>{renderInlineMarkdown(cell, language)}</th>)}</tr>
        </thead>
        <tbody>
          {rows.map((row, rowIndex) => (
            <tr key={`${rowIndex}-${row.join("|")}`}>
              {head.map((_, cellIndex) => <td key={cellIndex}>{renderInlineMarkdown(row[cellIndex] ?? "", language)}</td>)}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderInlineMarkdown(text: string, language: "vi" | "en" = "vi") {
  const cleaned = text.replace(/^\[[ xX]\]\s*/, "");
  const parts = cleaned.split(/(\*\*[^*]+\*\*|\[[^\]]+\]\([^)]+\))/g).filter(Boolean);
  return parts.map((part, index) => {
    const link = part.match(/^\[([^\]]+)\]\(([^)]+)\)$/);
    if (link) {
      const [, label, href] = link;
      return href.startsWith("#") ? (
        <a href={href} key={`${part}-${index}`}>{label}</a>
      ) : href.startsWith("/") ? (
        <Link to={withLanguagePrefix(href, language)} key={`${part}-${index}`}>{label}</Link>
      ) : (
        <a href={href} key={`${part}-${index}`} target="_blank" rel="noreferrer">{label}</a>
      );
    }
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    return part;
  });
}

function toGuideView(guide: GuidePost): GuideView {
  const cropMeta = guide.crop_type ? CROP_META[guide.crop_type] : undefined;
  const category = guide.category.toLowerCase();
  const section = category.startsWith("chăm sóc") || category.startsWith("care") ? "Chăm sóc" : "Cẩm nang";
  const plant = cropMeta?.plant ?? plantFromCategory(guide.category, guide.crop_type);
  return {
    ...guide,
    family: cropMeta?.family ?? familyFromPlant(plant),
    plant,
    section
  };
}

function plantFromCategory(category: string, cropType: string | null) {
  const fromCategory = category.replace(/^(Cẩm nang|Chăm sóc|Canh tác)\s+/i, "").trim();
  if (fromCategory && fromCategory !== category) return capitalizeWords(fromCategory);
  if (cropType && CROP_META[cropType]) return CROP_META[cropType].plant;
  if (category.toLowerCase().includes("quản trị")) return "Quản trị trang trại";
  return "Cây trồng";
}

function familyFromPlant(plant: string) {
  const lowered = plant.toLowerCase();
  if (["sầu riêng", "mít", "thanh long", "cam", "xoài", "chôm chôm"].some((item) => lowered.includes(item))) {
    return "Cây ăn quả";
  }
  if (["cà phê", "tiêu"].some((item) => lowered.includes(item))) {
    return "Cây công nghiệp";
  }
  if (lowered.includes("lúa")) {
    return "Cây lương thực";
  }
  return "Cây trồng khác";
}

function capitalizeWords(value: string) {
  return value
    .split(" ")
    .filter(Boolean)
    .map((part) => part.charAt(0).toLocaleUpperCase("vi-VN") + part.slice(1))
    .join(" ");
}

function sortGuides(a: GuideView, b: GuideView) {
  const familyDiff = FAMILY_ORDER.indexOf(a.family) - FAMILY_ORDER.indexOf(b.family);
  if (familyDiff !== 0) return familyDiff;
  const plantDiff = a.plant.localeCompare(b.plant, "vi");
  if (plantDiff !== 0) return plantDiff;
  const sectionDiff = a.section.localeCompare(b.section, "vi");
  if (sectionDiff !== 0) return sectionDiff;
  return a.title.localeCompare(b.title, "vi");
}
