import {
  BookOpenCheck,
  CalendarClock,
  ChevronRight,
  Clock3,
  FileText,
  Gauge,
  Layers3,
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

type Props = {
  guides: GuidePost[];
};

type GuideView = GuidePost & {
  family: string;
  plant: string;
  section: "Cẩm nang" | "Chăm sóc";
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
    <section className="content-page guide-workspace">
      <SeoHead
        title="Quy trình kỹ thuật trồng sầu riêng, cà phê, hồ tiêu và lúa"
        description="Thư viện hướng dẫn kỹ thuật nông nghiệp: cẩm nang, chăm sóc cây trồng, phòng trừ sâu bệnh và quy trình canh tác dễ tra cứu."
        canonical="/huong-dan"
      />
      <div className="content-hero guide-hero compact-guide-hero">
        <div>
          <span>
            <BookOpenCheck size={18} />
            Hướng dẫn nông nghiệp
          </span>
          <h1>Quy trình kỹ thuật trồng trọt</h1>
          <p>Chọn nhóm cây, chọn cây trồng rồi đọc cẩm nang hoặc quy trình chăm sóc theo từng chủ đề.</p>
        </div>
      </div>

      <div className="guide-mobile-filter-strip" aria-label="Bộ lọc hướng dẫn trên di động">
        <div className="plant-strip">
          {familyStats.map((item) => (
            <button
              type="button"
              className={item.family === currentFamily ? "active" : ""}
              key={item.family}
              onClick={() => {
                setActiveFamily(item.family);
                setActivePlant("");
                setSelectedSlug("");
              }}
            >
              {item.family} <small>({item.count})</small>
            </button>
          ))}
        </div>
        <div className="plant-strip plant-strip-secondary">
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
              {item.plant} <small>({item.count})</small>
            </button>
          ))}
        </div>
      </div>

      <div className="guide-layout">
        <aside className="guide-sidebar">
          <div className="quick-panel">
            <h2>Lối tắt của bạn</h2>
            {familyStats.map((item) => (
              <button
                type="button"
                className={item.family === currentFamily ? "active" : ""}
                key={item.family}
                onClick={() => {
                  setActiveFamily(item.family);
                  setActivePlant("");
                  setSelectedSlug("");
                }}
              >
                <Sprout size={17} />
                <span>{item.family}</span>
                <small>{item.plants} cây</small>
              </button>
            ))}
          </div>
        </aside>

        <div className="guide-main">
          <div className="tech-title">
            <Layers3 size={18} />
            <h2>{currentFamily}</h2>
          </div>

          <div className="family-grid">
            {familyStats.map((item) => (
              <button
                type="button"
                className={`guide-family-card ${item.family === currentFamily ? "active" : ""}`}
                key={item.family}
                onClick={() => {
                  setActiveFamily(item.family);
                  setActivePlant("");
                  setSelectedSlug("");
                }}
              >
                <GuideFamilyArt family={item.family} />
                <strong>{item.family}</strong>
                <span>{item.count} bài kỹ thuật</span>
              </button>
            ))}
          </div>

          <div className="plant-strip">
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
                {item.plant}
                <small>{item.count}</small>
              </button>
            ))}
          </div>

          <div className="guide-browser">
            <aside className="guide-list-panel">
              <div className="guide-filter-tabs">
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
                    {item.section}
                    <small>{item.count}</small>
                  </button>
                ))}
              </div>

              <label className="guide-search">
                <Search size={16} />
                <input
                  value={query}
                  onChange={(event) => {
                    setQuery(event.target.value);
                    setSelectedSlug("");
                  }}
                  placeholder="Tìm bài kỹ thuật"
                />
              </label>

              <div className="guide-list">
                {visibleGuides.map((guide) => (
                  <button
                    type="button"
                    className={guide.slug === selectedGuide?.slug ? "active" : ""}
                    key={guide.slug}
                    onClick={() => setSelectedSlug(guide.slug)}
                  >
                    <FileText size={16} />
                    <span className="guide-list-copy">
                      <strong>{guide.title}</strong>
                      <small>
                        {guide.section} · {guide.plant} · {estimateReadingMinutes(guide.content)} phút đọc
                      </small>
                    </span>
                    <ChevronRight size={15} />
                  </button>
                ))}
                {visibleGuides.length === 0 ? <div className="guide-empty">Không có bài phù hợp.</div> : null}
              </div>
            </aside>

            <article className="guide-detail-panel">
              {selectedGuide ? (
                <>
                  <header className="guide-article-header">
                    <div className="guide-tag-row">
                      <span>{selectedGuide.category}</span>
                      <span>{selectedGuide.family}</span>
                      <span>{selectedGuide.plant}</span>
                    </div>
                    <h2>{selectedGuide.title}</h2>
                    <p>{selectedGuide.summary}</p>
                    <div className="guide-meta-grid">
                      <small>
                        <Clock3 size={15} />
                        {estimateReadingMinutes(selectedGuide.content)} phút đọc
                      </small>
                      <small>
                        <Gauge size={15} />
                        {technicalDifficulty(selectedGuide.content)}
                      </small>
                      <small>
                        <CalendarClock size={15} />
                        Cập nhật {formatGuideDate(selectedGuide.published_at)}
                      </small>
                    </div>
                    <Link className="guide-canonical-link" to={guidePath(selectedGuide.slug)}>
                      Mở trang riêng của bài hướng dẫn
                    </Link>
                  </header>
                  <div className="guide-article-layout">
                    <GuideContent content={selectedGuide.content} postId={selectedGuide.post_id} />
                    <GuideReferencePanel guide={selectedGuide} />
                  </div>
                </>
              ) : (
                <div className="guide-empty">Chọn một cây trồng để xem hướng dẫn.</div>
              )}
            </article>
          </div>
        </div>
      </div>
    </section>
  );
}

