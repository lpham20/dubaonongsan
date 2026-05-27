const baseUrl = (process.env.MARKETAI_SMOKE_BASE_URL || "https://dubaonongsan.com").replace(/\/$/, "");

const routePaths = [
  "/",
  "/tin-tuc",
  "/tin-tuc/gia-sau-rieng",
  "/tin-tuc/gia-ca-phe",
  "/tin-tuc/gia-ho-tieu",
  "/huong-dan",
  "/du-bao-gia/sau_rieng",
  "/du-bao-gia/ca_phe",
  "/du-bao-gia/ho_tieu",
  "/du-bao-gia/lua",
  "/du-bao-gia/phan-bon",
  "/roi-uoc-tinh",
  "/thoi-diem-ban",
  "/chenh-lech-vung",
  "/so-sanh-cay-trong",
  "/khuyen-nghi-bon-phan",
  "/khuyen-nghi-bon-phan/logic",
  "/bao-cao-nang-suat",
  "/thuat-toan-du-bao"
];

const languagePrefixes = ["", "/vn", "/en"];
const failures = [];

for (const prefix of languagePrefixes) {
  for (const path of routePaths) {
    const url = `${baseUrl}${prefix}${path === "/" ? "" : path}`;
    const response = await fetch(url);
    const body = await response.text();
    const okStatus = response.status >= 200 && response.status < 400;
    const okShell = body.includes("<div id=\"root\"></div>") || body.includes("Dự báo nông sản") || body.includes("Agri Price Forecast");
    if (!okStatus || !okShell) {
      failures.push({ url, finalUrl: response.url, status: response.status, okShell });
    }
    console.log(`${response.status} ${url}`);
  }
}

if (failures.length) {
  console.error(JSON.stringify(failures, null, 2));
  process.exit(1);
}