function GuideContent({ content, postId }: { content: string; postId: number }) {
  const lines = content
    .split(/\n+/)
    .map((line) => line.trim())
    .filter((line) => line && !line.toLowerCase().startsWith("nguồn"));
  const blocks: { heading: string; body: string[]; bullets: string[]; images: { url: string; index: number }[] }[] = [];
  let current: { heading: string; body: string[]; bullets: string[]; images: { url: string; index: number }[] } | null = null;
  let imageIndex = 0;

  for (const line of lines) {
    if (isGuideHeading(line)) {
      current = { heading: line, body: [], bullets: [], images: [] };
      blocks.push(current);
      continue;
    }
    if (!current) {
      current = { heading: "Ghi chú kỹ thuật", body: [], bullets: [], images: [] };
      blocks.push(current);
    }
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
    <div className="guide-body structured-guide-body">
      {blocks.map((block) => (
        <section key={block.heading}>
          <h3>{block.heading}</h3>
          {block.body.map((line) => (
            <p key={line}>{line}</p>
          ))}
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
                <li key={line}>{line}</li>
              ))}
            </ul>
          ) : null}
        </section>
      ))}
    </div>
  );
}

function GuideReferencePanel({ guide }: { guide: GuideView }) {
  const specs = standardSpecs(guide);
  const supplies = relatedSupplies(guide);

  return (
    <aside className="guide-reference-panel" aria-label="Thông tin tra cứu nhanh">
      <section>
        <div>
          <Ruler size={17} />
          <h3>Thông số tiêu chuẩn</h3>
        </div>
        <dl>
          {specs.map((item) => (
            <div key={item.label}>
              <dt>{item.label}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      </section>

      <section>
        <div>
          <PackageCheck size={17} />
          <h3>Vật tư liên quan</h3>
        </div>
        <ul>
          {supplies.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </section>
    </aside>
  );
}

function estimateReadingMinutes(content: string) {
  const words = content.replace(/IMAGE::\S+/g, "").trim().split(/\s+/).filter(Boolean).length;
  return Math.max(2, Math.ceil(words / 230));
}

function technicalDifficulty(content: string) {
  const normalized = content.toLowerCase();
  const complexSignals = ["phun", "bệnh", "sâu", "liều", "ppm", "nấm", "cắt tỉa", "xử lý"];
  const score = complexSignals.filter((signal) => normalized.includes(signal)).length;
  if (score >= 4) return "Độ khó: nâng cao";
  if (score >= 2) return "Độ khó: trung bình";
  return "Độ khó: cơ bản";
}

function standardSpecs(guide: GuideView) {
  const plant = guide.plant.toLowerCase();
  if (plant.includes("cà phê") || plant.includes("tiêu")) {
    return [
      { label: "Nhóm cây", value: guide.family },
      { label: "Chu kỳ kiểm tra", value: "7-10 ngày/lần" },
      { label: "Ưu tiên theo dõi", value: "Ẩm độ đất, tán lá, sâu bệnh" }
    ];
  }
  if (plant.includes("lúa")) {
    return [
      { label: "Nhóm cây", value: guide.family },
      { label: "Chu kỳ kiểm tra", value: "3-5 ngày/lần" },
      { label: "Ưu tiên theo dõi", value: "Mực nước, rầy, bệnh lá" }
    ];
  }
  return [
    { label: "Nhóm cây", value: guide.family },
    { label: "Chu kỳ kiểm tra", value: "5-7 ngày/lần" },
    { label: "Ưu tiên theo dõi", value: "Tán cây, trái, rễ và thoát nước" }
  ];
}

function relatedSupplies(guide: GuideView) {
  const text = `${guide.title} ${guide.summary} ${guide.content}`.toLowerCase();
  const supplies = new Set<string>();
  if (text.includes("bệnh") || text.includes("nấm") || text.includes("loét")) supplies.add("Bộ test/ghi nhận sâu bệnh");
  if (text.includes("cắt") || text.includes("tỉa") || text.includes("tạo tán")) supplies.add("Kéo cắt tỉa, dụng cụ vệ sinh vết cắt");
  if (text.includes("tưới") || text.includes("nước") || text.includes("ẩm")) supplies.add("Cảm biến ẩm đất hoặc sổ theo dõi tưới");
  if (text.includes("phun")) supplies.add("Bình phun, đồ bảo hộ, nhãn ghi liều dùng");
  if (!supplies.size) {
    supplies.add("Sổ ghi chép vườn");
    supplies.add("Dụng cụ kiểm tra hiện trường");
  }
  return Array.from(supplies).slice(0, 4);
}

function formatGuideDate(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "đang cập nhật";
  return date.toLocaleDateString("vi-VN");
}

function guideImageUrl(postId: number, imageIndex: number) {
  return `/api/v1/content/guide-images/${postId}/${imageIndex}`;
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

function GuideFamilyArt({ family }: { family: string }) {
  const image = familyImage(family);
  return (
    <div className={`guide-family-art ${familyClass(family)}`} aria-hidden="true">
      {image ? <img src={image} alt={`Ảnh danh mục hướng dẫn ${family}`} loading="lazy" decoding="async" width="220" height="160" /> : null}
    </div>
  );
}

function toGuideView(guide: GuidePost): GuideView {
  const cropMeta = guide.crop_type ? CROP_META[guide.crop_type] : undefined;
  const section = guide.category.toLowerCase().startsWith("chăm sóc") ? "Chăm sóc" : "Cẩm nang";
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

function familyClass(family: string) {
  if (family === "Cây ăn quả") return "fruit";
  if (family === "Cây công nghiệp") return "industrial";
  if (family === "Cây lương thực") return "food";
  return "other";
}

function familyImage(family: string) {
  if (family === "Cây ăn quả") return "/guide-fruit-optimized.jpg";
  if (family === "Cây công nghiệp") return "/guide-industrial-optimized.jpg";
  if (family === "Cây lương thực") return "/guide-food-crop-optimized.jpg";
  return "/guide-other-optimized.jpg";
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
